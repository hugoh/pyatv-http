from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from pyatv.const import PowerState
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from pyatv_http import __version__, atv
from pyatv_http.atv import DeviceUnreachableError
from pyatv_http.auth import require_token
from pyatv_http.config import AppConfig
from pyatv_http.stats import StatsStore

TEMPLATES_DIR = Path(__file__).parent / "templates"


class PowerStateRequest(BaseModel):
    power_state: Literal["on", "off"]
    # Auth fallback for POST-only clients, per RFC 6750 section 2.2;
    # consumed by require_token's dependency, not by the route handler.
    # Ignored on PUT (header required).
    access_token: str | None = None


def create_app(config: AppConfig) -> FastAPI:
    # No app-wide auth dependency: it lives on protected_router below instead,
    # so public routes stay plain FastAPI routes (and so show up in /docs)
    # rather than needing to bypass a global dependency via add_route.
    app = FastAPI(
        title="pyatv-http",
        description="HTTP interface for controlling Apple TVs via pyatv",
        version=__version__,
        contact={
            "name": "GitHub repository",
            "url": "https://github.com/hugoh/pyatv-http",
        },
        license_info={
            "name": "MIT",
            "url": "https://github.com/hugoh/pyatv-http/blob/main/LICENSE",
        },
    )
    public_router = APIRouter()
    protected_router = APIRouter(dependencies=[Depends(require_token(config))])

    stats = StatsStore(config.status_history_size) if config.status_enabled else None

    @app.middleware("http")
    async def _add_version_header(request: Request, call_next):
        response = await call_next(request)
        response.headers["App-Version"] = __version__
        return response

    @public_router.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @public_router.get("/devices", tags=["devices"])
    async def list_devices() -> list[dict[str, str]]:
        return [
            {"device": device.key, "name": device.name}
            for device in sorted(config.devices.values(), key=lambda d: d.key)
        ]

    if stats is not None:
        templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

        def _split_totals() -> tuple[dict[str, dict[str, int]], dict[str, int]]:
            totals = stats.totals()
            global_totals = totals.pop("_global")
            return totals, global_totals

        @public_router.get("/status", response_class=HTMLResponse, tags=["status"])
        async def status_page(request: Request) -> HTMLResponse:
            totals, global_totals = _split_totals()
            return templates.TemplateResponse(
                request,
                "status.html",
                {
                    "version": __version__,
                    "devices": sorted(config.devices.values(), key=lambda d: d.key),
                    "totals": totals,
                    "global_totals": global_totals,
                    "recent": stats.recent(),
                },
            )

        @public_router.get("/stats", tags=["status"])
        async def stats_json() -> dict:
            totals, global_totals = _split_totals()
            return {
                "totals": totals,
                "global_totals": global_totals,
                "recent": [
                    {
                        "timestamp": record.timestamp.isoformat(),
                        "device": record.device,
                        "command": record.command,
                        "ok": record.ok,
                        "detail": record.detail,
                    }
                    for record in stats.recent()
                ],
            }

    def _get_device(name: str):
        device = config.get_device(name)
        if device is None:
            raise HTTPException(status_code=404, detail=f"unknown device: {name}")
        return device

    async def _run_atv_command(
        device_name: str, command: str, coro: Callable[[], Awaitable[PowerState]]
    ) -> PowerState:
        try:
            state = await coro()
        except DeviceUnreachableError as exc:
            if stats is not None:
                stats.record(device_name, command, ok=False, detail=str(exc))
            raise HTTPException(status_code=504, detail=str(exc)) from exc
        except Exception as exc:
            if stats is not None:
                stats.record(device_name, command, ok=False, detail=str(exc))
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        if stats is not None:
            stats.record(device_name, command, ok=True, detail=state.name.lower())
        return state

    async def _set_power_state(name: str, desired: PowerState) -> dict[str, str]:
        device = _get_device(name)
        loop = asyncio.get_running_loop()
        state = await _run_atv_command(
            name,
            "set_power_state",
            lambda: atv.set_power_state(loop, device, desired),
        )
        return {"device": name, "power_state": state.name.lower()}

    @protected_router.put("/{name}/power-state", tags=["power-state"])
    @protected_router.post("/{name}/power-state", tags=["power-state"])
    async def set_power_state_route(
        name: str, body: PowerStateRequest
    ) -> dict[str, str]:
        desired = PowerState.On if body.power_state == "on" else PowerState.Off
        return await _set_power_state(name, desired)

    @protected_router.get("/{name}/power-state", tags=["power-state"])
    async def power_state(
        name: str,
        # Auth fallback for GET-only clients, per RFC 6750 section 2.3;
        # consumed by require_token's dependency, exposed here only for
        # OpenAPI/Swagger visibility.
        access_token: str | None = None,
    ) -> dict[str, str]:
        device = _get_device(name)
        loop = asyncio.get_running_loop()
        state = await _run_atv_command(
            name, "get_power_state", lambda: atv.get_power_state(loop, device)
        )
        return {"device": name, "power_state": state.name.lower()}

    app.include_router(public_router)
    app.include_router(protected_router)

    return app

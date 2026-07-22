from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from pyatv.const import PowerState
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse

from pyatv_http import atv
from pyatv_http.atv import DeviceUnreachableError
from pyatv_http.auth import require_token
from pyatv_http.config import AppConfig


async def _health(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


class PowerStateRequest(BaseModel):
    power_state: Literal["on", "off"]


def create_app(config: AppConfig) -> FastAPI:
    app = FastAPI(dependencies=[Depends(require_token(config))])

    # Added as a raw Starlette route (like FastAPI's own /docs, /openapi.json)
    # so it bypasses the app-wide bearer-token dependency above -- health
    # probes (load balancers, uptime checks) shouldn't need a token.
    app.add_route("/health", _health, methods=["GET"])

    def _get_device(name: str):
        device = config.get_device(name)
        if device is None:
            raise HTTPException(status_code=404, detail=f"unknown device: {name}")
        return device

    async def _set_power_state(name: str, desired: PowerState) -> dict[str, str]:
        device = _get_device(name)
        loop = asyncio.get_running_loop()
        try:
            state = await atv.set_power_state(loop, device, desired)
        except DeviceUnreachableError as exc:
            raise HTTPException(status_code=504, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return {"device": name, "power_state": state.name.lower()}

    @app.put("/{name}/power-state")
    @app.post("/{name}/power-state")
    async def set_power_state_route(
        name: str, body: PowerStateRequest
    ) -> dict[str, str]:
        desired = PowerState.On if body.power_state == "on" else PowerState.Off
        return await _set_power_state(name, desired)

    @app.get("/{name}/power-state")
    async def power_state(name: str) -> dict[str, str]:
        device = _get_device(name)
        loop = asyncio.get_running_loop()
        try:
            state = await atv.get_power_state(loop, device)
        except DeviceUnreachableError as exc:
            raise HTTPException(status_code=504, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return {"device": name, "power_state": state.name.lower()}

    @app.get("/devices")
    async def list_devices() -> list[dict[str, str]]:
        return [
            {"device": device.key, "name": device.name}
            for device in sorted(config.devices.values(), key=lambda d: d.key)
        ]

    return app

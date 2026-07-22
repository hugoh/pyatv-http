from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.requests import Request

from pyatv_http.config import AppConfig

_bearer_scheme = HTTPBearer(auto_error=False)


def require_token(config: AppConfig):
    async def _verify(
        request: Request,
        credentials: Annotated[
            HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
        ] = None,
    ) -> None:
        if credentials is not None and credentials.credentials in config.auth_tokens:
            return

        # Fallback for clients that can't set an Authorization header (e.g.
        # home-automation rule engines limited to GET/POST): accept the
        # token in-band instead. Not offered for PUT -- that's the strict,
        # header-only path for clients capable of setting one.
        token: str | None = None
        if request.method == "GET":
            token = request.query_params.get("token")
        elif request.method == "POST":
            try:
                body = await request.json()
            except ValueError:
                body = None
            if isinstance(body, dict):
                token = body.get("token")

        if token is not None and token in config.auth_tokens:
            return

        raise HTTPException(
            status_code=401,
            detail="missing or invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _verify

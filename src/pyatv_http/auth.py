from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from pyatv_http.config import AppConfig

_bearer_scheme = HTTPBearer(auto_error=False)


def require_token(config: AppConfig):
    def _verify(
        credentials: Annotated[
            HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
        ] = None,
    ) -> None:
        if credentials is None or credentials.credentials not in config.auth_tokens:
            raise HTTPException(
                status_code=401,
                detail="missing or invalid bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return _verify

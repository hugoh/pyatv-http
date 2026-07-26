"""Dump the FastAPI app's OpenAPI schema to stdout, for CI doc generation.

Run with: uv run python scripts/export_openapi.py > openapi.json
"""

import json
import sys

from pyatv_http.app import create_app
from pyatv_http.config import AppConfig, DeviceConfig


def _placeholder_config() -> AppConfig:
    device = DeviceConfig(
        key="living_room",
        name="Living Room",
        address="10.0.0.5",
        identifier="AA:BB:CC:DD:EE:FF",
    )
    return AppConfig(
        port=8080,
        devices={"living_room": device},
        auth_tokens=frozenset({"placeholder"}),
        status_enabled=True,
    )


def main() -> None:
    app = create_app(_placeholder_config())
    json.dump(app.openapi(), sys.stdout, indent=2)


if __name__ == "__main__":
    main()

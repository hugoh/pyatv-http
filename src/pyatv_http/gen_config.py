from __future__ import annotations

import asyncio
from pathlib import Path

from pyatv.settings import Settings
from pyatv.storage.file_storage import FileStorage

PROTOCOL_NAMES = ("airplay", "companion", "dmap", "mrp", "raop")


class DeviceNotFoundError(Exception):
    """Raised when no stored device matches the given identifier."""


def _escape_toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _toml_string(value: str) -> str:
    return f'"{_escape_toml_string(value)}"'


def _settings_identifiers(settings: Settings) -> set[str]:
    identifiers = set()
    for proto_name in PROTOCOL_NAMES:
        proto_identifier = getattr(settings.protocols, proto_name).identifier
        if proto_identifier is not None:
            identifiers.add(proto_identifier)
    return identifiers


def _find_settings(devices: list[Settings], identifier: str) -> Settings | None:
    for settings in devices:
        if identifier in _settings_identifiers(settings):
            return settings
    return None


def render_toml_block(
    *,
    key: str,
    name: str,
    address: str,
    identifier: str,
    protocols: dict[str, dict[str, str | None]],
) -> str:
    lines = [
        f"[devices.{key}]",
        f"name = {_toml_string(name)}",
        f"identifier = {_toml_string(identifier)}",
        f"address = {_toml_string(address)}",
    ]

    for proto_name in PROTOCOL_NAMES:
        proto = protocols.get(proto_name)
        if not proto:
            continue
        if not proto.get("identifier") and not proto.get("credentials"):
            continue

        lines.append("")
        lines.append(f"[devices.{key}.protocols.{proto_name}]")
        for field_name in ("identifier", "credentials", "password"):
            value = proto.get(field_name)
            if value is not None:
                lines.append(f"{field_name} = {_toml_string(value)}")

    return "\n".join(lines) + "\n"


async def generate_config_block(
    *,
    storage_path: str | Path,
    identifier: str,
    key: str,
    name: str | None,
    address: str,
) -> str:
    loop = asyncio.get_running_loop()
    storage = FileStorage(str(storage_path), loop)
    await storage.load()

    devices = list(storage.settings)
    settings = _find_settings(devices, identifier)
    if settings is None:
        available = sorted(
            {i for device in devices for i in _settings_identifiers(device)}
        )
        raise DeviceNotFoundError(
            f"no paired device found with identifier '{identifier}'. "
            f"Available identifiers: {available}"
        )

    protocols = {
        proto_name: dict(getattr(settings.protocols, proto_name))
        for proto_name in PROTOCOL_NAMES
    }

    return render_toml_block(
        key=key,
        name=name or key,
        address=address,
        identifier=identifier,
        protocols=protocols,
    )

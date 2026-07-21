from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

KNOWN_PROTOCOLS = frozenset({"airplay", "companion", "dmap", "mrp", "raop"})


class ConfigError(Exception):
    """Raised when the config file is missing or invalid."""


@dataclass(frozen=True)
class ProtocolCredential:
    identifier: str | None = None
    credentials: str | None = None
    password: str | None = None


@dataclass(frozen=True)
class DeviceConfig:
    key: str
    name: str
    address: str
    identifier: str
    protocols: dict[str, ProtocolCredential] = field(default_factory=dict)


@dataclass(frozen=True)
class AppConfig:
    port: int
    devices: dict[str, DeviceConfig]
    auth_tokens: frozenset[str]

    def get_device(self, key: str) -> DeviceConfig | None:
        return self.devices.get(key)


def _parse_protocol(device_key: str, proto_name: str, raw: dict) -> ProtocolCredential:
    if proto_name not in KNOWN_PROTOCOLS:
        raise ConfigError(
            f"devices.{device_key}.protocols.{proto_name}: unknown protocol "
            f"(expected one of {sorted(KNOWN_PROTOCOLS)})"
        )
    return ProtocolCredential(
        identifier=raw.get("identifier"),
        credentials=raw.get("credentials"),
        password=raw.get("password"),
    )


def _parse_device(key: str, raw: dict) -> DeviceConfig:
    name = raw.get("name")
    if not name:
        raise ConfigError(f"devices.{key}: missing required field 'name'")

    identifier = raw.get("identifier")
    if not identifier:
        raise ConfigError(f"devices.{key}: missing required field 'identifier'")

    address = raw.get("address")
    if not address:
        raise ConfigError(f"devices.{key}: missing required field 'address'")

    raw_protocols = raw.get("protocols", {})
    protocols = {
        proto_name: _parse_protocol(key, proto_name, proto_raw)
        for proto_name, proto_raw in raw_protocols.items()
    }

    return DeviceConfig(
        key=key,
        name=name,
        address=address,
        identifier=identifier,
        protocols=protocols,
    )


def _parse_auth_tokens(data: dict) -> frozenset[str]:
    raw_auth = data.get("auth")
    if not raw_auth:
        raise ConfigError("missing or empty required table 'auth'")

    tokens = raw_auth.get("tokens")
    if not tokens:
        raise ConfigError("missing or empty required field 'auth.tokens'")

    return frozenset(tokens)


def load_config(path: str | Path) -> AppConfig:
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"config file not found: {path}")

    data = tomllib.loads(path.read_text())

    port = data.get("port")
    if not isinstance(port, int):
        raise ConfigError("missing or invalid required field 'port'")

    raw_devices = data.get("devices")
    if not raw_devices:
        raise ConfigError("missing or empty required table 'devices'")

    devices = {
        key: _parse_device(key, raw_device) for key, raw_device in raw_devices.items()
    }

    auth_tokens = _parse_auth_tokens(data)

    return AppConfig(port=port, devices=devices, auth_tokens=auth_tokens)

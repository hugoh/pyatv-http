import pytest

from pyatv_http.config import ConfigError, load_config

PORT_LINE = "port = 8080\n"
AUTH_BLOCK = """
[auth]
tokens = ["token-a", "token-b"]
"""

VALID_CONFIG = (
    PORT_LINE
    + AUTH_BLOCK
    + """
[devices.living_room]
name = "Living Room"
identifier = "AA:BB:CC:DD:EE:FF"
address = "10.0.0.5"

[devices.living_room.protocols.airplay]
identifier = "AA:BB:CC:DD:EE:FF"
credentials = "airplay-creds"

[devices.living_room.protocols.companion]
identifier = "11:22:33:44:55:66"
credentials = "companion-creds"
"""
)


def test_loads_port_and_device(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(VALID_CONFIG)

    config = load_config(path)

    assert config.port == 8080
    device = config.get_device("living_room")
    assert device is not None
    assert device.key == "living_room"
    assert device.name == "Living Room"
    assert device.address == "10.0.0.5"
    assert device.identifier == "AA:BB:CC:DD:EE:FF"


def test_loads_protocol_credentials(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(VALID_CONFIG)

    config = load_config(path)
    device = config.get_device("living_room")

    assert device is not None
    assert device.protocols["airplay"].identifier == "AA:BB:CC:DD:EE:FF"
    assert device.protocols["airplay"].credentials == "airplay-creds"
    assert device.protocols["companion"].identifier == "11:22:33:44:55:66"
    assert device.protocols["companion"].credentials == "companion-creds"


def test_loads_auth_tokens(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(VALID_CONFIG)

    config = load_config(path)

    assert config.auth_tokens == frozenset({"token-a", "token-b"})


def test_unknown_device_key_returns_none(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(VALID_CONFIG)

    config = load_config(path)

    assert config.get_device("bedroom") is None


def test_missing_port_raises(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        AUTH_BLOCK
        + """
[devices.living_room]
name = "Living Room"
identifier = "AA:BB:CC:DD:EE:FF"
address = "10.0.0.5"
"""
    )

    with pytest.raises(ConfigError, match="port"):
        load_config(path)


def test_missing_devices_raises(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(PORT_LINE + AUTH_BLOCK)

    with pytest.raises(ConfigError, match="devices"):
        load_config(path)


def test_device_missing_identifier_raises(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        PORT_LINE
        + AUTH_BLOCK
        + """
[devices.living_room]
name = "Living Room"
address = "10.0.0.5"
"""
    )

    with pytest.raises(ConfigError, match="identifier"):
        load_config(path)


def test_device_missing_address_raises(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        PORT_LINE
        + AUTH_BLOCK
        + """
[devices.living_room]
name = "Living Room"
identifier = "AA:BB:CC:DD:EE:FF"
"""
    )

    with pytest.raises(ConfigError, match="address"):
        load_config(path)


def test_unknown_protocol_raises(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        PORT_LINE
        + AUTH_BLOCK
        + """
[devices.living_room]
name = "Living Room"
identifier = "AA:BB:CC:DD:EE:FF"
address = "10.0.0.5"

[devices.living_room.protocols.bogus]
identifier = "x"
credentials = "y"
"""
    )

    with pytest.raises(ConfigError, match="bogus"):
        load_config(path)


def test_missing_auth_section_raises(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        PORT_LINE
        + """
[devices.living_room]
name = "Living Room"
identifier = "AA:BB:CC:DD:EE:FF"
address = "10.0.0.5"
"""
    )

    with pytest.raises(ConfigError, match="auth"):
        load_config(path)


def test_empty_auth_tokens_raises(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        PORT_LINE
        + """
[auth]
tokens = []

[devices.living_room]
name = "Living Room"
identifier = "AA:BB:CC:DD:EE:FF"
address = "10.0.0.5"
"""
    )

    with pytest.raises(ConfigError, match="auth"):
        load_config(path)


def test_file_not_found_raises(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "missing.toml")

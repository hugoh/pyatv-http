import json

import pytest

from pyatv_http.gen_config import (
    DeviceNotFoundError,
    generate_config_block,
    render_toml_block,
)

STORAGE_DATA = {
    "version": 1,
    "devices": [
        {
            "protocols": {
                "airplay": {
                    "identifier": "AA:BB:CC:DD:EE:FF",
                    "credentials": "airplay-creds",
                },
                "companion": {
                    "identifier": "11:22:33:44:55:66",
                    "credentials": "companion-creds",
                },
            }
        },
        {
            "protocols": {
                "mrp": {
                    "identifier": "77:88:99:00:11:22",
                    "credentials": "mrp-creds",
                }
            }
        },
    ],
}


@pytest.fixture
def storage_file(tmp_path):
    path = tmp_path / "pyatv.conf"
    path.write_text(json.dumps(STORAGE_DATA))
    return path


def test_render_toml_block_includes_name_identifier_address():
    block = render_toml_block(
        key="living_room",
        name="Living Room",
        address="10.0.0.5",
        identifier="AA:BB:CC:DD:EE:FF",
        protocols={
            "airplay": {"identifier": "AA:BB:CC:DD:EE:FF", "credentials": "creds"},
        },
    )

    assert "[devices.living_room]" in block
    assert 'name = "Living Room"' in block
    assert 'identifier = "AA:BB:CC:DD:EE:FF"' in block
    assert 'address = "10.0.0.5"' in block
    assert "[devices.living_room.protocols.airplay]" in block
    assert 'credentials = "creds"' in block


def test_render_toml_block_omits_empty_protocols():
    block = render_toml_block(
        key="living_room",
        name="Living Room",
        address="10.0.0.5",
        identifier="AA:BB:CC:DD:EE:FF",
        protocols={
            "airplay": {"identifier": "AA:BB:CC:DD:EE:FF", "credentials": "creds"},
            "dmap": {"identifier": None, "credentials": None},
        },
    )

    assert "dmap" not in block


def test_render_toml_block_escapes_quotes_and_backslashes():
    block = render_toml_block(
        key="k",
        name='We"ird\\Name',
        address="10.0.0.5",
        identifier="id",
        protocols={},
    )

    assert 'name = "We\\"ird\\\\Name"' in block


async def test_generate_config_block_finds_device_by_airplay_identifier(storage_file):
    block = await generate_config_block(
        storage_path=storage_file,
        identifier="AA:BB:CC:DD:EE:FF",
        key="living_room",
        name="Living Room",
        address="10.0.0.5",
    )

    assert "[devices.living_room]" in block
    assert 'identifier = "AA:BB:CC:DD:EE:FF"' in block
    assert "[devices.living_room.protocols.companion]" in block
    assert 'credentials = "companion-creds"' in block


async def test_generate_config_block_finds_device_by_mrp_identifier(storage_file):
    block = await generate_config_block(
        storage_path=storage_file,
        identifier="77:88:99:00:11:22",
        key="bedroom",
        name="Bedroom",
        address="10.0.0.6",
    )

    assert "[devices.bedroom.protocols.mrp]" in block
    assert 'credentials = "mrp-creds"' in block


async def test_generate_config_block_defaults_name_to_key(storage_file):
    block = await generate_config_block(
        storage_path=storage_file,
        identifier="AA:BB:CC:DD:EE:FF",
        key="living_room",
        name=None,
        address="10.0.0.5",
    )

    assert 'name = "living_room"' in block


async def test_generate_config_block_unknown_identifier_lists_available(storage_file):
    with pytest.raises(DeviceNotFoundError) as exc_info:
        await generate_config_block(
            storage_path=storage_file,
            identifier="not-a-real-id",
            key="living_room",
            name=None,
            address="10.0.0.5",
        )

    message = str(exc_info.value)
    assert "AA:BB:CC:DD:EE:FF" in message
    assert "77:88:99:00:11:22" in message


async def test_generate_config_block_missing_storage_file_raises(tmp_path):
    with pytest.raises(DeviceNotFoundError):
        await generate_config_block(
            storage_path=tmp_path / "missing.conf",
            identifier="AA:BB:CC:DD:EE:FF",
            key="living_room",
            name=None,
            address="10.0.0.5",
        )

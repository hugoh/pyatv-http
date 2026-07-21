import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pyatv.const import PowerState

from pyatv_http.atv import (
    DeviceUnreachableError,
    connect,
    get_power_state,
    set_power_state,
)
from pyatv_http.config import DeviceConfig, ProtocolCredential


def make_device(
    key: str = "living_room",
    name: str = "Living Room",
    address: str = "10.0.0.5",
    identifier: str = "AA:BB:CC:DD:EE:FF",
    protocols: dict[str, ProtocolCredential] | None = None,
) -> DeviceConfig:
    if protocols is None:
        protocols = {
            "airplay": ProtocolCredential(
                identifier="AA:BB:CC:DD:EE:FF", credentials="creds"
            )
        }
    return DeviceConfig(
        key=key, name=name, address=address, identifier=identifier, protocols=protocols
    )


def make_mock_atv(power_state: PowerState):
    atv = MagicMock()
    atv.power.power_state = power_state
    atv.power.turn_on = AsyncMock()
    atv.power.turn_off = AsyncMock()
    atv.close = MagicMock()
    return atv


async def test_connect_raises_when_device_not_found():
    device = make_device()
    loop = asyncio.get_running_loop()

    with (
        patch("pyatv_http.atv.pyatv.scan", new=AsyncMock(return_value=[])),
        pytest.raises(DeviceUnreachableError),
    ):
        await connect(loop, device)


async def test_connect_returns_connected_atv():
    device = make_device()
    loop = asyncio.get_running_loop()
    scanned_config = MagicMock()
    mock_atv = make_mock_atv(PowerState.Off)

    with (
        patch(
            "pyatv_http.atv.pyatv.scan", new=AsyncMock(return_value=[scanned_config])
        ),
        patch("pyatv_http.atv.pyatv.connect", new=AsyncMock(return_value=mock_atv)),
    ):
        result = await connect(loop, device)

    assert result is mock_atv


async def test_get_power_state_returns_current_state_without_changing_it():
    device = make_device()
    loop = asyncio.get_running_loop()
    scanned_config = MagicMock()
    mock_atv = make_mock_atv(PowerState.On)

    with (
        patch(
            "pyatv_http.atv.pyatv.scan", new=AsyncMock(return_value=[scanned_config])
        ),
        patch("pyatv_http.atv.pyatv.connect", new=AsyncMock(return_value=mock_atv)),
    ):
        result = await get_power_state(loop, device)

    assert result == PowerState.On
    mock_atv.power.turn_on.assert_not_awaited()
    mock_atv.power.turn_off.assert_not_awaited()
    mock_atv.close.assert_called_once()


async def test_get_power_state_raises_when_device_not_found():
    device = make_device()
    loop = asyncio.get_running_loop()

    with (
        patch("pyatv_http.atv.pyatv.scan", new=AsyncMock(return_value=[])),
        pytest.raises(DeviceUnreachableError),
    ):
        await get_power_state(loop, device)


async def test_set_power_state_turns_on_when_off():
    device = make_device()
    loop = asyncio.get_running_loop()
    scanned_config = MagicMock()
    mock_atv = make_mock_atv(PowerState.Off)

    with (
        patch(
            "pyatv_http.atv.pyatv.scan", new=AsyncMock(return_value=[scanned_config])
        ),
        patch("pyatv_http.atv.pyatv.connect", new=AsyncMock(return_value=mock_atv)),
    ):
        result = await set_power_state(loop, device, PowerState.On)

    mock_atv.power.turn_on.assert_awaited_once_with(await_new_state=False)
    mock_atv.power.turn_off.assert_not_awaited()
    mock_atv.close.assert_called_once()
    assert result == PowerState.On


async def test_set_power_state_turns_off_when_on():
    device = make_device()
    loop = asyncio.get_running_loop()
    scanned_config = MagicMock()
    mock_atv = make_mock_atv(PowerState.On)

    with (
        patch(
            "pyatv_http.atv.pyatv.scan", new=AsyncMock(return_value=[scanned_config])
        ),
        patch("pyatv_http.atv.pyatv.connect", new=AsyncMock(return_value=mock_atv)),
    ):
        result = await set_power_state(loop, device, PowerState.Off)

    mock_atv.power.turn_off.assert_awaited_once_with(await_new_state=False)
    mock_atv.power.turn_on.assert_not_awaited()
    assert result == PowerState.Off


async def test_set_power_state_is_noop_when_already_desired_state():
    device = make_device()
    loop = asyncio.get_running_loop()
    scanned_config = MagicMock()
    mock_atv = make_mock_atv(PowerState.On)

    with (
        patch(
            "pyatv_http.atv.pyatv.scan", new=AsyncMock(return_value=[scanned_config])
        ),
        patch("pyatv_http.atv.pyatv.connect", new=AsyncMock(return_value=mock_atv)),
    ):
        result = await set_power_state(loop, device, PowerState.On)

    mock_atv.power.turn_on.assert_not_awaited()
    mock_atv.power.turn_off.assert_not_awaited()
    mock_atv.close.assert_called_once()
    assert result == PowerState.On


async def test_set_power_state_closes_connection_on_error():
    device = make_device()
    loop = asyncio.get_running_loop()
    scanned_config = MagicMock()
    mock_atv = make_mock_atv(PowerState.Off)
    mock_atv.power.turn_on.side_effect = RuntimeError("boom")

    with (
        patch(
            "pyatv_http.atv.pyatv.scan", new=AsyncMock(return_value=[scanned_config])
        ),
        patch("pyatv_http.atv.pyatv.connect", new=AsyncMock(return_value=mock_atv)),
        pytest.raises(RuntimeError),
    ):
        await set_power_state(loop, device, PowerState.On)

    mock_atv.close.assert_called_once()

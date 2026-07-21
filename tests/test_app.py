from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from pyatv.const import PowerState

from pyatv_http.app import create_app
from pyatv_http.atv import DeviceUnreachableError
from pyatv_http.config import AppConfig, DeviceConfig

VALID_TOKEN = "test-token"


def make_config():
    device = DeviceConfig(
        key="living_room",
        name="Living Room",
        address="10.0.0.5",
        identifier="AA:BB:CC:DD:EE:FF",
        protocols={},
    )
    bedroom = DeviceConfig(
        key="bedroom",
        name="Bedroom",
        address="10.0.0.6",
        identifier="11:22:33:44:55:66",
        protocols={},
    )
    return AppConfig(
        port=8080,
        devices={"living_room": device, "bedroom": bedroom},
        auth_tokens=frozenset({VALID_TOKEN}),
    )


@pytest.fixture
async def client():
    app = create_app(make_config())
    transport = ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {VALID_TOKEN}"}
    async with AsyncClient(
        transport=transport, base_url="http://test", headers=headers
    ) as client:
        yield client


@pytest.fixture
async def unauthenticated_client():
    app = create_app(make_config())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_turn_on_returns_power_state(client):
    with patch(
        "pyatv_http.app.atv.set_power_state",
        new=AsyncMock(return_value=PowerState.On),
    ) as mock_set:
        response = await client.post("/living_room/turnOn")

    assert response.status_code == 200
    assert response.json() == {"device": "living_room", "power_state": "on"}
    assert mock_set.await_args is not None
    assert mock_set.await_args.args[2] == PowerState.On


async def test_turn_off_returns_power_state(client):
    with patch(
        "pyatv_http.app.atv.set_power_state",
        new=AsyncMock(return_value=PowerState.Off),
    ) as mock_set:
        response = await client.post("/living_room/turnOff")

    assert response.status_code == 200
    assert response.json() == {"device": "living_room", "power_state": "off"}
    assert mock_set.await_args is not None
    assert mock_set.await_args.args[2] == PowerState.Off


async def test_turn_on_unknown_device_returns_404(client):
    response = await client.post("/attic/turnOn")

    assert response.status_code == 404


async def test_unreachable_device_returns_504(client):
    with patch(
        "pyatv_http.app.atv.set_power_state",
        new=AsyncMock(side_effect=DeviceUnreachableError("nope")),
    ):
        response = await client.post("/living_room/turnOn")

    assert response.status_code == 504


async def test_other_atv_error_returns_502(client):
    with patch(
        "pyatv_http.app.atv.set_power_state",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        response = await client.post("/living_room/turnOn")

    assert response.status_code == 502


async def test_get_power_state_returns_current_state(client):
    with patch(
        "pyatv_http.app.atv.get_power_state",
        new=AsyncMock(return_value=PowerState.On),
    ) as mock_get:
        response = await client.get("/living_room/powerState")

    assert response.status_code == 200
    assert response.json() == {"device": "living_room", "power_state": "on"}
    assert mock_get.await_args is not None


async def test_get_power_state_unknown_device_returns_404(client):
    response = await client.get("/attic/powerState")

    assert response.status_code == 404


async def test_get_power_state_unreachable_returns_504(client):
    with patch(
        "pyatv_http.app.atv.get_power_state",
        new=AsyncMock(side_effect=DeviceUnreachableError("nope")),
    ):
        response = await client.get("/living_room/powerState")

    assert response.status_code == 504


async def test_list_devices_returns_configured_devices(client):
    response = await client.get("/devices")

    assert response.status_code == 200
    assert response.json() == [
        {"device": "bedroom", "name": "Bedroom"},
        {"device": "living_room", "name": "Living Room"},
    ]


async def test_requests_without_token_are_rejected(unauthenticated_client):
    response = await unauthenticated_client.post("/living_room/turnOn")

    assert response.status_code == 401


async def test_devices_without_token_are_rejected(unauthenticated_client):
    response = await unauthenticated_client.get("/devices")

    assert response.status_code == 401


async def test_power_state_without_token_are_rejected(unauthenticated_client):
    response = await unauthenticated_client.get("/living_room/powerState")

    assert response.status_code == 401


async def test_requests_with_wrong_token_are_rejected(unauthenticated_client):
    response = await unauthenticated_client.post(
        "/living_room/turnOn", headers={"Authorization": "Bearer wrong-token"}
    )

    assert response.status_code == 401

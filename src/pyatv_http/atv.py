from __future__ import annotations

import asyncio

import pyatv
from pyatv.const import PowerState
from pyatv.interface import AppleTV
from pyatv.settings import (
    AirPlaySettings,
    CompanionSettings,
    DmapSettings,
    MrpSettings,
    ProtocolSettings,
    RaopSettings,
    Settings,
)
from pyatv.storage import MODEL_VERSION, StorageModel
from pyatv.storage.memory_storage import MemoryStorage

from pyatv_http.config import DeviceConfig, ProtocolCredential

SCAN_TIMEOUT_SECONDS = 5


class DeviceUnreachableError(Exception):
    """Raised when the Apple TV cannot be found on the network."""


def _protocol_settings(
    device: DeviceConfig,
) -> dict[
    str, AirPlaySettings | CompanionSettings | DmapSettings | MrpSettings | RaopSettings
]:
    empty = ProtocolCredential()
    airplay = device.protocols.get("airplay", empty)
    companion = device.protocols.get("companion", empty)
    dmap = device.protocols.get("dmap", empty)
    mrp = device.protocols.get("mrp", empty)
    raop = device.protocols.get("raop", empty)

    return {
        "airplay": AirPlaySettings(
            identifier=airplay.identifier,
            credentials=airplay.credentials,
            password=airplay.password,
        ),
        "companion": CompanionSettings(
            identifier=companion.identifier, credentials=companion.credentials
        ),
        "dmap": DmapSettings(identifier=dmap.identifier, credentials=dmap.credentials),
        "mrp": MrpSettings(identifier=mrp.identifier, credentials=mrp.credentials),
        "raop": RaopSettings(
            identifier=raop.identifier,
            credentials=raop.credentials,
            password=raop.password,
        ),
    }


def _build_storage(device: DeviceConfig) -> MemoryStorage:
    settings = Settings(protocols=ProtocolSettings(**_protocol_settings(device)))
    storage = MemoryStorage()
    storage.storage_model = StorageModel(version=MODEL_VERSION, devices=[settings])
    return storage


async def connect(loop: asyncio.AbstractEventLoop, device: DeviceConfig) -> AppleTV:
    results = await pyatv.scan(
        loop,
        hosts=[device.address],
        identifier={device.identifier},
        timeout=SCAN_TIMEOUT_SECONDS,
    )
    if not results:
        raise DeviceUnreachableError(
            f"could not find '{device.name}' ({device.identifier}) at {device.address}"
        )

    storage = _build_storage(device)
    return await pyatv.connect(results[0], loop, storage=storage)


async def get_power_state(
    loop: asyncio.AbstractEventLoop, device: DeviceConfig
) -> PowerState:
    atv = await connect(loop, device)
    try:
        return atv.power.power_state
    finally:
        atv.close()


async def set_power_state(
    loop: asyncio.AbstractEventLoop, device: DeviceConfig, desired: PowerState
) -> PowerState:
    atv = await connect(loop, device)
    try:
        current = atv.power.power_state
        if current == desired:
            return current

        # await_new_state=True raises NotImplementedError on pyatv's Companion
        # protocol (pyatv/protocols/companion/__init__.py); we already read the
        # state ourselves above, so we don't need pyatv to wait for it too.
        if desired == PowerState.On:
            await atv.power.turn_on(await_new_state=False)
        else:
            await atv.power.turn_off(await_new_state=False)
        return desired
    finally:
        atv.close()

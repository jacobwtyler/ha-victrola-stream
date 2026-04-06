"""Binary sensor platform - streaming detection via ADC stream probe."""
from __future__ import annotations
import logging
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VictrolaStreamingSensor(data, entry)])


class VictrolaStreamingSensor(CoordinatorEntity, BinarySensorEntity):
    """Detects when the turntable ADC is actively streaming audio.

    Uses a stream data probe: connects to the Victrola's Icecast-compatible
    stream server and checks if audio bytes are flowing. The server always
    accepts connections but only sends data when the needle is on the record.
    """

    _attr_has_entity_name = True
    _attr_name = "Streaming"
    _attr_icon = "mdi:record-player"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, data: dict, entry: ConfigEntry) -> None:
        super().__init__(data["coordinator"])
        self._api = data["api"]
        self._state_store = data["state_store"]
        self._attr_unique_id = f"{entry.entry_id}_is_streaming"

    @property
    def device_info(self) -> dict:
        return {"identifiers": {(DOMAIN, self._api.host)}}

    @property
    def is_on(self) -> bool:
        return self._state_store.is_streaming

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "stream_port": self._api.stream_port,
            "power_target": self._state_store.power_target,
        }

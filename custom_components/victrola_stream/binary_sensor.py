"""Binary sensor platform - ADC stream active detection."""
from __future__ import annotations
import logging
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
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
    """Detects whether the turntable is actively streaming audio.

    Uses the Icecast ADC stream probe on port 34435 — returns True when
    the needle is on the record and audio data is flowing.
    """

    _attr_has_entity_name = True
    _attr_name = "Streaming"
    _attr_device_class = BinarySensorDeviceClass.SOUND
    _attr_icon = "mdi:record-player"

    def __init__(self, data: dict, entry: ConfigEntry) -> None:
        super().__init__(data["coordinator"])
        self._api = data["api"]
        self._state_store = data["state_store"]
        self._attr_unique_id = f"{entry.entry_id}_streaming"

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._api.host)}}

    @property
    def is_on(self) -> bool:
        return self._state_store.is_streaming

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "speaker_name": self._state_store.quickplay_speaker,
            "speaker_id": self._state_store.quickplay_speaker_id,
            "source": self._state_store.quickplay_source,
            "power_state": self._state_store.power_target,
        }

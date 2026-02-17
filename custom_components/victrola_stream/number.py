"""Number platform for Victrola Stream - audio latency control."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LATENCY_MIN, LATENCY_MAX, LATENCY_STEP

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([VictrolaLatencyNumber(data, config_entry)])


class VictrolaLatencyNumber(CoordinatorEntity, NumberEntity):
    """Number entity for audio latency in milliseconds."""

    _attr_has_entity_name = True
    _attr_name = "Audio Latency"
    _attr_icon = "mdi:timer-outline"
    _attr_native_min_value = LATENCY_MIN
    _attr_native_max_value = LATENCY_MAX
    _attr_native_step = LATENCY_STEP
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = "ms"

    def __init__(self, data: dict, config_entry: ConfigEntry):
        super().__init__(data["coordinator"])
        self._api = data["api"]
        self._attr_unique_id = f"{config_entry.entry_id}_audio_latency"
        self._attr_native_value = 0

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._api.host)}}

    @property
    def native_value(self) -> float:
        if self.coordinator.data:
            return self.coordinator.data.get("audio_latency", 0) or 0
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        """Set audio latency - real API call."""
        success = await self._api.async_set_audio_latency(int(value))
        if success:
            self._attr_native_value = value
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set audio latency: %s", value)

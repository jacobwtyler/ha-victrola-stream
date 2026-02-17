"""Number platform - Knob brightness slider 0-100."""
from __future__ import annotations
import logging
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, BRIGHTNESS_MIN, BRIGHTNESS_MAX, BRIGHTNESS_STEP

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VictrolaKnobBrightnessNumber(data, entry)])


class VictrolaKnobBrightnessNumber(CoordinatorEntity, NumberEntity):
    """Knob brightness slider 0-100."""

    _attr_has_entity_name = True
    _attr_name = "Knob Brightness"
    _attr_icon = "mdi:knob"
    _attr_native_min_value = BRIGHTNESS_MIN
    _attr_native_max_value = BRIGHTNESS_MAX
    _attr_native_step = BRIGHTNESS_STEP
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = "%"

    def __init__(self, data: dict, entry: ConfigEntry):
        super().__init__(data["coordinator"])
        self._api = data["api"]
        self._state_store = data["state_store"]
        self._attr_unique_id = f"{entry.entry_id}_knob_brightness"

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._api.host)}}

    @property
    def native_value(self) -> float:
        return self._state_store.knob_brightness

    async def async_set_native_value(self, value: float) -> None:
        """Set knob brightness via API."""
        success = await self._api.async_set_knob_brightness(int(value))
        if success:
            self._state_store.set_knob_brightness(int(value))
            self.async_write_ha_state()
        else:
            _LOGGER.error("Failed to set knob brightness: %s", value)

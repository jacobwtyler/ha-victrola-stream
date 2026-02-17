"""Light platform for Victrola Stream - knob brightness control."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import LightEntity, ColorMode, ATTR_BRIGHTNESS
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([VictrolaKnobLight(data, config_entry)])


class VictrolaKnobLight(CoordinatorEntity, LightEntity):
    """Light entity controlling the Victrola knob illumination brightness."""

    _attr_has_entity_name = True
    _attr_name = "Knob Brightness"
    _attr_icon = "mdi:knob"
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, data: dict, config_entry: ConfigEntry):
        super().__init__(data["coordinator"])
        self._api = data["api"]
        self._attr_unique_id = f"{config_entry.entry_id}_knob_brightness"
        self._brightness = 255  # Default full brightness
        self._is_on = True

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._api.host)}}

    @property
    def is_on(self) -> bool:
        """Return true if knob light is on (brightness > 0)."""
        brightness = self.coordinator.data.get("knob_brightness", 100) if self.coordinator.data else 100
        return brightness > 0

    @property
    def brightness(self) -> int:
        """Return brightness as HA scale (0-255)."""
        if self.coordinator.data:
            # Victrola uses 0-100, HA uses 0-255
            victrola_brightness = self.coordinator.data.get("knob_brightness", 100) or 100
            return int((victrola_brightness / 100) * 255)
        return self._brightness

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on knob light, optionally set brightness."""
        if ATTR_BRIGHTNESS in kwargs:
            # Convert HA 0-255 to Victrola 0-100
            victrola_brightness = int((kwargs[ATTR_BRIGHTNESS] / 255) * 100)
        else:
            victrola_brightness = 100

        success = await self._api.async_set_knob_brightness(victrola_brightness)
        if success:
            self._brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
            self._is_on = True
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set knob brightness")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off knob light (set brightness to 0)."""
        success = await self._api.async_set_knob_brightness(0)
        if success:
            self._brightness = 0
            self._is_on = False
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to turn off knob brightness")

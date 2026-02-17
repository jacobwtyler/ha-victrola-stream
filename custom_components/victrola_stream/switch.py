"""Switch platform for Victrola Stream - source enable/disable."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SOURCES, SOURCE_LABELS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        VictrolaSourceSwitch(data, config_entry, source)
        for source in SOURCES
    ]

    async_add_entities(entities)


class VictrolaSourceSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to enable/disable a Victrola source type."""

    _attr_has_entity_name = True

    def __init__(self, data: dict, config_entry: ConfigEntry, source: str):
        super().__init__(data["coordinator"])
        self._api = data["api"]
        self._source = source
        self._attr_unique_id = f"{config_entry.entry_id}_{source}_enabled"
        self._attr_name = f"{SOURCE_LABELS.get(source, source)} Enabled"
        self._attr_icon = {
            "roon": "mdi:music-circle",
            "sonos": "mdi:speaker-wireless",
            "upnp": "mdi:cast-audio",
            "bluetooth": "mdi:bluetooth-audio",
        }.get(source, "mdi:toggle-switch")

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._api.host)}}

    @property
    def is_on(self) -> bool:
        """Return whether this source is enabled."""
        if self.coordinator.data:
            return self.coordinator.data.get(f"{self._source}_enabled", True)
        return True

    async def async_turn_on(self, **kwargs) -> None:
        """Enable this source."""
        success = await self._api.async_set_source_enabled(self._source, True)
        if success:
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to enable source: %s", self._source)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable this source."""
        success = await self._api.async_set_source_enabled(self._source, False)
        if success:
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to disable source: %s", self._source)

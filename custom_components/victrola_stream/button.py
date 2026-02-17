"""Button platform for Victrola Stream - action buttons."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        VictrolaRebootButton(data, config_entry),
        VictrolaRefreshButton(data, config_entry),
    ]

    async_add_entities(entities)


class VictrolaRebootButton(ButtonEntity):
    """Button to reboot the Victrola device."""

    _attr_has_entity_name = True
    _attr_name = "Reboot Device"
    _attr_icon = "mdi:restart"

    def __init__(self, data: dict, config_entry: ConfigEntry):
        self._api = data["api"]
        self._coordinator = data["coordinator"]
        self._attr_unique_id = f"{config_entry.entry_id}_reboot"

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._api.host)}}

    async def async_press(self) -> None:
        """Press the reboot button."""
        _LOGGER.warning("Rebooting Victrola at %s", self._api.host)
        success = await self._api.async_reboot()
        if success:
            _LOGGER.info("Victrola reboot command sent successfully")
        else:
            _LOGGER.error("Failed to send reboot command to Victrola")


class VictrolaRefreshButton(ButtonEntity):
    """Button to force refresh state from Victrola device."""

    _attr_has_entity_name = True
    _attr_name = "Refresh State"
    _attr_icon = "mdi:refresh"

    def __init__(self, data: dict, config_entry: ConfigEntry):
        self._api = data["api"]
        self._coordinator = data["coordinator"]
        self._attr_unique_id = f"{config_entry.entry_id}_refresh"

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._api.host)}}

    async def async_press(self) -> None:
        """Force refresh state from Victrola."""
        _LOGGER.info("Forcing state refresh for Victrola at %s", self._api.host)
        await self._coordinator.async_request_refresh()

"""Button platform - Reboot and Refresh State."""
from __future__ import annotations
import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        VictrolaRebootButton(data, entry),
        VictrolaRefreshButton(data, entry),
        VictrolaRediscoverButton(data, entry),
    ])


class VictrolaRebootButton(ButtonEntity):
    """Reboot the Victrola device."""

    _attr_has_entity_name = True
    _attr_name = "Reboot Device"
    _attr_icon = "mdi:restart"

    def __init__(self, data: dict, entry: ConfigEntry):
        self._api = data["api"]
        self._coordinator = data["coordinator"]
        self._attr_unique_id = f"{entry.entry_id}_reboot"

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._api.host)}}

    async def async_press(self) -> None:
        """Send reboot command using correct path: powermanager:goReboot."""
        _LOGGER.warning("Rebooting Victrola at %s", self._api.host)
        success = await self._api.async_reboot()
        if success:
            _LOGGER.info("Reboot command sent successfully")
        else:
            _LOGGER.error("Reboot command failed")


class VictrolaRefreshButton(ButtonEntity):
    """Force a state refresh."""

    _attr_has_entity_name = True
    _attr_name = "Refresh State"
    _attr_icon = "mdi:refresh"

    def __init__(self, data: dict, entry: ConfigEntry):
        self._api = data["api"]
        self._coordinator = data["coordinator"]
        self._attr_unique_id = f"{entry.entry_id}_refresh"

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._api.host)}}

    async def async_press(self) -> None:
        await self._coordinator.async_request_refresh()
        _LOGGER.info("State refresh requested")


class VictrolaRediscoverButton(ButtonEntity):
    """Rediscover speakers for the currently active source."""

    _attr_has_entity_name = True
    _attr_name = "Rediscover Speakers"
    _attr_icon = "mdi:speaker-multiple"

    def __init__(self, data: dict, entry: ConfigEntry):
        self._api = data["api"]
        self._discovery = data["discovery"]
        self._coordinator = data["coordinator"]
        self._state_store = data["state_store"]
        self._attr_unique_id = f"{entry.entry_id}_rediscover"

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._api.host)}}

    async def async_press(self) -> None:
        """Rediscover speakers for currently active source only."""
        current = self._state_store.current_source
        _LOGGER.info("Rediscovering %s speakers...", current)
        await self._discovery.async_rediscover_current()
        await self._coordinator.async_request_refresh()
        _LOGGER.info("%s speaker rediscovery complete", current)

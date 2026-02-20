"""The Victrola Stream integration."""
from __future__ import annotations
import logging
from typing import Any
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN, CONF_VICTROLA_IP, CONF_VICTROLA_PORT, DEFAULT_PORT
from .victrola_api import VictrolaAPI
from .discovery import VictrolaDiscovery
from .state_store import VictrolaStateStore
from .coordinator import VictrolaCoordinator
from .event_listener import VictrolaEventListener

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.MEDIA_PLAYER,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.SWITCH,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    victrola_ip   = entry.data[CONF_VICTROLA_IP]
    victrola_port = entry.data.get(CONF_VICTROLA_PORT, DEFAULT_PORT)
    _LOGGER.info("Setting up Victrola Stream at %s:%s", victrola_ip, victrola_port)

    api         = VictrolaAPI(victrola_ip, victrola_port)
    state_store = VictrolaStateStore()
    discovery   = VictrolaDiscovery(hass, api)

    coordinator = VictrolaCoordinator(hass, api, state_store, discovery)
    # First refresh populates speaker list from device
    await coordinator.async_config_entry_first_refresh()

    # Start real-time event listener (push notifications from device)
    event_listener = VictrolaEventListener(api, state_store, discovery, coordinator)
    await event_listener.async_start()

    hass.data[DOMAIN][entry.entry_id] = {
        "api":            api,
        "discovery":      discovery,
        "state_store":    state_store,
        "coordinator":    coordinator,
        "event_listener": event_listener,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Stop event listener cleanly
    entry_data = hass.data[DOMAIN].get(entry.entry_id, {})
    listener = entry_data.get("event_listener")
    if listener:
        await listener.async_stop()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

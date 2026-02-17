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

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.MEDIA_PLAYER, Platform.SELECT]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Victrola Stream component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Victrola Stream from a config entry."""
    
    victrola_ip = entry.data[CONF_VICTROLA_IP]
    victrola_port = entry.data.get(CONF_VICTROLA_PORT, DEFAULT_PORT)
    
    _LOGGER.info("Setting up Victrola Stream at %s:%s", victrola_ip, victrola_port)
    
    # Create API instance
    api = VictrolaAPI(victrola_ip, victrola_port)
    
    # Create discovery instance
    discovery = VictrolaDiscovery(hass, api)
    
    # Run discovery for all source types
    await discovery.async_discover_all_sources()
    
    # Store in hass.data
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "discovery": discovery,
        "victrola_ip": victrola_ip,
        "victrola_port": victrola_port,
    }
    
    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok

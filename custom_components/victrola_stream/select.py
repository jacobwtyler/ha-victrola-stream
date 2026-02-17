"""Select platform for Victrola Stream."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SOURCE_ROON, SOURCE_SONOS, SOURCE_UPNP, SOURCE_BLUETOOTH, SOURCE_TYPE_MAP

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Victrola Stream select entities."""
    
    data = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = [
        VictrolaSourceSelect(data, config_entry),
        VictrolaSpeakerSelect(data, config_entry, SOURCE_ROON),
        VictrolaSpeakerSelect(data, config_entry, SOURCE_SONOS),
        VictrolaSpeakerSelect(data, config_entry, SOURCE_UPNP),
        VictrolaSpeakerSelect(data, config_entry, SOURCE_BLUETOOTH),
    ]
    
    async_add_entities(entities)


class VictrolaSourceSelect(SelectEntity):
    """Select entity for choosing audio source."""

    _attr_has_entity_name = True
    _attr_name = "Audio Source"
    _attr_icon = "mdi:audio-input-stereo-minijack"

    def __init__(self, data: dict, config_entry: ConfigEntry):
        """Initialize the select entity."""
        self._api = data["api"]
        self._attr_unique_id = f"{config_entry.entry_id}_source_select"
        self._attr_options = ["roon", "sonos", "upnp", "bluetooth"]
        self._attr_current_option = "roon"

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._api.host)},
        }

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        self._attr_current_option = option
        self.async_write_ha_state()
        _LOGGER.info("Source selected: %s", option)


class VictrolaSpeakerSelect(SelectEntity):
    """Select entity for choosing speaker for a source."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:speaker"

    def __init__(self, data: dict, config_entry: ConfigEntry, source: str):
        """Initialize the select entity."""
        self._api = data["api"]
        self._discovery = data["discovery"]
        self._source = source
        self._attr_unique_id = f"{config_entry.entry_id}_{source}_speaker_select"
        self._attr_name = f"{source.title()} Speaker"
        
        speakers = self._discovery.get_speakers_for_source(source)
        self._attr_options = list(speakers.keys()) if speakers else []
        self._attr_current_option = self._attr_options[0] if self._attr_options else None

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._api.host)},
        }

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        victrola_id = self._discovery.get_speaker_victrola_id(self._source, option)
        
        if victrola_id:
            source_type = SOURCE_TYPE_MAP.get(self._source)
            
            if await self._api.async_set_source(source_type, victrola_id):
                self._attr_current_option = option
                self.async_write_ha_state()
                _LOGGER.info("%s speaker changed to: %s", self._source, option)
            else:
                _LOGGER.error("Failed to set speaker: %s", option)
        else:
            _LOGGER.error("Speaker not mapped: %s", option)

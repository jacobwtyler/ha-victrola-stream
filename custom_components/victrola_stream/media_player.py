"""Media player platform for Victrola Stream."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_DEVICE_NAME

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Victrola Stream media player."""
    
    data = hass.data[DOMAIN][config_entry.entry_id]
    device_name = config_entry.data.get(CONF_DEVICE_NAME, "Victrola Stream Pearl")
    
    async_add_entities([VictrolaMediaPlayer(data, config_entry, device_name)])


class VictrolaMediaPlayer(MediaPlayerEntity):
    """Representation of a Victrola Stream media player."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = (
        MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.SELECT_SOUND_MODE
    )

    def __init__(self, data: dict, config_entry: ConfigEntry, device_name: str):
        """Initialize the media player."""
        self._api = data["api"]
        self._discovery = data["discovery"]
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_media_player"
        
        self._current_source = "roon"
        self._current_speaker = None
        self._attr_state = MediaPlayerState.IDLE

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._api.host)},
            "name": self._device_name,
            "manufacturer": "Victrola",
            "model": "Stream Pearl",
        }

    @property
    def source(self) -> str | None:
        """Return the current input source."""
        return self._current_source

    @property
    def source_list(self) -> list[str]:
        """List of available input sources."""
        return ["roon", "sonos", "upnp", "bluetooth"]

    @property
    def sound_mode(self) -> str | None:
        """Return the current sound mode."""
        return self._current_speaker

    @property
    def sound_mode_list(self) -> list[str] | None:
        """Return the available sound modes."""
        speakers = self._discovery.get_speakers_for_source(self._current_source)
        return list(speakers.keys()) if speakers else None

    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        if source in ["roon", "sonos", "upnp", "bluetooth"]:
            self._current_source = source
            self._current_speaker = None
            self.async_write_ha_state()
            _LOGGER.info("Source changed to: %s", source)

    async def async_select_sound_mode(self, sound_mode: str) -> None:
        """Select sound mode (speaker)."""
        victrola_id = self._discovery.get_speaker_victrola_id(
            self._current_source, sound_mode
        )
        
        if victrola_id:
            from .const import SOURCE_TYPE_MAP
            source_type = SOURCE_TYPE_MAP.get(self._current_source)
            
            if await self._api.async_set_source(source_type, victrola_id):
                self._current_speaker = sound_mode
                self._attr_state = MediaPlayerState.PLAYING
                self.async_write_ha_state()
                _LOGGER.info("Speaker changed to: %s", sound_mode)
            else:
                _LOGGER.error("Failed to set speaker: %s", sound_mode)
        else:
            _LOGGER.error("Speaker not mapped: %s", sound_mode)

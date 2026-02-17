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
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_DEVICE_NAME, SOURCE_TYPE_MAP, SOURCES
from .coordinator import VictrolaCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][config_entry.entry_id]
    device_name = config_entry.data.get(CONF_DEVICE_NAME, "Victrola Stream Pearl")
    async_add_entities([VictrolaMediaPlayer(data, config_entry, device_name)])


class VictrolaMediaPlayer(CoordinatorEntity, MediaPlayerEntity):
    """Victrola Stream media player entity."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = (
        MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.SELECT_SOUND_MODE
    )

    def __init__(self, data: dict, config_entry: ConfigEntry, device_name: str):
        super().__init__(data["coordinator"])
        self._api = data["api"]
        self._discovery = data["discovery"]
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_media_player"
        self._current_source = "roon"
        self._current_speaker: str | None = None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._api.host)},
            "name": self._device_name,
            "manufacturer": "Victrola",
            "model": "Stream Pearl",
        }

    @property
    def state(self) -> MediaPlayerState:
        """Return state based on coordinator data."""
        output = self.coordinator.data.get("current_output") if self.coordinator.data else None
        if output:
            return MediaPlayerState.PLAYING
        return MediaPlayerState.IDLE

    @property
    def source(self) -> str | None:
        """Return current source."""
        output = self.coordinator.data.get("current_output") if self.coordinator.data else None
        if output and isinstance(output, dict):
            source_type = output.get("type", "")
            for source, victrola_type in SOURCE_TYPE_MAP.items():
                if victrola_type == source_type:
                    self._current_source = source
                    return source
        return self._current_source

    @property
    def source_list(self) -> list[str]:
        return SOURCES

    @property
    def sound_mode(self) -> str | None:
        """Return current speaker (sound mode)."""
        output = self.coordinator.data.get("current_output") if self.coordinator.data else None
        if output and isinstance(output, dict):
            return output.get("name", self._current_speaker)
        return self._current_speaker

    @property
    def sound_mode_list(self) -> list[str] | None:
        """Return available speakers for current source."""
        speakers = self._discovery.get_speakers_for_source(self._current_source)
        return list(speakers.keys()) if speakers else None

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes from coordinator."""
        attrs = {}
        if self.coordinator.data:
            attrs["audio_quality"] = self.coordinator.data.get("audio_quality")
            attrs["audio_latency"] = self.coordinator.data.get("audio_latency")
            attrs["knob_brightness"] = self.coordinator.data.get("knob_brightness")
            attrs["current_output"] = self.coordinator.data.get("current_output")
        return attrs

    async def async_select_source(self, source: str) -> None:
        """Select input source - updates HA state only, speaker select triggers API."""
        self._current_source = source
        self.async_write_ha_state()

    async def async_select_sound_mode(self, sound_mode: str) -> None:
        """Select speaker - makes real API call to Victrola."""
        victrola_id = self._discovery.get_speaker_victrola_id(self._current_source, sound_mode)

        if not victrola_id:
            _LOGGER.error("No Victrola ID for speaker: %s/%s", self._current_source, sound_mode)
            return

        source_type = SOURCE_TYPE_MAP.get(self._current_source)
        if not source_type:
            _LOGGER.error("Unknown source type: %s", self._current_source)
            return

        success = await self._api.async_set_source(source_type, victrola_id)
        if success:
            self._current_speaker = sound_mode
            self.async_write_ha_state()
            # Refresh coordinator to verify state change
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set speaker on Victrola: %s", sound_mode)

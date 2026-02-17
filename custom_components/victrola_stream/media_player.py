"""Media player for Victrola Stream."""
from __future__ import annotations
import logging
from homeassistant.components.media_player import (
    MediaPlayerEntity, MediaPlayerEntityFeature, MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import (
    DOMAIN, CONF_DEVICE_NAME, SOURCES,
    SOURCE_TO_DEFAULT_TYPE, SOURCE_TO_QUICKPLAY_TYPE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    device_name = entry.data.get(CONF_DEVICE_NAME, "Victrola Stream Pearl")
    async_add_entities([VictrolaMediaPlayer(data, entry, device_name)])


class VictrolaMediaPlayer(CoordinatorEntity, MediaPlayerEntity):
    """Victrola Stream media player."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = (
        MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.SELECT_SOUND_MODE
    )

    def __init__(self, data: dict, entry: ConfigEntry, device_name: str):
        super().__init__(data["coordinator"])
        self._api = data["api"]
        self._discovery = data["discovery"]
        self._state_store = data["state_store"]
        self._device_name = device_name
        self._attr_unique_id = f"{entry.entry_id}_media_player"

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
        if not self._state_store.connected:
            return MediaPlayerState.OFF
        if self._state_store.current_speaker:
            return MediaPlayerState.PLAYING
        return MediaPlayerState.IDLE

    @property
    def source(self) -> str | None:
        return self._state_store.current_source

    @property
    def source_list(self) -> list[str]:
        return SOURCES

    @property
    def sound_mode(self) -> str | None:
        return self._state_store.current_speaker

    @property
    def sound_mode_list(self) -> list[str] | None:
        return self._discovery.get_speaker_names(self._state_store.current_source)

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "current_source": self._state_store.current_source,
            "current_speaker": self._state_store.current_speaker,
            "current_speaker_id": self._state_store.current_speaker_id,
            "audio_quality": self._state_store.audio_quality,
            "audio_latency": self._state_store.audio_latency,
            "knob_brightness": self._state_store.knob_brightness,
            "connected": self._state_store.connected,
        }

    async def async_select_source(self, source: str) -> None:
        """Switch source - updates state only, user then picks speaker."""
        self._state_store.current_source = source
        self._state_store.current_speaker = None
        self._state_store.current_speaker_id = None
        self.async_write_ha_state()

    async def async_select_sound_mode(self, sound_mode: str) -> None:
        """Select speaker and send to Victrola."""
        source = self._state_store.current_source
        victrola_id = self._discovery.get_victrola_id(source, sound_mode)

        if not victrola_id:
            _LOGGER.error("No Victrola ID for %s / %s", source, sound_mode)
            return

        default_type = SOURCE_TO_DEFAULT_TYPE.get(source)
        quickplay_type = SOURCE_TO_QUICKPLAY_TYPE.get(source)

        success = await self._api.async_select_speaker(default_type, quickplay_type, victrola_id)
        if success:
            self._state_store.set_speaker(source, sound_mode, victrola_id)
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set speaker: %s / %s", source, sound_mode)

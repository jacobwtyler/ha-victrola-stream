"""Select platform - Audio Source, Quality, Latency, Speaker selectors."""
from __future__ import annotations
import logging
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import (
    DOMAIN, SOURCES,
    AUDIO_QUALITY_OPTIONS, AUDIO_QUALITY_LABEL_TO_API,
    AUDIO_LATENCY_OPTIONS, AUDIO_LATENCY_LABEL_TO_API,
    SOURCE_TO_DEFAULT_TYPE, SOURCE_TO_QUICKPLAY_TYPE,
    SOURCE_ROON, SOURCE_SONOS, SOURCE_UPNP, SOURCE_BLUETOOTH,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    entities = [
        VictrolaAudioSourceSelect(data, entry),
        VictrolaAudioQualitySelect(data, entry),
        VictrolaAudioLatencySelect(data, entry),
        VictrolaSpeakerSelect(data, entry, SOURCE_ROON),
        VictrolaSpeakerSelect(data, entry, SOURCE_SONOS),
        VictrolaSpeakerSelect(data, entry, SOURCE_UPNP),
        VictrolaSpeakerSelect(data, entry, SOURCE_BLUETOOTH),
    ]
    async_add_entities(entities)


class VictrolaBaseSelect(CoordinatorEntity, SelectEntity):
    _attr_has_entity_name = True

    def __init__(self, data: dict, entry: ConfigEntry):
        super().__init__(data["coordinator"])
        self._api = data["api"]
        self._state_store = data["state_store"]
        self._discovery = data["discovery"]

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._api.host)}}


class VictrolaAudioSourceSelect(VictrolaBaseSelect):
    """Select the active audio source (Roon/Sonos/UPnP/Bluetooth).
    When changed: disables previous source, enables new source via API."""

    _attr_name = "Audio Source"
    _attr_icon = "mdi:audio-input-stereo-minijack"
    _attr_options = SOURCES

    def __init__(self, data: dict, entry: ConfigEntry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_audio_source"

    @property
    def current_option(self) -> str | None:
        return self._state_store.current_source

    async def async_select_option(self, option: str) -> None:
        """Switch source: disable previous, enable new."""
        previous = self._state_store.current_source

        if previous and previous != option:
            # Disable previous source
            await self._api.async_set_source_enabled(previous.lower(), False)
            self._state_store.set_source_enabled(previous, False)
            _LOGGER.info("Disabled source: %s", previous)

        # Enable new source
        await self._api.async_set_source_enabled(option.lower(), True)
        self._state_store.set_source_enabled(option, True)
        self._state_store.current_source = option
        self._state_store.current_speaker = None
        self._state_store.current_speaker_id = None

        _LOGGER.info("Audio source changed to: %s", option)
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()


class VictrolaAudioQualitySelect(VictrolaBaseSelect):
    """Select audio quality - Prioritize Connection / Standard / Prioritize Audio (FLAC)."""

    _attr_name = "Audio Quality"
    _attr_icon = "mdi:music-note"
    _attr_options = AUDIO_QUALITY_OPTIONS

    def __init__(self, data: dict, entry: ConfigEntry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_audio_quality"

    @property
    def current_option(self) -> str | None:
        return self._state_store.audio_quality

    async def async_select_option(self, option: str) -> None:
        api_value = AUDIO_QUALITY_LABEL_TO_API.get(option)
        if not api_value:
            _LOGGER.error("Unknown audio quality option: %s", option)
            return
        success = await self._api.async_set_audio_quality(api_value)
        if success:
            self._state_store.set_audio_quality(option)
            self.async_write_ha_state()
        else:
            _LOGGER.error("Failed to set audio quality: %s", option)


class VictrolaAudioLatencySelect(VictrolaBaseSelect):
    """Select audio latency - Low / Medium / High / Max."""

    _attr_name = "Audio Latency"
    _attr_icon = "mdi:timer-outline"
    _attr_options = AUDIO_LATENCY_OPTIONS

    def __init__(self, data: dict, entry: ConfigEntry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_audio_latency"

    @property
    def current_option(self) -> str | None:
        return self._state_store.audio_latency

    async def async_select_option(self, option: str) -> None:
        api_value = AUDIO_LATENCY_LABEL_TO_API.get(option)
        if not api_value:
            _LOGGER.error("Unknown latency option: %s", option)
            return
        success = await self._api.async_set_audio_latency(api_value)
        if success:
            self._state_store.set_audio_latency(option)
            self.async_write_ha_state()
        else:
            _LOGGER.error("Failed to set audio latency: %s", option)


class VictrolaSpeakerSelect(VictrolaBaseSelect):
    """Select a speaker for a given source type."""

    _attr_icon = "mdi:speaker"

    def __init__(self, data: dict, entry: ConfigEntry, source: str):
        super().__init__(data, entry)
        self._source = source
        self._attr_unique_id = f"{entry.entry_id}_{source.lower()}_speaker"
        self._attr_name = f"{source} Speaker"

    @property
    def options(self) -> list[str]:
        names = self._discovery.get_speaker_names(self._source)
        return names if names else ["None"]

    @property
    def current_option(self) -> str | None:
        if self._state_store.current_source == self._source:
            return self._state_store.current_speaker
        return None

    async def async_select_option(self, option: str) -> None:
        """Select speaker and send quickplay + setDefault to Victrola."""
        victrola_id = self._discovery.get_victrola_id(self._source, option)
        if not victrola_id:
            _LOGGER.error("No Victrola ID for %s / %s", self._source, option)
            return

        default_type = SOURCE_TO_DEFAULT_TYPE.get(self._source)
        quickplay_type = SOURCE_TO_QUICKPLAY_TYPE.get(self._source)

        _LOGGER.info("Setting speaker: %s / %s (%s)", self._source, option, victrola_id)

        success = await self._api.async_select_speaker(default_type, quickplay_type, victrola_id)
        if success:
            self._state_store.set_speaker(self._source, option, victrola_id)
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set speaker: %s / %s", self._source, option)

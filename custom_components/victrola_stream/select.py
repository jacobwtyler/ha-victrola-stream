"""Select platform - unified QuickPlay, Audio settings, Default Output per source."""
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
    VICTROLA_TYPE_SONOS_QUICKPLAY,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    entities = [
        VictrolaAudioSourceSelect(data, entry),
        VictrolaAudioQualitySelect(data, entry),
        VictrolaAudioLatencySelect(data, entry),
        VictrolaUnifiedQuickPlaySelect(data, entry),  # ONE unified select from live list
    ]
    # Default Output selects remain per-source (different semantics)
    for source in [SOURCE_ROON, SOURCE_SONOS, SOURCE_UPNP, SOURCE_BLUETOOTH]:
        entities.append(VictrolaDefaultOutputSelect(data, entry, source))

    async_add_entities(entities)


class VictrolaBaseSelect(CoordinatorEntity, SelectEntity):
    _attr_has_entity_name = True

    def __init__(self, data: dict, entry: ConfigEntry):
        super().__init__(data["coordinator"])
        self._api        = data["api"]
        self._state_store = data["state_store"]
        self._discovery  = data["discovery"]

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._api.host)}}


class VictrolaAudioSourceSelect(VictrolaBaseSelect):
    """Active source selector."""
    _attr_name    = "Audio Source"
    _attr_icon    = "mdi:audio-input-stereo-minijack"
    _attr_options = SOURCES

    def __init__(self, data, entry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_audio_source"

    @property
    def current_option(self) -> str | None:
        return self._state_store.current_source

    async def async_select_option(self, option: str) -> None:
        previous = self._state_store.current_source
        if previous and previous != option:
            await self._api.async_set_source_enabled(previous.lower(), False)
            self._state_store.set_source_enabled(previous, False)
        await self._api.async_set_source_enabled(option.lower(), True)
        self._state_store.set_source_enabled(option, True)
        self._state_store.current_source = option
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()


class VictrolaAudioQualitySelect(VictrolaBaseSelect):
    _attr_name    = "Audio Quality"
    _attr_icon    = "mdi:music-note"
    _attr_options = AUDIO_QUALITY_OPTIONS

    def __init__(self, data, entry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_audio_quality"

    @property
    def current_option(self) -> str | None:
        return self._state_store.audio_quality

    async def async_select_option(self, option: str) -> None:
        api_value = AUDIO_QUALITY_LABEL_TO_API.get(option)
        if api_value and await self._api.async_set_audio_quality(api_value):
            self._state_store.set_audio_quality(option)
            self.async_write_ha_state()


class VictrolaAudioLatencySelect(VictrolaBaseSelect):
    _attr_name    = "Audio Latency"
    _attr_icon    = "mdi:timer-outline"
    _attr_options = AUDIO_LATENCY_OPTIONS

    def __init__(self, data, entry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_audio_latency"

    @property
    def current_option(self) -> str | None:
        return self._state_store.audio_latency

    async def async_select_option(self, option: str) -> None:
        api_value = AUDIO_LATENCY_LABEL_TO_API.get(option)
        if api_value and await self._api.async_set_audio_latency(api_value):
            self._state_store.set_audio_latency(option)
            self.async_write_ha_state()


class VictrolaUnifiedQuickPlaySelect(VictrolaBaseSelect):
    """Unified QuickPlay - live speaker list from device, one select for all sources.
    
    Speaker list is populated dynamically from victrola:ui/speakerQuickplay.
    Current selection reflects device state (preferred=True in device response).
    Selecting a speaker sends victrola:ui/quickplay immediately.
    """
    _attr_name = "Quick Play Speaker"
    _attr_icon = "mdi:play-circle"

    def __init__(self, data, entry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_unified_quickplay"

    @property
    def options(self) -> list[str]:
        names = self._discovery.get_quickplay_speaker_names()
        return names if names else ["None"]

    @property
    def current_option(self) -> str | None:
        """Current quickplay speaker - polled from device (preferred=True)."""
        return self._state_store.quickplay_speaker

    async def async_select_option(self, option: str) -> None:
        """Send quickplay to selected speaker - starts audio immediately."""
        speaker_id = self._discovery.get_quickplay_id(option)
        if not speaker_id:
            _LOGGER.error("No ID found for quickplay speaker: %s", option)
            return

        _LOGGER.info("QuickPlay → %s (%s)", option, speaker_id)
        success = await self._api.async_quickplay(VICTROLA_TYPE_SONOS_QUICKPLAY, speaker_id)
        if success:
            self._state_store.set_quickplay(SOURCE_SONOS, option, speaker_id)
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("QuickPlay failed for: %s", option)


class VictrolaDefaultOutputSelect(VictrolaBaseSelect):
    """Default Output per source - sets where audio goes next time, no immediate playback."""
    _attr_icon = "mdi:speaker-multiple"

    def __init__(self, data, entry, source: str):
        super().__init__(data, entry)
        self._source = source
        self._attr_unique_id = f"{entry.entry_id}_{source.lower()}_default_output"
        self._attr_name = f"{source} Default Output"

    @property
    def options(self) -> list[str]:
        names = self._discovery.get_speaker_names(self._source)
        return names if names else ["None"]

    @property
    def current_option(self) -> str | None:
        """Current default output - polled from device via getRows."""
        info = self._state_store.get_default_output(self._source)
        return info["name"] if info else None

    async def async_select_option(self, option: str) -> None:
        """Set default output - no immediate playback."""
        victrola_id = self._discovery.get_victrola_id(self._source, option)
        if not victrola_id:
            _LOGGER.error("No ID for %s / %s", self._source, option)
            return
        default_type = SOURCE_TO_DEFAULT_TYPE.get(self._source)
        success = await self._api.async_set_default_output(default_type, victrola_id)
        if success:
            self._state_store.set_default_output(self._source, option, victrola_id)
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()

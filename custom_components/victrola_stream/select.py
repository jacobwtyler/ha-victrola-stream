"""Select platform for Victrola Stream."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SOURCE_ROON, SOURCE_SONOS, SOURCE_UPNP, SOURCE_BLUETOOTH,
    SOURCE_TYPE_MAP, AUDIO_QUALITY_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        VictrolaAudioQualitySelect(data, config_entry),
        VictrolaSpeakerSelect(data, config_entry, SOURCE_ROON),
        VictrolaSpeakerSelect(data, config_entry, SOURCE_SONOS),
        VictrolaSpeakerSelect(data, config_entry, SOURCE_UPNP),
        VictrolaSpeakerSelect(data, config_entry, SOURCE_BLUETOOTH),
    ]

    async_add_entities(entities)


class VictrolaAudioQualitySelect(CoordinatorEntity, SelectEntity):
    """Select entity for audio quality - makes real API call."""

    _attr_has_entity_name = True
    _attr_name = "Audio Quality"
    _attr_icon = "mdi:music-note"
    _attr_options = AUDIO_QUALITY_OPTIONS

    def __init__(self, data: dict, config_entry: ConfigEntry):
        super().__init__(data["coordinator"])
        self._api = data["api"]
        self._attr_unique_id = f"{config_entry.entry_id}_audio_quality"
        self._attr_current_option = AUDIO_QUALITY_OPTIONS[0]

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._api.host)}}

    @property
    def current_option(self) -> str | None:
        if self.coordinator.data:
            return self.coordinator.data.get("audio_quality", self._attr_current_option)
        return self._attr_current_option

    async def async_select_option(self, option: str) -> None:
        """Set audio quality - real API call."""
        success = await self._api.async_set_audio_quality(option)
        if success:
            self._attr_current_option = option
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set audio quality: %s", option)


class VictrolaSpeakerSelect(CoordinatorEntity, SelectEntity):
    """Select entity for choosing a speaker for a given source - makes real API call."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:speaker"

    def __init__(self, data: dict, config_entry: ConfigEntry, source: str):
        super().__init__(data["coordinator"])
        self._api = data["api"]
        self._discovery = data["discovery"]
        self._source = source
        self._attr_unique_id = f"{config_entry.entry_id}_{source}_speaker"
        self._attr_name = f"{source.title()} Speaker"

        speakers = self._discovery.get_speakers_for_source(source)
        self._attr_options = list(speakers.keys()) if speakers else ["None"]
        self._attr_current_option = self._attr_options[0] if self._attr_options else None

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._api.host)}}

    async def async_select_option(self, option: str) -> None:
        """Set speaker - makes real API call to Victrola device."""
        victrola_id = self._discovery.get_speaker_victrola_id(self._source, option)

        if not victrola_id:
            _LOGGER.error("No Victrola ID found for %s/%s", self._source, option)
            return

        source_type = SOURCE_TYPE_MAP.get(self._source)
        if not source_type:
            _LOGGER.error("Unknown source type: %s", self._source)
            return

        _LOGGER.info("Setting Victrola: %s -> %s (%s)", self._source, option, victrola_id)

        success = await self._api.async_set_source(source_type, victrola_id)
        if success:
            self._attr_current_option = option
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Victrola API call failed for %s/%s", self._source, option)

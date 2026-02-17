"""Sensor platform for Victrola Stream - state verification sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SOURCE_TYPE_MAP

_LOGGER = logging.getLogger(__name__)

# Reverse map: victrolaOutputRoon -> roon
VICTROLA_TYPE_TO_SOURCE = {v: k for k, v in SOURCE_TYPE_MAP.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        VictrolaCurrentSourceSensor(data, config_entry),
        VictrolaCurrentSpeakerSensor(data, config_entry),
        VictrolaAudioQualitySensor(data, config_entry),
        VictrolaAudioLatencySensor(data, config_entry),
        VictrolaKnobBrightnessSensor(data, config_entry),
        VictrolaConnectionStatusSensor(data, config_entry),
    ]

    async_add_entities(entities)


class VictrolaBaseSensor(CoordinatorEntity, SensorEntity):
    """Base sensor with shared device info."""

    _attr_has_entity_name = True

    def __init__(self, data: dict, config_entry: ConfigEntry):
        super().__init__(data["coordinator"])
        self._api = data["api"]
        self._config_entry = config_entry

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._api.host)}}


class VictrolaCurrentSourceSensor(VictrolaBaseSensor):
    """Sensor showing the currently active source type (roon/sonos/upnp/bluetooth)."""

    _attr_name = "Current Source"
    _attr_icon = "mdi:audio-input-stereo-minijack"

    def __init__(self, data: dict, config_entry: ConfigEntry):
        super().__init__(data, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_current_source"

    @property
    def native_value(self) -> str | None:
        """Return the current source from device state."""
        if not self.coordinator.data:
            return None
        output = self.coordinator.data.get("current_output")
        if output and isinstance(output, dict):
            source_type = output.get("type", "")
            return VICTROLA_TYPE_TO_SOURCE.get(source_type, source_type)
        return "unknown"


class VictrolaCurrentSpeakerSensor(VictrolaBaseSensor):
    """Sensor showing the currently active speaker name."""

    _attr_name = "Current Speaker"
    _attr_icon = "mdi:speaker"

    def __init__(self, data: dict, config_entry: ConfigEntry):
        super().__init__(data, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_current_speaker"

    @property
    def native_value(self) -> str | None:
        """Return the current speaker name from device state."""
        if not self.coordinator.data:
            return None
        output = self.coordinator.data.get("current_output")
        if output and isinstance(output, dict):
            return output.get("name") or output.get("id", "unknown")
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict:
        """Return full output details."""
        if not self.coordinator.data:
            return {}
        output = self.coordinator.data.get("current_output")
        if output and isinstance(output, dict):
            return {
                "output_id": output.get("id"),
                "output_type": output.get("type"),
                "output_name": output.get("name"),
            }
        return {}


class VictrolaAudioQualitySensor(VictrolaBaseSensor):
    """Sensor verifying current audio quality setting."""

    _attr_name = "Audio Quality (Verified)"
    _attr_icon = "mdi:music-note"

    def __init__(self, data: dict, config_entry: ConfigEntry):
        super().__init__(data, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_verified_audio_quality"

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("audio_quality", "unknown")


class VictrolaAudioLatencySensor(VictrolaBaseSensor):
    """Sensor verifying current audio latency setting."""

    _attr_name = "Audio Latency (Verified)"
    _attr_icon = "mdi:timer-outline"
    _attr_native_unit_of_measurement = "ms"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, data: dict, config_entry: ConfigEntry):
        super().__init__(data, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_verified_audio_latency"

    @property
    def native_value(self) -> int | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("audio_latency")


class VictrolaKnobBrightnessSensor(VictrolaBaseSensor):
    """Sensor verifying current knob brightness setting."""

    _attr_name = "Knob Brightness (Verified)"
    _attr_icon = "mdi:knob"
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, data: dict, config_entry: ConfigEntry):
        super().__init__(data, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_verified_knob_brightness"

    @property
    def native_value(self) -> int | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("knob_brightness")


class VictrolaConnectionStatusSensor(VictrolaBaseSensor):
    """Sensor showing connection status to Victrola device."""

    _attr_name = "Connection Status"
    _attr_icon = "mdi:wifi-check"

    def __init__(self, data: dict, config_entry: ConfigEntry):
        super().__init__(data, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_connection_status"

    @property
    def native_value(self) -> str:
        """Return connected if coordinator has data, disconnected otherwise."""
        if self.coordinator.last_update_success and self.coordinator.data:
            return "connected"
        return "disconnected"

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "host": self._api.host,
            "last_update_success": self.coordinator.last_update_success,
            "last_update": str(self.coordinator.last_update_success),
        }

"""Sensor platform - connection, settings, quickplay and default output sensors."""
from __future__ import annotations
import logging
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        VictrolaConnectionSensor(data, entry),
        VictrolaCurrentSourceSensor(data, entry),
        VictrolaAudioQualitySensor(data, entry),
        VictrolaAudioLatencySensor(data, entry),
        VictrolaKnobBrightnessSensor(data, entry),
        # QuickPlay sensors - last speaker sent via quickplay per source
        VictrolaLastQuickPlaySensor(data, entry),
        # Default Output sensors - last speaker set as default per source
        VictrolaLastDefaultOutputSensor(data, entry),
    ])


class VictrolaBaseSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, data: dict, entry: ConfigEntry):
        super().__init__(data["coordinator"])
        self._api = data["api"]
        self._state_store = data["state_store"]

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._api.host)}}


class VictrolaConnectionSensor(VictrolaBaseSensor):
    _attr_name = "Connection Status"
    _attr_icon = "mdi:wifi-check"

    def __init__(self, data: dict, entry: ConfigEntry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_connection_status"

    @property
    def native_value(self) -> str:
        return "connected" if self._state_store.connected else "disconnected"

    @property
    def extra_state_attributes(self) -> dict:
        return {"host": self._api.host}


class VictrolaCurrentSourceSensor(VictrolaBaseSensor):
    _attr_name = "Current Source"
    _attr_icon = "mdi:audio-input-stereo-minijack"

    def __init__(self, data: dict, entry: ConfigEntry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_current_source"

    @property
    def native_value(self) -> str | None:
        return self._state_store.current_source

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "roon_enabled": self._state_store.source_enabled.get("Roon"),
            "sonos_enabled": self._state_store.source_enabled.get("Sonos"),
            "upnp_enabled": self._state_store.source_enabled.get("UPnP"),
            "bluetooth_enabled": self._state_store.source_enabled.get("Bluetooth"),
        }


class VictrolaAudioQualitySensor(VictrolaBaseSensor):
    _attr_name = "Audio Quality"
    _attr_icon = "mdi:music-note"

    def __init__(self, data: dict, entry: ConfigEntry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_audio_quality_sensor"

    @property
    def native_value(self) -> str | None:
        return self._state_store.audio_quality


class VictrolaAudioLatencySensor(VictrolaBaseSensor):
    _attr_name = "Audio Latency"
    _attr_icon = "mdi:timer-outline"

    def __init__(self, data: dict, entry: ConfigEntry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_audio_latency_sensor"

    @property
    def native_value(self) -> str | None:
        return self._state_store.audio_latency


class VictrolaKnobBrightnessSensor(VictrolaBaseSensor):
    _attr_name = "Knob Brightness"
    _attr_icon = "mdi:knob"
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, data: dict, entry: ConfigEntry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_knob_brightness_sensor"

    @property
    def native_value(self) -> int:
        return self._state_store.knob_brightness


class VictrolaLastQuickPlaySensor(VictrolaBaseSensor):
    """Shows the last speaker that was sent a QuickPlay command.
    NOTE: This reflects what HA last sent - the API does not expose current playback state."""
    _attr_name = "Last Quick Play"
    _attr_icon = "mdi:play-circle"

    def __init__(self, data: dict, entry: ConfigEntry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_quickplay"

    @property
    def native_value(self) -> str:
        return self._state_store.quickplay_speaker or "None"

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "source": self._state_store.quickplay_source,
            "speaker_id": self._state_store.quickplay_speaker_id,
            "note": "Reflects last command sent by HA - not confirmed device state",
        }


class VictrolaLastDefaultOutputSensor(VictrolaBaseSensor):
    """Shows the last speaker set as Default Output.
    NOTE: This reflects what HA last sent - the API does not expose current default output."""
    _attr_name = "Last Default Output"
    _attr_icon = "mdi:speaker-multiple"

    def __init__(self, data: dict, entry: ConfigEntry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_default_output"

    @property
    def native_value(self) -> str:
        return self._state_store.default_speaker or "None"

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "source": self._state_store.default_source,
            "speaker_id": self._state_store.default_speaker_id,
            "note": "Reflects last command sent by HA - not confirmed device state",
        }

"""Sensor platform - all values polled from device."""
from __future__ import annotations
import logging
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, SOURCE_ROON, SOURCE_SONOS, SOURCE_UPNP, SOURCE_BLUETOOTH

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    entities = [
        VictrolaConnectionSensor(data, entry),
        VictrolaCurrentSourceSensor(data, entry),
        VictrolaDefaultSpeakerSensor(data, entry),       # from ui: getRows (authoritative)
        VictrolaCurrentQuickPlaySensor(data, entry),     # from speakerQuickplay getRows (preferred=True)
        VictrolaAudioQualitySensor(data, entry),
        VictrolaAudioLatencySensor(data, entry),
        VictrolaKnobBrightnessSensor(data, entry),
        VictrolaPowerStateSensor(data, entry),
        VictrolaVolumeSensor(data, entry),
        # Per-source default output sensors
        VictrolaDefaultOutputSensor(data, entry, SOURCE_ROON),
        VictrolaDefaultOutputSensor(data, entry, SOURCE_SONOS),
        VictrolaDefaultOutputSensor(data, entry, SOURCE_UPNP),
        VictrolaDefaultOutputSensor(data, entry, SOURCE_BLUETOOTH),
    ]
    async_add_entities(entities)


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

    def __init__(self, data, entry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_connection_status"

    @property
    def native_value(self):
        return "connected" if self._state_store.connected else "disconnected"

    @property
    def extra_state_attributes(self):
        return {"host": self._api.host}


class VictrolaCurrentSourceSensor(VictrolaBaseSensor):
    _attr_name = "Current Source"
    _attr_icon = "mdi:audio-input-stereo-minijack"

    def __init__(self, data, entry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_current_source"

    @property
    def native_value(self):
        return self._state_store.current_source

    @property
    def extra_state_attributes(self):
        return {s: self._state_store.source_enabled.get(s)
                for s in ["Roon", "Sonos", "UPnP", "Bluetooth"]}


class VictrolaDefaultSpeakerSensor(VictrolaBaseSensor):
    """Current default speaker - polled from ui: getRows (device-authoritative name)."""
    _attr_name = "Default Speaker"
    _attr_icon = "mdi:speaker-multiple"

    def __init__(self, data, entry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_default_speaker"

    @property
    def native_value(self) -> str:
        return self._state_store.current_default_speaker_name or "Unknown"

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "source": "ui: getRows row 1 title",
            "note": "Polled from device - reflects actual device state",
        }


class VictrolaCurrentQuickPlaySensor(VictrolaBaseSensor):
    """Current quickplay speaker - polled from speakerQuickplay getRows (preferred=True)."""
    _attr_name = "Current Quick Play"
    _attr_icon = "mdi:play-circle"

    def __init__(self, data, entry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_current_quickplay"

    @property
    def native_value(self) -> str:
        return self._state_store.quickplay_speaker or "None"

    @property
    def extra_state_attributes(self) -> dict:
        speakers = [
            {"name": s.get("name"), "id": s.get("id"), "preferred": s.get("preferred", False)}
            for s in self._state_store.available_quickplay_speakers
        ]
        return {
            "speaker_id": self._state_store.quickplay_speaker_id,
            "source": "speakerQuickplay getRows preferred=True",
            "note": "Polled from device - reflects actual device state",
            "available_speakers": speakers,
        }


class VictrolaAudioQualitySensor(VictrolaBaseSensor):
    _attr_name = "Audio Quality"
    _attr_icon = "mdi:music-note"

    def __init__(self, data, entry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_audio_quality_sensor"

    @property
    def native_value(self):
        return self._state_store.audio_quality


class VictrolaAudioLatencySensor(VictrolaBaseSensor):
    _attr_name = "Audio Latency"
    _attr_icon = "mdi:timer-outline"

    def __init__(self, data, entry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_audio_latency_sensor"

    @property
    def native_value(self):
        return self._state_store.audio_latency


class VictrolaKnobBrightnessSensor(VictrolaBaseSensor):
    _attr_name = "Knob Brightness"
    _attr_icon = "mdi:knob"
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, data, entry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_knob_brightness_sensor"

    @property
    def native_value(self) -> int | None:
        """Return numeric brightness value (0-100)."""
        return self._state_store.knob_brightness


class VictrolaPowerStateSensor(VictrolaBaseSensor):
    """Device power state from powermanager:target."""
    _attr_name = "Power State"
    _attr_icon = "mdi:power"

    def __init__(self, data, entry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_power_state"

    @property
    def native_value(self) -> str:
        return self._state_store.power_target or "Unknown"

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "reason": self._state_store.power_reason,
        }


class VictrolaVolumeSensor(VictrolaBaseSensor):
    """Device volume from player:volume."""
    _attr_name = "Volume"
    _attr_icon = "mdi:volume-high"
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, data, entry):
        super().__init__(data, entry)
        self._attr_unique_id = f"{entry.entry_id}_volume"

    @property
    def native_value(self) -> int | None:
        return self._state_store.volume


class VictrolaDefaultOutputSensor(VictrolaBaseSensor):
    """Current default output per source - from settings:/victrola getRows."""
    _attr_icon = "mdi:speaker-multiple"

    def __init__(self, data, entry, source: str):
        super().__init__(data, entry)
        self._source = source
        self._attr_unique_id = f"{entry.entry_id}_{source.lower()}_default_output"
        self._attr_name = f"{source} Default Output"

    @property
    def native_value(self) -> str:
        info = self._state_store.get_default_output(self._source)
        return info["name"] if info else "Unknown"

    @property
    def extra_state_attributes(self) -> dict:
        info = self._state_store.get_default_output(self._source)
        return {
            "speaker_id": info["id"] if info else None,
            "source": self._source,
            "note": "Polled from device via getRows - reflects actual device state",
        }

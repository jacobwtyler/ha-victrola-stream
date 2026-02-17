"""Internal state store - all values polled from device."""
from __future__ import annotations
from .const import AUDIO_QUALITY_OPTIONS, AUDIO_LATENCY_OPTIONS, BRIGHTNESS_MIN, BRIGHTNESS_MAX


class VictrolaStateStore:
    def __init__(self):
        self.current_source: str = "Roon"
        self.current_default_speaker_name: str | None = None  # from ui: getRows (authoritative)

        # QuickPlay: now POLLED from device via speakerQuickplay getRows (preferred=True)
        self.quickplay_speaker: str | None = None
        self.quickplay_speaker_id: str | None = None
        self.quickplay_source: str | None = None

        # Available quickplay speakers (full list from speakerQuickplay getRows)
        self.available_quickplay_speakers: list = []

        # Default Output per source (from settings:/victrola getRows rows 2,3,15)
        self.default_outputs: dict[str, dict] = {}

        # Settings
        self.audio_quality: str = "Standard"
        self.audio_latency: str = "Medium"
        self.knob_brightness: int = 100
        self.autoplay: bool = True
        self.volume: int | None = None
        self.power_target: str | None = None
        self.power_reason: str | None = None

        self.source_enabled: dict[str, bool] = {
            "Roon": True, "Sonos": True, "UPnP": True, "Bluetooth": True,
        }
        self.connected: bool = False

    def set_quickplay(self, source: str, speaker_name: str, speaker_id: str):
        self.quickplay_source = source
        self.quickplay_speaker = speaker_name
        self.quickplay_speaker_id = speaker_id

    def set_default_output(self, source: str, speaker_name: str, speaker_id: str):
        self.default_outputs[source] = {"name": speaker_name, "id": speaker_id}

    def get_default_output(self, source: str) -> dict | None:
        return self.default_outputs.get(source)

    def set_audio_quality(self, label: str):
        if label in AUDIO_QUALITY_OPTIONS:
            self.audio_quality = label

    def set_audio_latency(self, label: str):
        if label in AUDIO_LATENCY_OPTIONS:
            self.audio_latency = label

    def set_knob_brightness(self, value: int):
        self.knob_brightness = max(BRIGHTNESS_MIN, min(BRIGHTNESS_MAX, value))

    def set_source_enabled(self, source: str, enabled: bool):
        self.source_enabled[source] = enabled

    def to_dict(self) -> dict:
        return {
            "current_source": self.current_source,
            "current_default_speaker_name": self.current_default_speaker_name,
            "quickplay_speaker": self.quickplay_speaker,
            "quickplay_speaker_id": self.quickplay_speaker_id,
            "quickplay_source": self.quickplay_source,
            "default_outputs": self.default_outputs,
            "audio_quality": self.audio_quality,
            "audio_latency": self.audio_latency,
            "knob_brightness": self.knob_brightness,
            "autoplay": self.autoplay,
            "volume": self.volume,
            "power_target": self.power_target,
            "power_reason": self.power_reason,
            "source_enabled": self.source_enabled,
            "connected": self.connected,
        }

"""Internal state store - tracks last-sent commands and polled settings."""
from __future__ import annotations

from .const import AUDIO_QUALITY_OPTIONS, AUDIO_LATENCY_OPTIONS, BRIGHTNESS_MIN, BRIGHTNESS_MAX


class VictrolaStateStore:
    """Tracks Victrola state - settings polled from API, speaker state from last command."""

    def __init__(self):
        self.current_source: str = "Roon"

        # Last quickplay speaker
        self.quickplay_speaker: str | None = None
        self.quickplay_speaker_id: str | None = None
        self.quickplay_source: str | None = None

        # Last default output speaker
        self.default_speaker: str | None = None
        self.default_speaker_id: str | None = None
        self.default_source: str | None = None

        # Settings polled from device
        self.audio_quality: str = "Standard"
        self.audio_latency: str = "Medium"
        self.knob_brightness: int = 100
        self.autoplay: bool = True

        self.source_enabled: dict[str, bool] = {
            "Roon": True, "Sonos": True, "UPnP": True, "Bluetooth": True,
        }
        self.connected: bool = False

    def set_quickplay(self, source: str, speaker_name: str, speaker_id: str):
        self.quickplay_source = source
        self.quickplay_speaker = speaker_name
        self.quickplay_speaker_id = speaker_id

    def set_default_output(self, source: str, speaker_name: str, speaker_id: str):
        self.default_source = source
        self.default_speaker = speaker_name
        self.default_speaker_id = speaker_id

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
            "quickplay_speaker": self.quickplay_speaker,
            "quickplay_speaker_id": self.quickplay_speaker_id,
            "quickplay_source": self.quickplay_source,
            "default_speaker": self.default_speaker,
            "default_speaker_id": self.default_speaker_id,
            "default_source": self.default_source,
            "audio_quality": self.audio_quality,
            "audio_latency": self.audio_latency,
            "knob_brightness": self.knob_brightness,
            "autoplay": self.autoplay,
            "source_enabled": self.source_enabled,
            "connected": self.connected,
        }

"""Internal state store - Victrola API is write-only so we track state ourselves."""
from __future__ import annotations

from .const import (
    AUDIO_QUALITY_OPTIONS,
    AUDIO_LATENCY_OPTIONS,
    BRIGHTNESS_MIN,
    BRIGHTNESS_MAX,
)


class VictrolaStateStore:
    """Tracks current Victrola state since getData paths don't exist."""

    def __init__(self):
        # Source / speaker
        self.current_source: str = "Roon"
        self.current_speaker: str | None = None
        self.current_speaker_id: str | None = None

        # Settings
        self.audio_quality: str = "Standard"
        self.audio_latency: str = "Medium"
        self.knob_brightness: int = 100

        # Source enabled states
        self.source_enabled: dict[str, bool] = {
            "Roon": True,
            "Sonos": True,
            "UPnP": True,
            "Bluetooth": True,
        }

        # Autoplay
        self.autoplay: bool = True

        # Connection
        self.connected: bool = False

    def set_speaker(self, source: str, speaker_name: str, speaker_id: str):
        self.current_source = source
        self.current_speaker = speaker_name
        self.current_speaker_id = speaker_id

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
            "current_speaker": self.current_speaker,
            "current_speaker_id": self.current_speaker_id,
            "audio_quality": self.audio_quality,
            "audio_latency": self.audio_latency,
            "knob_brightness": self.knob_brightness,
            "source_enabled": self.source_enabled,
            "autoplay": self.autoplay,
            "connected": self.connected,
        }

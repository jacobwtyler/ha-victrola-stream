"""Tests for VictrolaStateStore."""
from custom_components.victrola_stream.state_store import VictrolaStateStore


class TestVictrolaStateStore:
    """Test state store initialization and setters."""

    def setup_method(self):
        self.store = VictrolaStateStore()

    # ── Defaults ──────────────────────────────────────────────────────

    def test_initial_defaults(self):
        assert self.store.current_source == "Roon"
        assert self.store.current_default_speaker_name is None
        assert self.store.quickplay_speaker is None
        assert self.store.quickplay_speaker_id is None
        assert self.store.quickplay_source is None
        assert self.store.audio_quality == "Standard"
        assert self.store.audio_latency == "Medium"
        assert self.store.rca_mode == "Switching"
        assert self.store.rca_delay == 0
        assert self.store.rca_fixed_volume is False
        assert self.store.knob_brightness == 100
        assert self.store.autoplay is True
        assert self.store.volume is None
        assert self.store.muted is False
        assert self.store.power_target is None
        assert self.store.connected is False

    def test_initial_source_enabled(self):
        assert self.store.source_enabled == {
            "Roon": True, "Sonos": True, "UPnP": True, "Bluetooth": True,
        }

    # ── QuickPlay ─────────────────────────────────────────────────────

    def test_set_quickplay(self):
        self.store.set_quickplay("Sonos", "Living Room", "spk-123")
        assert self.store.quickplay_source == "Sonos"
        assert self.store.quickplay_speaker == "Living Room"
        assert self.store.quickplay_speaker_id == "spk-123"

    # ── Default output ────────────────────────────────────────────────

    def test_set_and_get_default_output(self):
        self.store.set_default_output("Sonos", "Kitchen", "k-1")
        result = self.store.get_default_output("Sonos")
        assert result == {"name": "Kitchen", "id": "k-1"}

    def test_get_default_output_missing(self):
        assert self.store.get_default_output("Roon") is None

    # ── Audio quality ─────────────────────────────────────────────────

    def test_set_audio_quality_valid(self):
        self.store.set_audio_quality("Prioritize Connection")
        assert self.store.audio_quality == "Prioritize Connection"

    def test_set_audio_quality_invalid_ignored(self):
        self.store.set_audio_quality("InvalidOption")
        assert self.store.audio_quality == "Standard"

    # ── Audio latency ─────────────────────────────────────────────────

    def test_set_audio_latency_valid(self):
        self.store.set_audio_latency("Low")
        assert self.store.audio_latency == "Low"

    def test_set_audio_latency_invalid_ignored(self):
        self.store.set_audio_latency("InvalidOption")
        assert self.store.audio_latency == "Medium"

    # ── RCA mode ──────────────────────────────────────────────────────

    def test_set_rca_mode_valid(self):
        self.store.set_rca_mode("Simultaneous")
        assert self.store.rca_mode == "Simultaneous"

    def test_set_rca_mode_invalid_ignored(self):
        self.store.set_rca_mode("InvalidMode")
        assert self.store.rca_mode == "Switching"

    # ── RCA delay ─────────────────────────────────────────────────────

    def test_set_rca_delay(self):
        self.store.set_rca_delay(250)
        assert self.store.rca_delay == 250

    def test_set_rca_delay_clamped_low(self):
        self.store.set_rca_delay(-10)
        assert self.store.rca_delay == 0

    def test_set_rca_delay_clamped_high(self):
        self.store.set_rca_delay(999)
        assert self.store.rca_delay == 500

    # ── RCA fixed volume ──────────────────────────────────────────────

    def test_set_rca_fixed_volume(self):
        self.store.set_rca_fixed_volume(True)
        assert self.store.rca_fixed_volume is True
        self.store.set_rca_fixed_volume(False)
        assert self.store.rca_fixed_volume is False

    # ── Knob brightness ───────────────────────────────────────────────

    def test_set_knob_brightness(self):
        self.store.set_knob_brightness(50)
        assert self.store.knob_brightness == 50

    def test_set_knob_brightness_clamped_low(self):
        self.store.set_knob_brightness(-5)
        assert self.store.knob_brightness == 0

    def test_set_knob_brightness_clamped_high(self):
        self.store.set_knob_brightness(200)
        assert self.store.knob_brightness == 100

    # ── Source enabled ────────────────────────────────────────────────

    def test_set_source_enabled(self):
        self.store.set_source_enabled("Roon", False)
        assert self.store.source_enabled["Roon"] is False

    # ── to_dict ───────────────────────────────────────────────────────

    def test_to_dict_contains_all_keys(self):
        d = self.store.to_dict()
        expected_keys = {
            "current_source", "current_default_speaker_name",
            "quickplay_speaker", "quickplay_speaker_id", "quickplay_source",
            "default_outputs", "audio_quality", "audio_latency",
            "rca_mode", "rca_delay", "rca_fixed_volume", "knob_brightness",
            "autoplay", "volume", "muted", "power_target", "power_reason",
            "source_enabled", "connected",
        }
        assert set(d.keys()) == expected_keys

    def test_to_dict_reflects_changes(self):
        self.store.set_quickplay("Sonos", "Bedroom", "bed-1")
        self.store.volume = 42
        self.store.connected = True
        d = self.store.to_dict()
        assert d["quickplay_speaker"] == "Bedroom"
        assert d["volume"] == 42
        assert d["connected"] is True

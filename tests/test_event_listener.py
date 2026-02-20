"""Tests for VictrolaEventListener event handling logic."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from custom_components.victrola_stream.event_listener import VictrolaEventListener
from custom_components.victrola_stream.state_store import VictrolaStateStore
from custom_components.victrola_stream.const import (
    SOURCE_ROON, SOURCE_SONOS, SOURCE_UPNP, SOURCE_BLUETOOTH,
)


@pytest.fixture
def listener():
    api = AsyncMock()
    store = VictrolaStateStore()
    discovery = MagicMock()
    coordinator = MagicMock()
    el = VictrolaEventListener(api, store, discovery, coordinator)
    return el, api, store, discovery, coordinator


class TestHandleEvents:
    """Test _handle_events with different event types."""

    @pytest.mark.asyncio
    async def test_volume_change(self, listener):
        el, api, store, discovery, coordinator = listener
        events = [{"path": "player:volume", "value": {"i32_": 75}}]
        changed = await el._handle_events(events)
        assert changed is True
        assert store.volume == 75

    @pytest.mark.asyncio
    async def test_power_target_change(self, listener):
        el, api, store, discovery, coordinator = listener
        events = [{
            "path": "powermanager:target",
            "value": {"powerTarget": {"target": "networkStandby", "reason": "user"}},
        }]
        changed = await el._handle_events(events)
        assert changed is True
        assert store.power_target == "networkStandby"
        assert store.power_reason == "user"

    @pytest.mark.asyncio
    async def test_audio_quality_change(self, listener):
        el, api, store, discovery, coordinator = listener
        events = [{
            "path": "settings:/victrola/forceLowBitrate",
            "value": {"forceLowBitrate": "losslessQuality"},
        }]
        changed = await el._handle_events(events)
        assert changed is True
        assert store.audio_quality == "Prioritize Audio (FLAC)"

    @pytest.mark.asyncio
    async def test_audio_latency_change(self, listener):
        el, api, store, discovery, coordinator = listener
        events = [{
            "path": "settings:/victrola/wirelessAudioDelay",
            "value": {"adchlsLatency": "min"},
        }]
        changed = await el._handle_events(events)
        assert changed is True
        assert store.audio_latency == "Low"

    @pytest.mark.asyncio
    async def test_knob_brightness_change(self, listener):
        el, api, store, discovery, coordinator = listener
        events = [{
            "path": "settings:/victrola/lightBrightness",
            "value": {"i32_": 42},
        }]
        changed = await el._handle_events(events)
        assert changed is True
        assert store.knob_brightness == 42

    @pytest.mark.asyncio
    async def test_mute_change(self, listener):
        el, api, store, discovery, coordinator = listener
        events = [{
            "path": "settings:/mediaPlayer/mute",
            "value": {"bool_": True},
        }]
        changed = await el._handle_events(events)
        assert changed is True
        assert store.muted is True

    @pytest.mark.asyncio
    async def test_autoplay_change(self, listener):
        el, api, store, discovery, coordinator = listener
        events = [{
            "path": "settings:/victrola/autoplay",
            "value": {"bool_": False},
        }]
        changed = await el._handle_events(events)
        assert changed is True
        assert store.autoplay is False

    @pytest.mark.asyncio
    async def test_source_enabled_sonos(self, listener):
        el, api, store, discovery, coordinator = listener
        events = [{
            "path": "settings:/victrola/sonosEnabled",
            "value": {"bool_": True},
        }]
        changed = await el._handle_events(events)
        assert changed is True
        assert store.source_enabled[SOURCE_SONOS] is True
        assert store.current_source == SOURCE_SONOS

    @pytest.mark.asyncio
    async def test_source_disabled(self, listener):
        el, api, store, discovery, coordinator = listener
        events = [{
            "path": "settings:/victrola/roonEnabled",
            "value": {"bool_": False},
        }]
        changed = await el._handle_events(events)
        assert changed is True
        assert store.source_enabled[SOURCE_ROON] is False

    @pytest.mark.asyncio
    async def test_speaker_selection_change(self, listener):
        el, api, store, discovery, coordinator = listener
        api.async_get_ui_state.return_value = {
            "current_default_speaker_name": "Kitchen Speaker"
        }
        events = [{"path": "victrola:ui/speakerSelection"}]
        changed = await el._handle_events(events)
        assert changed is True
        assert store.current_default_speaker_name == "Kitchen Speaker"

    @pytest.mark.asyncio
    async def test_quickplay_rows_change(self, listener):
        el, api, store, discovery, coordinator = listener
        events = [{
            "path": "victrola:ui/speakerQuickplay",
            "rows": [
                {"title": "Bedroom", "id": "bed-1", "path": "/p", "type": "victrolaQuickplaySonos", "preferred": True},
                {"title": "Kitchen", "id": "kit-1", "path": "/p", "type": "victrolaQuickplaySonos", "preferred": False},
            ],
        }]
        changed = await el._handle_events(events)
        assert changed is True
        assert store.quickplay_speaker == "Bedroom"
        assert store.quickplay_speaker_id == "bed-1"
        discovery.update_from_quickplay.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_change_on_empty_events(self, listener):
        el, api, store, discovery, coordinator = listener
        changed = await el._handle_events([])
        assert changed is False

    @pytest.mark.asyncio
    async def test_non_dict_events_skipped(self, listener):
        el, api, store, discovery, coordinator = listener
        changed = await el._handle_events(["not-a-dict", 42, None])
        assert changed is False

    @pytest.mark.asyncio
    async def test_unknown_path_no_change(self, listener):
        el, api, store, discovery, coordinator = listener
        events = [{"path": "unknown:path", "value": {"foo": "bar"}}]
        changed = await el._handle_events(events)
        assert changed is False


class TestParseQuickplayRows:
    """Test _parse_quickplay_rows parsing logic."""

    def test_parse_valid_rows(self, listener):
        el, *_ = listener
        rows = [
            {"title": "Speaker A", "id": "a-1", "path": "/a", "type": "victrolaQuickplaySonos", "preferred": True, "value": {}},
            {"title": "Speaker B", "id": "b-1", "path": "/b", "type": "victrolaQuickplaySonos", "preferred": False, "value": {}},
        ]
        result = el._parse_quickplay_rows(rows)
        assert len(result) == 2
        assert result[0]["name"] == "Speaker A"
        assert result[0]["preferred"] is True
        assert result[1]["name"] == "Speaker B"

    def test_parse_skips_invalid_rows(self, listener):
        el, *_ = listener
        rows = [
            "not a dict",
            {"title": None, "id": "a-1"},  # no name
            {"title": "Valid", "id": None},  # no id
            {"title": "Good", "id": "g-1", "path": "/g", "type": "t", "preferred": False, "value": {}},
        ]
        result = el._parse_quickplay_rows(rows)
        assert len(result) == 1
        assert result[0]["name"] == "Good"

    def test_parse_extracts_sonos_group(self, listener):
        el, *_ = listener
        rows = [{
            "title": "Group",
            "id": "grp-1",
            "path": "/p",
            "type": "victrolaQuickplaySonos",
            "preferred": False,
            "value": {
                "type": "sonosGroup",
                "sonosGroup": {"sonosGroupId": "sg-123", "groupName": "My Group"},
            },
        }]
        result = el._parse_quickplay_rows(rows)
        assert result[0]["sonos_group_id"] == "sg-123"

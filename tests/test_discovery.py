"""Tests for VictrolaDiscovery public accessors and update_from_quickplay."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from custom_components.victrola_stream.discovery import VictrolaDiscovery
from custom_components.victrola_stream.const import (
    SOURCE_SONOS, SOURCE_ROON, SOURCE_UPNP, SOURCE_BLUETOOTH,
)


@pytest.fixture
def discovery():
    hass = MagicMock()
    api = AsyncMock()
    return VictrolaDiscovery(hass, api)


class TestDiscoveryAccessors:
    """Test public accessor methods with pre-populated caches."""

    def test_get_speakers_empty(self, discovery):
        assert discovery.get_speakers(SOURCE_SONOS) == {}

    def test_get_speaker_names_empty(self, discovery):
        assert discovery.get_speaker_names(SOURCE_ROON) == []

    def test_get_victrola_id_missing(self, discovery):
        assert discovery.get_victrola_id(SOURCE_SONOS, "Missing") is None

    def test_get_quickplay_speakers_empty(self, discovery):
        assert discovery.get_quickplay_speakers() == {}

    def test_get_quickplay_speaker_names_empty(self, discovery):
        assert discovery.get_quickplay_speaker_names() == []

    def test_get_quickplay_speaker_missing(self, discovery):
        assert discovery.get_quickplay_speaker("Missing") is None

    def test_get_quickplay_id_missing(self, discovery):
        assert discovery.get_quickplay_id("Missing") is None

    def test_find_speaker_name_by_id_not_found(self, discovery):
        assert discovery.find_speaker_name_by_id("id-999") is None


class TestDiscoveryWithData:
    """Test accessors after populating caches."""

    def test_get_speakers_populated(self, discovery):
        discovery._speakers[SOURCE_SONOS] = {
            "Kitchen": {"id": "k1", "type": "victrolaOutputSonos", "path": "/p", "preferred": False},
            "Bedroom": {"id": "b1", "type": "victrolaOutputSonos", "path": "/p", "preferred": True},
        }
        result = discovery.get_speakers(SOURCE_SONOS)
        assert len(result) == 2
        assert "Kitchen" in result
        assert "Bedroom" in result

    def test_get_speaker_names_sorted(self, discovery):
        discovery._speakers[SOURCE_ROON] = {
            "Zebra": {"id": "z"},
            "Alpha": {"id": "a"},
        }
        assert discovery.get_speaker_names(SOURCE_ROON) == ["Alpha", "Zebra"]

    def test_get_victrola_id(self, discovery):
        discovery._speakers[SOURCE_UPNP] = {
            "TV": {"id": "tv-123"},
        }
        assert discovery.get_victrola_id(SOURCE_UPNP, "TV") == "tv-123"

    def test_find_speaker_name_by_id(self, discovery):
        discovery._speakers[SOURCE_BLUETOOTH] = {
            "Headphones": {"id": "bt-abc"},
        }
        assert discovery.find_speaker_name_by_id("bt-abc") == "Headphones"

    def test_find_speaker_name_by_id_cross_source(self, discovery):
        discovery._speakers[SOURCE_SONOS] = {
            "Sonos One": {"id": "s1"},
        }
        discovery._speakers[SOURCE_ROON] = {
            "Roon Core": {"id": "r1"},
        }
        assert discovery.find_speaker_name_by_id("r1") == "Roon Core"


class TestUpdateFromQuickplay:
    """Test the update_from_quickplay method (used by event listener)."""

    def test_update_from_quickplay_sonos(self, discovery):
        speakers = [
            {"name": "Living Room", "id": "lr-1", "path": "/p1", "type": "victrolaQuickplaySonos", "preferred": True},
            {"name": "Kitchen", "id": "k-1", "path": "/p2", "type": "victrolaQuickplaySonos", "preferred": False},
        ]
        discovery.update_from_quickplay(speakers)
        names = discovery.get_quickplay_speaker_names()
        assert "Living Room (Sonos)" in names
        assert "Kitchen (Sonos)" in names

    def test_update_from_quickplay_roon(self, discovery):
        speakers = [
            {"name": "Studio", "id": "st-1", "path": "/p", "type": "victrolaQuickplayRoon", "preferred": False},
        ]
        discovery.update_from_quickplay(speakers)
        assert "Studio (Roon)" in discovery.get_quickplay_speaker_names()

    def test_update_from_quickplay_upnp(self, discovery):
        speakers = [
            {"name": "TV", "id": "tv-1", "path": "/p", "type": "victrolaQuickplayUPnP", "preferred": False},
        ]
        discovery.update_from_quickplay(speakers)
        assert "TV (UPnP)" in discovery.get_quickplay_speaker_names()

    def test_update_from_quickplay_bluetooth(self, discovery):
        speakers = [
            {"name": "Earbuds", "id": "eb-1", "path": "/p", "type": "victrolaQuickplayBluetooth", "preferred": False},
        ]
        discovery.update_from_quickplay(speakers)
        assert "Earbuds (Bluetooth)" in discovery.get_quickplay_speaker_names()

    def test_update_from_quickplay_unknown_type(self, discovery):
        speakers = [
            {"name": "Mystery", "id": "m-1", "path": "/p", "type": "somethingNew", "preferred": False},
        ]
        discovery.update_from_quickplay(speakers)
        assert "Mystery (Unknown)" in discovery.get_quickplay_speaker_names()

    def test_update_from_quickplay_replaces_previous(self, discovery):
        discovery.update_from_quickplay([
            {"name": "Old", "id": "o-1", "path": "/p", "type": "victrolaQuickplaySonos", "preferred": False},
        ])
        assert len(discovery.get_quickplay_speaker_names()) == 1
        discovery.update_from_quickplay([
            {"name": "New", "id": "n-1", "path": "/p", "type": "victrolaQuickplaySonos", "preferred": False},
        ])
        names = discovery.get_quickplay_speaker_names()
        assert len(names) == 1
        assert "New (Sonos)" in names

    def test_update_from_quickplay_skips_nameless(self, discovery):
        speakers = [
            {"name": None, "id": "x-1", "path": "/p", "type": "victrolaQuickplaySonos", "preferred": False},
            {"name": "Valid", "id": "v-1", "path": "/p", "type": "victrolaQuickplaySonos", "preferred": False},
        ]
        discovery.update_from_quickplay(speakers)
        assert len(discovery.get_quickplay_speaker_names()) == 1

    def test_get_quickplay_id_after_update(self, discovery):
        speakers = [
            {"name": "Living Room", "id": "lr-1", "path": "/p1", "type": "victrolaQuickplaySonos", "preferred": True},
        ]
        discovery.update_from_quickplay(speakers)
        assert discovery.get_quickplay_id("Living Room (Sonos)") == "lr-1"

    def test_get_quickplay_speaker_info(self, discovery):
        speakers = [
            {"name": "Living Room", "id": "lr-1", "path": "/p1", "type": "victrolaQuickplaySonos", "preferred": True},
        ]
        discovery.update_from_quickplay(speakers)
        info = discovery.get_quickplay_speaker("Living Room (Sonos)")
        assert info is not None
        assert info["id"] == "lr-1"
        assert info["source"] == SOURCE_SONOS
        assert info["original_name"] == "Living Room"
        assert info["preferred"] is True

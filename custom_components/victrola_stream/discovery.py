"""Dynamic speaker discovery - populated from device's live speakerQuickplay API."""
from __future__ import annotations
import logging
from homeassistant.core import HomeAssistant
from .const import SOURCE_SONOS, SOURCE_ROON, SOURCE_UPNP, SOURCE_BLUETOOTH, DEFAULT_ROON_CORE_ID

_LOGGER = logging.getLogger(__name__)


class VictrolaDiscovery:
    """Manages live speaker list fetched from victrola:ui/speakerQuickplay.

    Speaker data is populated on startup and refreshed each coordinator cycle.
    Each speaker entry: {name -> {victrola_id, path, type, sonos_group_id, source}}
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        # Live speakers from speakerQuickplay (Sonos-based, from device)
        self._quickplay_speakers: dict[str, dict] = {}
        # Roon/UPnP/Bluetooth from settings:/victrola getRows
        self._default_output_speakers: dict[str, dict[str, dict]] = {
            SOURCE_ROON:      {},
            SOURCE_SONOS:     {},
            SOURCE_UPNP:      {},
            SOURCE_BLUETOOTH: {},
        }

    def update_from_quickplay(self, speakers: list[dict]) -> None:
        """Update speaker list from speakerQuickplay getRows response."""
        self._quickplay_speakers = {}
        self._default_output_speakers[SOURCE_SONOS] = {}

        for spk in speakers:
            name  = spk.get("name") or spk.get("title")
            spk_id = spk.get("id")
            if not name or not spk_id:
                continue

            entry = {
                "victrola_id":    spk_id,
                "path":           spk.get("path"),
                "type":           spk.get("type", "victrolaQuickplaySonos"),
                "sonos_group_id": spk.get("sonos_group_id"),
                "source":         SOURCE_SONOS,
                "preferred":      spk.get("preferred", False),
            }
            self._quickplay_speakers[name] = entry
            self._default_output_speakers[SOURCE_SONOS][name] = entry

        _LOGGER.debug(
            "Discovery updated: %d quickplay speakers: %s",
            len(self._quickplay_speakers),
            list(self._quickplay_speakers.keys()),
        )

    def update_roon_speaker(self, name: str, victrola_id: str) -> None:
        """Register a Roon speaker by its full output ID."""
        self._default_output_speakers[SOURCE_ROON][name] = {
            "victrola_id": victrola_id,
            "source": SOURCE_ROON,
        }

    def update_upnp_speaker(self, name: str, victrola_id: str) -> None:
        """Register a UPnP speaker by its UUID."""
        self._default_output_speakers[SOURCE_UPNP][name] = {
            "victrola_id": victrola_id,
            "source": SOURCE_UPNP,
        }

    def update_bluetooth_speaker(self, name: str, victrola_id: str) -> None:
        """Register a Bluetooth speaker."""
        self._default_output_speakers[SOURCE_BLUETOOTH][name] = {
            "victrola_id": victrola_id,
            "source": SOURCE_BLUETOOTH,
        }

    # ── Public accessors ─────────────────────────────────────────────────

    def get_quickplay_speakers(self) -> dict[str, dict]:
        """Return all speakers available for quickplay (live from device)."""
        return self._quickplay_speakers

    def get_quickplay_speaker_names(self) -> list[str]:
        """Return sorted list of quickplay speaker names."""
        return sorted(self._quickplay_speakers.keys())

    def get_speakers(self, source: str) -> dict[str, dict]:
        """Return speakers for a specific source (for Default Output selects)."""
        return self._default_output_speakers.get(source, {})

    def get_speaker_names(self, source: str) -> list[str]:
        """Return sorted speaker names for a source."""
        return sorted(self._default_output_speakers.get(source, {}).keys())

    def get_victrola_id(self, source: str, name: str) -> str | None:
        """Get Victrola ID for a speaker by source + name."""
        speakers = self._default_output_speakers.get(source, {})
        entry = speakers.get(name)
        return entry.get("victrola_id") if entry else None

    def get_quickplay_id(self, name: str) -> str | None:
        """Get Victrola ID for a quickplay speaker by name."""
        entry = self._quickplay_speakers.get(name)
        return entry.get("victrola_id") if entry else None

    def find_speaker_name_by_id(self, victrola_id: str) -> str | None:
        """Reverse lookup: find any speaker name from its ID across all sources."""
        for source_dict in self._default_output_speakers.values():
            for name, info in source_dict.items():
                if info.get("victrola_id") == victrola_id:
                    return name
        return None

    async def async_discover_all(self) -> None:
        """Called on startup - actual population happens via coordinator first refresh."""
        _LOGGER.debug("Discovery initialized - speakers will populate on first coordinator refresh")

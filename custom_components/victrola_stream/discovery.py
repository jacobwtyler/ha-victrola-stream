"""Safe speaker discovery via victrola:ui/speakerSelection.

Switches sources temporarily with autoplay disabled to discover all speakers.
"""
from __future__ import annotations
import asyncio
import logging
from homeassistant.core import HomeAssistant
from .const import SOURCE_SONOS, SOURCE_ROON, SOURCE_UPNP, SOURCE_BLUETOOTH

_LOGGER = logging.getLogger(__name__)

# Discovery delays per source (seconds to wait for speaker list to populate)
DISCOVERY_DELAYS = {
    SOURCE_SONOS:     5,
    SOURCE_ROON:      8,
    SOURCE_UPNP:      5,
    SOURCE_BLUETOOTH: 5,
}


class VictrolaDiscovery:
    """Discovers speakers by temporarily enabling each source.
    
    Safe discovery procedure:
    1. Save current source + autoplay state
    2. Disable autoplay (prevent playback during discovery)
    3. Enable each source, wait, read speakerSelection
    4. Restore original source + autoplay
    """

    def __init__(self, hass: HomeAssistant, api) -> None:
        self._hass = hass
        self._api = api
        # Speaker cache: {source: {name: {id, type, path, ...}}}
        self._speakers: dict[str, dict[str, dict]] = {
            SOURCE_SONOS:     {},
            SOURCE_ROON:      {},
            SOURCE_UPNP:      {},
            SOURCE_BLUETOOTH: {},
        }
        # QuickPlay speakers (Sonos-only, from speakerQuickplay)
        self._quickplay_speakers: dict[str, dict] = {}

    async def async_discover_all(self) -> None:
        """Safely discover speakers from all sources.
        
        Called on startup only. Takes ~25 seconds.
        """
        _LOGGER.info("Starting speaker discovery across all sources...")
        
        try:
            # 1. Save current state
            original_autoplay = await self._api.async_get_autoplay()
            original_source = await self._get_current_source()
            _LOGGER.debug("Saved state: source=%s, autoplay=%s", original_source, original_autoplay)

            # 2. Disable autoplay to prevent playback during discovery
            if original_autoplay:
                await self._api.async_set_autoplay(False)
                await asyncio.sleep(0.5)

            # 3. Discover each source
            for source in [SOURCE_SONOS, SOURCE_ROON, SOURCE_UPNP, SOURCE_BLUETOOTH]:
                await self._discover_source(source)

            # 4. Update QuickPlay speakers (reads speakerQuickplay)
            await self._update_quickplay()

            # 5. Restore original state (CRITICAL: end on original source)
            if original_source:
                await self._enable_source(original_source)
                await asyncio.sleep(1)
            if original_autoplay:
                await self._api.async_set_autoplay(True)

            total = sum(len(speakers) for speakers in self._speakers.values())
            _LOGGER.info(
                "Discovery complete: %d speakers (%s: %d, %s: %d, %s: %d, %s: %d)",
                total,
                SOURCE_SONOS, len(self._speakers[SOURCE_SONOS]),
                SOURCE_ROON, len(self._speakers[SOURCE_ROON]),
                SOURCE_UPNP, len(self._speakers[SOURCE_UPNP]),
                SOURCE_BLUETOOTH, len(self._speakers[SOURCE_BLUETOOTH]),
            )

        except Exception as err:
            _LOGGER.error("Discovery failed: %s", err)

    async def async_rediscover_current(self) -> None:
        """Rediscover speakers for currently active source only.
        
        Called when user presses Rediscover button or manually changes source.
        Takes 5-8 seconds depending on source.
        """
        current_source = await self._get_current_source()
        if not current_source:
            _LOGGER.warning("No source currently active, skipping rediscovery")
            return
        
        _LOGGER.info("Rediscovering %s speakers (already on this source)...", current_source)
        await self._discover_source(current_source)
        
        # Also update QuickPlay if relevant
        if current_source in (SOURCE_SONOS, SOURCE_ROON):
            await self._update_quickplay()

    async def _discover_source(self, source: str) -> None:
        """Enable a source, wait for discovery, read speakers."""
        _LOGGER.debug("Discovering %s speakers...", source)
        
        # Enable source
        await self._enable_source(source)
        
        # Wait for device to discover speakers
        delay = DISCOVERY_DELAYS.get(source, 5)
        await asyncio.sleep(delay)
        
        # Read speakerSelection
        speakers_list = await self._api.async_get_speaker_selection()
        
        # Parse and cache
        self._speakers[source] = {}
        for spk in speakers_list:
            name = spk.get("title")
            if not name:
                continue
            self._speakers[source][name] = {
                "id": spk.get("id"),
                "type": spk.get("type"),
                "path": spk.get("path"),
                "preferred": spk.get("preferred", False),
                "sonos_group_id": spk.get("sonos_group_id"),
            }
        
        _LOGGER.debug("Found %d %s speakers: %s", 
                      len(self._speakers[source]), source, 
                      list(self._speakers[source].keys()))

    async def _update_quickplay(self) -> None:
        """Update QuickPlay speaker list (from speakerQuickplay) with source labels."""
        qp_state = await self._api.async_get_quickplay_state()
        if qp_state.get("speakers"):
            self._quickplay_speakers = {}
            for spk in qp_state["speakers"]:
                name = spk.get("name")
                spk_type = spk.get("type", "")
                
                # Determine source from type
                if "Sonos" in spk_type:
                    source = SOURCE_SONOS
                elif "Roon" in spk_type:
                    source = SOURCE_ROON
                elif "UPnP" in spk_type:
                    source = SOURCE_UPNP
                elif "Bluetooth" in spk_type:
                    source = SOURCE_BLUETOOTH
                else:
                    source = "Unknown"
                
                if name:
                    # Add source label to name for clarity
                    display_name = f"{name} ({source})"
                    self._quickplay_speakers[display_name] = {
                        "id": spk.get("id"),
                        "path": spk.get("path"),
                        "type": spk_type,
                        "source": source,
                        "original_name": name,
                        "preferred": spk.get("preferred", False),
                    }

    async def _enable_source(self, source: str) -> None:
        """Enable a specific source, disabling all others first."""
        source_to_api = {
            SOURCE_SONOS:     "sonos",
            SOURCE_ROON:      "roon",
            SOURCE_UPNP:      "upnp",
            SOURCE_BLUETOOTH: "bluetooth",
        }
        api_name = source_to_api.get(source)
        if api_name:
            await self._api.async_set_source_enabled(api_name, True)

    async def _get_current_source(self) -> str | None:
        """Determine which source is currently enabled."""
        state = await self._api.async_get_current_default_outputs()
        if state.get("roon_enabled"):
            return SOURCE_ROON
        if state.get("sonos_enabled"):
            return SOURCE_SONOS
        if state.get("upnp_enabled"):
            return SOURCE_UPNP
        if state.get("bluetooth_enabled"):
            return SOURCE_BLUETOOTH
        return None

    # ── Public accessors for select entities ─────────────────────────────

    def get_speakers(self, source: str) -> dict[str, dict]:
        """Get all speakers for a source (for Default Output selects)."""
        return self._speakers.get(source, {})

    def get_speaker_names(self, source: str) -> list[str]:
        """Get sorted speaker names for a source."""
        return sorted(self._speakers.get(source, {}).keys())

    def get_victrola_id(self, source: str, name: str) -> str | None:
        """Get Victrola ID for a speaker by source + name."""
        speakers = self._speakers.get(source, {})
        entry = speakers.get(name)
        return entry.get("id") if entry else None

    def get_quickplay_speakers(self) -> dict[str, dict]:
        """Get all QuickPlay speakers (live from speakerQuickplay)."""
        return self._quickplay_speakers

    def get_quickplay_speaker_names(self) -> list[str]:
        """Get sorted QuickPlay speaker names."""
        return sorted(self._quickplay_speakers.keys())

    def get_quickplay_speaker(self, name: str) -> dict | None:
        """Get full QuickPlay speaker info by name."""
        return self._quickplay_speakers.get(name)

    def get_quickplay_id(self, name: str) -> str | None:
        """Get Victrola ID for a QuickPlay speaker by name."""
        entry = self._quickplay_speakers.get(name)
        return entry.get("id") if entry else None

    def update_from_quickplay(self, speakers: list[dict]) -> None:
        """Update QuickPlay speaker cache from event listener data.

        Called when the event listener receives a speakerQuickplay rows event.
        Rebuilds the quickplay cache with source labels, same as _update_quickplay
        but from pre-parsed speaker dicts instead of an API call.
        """
        self._quickplay_speakers = {}
        for spk in speakers:
            name = spk.get("name")
            spk_type = spk.get("type", "")

            if "Sonos" in spk_type:
                source = SOURCE_SONOS
            elif "Roon" in spk_type:
                source = SOURCE_ROON
            elif "UPnP" in spk_type:
                source = SOURCE_UPNP
            elif "Bluetooth" in spk_type:
                source = SOURCE_BLUETOOTH
            else:
                source = "Unknown"

            if name:
                display_name = f"{name} ({source})"
                self._quickplay_speakers[display_name] = {
                    "id": spk.get("id"),
                    "path": spk.get("path"),
                    "type": spk_type,
                    "source": source,
                    "original_name": name,
                    "preferred": spk.get("preferred", False),
                }

    def find_speaker_name_by_id(self, speaker_id: str) -> str | None:
        """Reverse lookup: find speaker name from its ID across all sources."""
        for source_dict in self._speakers.values():
            for name, info in source_dict.items():
                if info.get("id") == speaker_id:
                    return name
        return None

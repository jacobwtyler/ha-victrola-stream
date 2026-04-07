"""Coordinator - 30s polling fallback. Real-time updates via event_listener."""
from __future__ import annotations
import asyncio
from datetime import timedelta
import logging
from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import (
    DOMAIN, DEFAULT_SCAN_INTERVAL, SOURCES,
    AUDIO_QUALITY_API_TO_LABEL, AUDIO_LATENCY_API_TO_LABEL,
    RCA_MODE_API_TO_LABEL,
    SOURCE_ROON, SOURCE_SONOS, SOURCE_UPNP, SOURCE_BLUETOOTH,
    STARTUP_SOURCE_LAST_KNOWN, STARTUP_SOURCE_NONE,
)

_LOGGER = logging.getLogger(__name__)


class VictrolaCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, api, state_store, discovery) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self.state_store = state_store
        self.discovery = discovery
        self._discovery_done = False  # Run full discovery once on startup

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            connected = await self.api.async_test_connection()
            self.state_store.connected = connected
            if not connected:
                return self.state_store.to_dict()

            # ── ONE-TIME: Full speaker discovery on first refresh ──
            if not self._discovery_done:
                await self.discovery.async_discover_all()
                self._discovery_done = True

            # ── 1. speakerQuickplay → live speaker list + current quickplay ──
            qp_state = await self.api.async_get_quickplay_state()
            if qp_state.get("speakers"):
                self.state_store.available_quickplay_speakers = qp_state["speakers"]
                # Update discovery QuickPlay cache with source labels
                await self.discovery._update_quickplay()
            if qp_state.get("current_quickplay_name"):
                qp_source = self._source_from_type(
                    qp_state.get("current_quickplay_type", "")
                )
                # Use display name (with source suffix) to match options list
                raw_name = qp_state["current_quickplay_name"]
                display_name = f"{raw_name} ({qp_source})"
                # Verify the display name exists in discovery cache;
                # fall back to raw name if not found (shouldn't happen)
                if not self.discovery.get_quickplay_speaker(display_name):
                    _LOGGER.debug(
                        "QuickPlay display name '%s' not in discovery cache, "
                        "using raw name '%s'", display_name, raw_name
                    )
                    display_name = raw_name
                self.state_store.set_quickplay(
                    qp_source,
                    display_name,
                    qp_state.get("current_quickplay_id", ""),
                )
            else:
                # No preferred speaker — playback stopped or no quickplay active
                self.state_store.quickplay_speaker = None
                self.state_store.quickplay_speaker_id = None
                self.state_store.quickplay_source = None

            # ── 2. settings:/victrola getRows → settings + default output IDs ──
            device_state = await self.api.async_get_current_default_outputs()
            if device_state:
                if device_state.get("audio_quality_api"):
                    self.state_store.set_audio_quality(
                        AUDIO_QUALITY_API_TO_LABEL.get(device_state["audio_quality_api"], "Standard")
                    )
                if device_state.get("audio_latency_api"):
                    self.state_store.set_audio_latency(
                        AUDIO_LATENCY_API_TO_LABEL.get(device_state["audio_latency_api"], "Medium")
                    )
                if device_state.get("knob_brightness") is not None:
                    self.state_store.set_knob_brightness(device_state["knob_brightness"])
                if device_state.get("autoplay") is not None:
                    self.state_store.autoplay = device_state["autoplay"]

                source_map = {
                    "roon_enabled":      SOURCE_ROON,
                    "sonos_enabled":     SOURCE_SONOS,
                    "upnp_enabled":      SOURCE_UPNP,
                    "bluetooth_enabled": SOURCE_BLUETOOTH,
                }
                enabled_sources = []
                for key, source in source_map.items():
                    val = device_state.get(key)
                    if val is not None:
                        self.state_store.set_source_enabled(source, val)
                        if val:
                            enabled_sources.append(source)
                
                # Determine current_source from enabled toggles + quickplay hint
                if len(enabled_sources) == 1:
                    self.state_store.current_source = enabled_sources[0]
                elif len(enabled_sources) == 0:
                    self.state_store.current_source = None
                    _LOGGER.warning("No audio sources enabled!")
                else:
                    # Multiple sources enabled — use quickplay source if valid,
                    # then keep current if valid, otherwise first enabled
                    qp_src = self.state_store.quickplay_source
                    if qp_src and qp_src in enabled_sources:
                        self.state_store.current_source = qp_src
                    elif self.state_store.current_source not in enabled_sources:
                        self.state_store.current_source = enabled_sources[0]
                    _LOGGER.debug("Multiple sources enabled: %s - current: %s (qp: %s)",
                                  enabled_sources, self.state_store.current_source, qp_src)

                # Default output IDs → register in discovery + store
                id_map = {
                    "roon_default_id":      SOURCE_ROON,
                    "sonos_default_id":     SOURCE_SONOS,
                    "upnp_default_id":      SOURCE_UPNP,
                    "bluetooth_default_id": SOURCE_BLUETOOTH,
                }
                for id_key, source in id_map.items():
                    speaker_id = device_state.get(id_key)
                    if speaker_id:
                        name = self.discovery.find_speaker_name_by_id(speaker_id)
                        self.state_store.set_default_output(
                            source, name or speaker_id, speaker_id
                        )

            # ── 2b. settings:/adchls → RCA settings ──
            rca_state = await self.api.async_get_rca_settings()
            if rca_state:
                if rca_state.get("rca_mode_api"):
                    self.state_store.set_rca_mode(
                        RCA_MODE_API_TO_LABEL.get(rca_state["rca_mode_api"], "Switching")
                    )
                if rca_state.get("rca_delay") is not None:
                    self.state_store.set_rca_delay(rca_state["rca_delay"])
                if rca_state.get("rca_fixed_volume") is not None:
                    self.state_store.rca_fixed_volume = rca_state["rca_fixed_volume"]

            # ── 3. ui: getRows → authoritative default speaker name ──
            ui_state = await self.api.async_get_ui_state()
            if ui_state.get("current_default_speaker_name"):
                self.state_store.current_default_speaker_name = ui_state["current_default_speaker_name"]

            # ── 4. player:volume + powermanager:target ──
            player_state = await self.api.async_get_player_state()
            if player_state.get("volume") is not None:
                self.state_store.volume = player_state["volume"]
            if player_state.get("power_target"):
                self.state_store.power_target = player_state["power_target"]
                self.state_store.power_reason = player_state.get("power_reason")

            # Note: is_streaming is managed by VictrolaStreamMonitor
            # (persistent connection, ~1-3s detection latency)

            return self.state_store.to_dict()

        except Exception as err:
            self.state_store.connected = False
            raise UpdateFailed(f"Cannot reach Victrola: {err}")

    @staticmethod
    def _source_from_type(spk_type: str) -> str:
        """Derive source from speaker type string (e.g. 'UPnP' → SOURCE_UPNP)."""
        if not spk_type:
            return SOURCE_SONOS
        t = spk_type.lower()
        if "upnp" in t:
            return SOURCE_UPNP
        if "roon" in t:
            return SOURCE_ROON
        if "bluetooth" in t or "bt" in t:
            return SOURCE_BLUETOOTH
        return SOURCE_SONOS

    async def async_apply_startup_source(self) -> None:
        """Apply startup source preference after discovery completes.

        Reads the 'Startup Source' select entity (persisted via RestoreEntity).
        Enables the configured source, disables others, and quickplays if UPnP.
        """
        try:
            entry_data = self.hass.data.get(DOMAIN, {})
            startup_select = None
            for data in entry_data.values():
                if isinstance(data, dict):
                    startup_select = data.get("startup_source_select")
                    if startup_select:
                        break

            pref = STARTUP_SOURCE_LAST_KNOWN
            if startup_select:
                pref = startup_select.current_option or STARTUP_SOURCE_LAST_KNOWN

            _LOGGER.info("Startup source preference: %s", pref)

            if pref == STARTUP_SOURCE_LAST_KNOWN:
                # Don't change anything — keep whatever the device has
                return
            if pref == STARTUP_SOURCE_NONE:
                # Disable all sources
                for src in SOURCES:
                    await self.api.async_set_source_enabled(src.lower(), False)
                _LOGGER.info("Startup: disabled all sources")
                return

            # Enable the preferred source, disable others
            for src in SOURCES:
                await self.api.async_set_source_enabled(
                    src.lower(), src == pref
                )
            _LOGGER.info("Startup: enabled %s, disabled others", pref)

            # If UPnP, also quickplay to establish stream session
            if pref == SOURCE_UPNP:
                await asyncio.sleep(2)  # Let source switch settle
                state = await self.api.async_get_current_default_outputs()
                upnp_id = state.get("upnp_default_id")
                if upnp_id:
                    _LOGGER.info("Startup quickplay to UPnP default: %s", upnp_id)
                    await self.api.async_quickplay("upnp", upnp_id)

        except Exception as err:
            _LOGGER.warning("Startup source application failed: %s", err)

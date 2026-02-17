"""Coordinator - polls real device state every 30 seconds."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN, DEFAULT_SCAN_INTERVAL,
    AUDIO_QUALITY_API_TO_LABEL, AUDIO_LATENCY_API_TO_LABEL,
    SOURCE_ROON, SOURCE_SONOS, SOURCE_UPNP, SOURCE_BLUETOOTH,
)

_LOGGER = logging.getLogger(__name__)


class VictrolaCoordinator(DataUpdateCoordinator):
    """Polls Victrola device for real state every 30 seconds."""

    def __init__(self, hass: HomeAssistant, api, state_store, discovery) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self.state_store = state_store
        self.discovery = discovery

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            connected = await self.api.async_test_connection()
            self.state_store.connected = connected

            if not connected:
                _LOGGER.warning("Victrola at %s is not reachable", self.api.host)
                return self.state_store.to_dict()

            # ── 1. Settings + default output IDs via settings:/victrola getRows ──
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
                    "roon_enabled": SOURCE_ROON,
                    "sonos_enabled": SOURCE_SONOS,
                    "upnp_enabled": SOURCE_UPNP,
                    "bluetooth_enabled": SOURCE_BLUETOOTH,
                }
                for key, source in source_map.items():
                    val = device_state.get(key)
                    if val is not None:
                        self.state_store.set_source_enabled(source, val)
                    if val:
                        self.state_store.current_source = source

                # Default output IDs → reverse-lookup to speaker names
                id_map = {
                    "roon_default_id":      SOURCE_ROON,
                    "sonos_default_id":     SOURCE_SONOS,
                    "upnp_default_id":      SOURCE_UPNP,
                    "bluetooth_default_id": SOURCE_BLUETOOTH,
                }
                for id_key, source in id_map.items():
                    speaker_id = device_state.get(id_key)
                    if speaker_id:
                        name = self._find_speaker_name(source, speaker_id)
                        self.state_store.set_default_output(
                            source, name or speaker_id, speaker_id
                        )

            # ── 2. ui: getRows → current default speaker name (authoritative) ──
            ui_state = await self.api.async_get_ui_state()
            if ui_state.get("current_default_speaker_name"):
                # Store the human-readable name the device itself reports
                self.state_store.current_default_speaker_name = ui_state["current_default_speaker_name"]
                _LOGGER.debug("Device reports default speaker: %s",
                              ui_state["current_default_speaker_name"])

            # ── 3. speakerQuickplay getRows → current quickplay speaker ──
            qp_state = await self.api.async_get_quickplay_state()
            if qp_state.get("current_quickplay_name"):
                self.state_store.set_quickplay(
                    source=SOURCE_SONOS,
                    speaker_name=qp_state["current_quickplay_name"],
                    speaker_id=qp_state.get("current_quickplay_id", ""),
                )
                _LOGGER.debug("Device reports quickplay speaker: %s",
                              qp_state["current_quickplay_name"])
            # Store full speaker list for reference
            if qp_state.get("speakers"):
                self.state_store.available_quickplay_speakers = qp_state["speakers"]

            # ── 4. Player volume + power state ──
            player_state = await self.api.async_get_player_state()
            if player_state.get("volume") is not None:
                self.state_store.volume = player_state["volume"]
            if player_state.get("power_target"):
                self.state_store.power_target = player_state["power_target"]
                self.state_store.power_reason = player_state.get("power_reason")

            return self.state_store.to_dict()

        except Exception as err:
            self.state_store.connected = False
            raise UpdateFailed(f"Cannot reach Victrola: {err}")

    def _find_speaker_name(self, source: str, victrola_id: str) -> str | None:
        speakers = self.discovery.get_speakers(source)
        for name, info in speakers.items():
            if info.get("victrola_id") == victrola_id:
                return name
        return None

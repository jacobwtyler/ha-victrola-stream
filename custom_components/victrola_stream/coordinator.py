"""Coordinator - polls real device state every 30 seconds via getRows."""
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

    def __init__(self, hass: HomeAssistant, api: Any, state_store: Any, discovery: Any) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self.state_store = state_store
        self.discovery = discovery

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch real state from device via getRows and sync to state_store."""
        try:
            connected = await self.api.async_test_connection()
            self.state_store.connected = connected

            if not connected:
                _LOGGER.warning("Victrola at %s is not reachable", self.api.host)
                return self.state_store.to_dict()

            # Use getRows to get ALL state including current default output IDs
            device_state = await self.api.async_get_current_default_outputs()

            if device_state:
                # Audio quality
                if device_state.get("audio_quality_api"):
                    label = AUDIO_QUALITY_API_TO_LABEL.get(
                        device_state["audio_quality_api"], "Standard"
                    )
                    self.state_store.set_audio_quality(label)

                # Audio latency
                if device_state.get("audio_latency_api"):
                    label = AUDIO_LATENCY_API_TO_LABEL.get(
                        device_state["audio_latency_api"], "Medium"
                    )
                    self.state_store.set_audio_latency(label)

                # Knob brightness
                if device_state.get("knob_brightness") is not None:
                    self.state_store.set_knob_brightness(device_state["knob_brightness"])

                # Source enabled states
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

                # Autoplay
                if device_state.get("autoplay") is not None:
                    self.state_store.autoplay = device_state["autoplay"]

                # Active source = enabled one
                for key, source in source_map.items():
                    if device_state.get(key, False):
                        self.state_store.current_source = source
                        break

                # ── Current default output IDs → reverse-lookup speaker names ──
                id_to_source_map = {
                    "roon_default_id":       SOURCE_ROON,
                    "sonos_default_id":      SOURCE_SONOS,
                    "upnp_default_id":       SOURCE_UPNP,
                    "bluetooth_default_id":  SOURCE_BLUETOOTH,
                }
                for id_key, source in id_to_source_map.items():
                    speaker_id = device_state.get(id_key)
                    if speaker_id:
                        # Reverse-lookup: find speaker name from victrola_id
                        name = self._find_speaker_name(source, speaker_id)
                        if name:
                            self.state_store.set_default_output(source, name, speaker_id)
                            _LOGGER.debug(
                                "Default output for %s: %s (%s)", source, name, speaker_id
                            )
                        else:
                            # ID found but not in our speaker map - store raw ID
                            self.state_store.set_default_output(source, speaker_id, speaker_id)
                            _LOGGER.warning(
                                "Unknown speaker ID for %s: %s", source, speaker_id
                            )

            return self.state_store.to_dict()

        except Exception as err:
            self.state_store.connected = False
            raise UpdateFailed(f"Cannot reach Victrola: {err}")

    def _find_speaker_name(self, source: str, victrola_id: str) -> str | None:
        """Reverse lookup: find speaker display name from its Victrola ID."""
        speakers = self.discovery.get_speakers(source)
        for name, info in speakers.items():
            if info.get("victrola_id") == victrola_id:
                return name
        return None

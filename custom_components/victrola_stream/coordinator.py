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

    def __init__(self, hass: HomeAssistant, api: Any, state_store: Any) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self.state_store = state_store

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch real state from device and sync to state_store."""
        try:
            connected = await self.api.async_test_connection()
            self.state_store.connected = connected

            if not connected:
                _LOGGER.warning("Victrola at %s is not reachable", self.api.host)
                return self.state_store.to_dict()

            device_state = await self.api.async_get_full_state()

            if device_state:
                if "audio_quality_api" in device_state:
                    label = AUDIO_QUALITY_API_TO_LABEL.get(device_state["audio_quality_api"], "Standard")
                    self.state_store.set_audio_quality(label)

                if "audio_latency_api" in device_state:
                    label = AUDIO_LATENCY_API_TO_LABEL.get(device_state["audio_latency_api"], "Medium")
                    self.state_store.set_audio_latency(label)

                if "knob_brightness" in device_state:
                    self.state_store.set_knob_brightness(device_state["knob_brightness"])

                source_map = {
                    "roon": SOURCE_ROON,
                    "sonos": SOURCE_SONOS,
                    "upnp": SOURCE_UPNP,
                    "bluetooth": SOURCE_BLUETOOTH,
                }
                for key, source in source_map.items():
                    if f"{key}_enabled" in device_state:
                        self.state_store.set_source_enabled(source, device_state[f"{key}_enabled"])

                if "autoplay" in device_state:
                    self.state_store.autoplay = device_state["autoplay"]

                # Active source = the one that is enabled
                for key, source in source_map.items():
                    if device_state.get(f"{key}_enabled", False):
                        self.state_store.current_source = source
                        break

            return self.state_store.to_dict()

        except Exception as err:
            self.state_store.connected = False
            raise UpdateFailed(f"Cannot reach Victrola: {err}")

"""Victrola API wrapper - Full control implementation."""
from __future__ import annotations

import aiohttp
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


class VictrolaAPI:
    """Interface to Victrola Stream API."""

    def __init__(self, host: str, port: int = 80):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"

    # ─────────────────────────────────────────────
    # Core API methods
    # ─────────────────────────────────────────────

    async def async_test_connection(self) -> bool:
        """Test connection to Victrola."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/getData",
                    json={"path": "settings:/", "roles": ["value"]},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    return response.status == 200
        except Exception as err:
            _LOGGER.error("Connection test failed: %s", err)
            return False

    async def async_set_data(self, path: str, role: str, value: Any) -> bool:
        """Send setData command to Victrola."""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"path": path, "role": role, "value": value}
                async with session.post(
                    f"{self.base_url}/api/setData",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        _LOGGER.debug("setData success: %s = %s", path, value)
                        return True
                    else:
                        _LOGGER.warning("setData failed %s: HTTP %s", path, response.status)
                        return False
        except Exception as err:
            _LOGGER.error("setData error %s: %s", path, err)
            return False

    async def async_get_data(self, path: str, roles: list[str]) -> Any:
        """Send getData command to Victrola."""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"path": path, "roles": roles}
                async with session.post(
                    f"{self.base_url}/api/getData",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        data = await response.json(content_type=None)
                        _LOGGER.debug("getData %s = %s", path, data)
                        return data
                    return None
        except Exception as err:
            _LOGGER.error("getData error %s: %s", path, err)
            return None

    # ─────────────────────────────────────────────
    # Source / Speaker control
    # ─────────────────────────────────────────────

    async def async_set_source(self, source_type: str, speaker_id: str) -> bool:
        """Set active source and speaker on Victrola device."""
        value = {"type": source_type, "id": speaker_id}

        # Set default output
        r1 = await self.async_set_data("victrola:ui/setDefaultOutput", "activate", value)

        # Also trigger quickplay so audio starts immediately
        r2 = await self.async_set_data("victrola:ui/quickplay", "activate", value)

        success = r1 or r2
        if success:
            _LOGGER.info("Source set: %s -> %s", source_type, speaker_id)
        else:
            _LOGGER.error("Failed to set source: %s -> %s", source_type, speaker_id)
        return success

    async def async_set_roon_speaker(self, core_id: str, output_id: str) -> bool:
        """Set Roon speaker."""
        victrola_id = f"{core_id}:{output_id}"
        return await self.async_set_source("victrolaOutputRoon", victrola_id)

    async def async_set_sonos_speaker(self, rincon_id: str) -> bool:
        """Set Sonos speaker."""
        return await self.async_set_source("victrolaOutputSonos", rincon_id)

    async def async_set_upnp_speaker(self, uuid: str) -> bool:
        """Set UPnP speaker."""
        return await self.async_set_source("victrolaOutputUpnp", uuid)

    async def async_set_bluetooth_speaker(self, bt_id: str) -> bool:
        """Set Bluetooth speaker."""
        return await self.async_set_source("victrolaOutputBluetooth", bt_id)

    # ─────────────────────────────────────────────
    # Audio Quality
    # ─────────────────────────────────────────────

    async def async_get_audio_quality(self) -> str | None:
        """Get current audio quality setting."""
        data = await self.async_get_data("settings:/multiroom/audio_quality", ["value"])
        if data and isinstance(data, list) and len(data) > 0:
            item = data[0]
            if item and "value" in item:
                return item["value"]
        return None

    async def async_set_audio_quality(self, quality: str) -> bool:
        """Set audio quality (cd/high/medium/low)."""
        return await self.async_set_data(
            "settings:/multiroom/audio_quality", "value", quality
        )

    # ─────────────────────────────────────────────
    # Audio Latency
    # ─────────────────────────────────────────────

    async def async_get_audio_latency(self) -> int | None:
        """Get current audio latency in ms."""
        data = await self.async_get_data("settings:/multiroom/audio_latency", ["value"])
        if data and isinstance(data, list) and len(data) > 0:
            item = data[0]
            if item and "value" in item:
                return int(item["value"])
        return None

    async def async_set_audio_latency(self, latency_ms: int) -> bool:
        """Set audio latency in milliseconds."""
        return await self.async_set_data(
            "settings:/multiroom/audio_latency", "value", latency_ms
        )

    # ─────────────────────────────────────────────
    # Knob Brightness
    # ─────────────────────────────────────────────

    async def async_get_knob_brightness(self) -> int | None:
        """Get current knob brightness (0-100)."""
        data = await self.async_get_data("settings:/ui/knob_brightness", ["value"])
        if data and isinstance(data, list) and len(data) > 0:
            item = data[0]
            if item and "value" in item:
                return int(item["value"])
        return None

    async def async_set_knob_brightness(self, brightness: int) -> bool:
        """Set knob brightness (0-100)."""
        return await self.async_set_data(
            "settings:/ui/knob_brightness", "value", brightness
        )

    # ─────────────────────────────────────────────
    # Source Enable/Disable Toggles
    # ─────────────────────────────────────────────

    async def async_get_source_enabled(self, source: str) -> bool | None:
        """Get whether a source is enabled."""
        path_map = {
            "roon":      "settings:/multiroom/client_roon/enabled",
            "sonos":     "settings:/multiroom/client_sonos/enabled",
            "upnp":      "settings:/multiroom/client_upnp/enabled",
            "bluetooth": "settings:/multiroom/client_bluetooth/enabled",
        }
        path = path_map.get(source)
        if not path:
            return None
        data = await self.async_get_data(path, ["value"])
        if data and isinstance(data, list) and len(data) > 0:
            item = data[0]
            if item and "value" in item:
                return bool(item["value"])
        return None

    async def async_set_source_enabled(self, source: str, enabled: bool) -> bool:
        """Enable or disable a source."""
        path_map = {
            "roon":      "settings:/multiroom/client_roon/enabled",
            "sonos":     "settings:/multiroom/client_sonos/enabled",
            "upnp":      "settings:/multiroom/client_upnp/enabled",
            "bluetooth": "settings:/multiroom/client_bluetooth/enabled",
        }
        path = path_map.get(source)
        if not path:
            return False
        return await self.async_set_data(path, "value", enabled)

    # ─────────────────────────────────────────────
    # Current State
    # ─────────────────────────────────────────────

    async def async_get_current_output(self) -> dict | None:
        """Get the current active output."""
        data = await self.async_get_data("settings:/multiroom/current_output", ["value"])
        if data and isinstance(data, list) and len(data) > 0:
            item = data[0]
            if item and "value" in item:
                return item["value"]
        return None

    # ─────────────────────────────────────────────
    # System
    # ─────────────────────────────────────────────

    async def async_reboot(self) -> bool:
        """Reboot the Victrola device."""
        _LOGGER.warning("Rebooting Victrola at %s", self.host)
        return await self.async_set_data("settings:/system/reboot", "activate", True)

    # ─────────────────────────────────────────────
    # Full state fetch (for coordinator)
    # ─────────────────────────────────────────────

    async def async_get_full_state(self) -> dict:
        """Fetch all current state from Victrola."""
        state = {}

        audio_quality = await self.async_get_audio_quality()
        if audio_quality is not None:
            state["audio_quality"] = audio_quality

        audio_latency = await self.async_get_audio_latency()
        if audio_latency is not None:
            state["audio_latency"] = audio_latency

        knob_brightness = await self.async_get_knob_brightness()
        if knob_brightness is not None:
            state["knob_brightness"] = knob_brightness

        current_output = await self.async_get_current_output()
        if current_output is not None:
            state["current_output"] = current_output

        for source in ["roon", "sonos", "upnp", "bluetooth"]:
            enabled = await self.async_get_source_enabled(source)
            if enabled is not None:
                state[f"{source}_enabled"] = enabled

        return state

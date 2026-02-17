"""Victrola API - correct paths and payload formats from working rest_commands."""
from __future__ import annotations

import aiohttp
import logging
import time
from typing import Any

_LOGGER = logging.getLogger(__name__)


class VictrolaAPI:
    """Interface to Victrola Stream API."""

    def __init__(self, host: str, port: int = 80):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"

    # ─────────────────────────────────────────────
    # Core
    # ─────────────────────────────────────────────

    async def async_test_connection(self) -> bool:
        """Test connection."""
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
        """Send setData with correct platform field."""
        try:
            payload = {
                "path": path,
                "role": role,
                "value": value,
                "platform": "other",
            }
            # Add nocache for activate calls (matches quickplay rest_commands)
            if role == "activate":
                payload["_nocache"] = int(time.time())

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/setData",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    ok = response.status == 200
                    if ok:
                        _LOGGER.debug("setData OK: %s = %s", path, value)
                    else:
                        body = await response.text()
                        _LOGGER.warning("setData failed %s HTTP %s: %s", path, response.status, body)
                    return ok
        except Exception as err:
            _LOGGER.error("setData error %s: %s", path, err)
            return False

    # ─────────────────────────────────────────────
    # Speaker / Source selection
    # ─────────────────────────────────────────────

    async def async_quickplay(self, victrola_type: str, speaker_id: str) -> bool:
        """QuickPlay - starts audio immediately."""
        return await self.async_set_data(
            "victrola:ui/quickplay",
            "activate",
            {"type": victrola_type, "id": speaker_id},
        )

    async def async_set_default_output(self, victrola_type: str, speaker_id: str) -> bool:
        """Set default output without starting playback."""
        return await self.async_set_data(
            "victrola:ui/setDefaultOutput",
            "activate",
            {"type": victrola_type, "id": speaker_id},
        )

    async def async_select_speaker(self, victrola_default_type: str, victrola_quickplay_type: str, speaker_id: str) -> bool:
        """Set default output AND quickplay."""
        r1 = await self.async_set_default_output(victrola_default_type, speaker_id)
        r2 = await self.async_quickplay(victrola_quickplay_type, speaker_id)
        return r1 or r2

    # ─────────────────────────────────────────────
    # Audio Quality
    # path: settings:/victrola/forceLowBitrate
    # value: {"forceLowBitrate": "connectionQuality|soundQuality|losslessQuality", "type": "forceLowBitrate"}
    # ─────────────────────────────────────────────

    async def async_set_audio_quality(self, api_value: str) -> bool:
        """Set audio quality. api_value: connectionQuality / soundQuality / losslessQuality"""
        return await self.async_set_data(
            "settings:/victrola/forceLowBitrate",
            "value",
            {"forceLowBitrate": api_value, "type": "forceLowBitrate"},
        )

    # ─────────────────────────────────────────────
    # Audio Latency
    # path: settings:/victrola/wirelessAudioDelay
    # value: {"adchlsLatency": "min|med|high|max", "type": "adchlsLatency"}
    # ─────────────────────────────────────────────

    async def async_set_audio_latency(self, api_value: str) -> bool:
        """Set audio latency. api_value: min / med / high / max"""
        return await self.async_set_data(
            "settings:/victrola/wirelessAudioDelay",
            "value",
            {"adchlsLatency": api_value, "type": "adchlsLatency"},
        )

    # ─────────────────────────────────────────────
    # Knob Brightness
    # path: settings:/victrola/lightBrightness
    # value: {"type": "i32_", "i32_": 0-100}
    # ─────────────────────────────────────────────

    async def async_set_knob_brightness(self, brightness: int) -> bool:
        """Set knob brightness 0-100."""
        return await self.async_set_data(
            "settings:/victrola/lightBrightness",
            "value",
            {"type": "i32_", "i32_": max(0, min(100, int(brightness)))},
        )

    # ─────────────────────────────────────────────
    # Source Enable/Disable
    # path: settings:/victrola/{source}Enabled
    # value: {"type": "bool_", "bool_": true/false}
    # ─────────────────────────────────────────────

    async def async_set_source_enabled(self, source: str, enabled: bool) -> bool:
        """Enable/disable a source. source: roon/sonos/upnp/bluetooth"""
        path_map = {
            "roon":      "settings:/victrola/roonEnabled",
            "sonos":     "settings:/victrola/sonosEnabled",
            "upnp":      "settings:/victrola/upnpEnabled",
            "bluetooth": "settings:/victrola/bluetoothEnabled",
        }
        path = path_map.get(source.lower())
        if not path:
            _LOGGER.error("Unknown source: %s", source)
            return False
        return await self.async_set_data(
            path, "value", {"type": "bool_", "bool_": enabled}
        )

    # ─────────────────────────────────────────────
    # Autoplay
    # ─────────────────────────────────────────────

    async def async_set_autoplay(self, enabled: bool) -> bool:
        """Enable/disable autoplay."""
        return await self.async_set_data(
            "settings:/victrola/autoplay",
            "value",
            {"type": "bool_", "bool_": enabled},
        )

    # ─────────────────────────────────────────────
    # Reboot
    # path: powermanager:goReboot
    # ─────────────────────────────────────────────

    async def async_reboot(self) -> bool:
        """Reboot the Victrola device."""
        _LOGGER.warning("Sending reboot command to Victrola at %s", self.host)
        return await self.async_set_data(
            "powermanager:goReboot",
            "activate",
            {"type": "bool_", "bool_": True},
        )

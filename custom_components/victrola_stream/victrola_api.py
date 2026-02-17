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

    # ─────────────────────────────────────────────
    # Full state poll (all paths confirmed readable)
    # ─────────────────────────────────────────────

    async def async_get_full_state(self) -> dict:
        """Poll all readable settings from the device."""
        state = {}

        try:
            async with aiohttp.ClientSession() as session:

                async def _get(path: str) -> list | None:
                    try:
                        async with session.post(
                            f"{self.base_url}/api/getData",
                            json={"path": path, "roles": ["value"]},
                            headers={"Content-Type": "application/json"},
                            timeout=aiohttp.ClientTimeout(total=5),
                        ) as r:
                            if r.status == 200:
                                data = await r.json(content_type=None)
                                if isinstance(data, list) and data and data[0] is not None:
                                    return data[0]
                    except Exception as e:
                        _LOGGER.debug("getData %s failed: %s", path, e)
                    return None

                # Audio quality -> {"forceLowBitrate": "losslessQuality", "type": "forceLowBitrate"}
                d = await _get("settings:/victrola/forceLowBitrate")
                if d:
                    state["audio_quality_api"] = d.get("forceLowBitrate")

                # Audio latency -> {"adchlsLatency": "med", "type": "adchlsLatency"}
                d = await _get("settings:/victrola/wirelessAudioDelay")
                if d:
                    state["audio_latency_api"] = d.get("adchlsLatency")

                # Knob brightness -> {"type": "i32_", "i32_": 50}
                d = await _get("settings:/victrola/lightBrightness")
                if d:
                    state["knob_brightness"] = int(d.get("i32_", 100))

                # Source enabled states -> {"bool_": True, "type": "bool_"}
                for source, path in [
                    ("roon",      "settings:/victrola/roonEnabled"),
                    ("sonos",     "settings:/victrola/sonosEnabled"),
                    ("upnp",      "settings:/victrola/upnpEnabled"),
                    ("bluetooth", "settings:/victrola/bluetoothEnabled"),
                ]:
                    d = await _get(path)
                    if d:
                        state[f"{source}_enabled"] = bool(d.get("bool_", False))

                # Autoplay
                d = await _get("settings:/victrola/autoplay")
                if d:
                    state["autoplay"] = bool(d.get("bool_", True))

        except Exception as err:
            _LOGGER.error("get_full_state error: %s", err)

        return state

    async def async_reboot(self) -> bool:
        """Reboot the Victrola device."""
        _LOGGER.warning("Sending reboot command to Victrola at %s", self.host)
        return await self.async_set_data(
            "powermanager:goReboot",
            "activate",
            {"type": "bool_", "bool_": True},
        )

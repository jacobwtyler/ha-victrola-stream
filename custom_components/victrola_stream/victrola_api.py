"""Victrola API - correct paths and payload formats from working rest_commands."""
from __future__ import annotations

import asyncio
import aiohttp
import logging
import time
from typing import Any
from urllib.parse import quote

from .const import DEFAULT_STREAM_PORT, STREAM_PROBE_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class VictrolaAPI:
    """Interface to Victrola Stream API."""

    def __init__(self, host: str, port: int = 80, session: aiohttp.ClientSession | None = None):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self._session = session
        self._stream_port: int = DEFAULT_STREAM_PORT

    @property
    def session(self) -> aiohttp.ClientSession | None:
        """Expose the shared session for use by other components."""
        return self._session

    # ─────────────────────────────────────────────
    # Core
    # ─────────────────────────────────────────────

    async def async_test_connection(self) -> bool:
        """Test connection."""
        try:
            own_session = self._session is None
            session = self._session or aiohttp.ClientSession()
            try:
                async with session.post(
                    f"{self.base_url}/api/getData",
                    json={"path": "settings:/", "roles": ["value"]},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    return response.status == 200
            finally:
                if own_session:
                    await session.close()
        except (aiohttp.ClientError, TimeoutError, OSError) as err:
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

            own_session = self._session is None
            session = self._session or aiohttp.ClientSession()
            try:
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
            finally:
                if own_session:
                    await session.close()
        except (aiohttp.ClientError, TimeoutError, OSError) as err:
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
        return r1 and r2

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
    # RCA Settings
    # ─────────────────────────────────────────────

    async def async_set_rca_mode(self, mode: str) -> bool:
        """Set RCA mode. mode: switching / simultaneous"""
        return await self.async_set_data(
            "settings:/adchls/dacMode",
            "value",
            {"type": "adchlsDACMode", "adchlsDACMode": mode},
        )

    async def async_set_rca_delay(self, delay_ms: int) -> bool:
        """Set RCA delay in milliseconds (0-500)."""
        return await self.async_set_data(
            "settings:/adchls/dacDelay",
            "value",
            {"type": "i32_", "i32_": max(0, min(500, int(delay_ms)))},
        )

    async def async_set_rca_fixed_volume(self, enabled: bool) -> bool:
        """Set RCA fixed volume (volume control enabled/disabled)."""
        return await self.async_set_data(
            "settings:/adchls/fixedVolume",
            "value",
            {"type": "bool_", "bool_": enabled},
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

    async def async_get_ui_state(self) -> dict:
        """Fetch ui: getRows - returns current default speaker name and UI structure.
        
        Row 0: header "DEFAULT SPEAKER"
        Row 1: victrola:ui/speakerSelection - title = current default speaker name
        Row 2: autoplay setting
        Row 3: header "QUICKPLAY"
        Row 4: victrola:ui/speakerQuickplay container
        """
        try:
            url = f"{self.base_url}/api/getRows?path={quote('ui:')}&roles=%40all&from=0&to=30&type=structure&_nocache={int(time.time()*1000)}"
            session = self._session
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                if r.status == 200:
                    data = await r.json(content_type=None)
                    rows = data.get("rows", [])
                    result = {}
                    for row in rows:
                        if isinstance(row, dict):
                            path = row.get("path", "")
                            title = row.get("title")
                            if path == "victrola:ui/speakerSelection" and title:
                                result["current_default_speaker_name"] = title
                                _LOGGER.debug("Current default speaker from ui:: %s", title)
                            if path == "settings:/victrola/autoplay":
                                val = row.get("value", {})
                                if val:
                                    result["autoplay"] = val.get("bool_")
                    return result
        except (aiohttp.ClientError, TimeoutError, OSError) as err:
            _LOGGER.error("ui: getRows error: %s", err)
        return {}

    async def async_get_quickplay_state(self) -> dict:
        """Fetch victrola:ui/speakerQuickplay getRows.
        
        Returns list of available speakers with preferred=True on currently quickplayed one.
        Each row has: type, path, id, title, preferred (bool), value (sonosGroup details)
        """
        try:
            url = f"{self.base_url}/api/getRows?path={quote('victrola:ui/speakerQuickplay')}&roles=%40all&from=0&to=65535&type=structure&_nocache={int(time.time()*1000)}"
            session = self._session
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                    if r.status == 200:
                        data = await r.json(content_type=None)
                        rows = data.get("rows", [])
                        result = {
                            "speakers": [],
                            "current_quickplay_name": None,
                            "current_quickplay_id": None,
                        }
                        for row in rows:
                            if not isinstance(row, dict):
                                continue
                            speaker = {
                                "name": row.get("title"),
                                "id": row.get("id"),
                                "path": row.get("path"),
                                "preferred": row.get("preferred", False),
                                "type": row.get("type"),
                            }
                            # Extract sonosGroupId for full group ID
                            val = row.get("value", {})
                            if val and val.get("type") == "sonosGroup":
                                sg = val.get("sonosGroup", {})
                                speaker["sonos_group_id"] = sg.get("sonosGroupId")
                                speaker["group_name"] = sg.get("groupName")
                            result["speakers"].append(speaker)
                            if row.get("preferred"):
                                result["current_quickplay_name"] = row.get("title")
                                result["current_quickplay_id"] = row.get("id")
                                _LOGGER.debug(
                                    "Current quickplay speaker: %s (%s)",
                                    row.get("title"), row.get("id")
                                )
                        return result
        except (aiohttp.ClientError, TimeoutError, OSError) as err:
            _LOGGER.error("speakerQuickplay getRows error: %s", err)
        return {}

    async def async_get_player_state(self) -> dict:
        """Fetch player volume and power state."""
        result = {}
        try:
            session = self._session
            # Volume
            url = f"{self.base_url}/api/getData?path={quote('player:volume')}&roles=%40all&type=structure&_nocache={int(time.time()*1000)}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                if r.status == 200:
                    data = await r.json(content_type=None)
                    val = data.get("value", {})
                    if val and val.get("type") == "i32_":
                        result["volume"] = val.get("i32_")
            # Power state
            url2 = f"{self.base_url}/api/getData?path={quote('powermanager:target')}&roles=%40all&type=structure&_nocache={int(time.time()*1000)}"
            async with session.get(url2, timeout=aiohttp.ClientTimeout(total=5)) as r:
                if r.status == 200:
                    data = await r.json(content_type=None)
                    val = data.get("value", {})
                    if val and val.get("type") == "powerTarget":
                        pt = val.get("powerTarget", {})
                        result["power_target"] = pt.get("target")
                        result["power_reason"] = pt.get("reason")
        except (aiohttp.ClientError, TimeoutError, OSError) as err:
            _LOGGER.error("player state error: %s", err)
        return result

    async def async_get_rows(self, path: str, from_idx: int, to_idx: int) -> list:
        """Fetch getRows from device."""
        try:
            session = self._session
            async with session.post(
                f"{self.base_url}/api/getRows",
                json={"path": path, "roles": ["value"], "from": from_idx, "to": to_idx},
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                if r.status == 200:
                    data = await r.json(content_type=None)
                    return data.get("rows", [])
        except (aiohttp.ClientError, TimeoutError, OSError) as err:
            _LOGGER.error("getRows %s error: %s", path, err)
        return []

    async def async_get_current_default_outputs(self) -> dict:
        """Read current default output IDs from settings:/victrola getRows.
        
        Row mapping (discovered via firmware analysis):
          Row  1: roonEnabled (bool)
          Row  2: current Sonos default output ID (string)
          Row  3: current Roon default output ID (string)
          Row  4: sonosEnabled (bool)
          Row  5: upnpEnabled (bool)
          Row  6: bluetoothEnabled (bool)
          Row  7: audio quality (forceLowBitrate)
          Row 10: knob brightness (i32_)
          Row 11: autoplay (bool)
          Row 12: bluetooth default output path ref (string - e.g. "settings:/victrola/bluetoothEnabled")
          Row 13: unknown bool
          Row 14: unknown bool
          Row 15: current UPnP default output ID (string)
          Row 18: audio latency (adchlsLatency)
          
          speakerSelection getRows:
          Row  4: currently selected/checked speaker slot (bool true)
        """
        rows = await self.async_get_rows("settings:/victrola", 0, 19)
        result = {}

        def _str_val(row):
            if row and row[0] and row[0].get("type") == "string_":
                return row[0].get("string_")
            return None

        def _bool_val(row):
            if row and row[0] and row[0].get("type") == "bool_":
                return row[0].get("bool_")
            return None

        def _typed_val(row, key):
            if row and row[0] and key in row[0]:
                return row[0].get(key)
            return None

        if len(rows) > 2:
            result["sonos_default_id"] = _str_val(rows[2])
        if len(rows) > 3:
            result["roon_default_id"] = _str_val(rows[3])
        if len(rows) > 15:
            result["upnp_default_id"] = _str_val(rows[15])
        # Row 12: bluetooth default - stored as path string, resolve it
        if len(rows) > 12:
            bt_path = _str_val(rows[12])
            if bt_path and bt_path != "settings:/victrola/bluetoothEnabled":
                # When a BT device is selected, row 12 contains its ID
                result["bluetooth_default_id"] = bt_path
            elif bt_path == "settings:/victrola/bluetoothEnabled":
                # This is the default/unset state for bluetooth
                result["bluetooth_default_id"] = None
        # Also re-read settings from rows for cross-validation
        if len(rows) > 1:
            result["roon_enabled"] = _bool_val(rows[1])
        if len(rows) > 4:
            result["sonos_enabled"] = _bool_val(rows[4])
        if len(rows) > 5:
            result["upnp_enabled"] = _bool_val(rows[5])
        if len(rows) > 6:
            result["bluetooth_enabled"] = _bool_val(rows[6])
        if len(rows) > 7:
            result["audio_quality_api"] = _typed_val(rows[7], "forceLowBitrate")
        if len(rows) > 10:
            if rows[10] and rows[10][0]:
                result["knob_brightness"] = rows[10][0].get("i32_")
        if len(rows) > 11:
            result["autoplay"] = _bool_val(rows[11])
        if len(rows) > 18:
            result["audio_latency_api"] = _typed_val(rows[18], "adchlsLatency")

        _LOGGER.debug("Current default outputs: %s", result)
        return result

    async def async_get_selected_speaker_slot(self) -> int | None:
        """Read victrola:ui/speakerSelection to find which slot is currently selected (True).
        Returns the row index of the selected speaker, or None."""
        rows = await self.async_get_rows("victrola:ui/speakerSelection", 0, 20)
        for i, row in enumerate(rows):
            if row and row[0] and row[0].get("type") == "bool_" and row[0].get("bool_") is True:
                _LOGGER.debug("Selected speaker slot: %d", i)
                return i
        return None


    async def async_set_volume(self, volume: int) -> bool:
        """Set player volume (0-100)."""
        return await self.async_set_data(
            "player:volume", "value",
            {"type": "i32_", "i32_": max(0, min(100, volume))}
        )

    async def async_set_mute(self, mute: bool) -> bool:
        """Set mute state."""
        return await self.async_set_data(
            "settings:/mediaPlayer/mute", "value",
            {"type": "bool_", "bool_": mute}
        )

    async def async_quickplay_by_path(self, victrola_type: str, speaker_id: str, speaker_path: str | None = None) -> bool:
        """Send quickplay using speaker path if available, else fall back to ID."""
        return await self.async_quickplay(victrola_type, speaker_id)

    async def async_get_speaker_selection(self) -> list[dict]:
        """Fetch victrola:ui/speakerSelection getRows - all speakers for current source.
        
        Returns list of speaker dicts with: title, type, id, path, preferred
        Types: victrolaOutputSonos, victrolaOutputRoon, victrolaOutputUPnP, victrolaOutputBluetooth
        """
        try:
            url = f"{self.base_url}/api/getRows?path={quote('victrola:ui/speakerSelection')}&roles=%40all&from=0&to=100&type=structure&_nocache={int(time.time()*1000)}"
            session = self._session
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                    if r.status == 200:
                        data = await r.json(content_type=None)
                        rows = data.get("rows", [])
                        speakers = []
                        for row in rows:
                            if not isinstance(row, dict):
                                continue
                            row_type = row.get("type", "")
                            # Filter for actual speaker entries (not headers, toggles, etc)
                            if row_type in (
                                "victrolaOutputSonos",
                                "victrolaOutputRoon",
                                "victrolaOutputUPnP",
                                "victrolaOutputBluetooth",
                            ):
                                speaker = {
                                    "title": row.get("title"),
                                    "type": row_type,
                                    "id": row.get("id"),
                                    "path": row.get("path"),
                                    "preferred": row.get("preferred", False),
                                }
                                # For Sonos, also grab full sonosGroup details
                                if row_type == "victrolaOutputSonos":
                                    val = row.get("value", {})
                                    if val and val.get("type") == "sonosGroup":
                                        sg = val.get("sonosGroup", {})
                                        speaker["sonos_group_id"] = sg.get("sonosGroupId")
                                        speaker["group_name"] = sg.get("groupName")
                                speakers.append(speaker)
                        return speakers
        except (aiohttp.ClientError, TimeoutError, OSError) as err:
            _LOGGER.error("speakerSelection getRows error: %s", err)
        return []

    async def async_get_autoplay(self) -> bool | None:
        """Get current autoplay state."""
        try:
            url = f"{self.base_url}/api/getData?path={quote('settings:/victrola/autoplay')}&roles=value&type=structure&_nocache={int(time.time()*1000)}"
            session = self._session
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                    if r.status == 200:
                        data = await r.json(content_type=None)
                        val = data.get("value", {})
                        if val and val.get("type") == "bool_":
                            return val.get("bool_")
        except (aiohttp.ClientError, TimeoutError, OSError) as err:
            _LOGGER.error("get autoplay error: %s", err)
        return None

    async def async_reboot(self) -> bool:
        """Reboot the Victrola device."""
        _LOGGER.warning("Sending reboot command to Victrola at %s", self.host)
        return await self.async_set_data(
            "powermanager:goReboot",
            "activate",
            {"type": "bool_", "bool_": True},
        )

    # ─────────────────────────────────────────────
    # ADC Stream Probe
    #
    # The Victrola runs an Icecast-compatible stream server on a dynamic
    # port (default 34435). It always accepts connections and returns
    # HTTP 200 headers, but only sends audio bytes when the ADC is
    # actively capturing (needle on record). We detect streaming by
    # trying to read a small chunk with a short timeout.
    # ─────────────────────────────────────────────

    async def async_check_stream_active(self) -> bool:
        """Check if the ADC stream is actively producing audio data.

        The Icecast stream server always sends ~292 bytes of Ogg FLAC
        container headers on connection, even when idle. When the needle
        is on, it sends 100-200 KB/s of audio frames. We distinguish
        the two by reading for the full probe timeout and checking if
        total throughput exceeds 1 KB (well above the idle header size).
        """
        url = f"http://{self.host}:{self._stream_port}/stream.flac"
        try:
            timeout = aiohttp.ClientTimeout(
                total=STREAM_PROBE_TIMEOUT + 1,
                sock_read=STREAM_PROBE_TIMEOUT,
            )
            async with aiohttp.ClientSession() as probe_session:
                async with probe_session.get(url, timeout=timeout) as resp:
                    if resp.status != 200:
                        return False
                    total = 0
                    async for chunk in resp.content.iter_any():
                        total += len(chunk)
                        if total > 1024:
                            return True  # Audio data flowing
                    # Stream ended before threshold — only headers
                    return False
        except asyncio.TimeoutError:
            # Timeout with ≤1024 bytes = idle (just headers, no audio)
            return False
        except (aiohttp.ClientError, OSError) as err:
            _LOGGER.debug("Stream probe failed on port %d: %s", self._stream_port, err)
            return False

    @property
    def stream_port(self) -> int:
        """Current stream server port."""
        return self._stream_port

    @stream_port.setter
    def stream_port(self, port: int) -> None:
        self._stream_port = port

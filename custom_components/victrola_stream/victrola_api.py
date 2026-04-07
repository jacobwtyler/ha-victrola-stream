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
                                result["current_quickplay_type"] = row.get("type")
                                _LOGGER.debug(
                                    "Current quickplay speaker: %s (%s) type=%s",
                                    row.get("title"), row.get("id"), row.get("type")
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
        """Fetch getRows from device (value-only format, no path names)."""
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

    async def _get_rows_by_path(self, path: str) -> dict:
        """Fetch getRows with full metadata and index by path name.

        Uses GET with roles=@all to get path names for each row, then builds
        a dict mapping path → value object for robust lookups.
        """
        try:
            url = (
                f"{self.base_url}/api/getRows?path={quote(path)}"
                f"&roles=%40all&from=0&to=65535&type=structure"
                f"&_nocache={int(time.time() * 1000)}"
            )
            session = self._session
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                if r.status == 200:
                    data = await r.json(content_type=None)
                    result = {}
                    for row in data.get("rows", []):
                        if not isinstance(row, dict):
                            continue
                        row_path = row.get("path")
                        if row_path:
                            val = row.get("value")
                            if val:
                                result[row_path] = val
                    return result
        except (aiohttp.ClientError, TimeoutError, OSError) as err:
            _LOGGER.error("getRows (by path) %s error: %s", path, err)
        return {}

    async def async_get_rca_settings(self) -> dict:
        """Read RCA/ADC settings from settings:/adchls.

        Key paths:
          settings:/adchls/dacMode      — adchlsDACMode (switching/simultaneous)
          settings:/adchls/dacDelay     — i32 (0-500 ms)
          settings:/adchls/fixedVolume  — bool (RCA fixed volume / volume control)
        """
        rows_by_path = await self._get_rows_by_path("settings:/adchls")
        result = {}

        mode_val = rows_by_path.get("settings:/adchls/dacMode")
        if mode_val:
            result["rca_mode_api"] = mode_val.get("adchlsDACMode")

        delay_val = rows_by_path.get("settings:/adchls/dacDelay")
        if delay_val and delay_val.get("type") == "i32_":
            result["rca_delay"] = delay_val.get("i32_")

        vol_val = rows_by_path.get("settings:/adchls/fixedVolume")
        if vol_val and vol_val.get("type") == "bool_":
            result["rca_fixed_volume"] = vol_val.get("bool_")

        _LOGGER.debug("RCA settings: %s", result)
        return result

    async def async_get_current_default_outputs(self) -> dict:
        """Read current settings from settings:/victrola getRows.

        Uses path-based matching (rows are sorted alphabetically by path).
        Actual row paths (verified from device):
          settings:/victrola/autoplay              — bool (autoplay toggle)
          settings:/victrola/autoplayGroup          — string (Sonos default output ID)
          settings:/victrola/autoplayRoonOutput     — string (Roon default output ID)
          settings:/victrola/bluetoothEnabled       — bool
          settings:/victrola/forceLowBitrate        — enum (audio quality)
          settings:/victrola/lightBrightness        — i32 (knob brightness 0-100)
          settings:/victrola/previousSource         — string (previous source path ref)
          settings:/victrola/roonEnabled            — bool
          settings:/victrola/savedOutput            — string (UPnP default output ID)
          settings:/victrola/sonosEnabled           — bool
          settings:/victrola/upnpEnabled            — bool
          settings:/victrola/wirelessAudioDelay     — enum (audio latency)
        """
        rows_by_path = await self._get_rows_by_path("settings:/victrola")
        result = {}

        def _bool(path: str):
            v = rows_by_path.get(path)
            if v and v.get("type") == "bool_":
                return v.get("bool_")
            return None

        def _str(path: str):
            v = rows_by_path.get(path)
            if v and v.get("type") == "string_":
                return v.get("string_")
            return None

        # Source enabled flags
        result["roon_enabled"] = _bool("settings:/victrola/roonEnabled")
        result["sonos_enabled"] = _bool("settings:/victrola/sonosEnabled")
        result["upnp_enabled"] = _bool("settings:/victrola/upnpEnabled")
        result["bluetooth_enabled"] = _bool("settings:/victrola/bluetoothEnabled")

        # Default output IDs
        result["sonos_default_id"] = _str("settings:/victrola/autoplayGroup")
        result["roon_default_id"] = _str("settings:/victrola/autoplayRoonOutput")
        result["upnp_default_id"] = _str("settings:/victrola/savedOutput")
        # previousSource stores last-active source path, not BT default
        prev_src = _str("settings:/victrola/previousSource")
        if prev_src and not prev_src.startswith("settings:/victrola/"):
            result["bluetooth_default_id"] = prev_src
        else:
            result["bluetooth_default_id"] = None

        # Audio settings
        aq = rows_by_path.get("settings:/victrola/forceLowBitrate")
        if aq:
            result["audio_quality_api"] = aq.get("forceLowBitrate")
        al = rows_by_path.get("settings:/victrola/wirelessAudioDelay")
        if al:
            result["audio_latency_api"] = al.get("adchlsLatency")

        # Knob brightness
        kb = rows_by_path.get("settings:/victrola/lightBrightness")
        if kb and kb.get("type") == "i32_":
            result["knob_brightness"] = kb.get("i32_")

        # Autoplay
        result["autoplay"] = _bool("settings:/victrola/autoplay")

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

        The Icecast stream server continuously sends data even when idle
        (~256 bytes/sec of keep-alive frames). When the needle is on, it
        sends ~100-200 KB/s of real audio. We measure throughput over the
        probe window and check if it exceeds 2000 bytes/sec.
        """
        url = f"http://{self.host}:{self._stream_port}/stream"
        try:
            timeout = aiohttp.ClientTimeout(
                total=STREAM_PROBE_TIMEOUT + 2,
                sock_read=STREAM_PROBE_TIMEOUT + 1,
            )
            async with aiohttp.ClientSession() as probe_session:
                async with probe_session.get(url, timeout=timeout) as resp:
                    if resp.status != 200:
                        return False
                    total = 0
                    start = asyncio.get_event_loop().time()
                    try:
                        async for chunk in resp.content.iter_any():
                            total += len(chunk)
                            elapsed = asyncio.get_event_loop().time() - start
                            if elapsed >= STREAM_PROBE_TIMEOUT:
                                break
                    except asyncio.TimeoutError:
                        pass
                    elapsed = asyncio.get_event_loop().time() - start
                    if elapsed <= 0:
                        return False
                    rate = total / elapsed
                    active = rate > 2000  # Well above idle ~256 B/s
                    _LOGGER.debug(
                        "Stream probe: %d bytes in %.1fs = %.0f B/s → %s",
                        total, elapsed, rate,
                        "ACTIVE" if active else "idle",
                    )
                    return active
        except asyncio.TimeoutError:
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

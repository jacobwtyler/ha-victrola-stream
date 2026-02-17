"""Long-poll event listener for Victrola device push notifications.

Uses the device's /api/event/modifyQueue + /api/event/pollQueue system
to receive instant state updates when the device or web UI changes state.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import TYPE_CHECKING

import aiohttp

from .const import (
    EVENT_SUBSCRIPTIONS,
    AUDIO_QUALITY_API_TO_LABEL,
    AUDIO_LATENCY_API_TO_LABEL,
    SOURCE_ROON, SOURCE_SONOS, SOURCE_UPNP, SOURCE_BLUETOOTH,
)

if TYPE_CHECKING:
    from .victrola_api import VictrolaAPI
    from .state_store import VictrolaStateStore
    from .discovery import VictrolaDiscovery
    from .coordinator import VictrolaCoordinator

_LOGGER = logging.getLogger(__name__)

POLL_TIMEOUT_MS = 1500
RECONNECT_DELAY  = 5   # seconds before retrying after failure
MAX_FAILURES     = 3   # consecutive failures before backing off


class VictrolaEventListener:
    """Subscribes to device events and updates state_store in real time."""

    def __init__(
        self,
        api: "VictrolaAPI",
        state_store: "VictrolaStateStore",
        discovery: "VictrolaDiscovery",
        coordinator: "VictrolaCoordinator",
    ) -> None:
        self._api        = api
        self._store      = state_store
        self._discovery  = discovery
        self._coordinator = coordinator
        self._queue_id: str | None = None
        self._task: asyncio.Task | None = None
        self._running = False
        self._failures = 0

    # ── Lifecycle ────────────────────────────────────────────────────────

    async def async_start(self) -> None:
        """Start the event listener background task."""
        self._running = True
        self._task = asyncio.ensure_future(self._listen_loop())
        _LOGGER.info("Victrola event listener started")

    async def async_stop(self) -> None:
        """Stop the event listener and clean up the queue on the device."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._queue_id:
            await self._unsubscribe_all()
        _LOGGER.info("Victrola event listener stopped")

    # ── Internal loop ────────────────────────────────────────────────────

    async def _listen_loop(self) -> None:
        """Main loop: subscribe → poll → handle → repeat."""
        while self._running:
            try:
                # Register queue and subscribe to all paths
                self._queue_id = f"{{{uuid.uuid4()}}}"
                await self._subscribe(self._queue_id)
                self._failures = 0
                _LOGGER.debug("Event queue registered: %s", self._queue_id)

                # Poll loop
                while self._running:
                    events = await self._poll()
                    if events:
                        changed = await self._handle_events(events)
                        if changed:
                            # Push updated state to HA immediately
                            self._coordinator.async_set_updated_data(
                                self._store.to_dict()
                            )

            except asyncio.CancelledError:
                break
            except Exception as err:
                self._failures += 1
                _LOGGER.warning(
                    "Event listener error (attempt %d): %s", self._failures, err
                )
                self._queue_id = None
                delay = RECONNECT_DELAY * min(self._failures, MAX_FAILURES)
                await asyncio.sleep(delay)

    async def _subscribe(self, queue_id: str) -> None:
        """Register queue and subscribe to all event paths."""
        base = self._api.base_url
        nocache = int(time.time() * 1000)

        # First create the queue
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base}/api/event/modifyQueue",
                json={
                    "queueId": "",
                    "subscribe": [],
                    "unsubscribe": [],
                    "_nocache": str(nocache),
                },
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                pass  # queue_id assigned by us, not device

            # Now subscribe with our queue_id
            nocache += 1
            async with session.post(
                f"{base}/api/event/modifyQueue",
                json={
                    "queueId": queue_id,
                    "subscribe": EVENT_SUBSCRIPTIONS,
                    "unsubscribe": [],
                    "_nocache": str(nocache),
                },
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                if r.status != 200:
                    raise ConnectionError(f"modifyQueue failed: {r.status}")

    async def _poll(self) -> list[dict]:
        """Long-poll the event queue. Returns list of changed items."""
        if not self._queue_id:
            return []
        nocache = int(time.time() * 1000)
        url = (
            f"{self._api.base_url}/api/event/pollQueue"
            f"?queueId={self._queue_id}"
            f"&timeout={POLL_TIMEOUT_MS}"
            f"&_nocache={nocache}"
        )
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=POLL_TIMEOUT_MS / 1000 + 3),
                ) as r:
                    if r.status == 200:
                        data = await r.json(content_type=None)
                        return data if isinstance(data, list) else []
                    elif r.status == 404:
                        # Queue expired, need to re-subscribe
                        self._queue_id = None
                        raise ConnectionError("Queue expired (404)")
        except aiohttp.ServerTimeoutError:
            pass  # Normal - poll timeout with no events
        return []

    async def _unsubscribe_all(self) -> None:
        """Clean up queue on device."""
        if not self._queue_id:
            return
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"{self._api.base_url}/api/event/modifyQueue",
                    json={
                        "queueId": self._queue_id,
                        "subscribe": [],
                        "unsubscribe": EVENT_SUBSCRIPTIONS,
                        "_nocache": str(int(time.time() * 1000)),
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=5),
                )
        except Exception:
            pass

    # ── Event handlers ───────────────────────────────────────────────────

    async def _handle_events(self, events: list[dict]) -> bool:
        """Process incoming events, update state_store. Returns True if anything changed."""
        changed = False

        for event in events:
            if not isinstance(event, dict):
                continue
            path  = event.get("path", "")
            etype = event.get("type")
            value = event.get("value")

            _LOGGER.debug("Event: %s type=%s value=%s", path, etype, value)

            # ── speakerQuickplay rows changed ──────────────────────────
            if path == "victrola:ui/speakerQuickplay":
                rows = event.get("rows", [])
                if rows:
                    speakers = self._parse_quickplay_rows(rows)
                    self._discovery.update_from_quickplay(speakers)
                    self._store.available_quickplay_speakers = speakers
                    for spk in speakers:
                        if spk.get("preferred"):
                            self._store.set_quickplay(
                                SOURCE_SONOS,
                                spk["name"],
                                spk["id"],
                            )
                            _LOGGER.info("QuickPlay changed → %s", spk["name"])
                    changed = True

            # ── speakerSelection (default speaker) changed ─────────────
            elif path == "victrola:ui/speakerSelection":
                # Re-fetch ui: to get current default name
                ui_state = await self._api.async_get_ui_state()
                if ui_state.get("current_default_speaker_name"):
                    self._store.current_default_speaker_name = ui_state["current_default_speaker_name"]
                    _LOGGER.info("Default speaker changed → %s",
                                 ui_state["current_default_speaker_name"])
                    changed = True

            # ── Volume changed ─────────────────────────────────────────
            elif path == "player:volume" and value:
                vol = value.get("i32_")
                if vol is not None:
                    self._store.volume = vol
                    _LOGGER.debug("Volume changed → %d", vol)
                    changed = True

            # ── Power target changed ───────────────────────────────────
            elif path == "powermanager:target" and value:
                pt = value.get("powerTarget", {})
                if pt:
                    self._store.power_target = pt.get("target")
                    self._store.power_reason = pt.get("reason")
                    changed = True

            # ── Audio quality changed ──────────────────────────────────
            elif path == "settings:/victrola/forceLowBitrate" and value:
                api_val = value.get("forceLowBitrate")
                if api_val:
                    label = AUDIO_QUALITY_API_TO_LABEL.get(api_val, "Standard")
                    self._store.set_audio_quality(label)
                    changed = True

            # ── Audio latency changed ──────────────────────────────────
            elif path == "settings:/victrola/wirelessAudioDelay" and value:
                api_val = value.get("adchlsLatency")
                if api_val:
                    label = AUDIO_LATENCY_API_TO_LABEL.get(api_val, "Medium")
                    self._store.set_audio_latency(label)
                    changed = True

            # ── Knob brightness changed ────────────────────────────────
            elif path == "settings:/victrola/lightBrightness" and value:
                brightness = value.get("i32_")
                if brightness is not None:
                    self._store.set_knob_brightness(brightness)
                    changed = True

            # ── Source enabled/disabled ────────────────────────────────
            elif path in (
                "settings:/victrola/roonEnabled",
                "settings:/victrola/sonosEnabled",
                "settings:/victrola/upnpEnabled",
                "settings:/victrola/bluetoothEnabled",
            ) and value:
                source_map = {
                    "settings:/victrola/roonEnabled":      SOURCE_ROON,
                    "settings:/victrola/sonosEnabled":     SOURCE_SONOS,
                    "settings:/victrola/upnpEnabled":      SOURCE_UPNP,
                    "settings:/victrola/bluetoothEnabled": SOURCE_BLUETOOTH,
                }
                source = source_map[path]
                enabled = value.get("bool_")
                if enabled is not None:
                    self._store.set_source_enabled(source, enabled)
                    if enabled:
                        self._store.current_source = source
                    changed = True

            # ── Mute changed ──────────────────────────────────────────────
            elif path == "settings:/mediaPlayer/mute" and value:
                val = value.get("bool_")
                if val is not None:
                    self._store.muted = val
                    changed = True

            # ── Autoplay changed ───────────────────────────────────────
            elif path == "settings:/victrola/autoplay" and value:
                val = value.get("bool_")
                if val is not None:
                    self._store.autoplay = val
                    changed = True

        return changed

    def _parse_quickplay_rows(self, rows: list) -> list[dict]:
        """Parse speakerQuickplay rows into normalized speaker dicts."""
        speakers = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            name  = row.get("title") or row.get("name")
            spk_id = row.get("id")
            if not name or not spk_id:
                continue
            val = row.get("value", {})
            sg = val.get("sonosGroup", {}) if val else {}
            speakers.append({
                "name":           name,
                "id":             spk_id,
                "path":           row.get("path"),
                "type":           row.get("type"),
                "preferred":      row.get("preferred", False),
                "sonos_group_id": sg.get("sonosGroupId"),
            })
        return speakers

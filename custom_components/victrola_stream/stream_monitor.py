"""Stream monitor - persistent connection for near-instant needle detection.

Maintains a long-lived connection to the Victrola's Icecast stream server.
The server always sends Ogg FLAC headers on connect (~300-1000 bytes),
then only sends audio frames when the ADC is active (needle on record).

Detection latency:
  Needle drop: <1 second (data arrives on persistent connection)
  Needle lift:  ~3 seconds (read timeout fires)
"""
from __future__ import annotations

import asyncio
import logging

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Seconds without data before declaring idle
IDLE_TIMEOUT = 3.0
# Seconds before reconnecting after connection failure
RECONNECT_DELAY = 5.0
# If we receive more than this many bytes before the first timeout,
# the needle was already on when we connected (headers are <1KB)
HEADER_OVERFLOW = 4096


class VictrolaStreamMonitor:
    """Watches the ADC stream for audio data flow."""

    def __init__(self, api, state_store, coordinator) -> None:
        self._api = api
        self._state_store = state_store
        self._coordinator = coordinator
        self._running = False
        self._task: asyncio.Task | None = None

    async def async_start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run())
        _LOGGER.info(
            "Stream monitor started on %s:%d",
            self._api.host, self._api.stream_port,
        )

    async def async_stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        _LOGGER.info("Stream monitor stopped")

    def _set_streaming(self, streaming: bool) -> None:
        """Update state and push to HA immediately if changed."""
        if self._state_store.is_streaming != streaming:
            self._state_store.is_streaming = streaming
            _LOGGER.info(
                "Streaming state: %s", "PLAYING" if streaming else "IDLE"
            )
            self._coordinator.async_set_updated_data(
                self._state_store.to_dict()
            )

    async def _run(self) -> None:
        """Outer loop — reconnects on failure."""
        while self._running:
            try:
                await self._monitor_connection()
            except asyncio.CancelledError:
                raise
            except (aiohttp.ClientError, OSError) as err:
                _LOGGER.debug("Stream monitor connection lost: %s", err)
            except Exception as err:
                _LOGGER.error("Stream monitor error: %s", err)

            self._set_streaming(False)
            if self._running:
                await asyncio.sleep(RECONNECT_DELAY)

    async def _monitor_connection(self) -> None:
        """Single connection lifecycle.

        Phase 1 (header consumption):
          Read data until either a timeout fires (= headers done, needle off)
          or we accumulate >HEADER_OVERFLOW bytes (= needle already on).

        Phase 2 (audio monitoring):
          Any data arriving = needle on.
          Timeout with no data  = needle off.
        """
        url = f"http://{self._api.host}:{self._api.stream_port}/stream.flac"
        conn_timeout = aiohttp.ClientTimeout(total=None, sock_connect=10)

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=conn_timeout) as resp:
                if resp.status != 200:
                    _LOGGER.warning("Stream server HTTP %d", resp.status)
                    return

                _LOGGER.debug("Stream monitor connected")
                total_bytes = 0
                headers_done = False

                while self._running:
                    try:
                        chunk = await asyncio.wait_for(
                            resp.content.readany(), timeout=IDLE_TIMEOUT
                        )
                        if not chunk:
                            return  # Connection closed by server

                        total_bytes += len(chunk)

                        if headers_done:
                            # Past headers — any data is audio
                            self._set_streaming(True)
                        elif total_bytes > HEADER_OVERFLOW:
                            # Way more data than headers — already streaming
                            headers_done = True
                            self._set_streaming(True)
                        # else: still in header phase, keep reading

                    except asyncio.TimeoutError:
                        if not headers_done:
                            # First timeout after headers = monitoring begins
                            headers_done = True
                            _LOGGER.debug(
                                "Headers consumed (%d bytes), monitoring",
                                total_bytes,
                            )
                        else:
                            # Timeout during monitoring = no audio
                            self._set_streaming(False)

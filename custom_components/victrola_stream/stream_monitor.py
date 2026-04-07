"""Stream monitor - persistent connection for near-instant needle detection.

Maintains a long-lived connection to the Victrola's Icecast stream server.
The server continuously sends ADC audio data regardless of needle position:
  - Needle UP:   ~256 bytes/sec (silence frames, keep-alive)
  - Needle DOWN: ~100,000+ bytes/sec (real audio)

Detection method: time-to-fill measurement.
  We attempt to read a fixed PROBE_BYTES chunk and measure how long it takes.
  Fast fill (<FILL_TIME_THRESHOLD) = needle on, active audio.
  Slow fill (timeout) = needle off, idle keep-alive only.

This avoids aiohttp buffer-backlog issues that can occur with rate-window
approaches when transitioning from active to idle.

Detection latency:
  Needle drop: <1 second (large data burst fills probe instantly)
  Needle lift:  ~FILL_TIMEOUT seconds (read times out waiting for data)

Port discovery:
  The Icecast server port changes after device reboots. On startup and
  after connection failures, we scan for the port by looking for an HTTP
  server returning Content-Type: audio/* on the /stream endpoint.
"""
from __future__ import annotations

import asyncio
import logging

import aiohttp

_LOGGER = logging.getLogger(__name__)

# ── Timing ──────────────────────────────────────────────────────────────
RECONNECT_DELAY = 5.0
# Time to consume initial Ogg/FLAC headers before monitoring begins.
HEADER_PHASE_SECS = 4.0

# ── Fill-time detection ─────────────────────────────────────────────────
# Bytes to attempt reading per probe cycle.
# At ~100 KB/s (active), this fills in ~50ms.
# At ~256 B/s (idle), this would take ~20 seconds — well past timeout.
PROBE_BYTES = 5000
# Max time to wait for PROBE_BYTES. If exceeded → idle.
# Must be longer than the idle inter-frame gap (~0.5s) times the number
# of frames needed, but short enough for responsive detection.
FILL_TIMEOUT = 3.0
# After detecting idle, require this many consecutive idle probes before
# declaring needle-off (debounce brief audio dips during track changes).
IDLE_PROBES_REQUIRED = 1
# Short pause between probe cycles to avoid busy-looping.
PROBE_INTERVAL = 0.2
# If we receive exactly 0 bytes this many times in a row, assume
# the connection is dead (half-open after device reboot) and reconnect.
ZERO_BYTES_RECONNECT = 10
# Port scan range for discovering the Icecast server after reboots.
PORT_SCAN_START = 34000
PORT_SCAN_END = 36000
PORT_SCAN_TIMEOUT = 0.3
# How often to retry port discovery when the stream server isn't found.
PORT_DISCOVERY_INTERVAL = 15.0


class VictrolaStreamMonitor:
    """Watches the ADC stream for audio data flow using fill-time analysis."""

    def __init__(self, api, state_store, coordinator) -> None:
        self._api = api
        self._state_store = state_store
        self._coordinator = coordinator
        self._running = False
        self._task: asyncio.Task | None = None
        self._discovered_port: int | None = None

    async def async_start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run())
        _LOGGER.info(
            "Stream monitor started on %s:%d (probe: %d bytes, "
            "fill timeout: %.1fs)",
            self._api.host, self._api.stream_port,
            PROBE_BYTES, FILL_TIMEOUT,
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
        if streaming:
            # Stream data proves device is reachable
            self._state_store.connected = True
        if self._state_store.is_streaming != streaming:
            self._state_store.is_streaming = streaming
            _LOGGER.info(
                "Streaming state: %s", "PLAYING" if streaming else "IDLE"
            )
            self._coordinator.async_set_updated_data(
                self._state_store.to_dict()
            )

    async def _discover_port(self) -> int | None:
        """Scan for the Icecast stream server port.

        The port changes after device reboots. We scan a range around the
        default port looking for an HTTP server that returns audio content.
        """
        host = self._api.host
        default_port = self._api.stream_port

        # Try the configured port first
        ports_to_try = [default_port]
        # Then try the last discovered port
        if self._discovered_port and self._discovered_port != default_port:
            ports_to_try.append(self._discovered_port)

        # Then scan the range
        for port in ports_to_try:
            if await self._probe_port(host, port):
                return port

        # Full range scan
        _LOGGER.debug(
            "Default port %d not responding, scanning %d-%d...",
            default_port, PORT_SCAN_START, PORT_SCAN_END,
        )
        for port in range(PORT_SCAN_START, PORT_SCAN_END + 1):
            if port in ports_to_try:
                continue
            if await self._probe_port(host, port):
                return port

        return None

    @staticmethod
    async def _probe_port(host: str, port: int) -> bool:
        """Check if a port serves the Icecast audio stream."""
        try:
            conn = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(conn, PORT_SCAN_TIMEOUT)
            writer.write(
                f"GET /stream HTTP/1.1\r\nHost: {host}\r\n\r\n".encode()
            )
            await writer.drain()
            header = await asyncio.wait_for(reader.read(512), 2.0)
            writer.close()
            # Look for audio content type in response
            return b"audio/" in header
        except (OSError, asyncio.TimeoutError, TimeoutError):
            return False

    async def _run(self) -> None:
        """Outer loop — discovers port, connects, reconnects on failure."""
        while self._running:
            # Discover the stream port
            port = await self._discover_port()
            if port is None:
                _LOGGER.debug(
                    "Stream server not found on %s — retrying in %.0fs",
                    self._api.host, PORT_DISCOVERY_INTERVAL,
                )
                self._set_streaming(False)
                if self._running:
                    await asyncio.sleep(PORT_DISCOVERY_INTERVAL)
                continue

            if port != self._api.stream_port:
                _LOGGER.info(
                    "Stream server discovered on port %d (default: %d)",
                    port, self._api.stream_port,
                )
            self._discovered_port = port

            try:
                await self._monitor_connection(port)
            except asyncio.CancelledError:
                raise
            except (aiohttp.ClientError, OSError) as err:
                _LOGGER.debug("Stream monitor connection lost: %s", err)
            except Exception as err:
                _LOGGER.error("Stream monitor error: %s", err)

            self._set_streaming(False)
            if self._running:
                await asyncio.sleep(RECONNECT_DELAY)

    async def _read_exactly(self, resp, n_bytes: int, timeout: float) -> int:
        """Read up to n_bytes from response within timeout. Returns bytes read."""
        total = 0
        try:
            async with asyncio.timeout(timeout):
                while total < n_bytes:
                    chunk = await resp.content.readany()
                    if not chunk:
                        return -1  # Connection closed
                    total += len(chunk)
        except (asyncio.TimeoutError, TimeoutError):
            pass  # Timeout is expected for idle detection
        return total

    async def _monitor_connection(self, port: int) -> None:
        """Single connection lifecycle with fill-time monitoring.

        Phase 1 (header consumption, HEADER_PHASE_SECS):
          Read and discard initial Ogg container headers. The server
          always sends headers on connect regardless of needle state.

        Phase 2 (fill-time probing):
          Repeatedly try to read PROBE_BYTES within FILL_TIMEOUT.
          If the buffer fills quickly → active audio → needle on.
          If the read times out → idle keep-alive → needle off.
        """
        url = f"http://{self._api.host}:{port}/stream"
        conn_timeout = aiohttp.ClientTimeout(total=None, sock_connect=10)

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=conn_timeout) as resp:
                if resp.status != 200:
                    _LOGGER.warning("Stream server HTTP %d", resp.status)
                    return

                _LOGGER.debug("Stream monitor connected")

                # ── Phase 1: Consume and discard headers ──────────────
                header_bytes = await self._read_exactly(
                    resp, 1_000_000, HEADER_PHASE_SECS
                )
                if header_bytes == -1:
                    return  # Connection closed

                # If a LOT of data arrived during header phase, needle
                # was probably already on when we connected.
                header_rate = header_bytes / HEADER_PHASE_SECS
                already_streaming = header_rate > 2000
                _LOGGER.debug(
                    "Header phase: %d bytes (%.0f B/s) → %s",
                    header_bytes, header_rate,
                    "already streaming" if already_streaming else "idle",
                )
                if already_streaming:
                    self._set_streaming(True)

                # ── Phase 2: Fill-time probing ────────────────────────
                consecutive_idle = 0
                consecutive_zero = 0

                while self._running:
                    bytes_read = await self._read_exactly(
                        resp, PROBE_BYTES, FILL_TIMEOUT
                    )

                    if bytes_read == -1:
                        return  # Connection closed

                    if bytes_read >= PROBE_BYTES:
                        # Buffer filled within timeout → active audio
                        consecutive_idle = 0
                        consecutive_zero = 0
                        self._set_streaming(True)
                        _LOGGER.debug(
                            "Probe: %d/%d bytes in <%.1fs [ACTIVE]",
                            bytes_read, PROBE_BYTES, FILL_TIMEOUT,
                        )
                    elif bytes_read == 0:
                        # No data at all — possible dead connection
                        consecutive_zero += 1
                        consecutive_idle += 1
                        if consecutive_idle >= IDLE_PROBES_REQUIRED:
                            self._set_streaming(False)
                        if consecutive_zero >= ZERO_BYTES_RECONNECT:
                            _LOGGER.warning(
                                "Stream monitor: %d consecutive zero-byte "
                                "probes — reconnecting",
                                consecutive_zero,
                            )
                            return  # Break out to trigger reconnect
                    else:
                        # Got some data but timed out before filling → idle
                        consecutive_idle += 1
                        consecutive_zero = 0
                        _LOGGER.debug(
                            "Probe: %d/%d bytes (timeout) [idle %d/%d]",
                            bytes_read, PROBE_BYTES,
                            consecutive_idle, IDLE_PROBES_REQUIRED,
                        )
                        if consecutive_idle >= IDLE_PROBES_REQUIRED:
                            self._set_streaming(False)

                    # Brief pause to avoid busy-loop during active streaming
                    await asyncio.sleep(PROBE_INTERVAL)

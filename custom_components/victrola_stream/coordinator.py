"""Coordinator - pings device for connection status, uses state_store for settings."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class VictrolaCoordinator(DataUpdateCoordinator):
    """Polls Victrola connection status; settings state tracked in state_store."""

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
        """Check connection and return combined state."""
        try:
            connected = await self.api.async_test_connection()
            self.state_store.connected = connected
            return self.state_store.to_dict()
        except Exception as err:
            self.state_store.connected = False
            raise UpdateFailed(f"Cannot reach Victrola: {err}")

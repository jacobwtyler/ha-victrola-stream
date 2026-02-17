"""Data coordinator for Victrola Stream - polls device state."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class VictrolaCoordinator(DataUpdateCoordinator):
    """Coordinator to poll Victrola state every 30 seconds."""

    def __init__(self, hass: HomeAssistant, api: Any) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch all state from Victrola device."""
        try:
            return await self.api.async_get_full_state()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Victrola: {err}")

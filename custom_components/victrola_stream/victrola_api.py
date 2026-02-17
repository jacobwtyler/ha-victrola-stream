"""Victrola API wrapper."""
from __future__ import annotations

import aiohttp
import asyncio
import json
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


class VictrolaAPI:
    """Interface to Victrola Stream API."""

    def __init__(self, host: str, port: int = 80):
        """Initialize the Victrola API."""
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"

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

    async def async_set_data(
        self, path: str, role: str, value: dict[str, Any]
    ) -> bool:
        """Set data via Victrola API."""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"path": path, "role": role, "value": value}
                
                async with session.post(
                    f"{self.base_url}/api/setData",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    return response.status == 200
        except Exception as err:
            _LOGGER.error("setData failed: %s", err)
            return False

    async def async_get_data(self, path: str, roles: list[str]) -> dict | None:
        """Get data via Victrola API."""
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
                        return await response.json()
                    return None
        except Exception as err:
            _LOGGER.error("getData failed: %s", err)
            return None

    async def async_set_source(self, source_type: str, speaker_id: str) -> bool:
        """Set the active source and speaker."""
        value = {"type": source_type, "id": speaker_id}
        
        success1 = await self.async_set_data(
            "victrola:ui/setDefaultOutput", "activate", value
        )
        success2 = await self.async_set_data(
            "victrola:ui/quickplay", "activate", value
        )
        
        return success1 or success2

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

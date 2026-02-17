"""Speaker discovery for Victrola Stream."""
from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    DEFAULT_ROON_CORE_ID,
    ROON_SEED_MAPPINGS,
    SOURCE_ROON,
    SOURCE_SONOS,
    SOURCE_UPNP,
    SOURCE_BLUETOOTH,
)

_LOGGER = logging.getLogger(__name__)


class VictrolaDiscovery:
    """Discover speakers from Home Assistant integrations."""

    def __init__(self, hass: HomeAssistant, api: Any):
        """Initialize discovery."""
        self.hass = hass
        self.api = api
        self.speakers = {
            SOURCE_ROON: {},
            SOURCE_SONOS: {},
            SOURCE_UPNP: {},
            SOURCE_BLUETOOTH: {},
        }
        self.roon_core_id = DEFAULT_ROON_CORE_ID

    async def async_discover_all_sources(self) -> dict:
        """Discover all source types."""
        await self.async_discover_roon()
        await self.async_discover_sonos()
        await self.async_discover_upnp()
        await self.async_discover_bluetooth()
        
        return self.speakers

    async def async_discover_roon(self):
        """Discover Roon speakers."""
        entity_reg = er.async_get(self.hass)
        
        for entity in entity_reg.entities.values():
            if entity.platform != "roon":
                continue
            
            if not entity.entity_id.startswith("media_player."):
                continue
            
            if not entity.unique_id.startswith("roon_"):
                continue
            
            parts = entity.unique_id.split("_", 2)
            if len(parts) < 3:
                continue
            
            speaker_name = parts[2]
            output_id = self._fuzzy_match(speaker_name, ROON_SEED_MAPPINGS)
            
            self.speakers[SOURCE_ROON][speaker_name] = {
                "name": speaker_name,
                "entity_id": entity.entity_id,
                "output_id": output_id,
                "victrola_id": f"{self.roon_core_id}:{output_id}" if output_id else None,
                "mapped": output_id is not None,
            }
        
        _LOGGER.info("Discovered %d Roon speakers", len(self.speakers[SOURCE_ROON]))

    async def async_discover_sonos(self):
        """Discover Sonos speakers."""
        entity_reg = er.async_get(self.hass)
        
        sonos_by_rincon = {}
        
        for entity in entity_reg.entities.values():
            if entity.platform != "sonos":
                continue
            
            if not entity.entity_id.startswith("media_player."):
                continue
            
            rincon_match = re.search(r"RINCON_[A-F0-9]+", entity.unique_id, re.IGNORECASE)
            if not rincon_match:
                continue
            
            rincon_id = rincon_match.group(0)
            speaker_name = entity.original_name or entity.name or "Unknown"
            
            if rincon_id not in sonos_by_rincon:
                sonos_by_rincon[rincon_id] = {
                    "name": speaker_name,
                    "entity_id": entity.entity_id,
                    "rincon_id": rincon_id,
                    "victrola_id": rincon_id,
                    "mapped": True,
                }
        
        self.speakers[SOURCE_SONOS] = sonos_by_rincon
        _LOGGER.info("Discovered %d Sonos speakers", len(self.speakers[SOURCE_SONOS]))

    async def async_discover_upnp(self):
        """Discover UPnP devices."""
        entity_reg = er.async_get(self.hass)
        
        for entity in entity_reg.entities.values():
            if entity.platform not in ["dlna_dmr", "upnp"]:
                continue
            
            if not entity.entity_id.startswith("media_player."):
                continue
            
            speaker_name = entity.original_name or entity.name or "Unknown"
            
            upnp_uuid = None
            if entity.unique_id.startswith("uuid:"):
                upnp_uuid = entity.unique_id
            else:
                match = re.search(r"uuid:[a-fA-F0-9\-]+", entity.unique_id)
                if match:
                    upnp_uuid = match.group(0)
            
            if upnp_uuid:
                self.speakers[SOURCE_UPNP][speaker_name] = {
                    "name": speaker_name,
                    "entity_id": entity.entity_id,
                    "upnp_uuid": upnp_uuid,
                    "victrola_id": upnp_uuid,
                    "mapped": True,
                }
        
        _LOGGER.info("Discovered %d UPnP devices", len(self.speakers[SOURCE_UPNP]))

    async def async_discover_bluetooth(self):
        """Discover Bluetooth devices."""
        entity_reg = er.async_get(self.hass)
        
        for entity in entity_reg.entities.values():
            if "bluetooth" not in entity.platform.lower():
                continue
            
            speaker_name = entity.original_name or entity.name or "Unknown"
            
            bt_id = None
            mac_match = re.search(
                r"[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}",
                entity.unique_id,
                re.IGNORECASE,
            )
            if mac_match:
                bt_id = mac_match.group(0)
            else:
                bt_id = entity.unique_id
            
            if bt_id:
                self.speakers[SOURCE_BLUETOOTH][speaker_name] = {
                    "name": speaker_name,
                    "entity_id": entity.entity_id,
                    "bluetooth_id": bt_id,
                    "victrola_id": bt_id,
                    "mapped": True,
                }
        
        _LOGGER.info("Discovered %d Bluetooth devices", len(self.speakers[SOURCE_BLUETOOTH]))

    def _fuzzy_match(self, name: str, mapping: dict) -> str | None:
        """Fuzzy match speaker name."""
        normalized = name.lower().replace(" ", "").replace("-", "").replace("_", "")
        
        for mapped_name, output_id in mapping.items():
            mapped_norm = mapped_name.lower().replace(" ", "").replace("-", "").replace("_", "")
            if normalized == mapped_norm or normalized in mapped_norm or mapped_norm in normalized:
                return output_id
        
        return None

    def get_speakers_for_source(self, source: str) -> dict:
        """Get speakers for a specific source."""
        return self.speakers.get(source, {})

    def get_speaker_victrola_id(self, source: str, speaker_name: str) -> str | None:
        """Get Victrola ID for a speaker."""
        speakers = self.speakers.get(source, {})
        speaker = speakers.get(speaker_name)
        return speaker["victrola_id"] if speaker else None

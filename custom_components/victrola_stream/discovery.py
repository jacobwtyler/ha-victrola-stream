"""Speaker discovery for all Victrola source types."""
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
        self.hass = hass
        self.api = api
        self.speakers: dict[str, dict] = {
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

    # ─────────────────────────────────────────────
    # Roon
    # ─────────────────────────────────────────────

    async def async_discover_roon(self):
        """Discover Roon speakers from HA Roon integration."""
        entity_reg = er.async_get(self.hass)
        seen = set()

        for entity in entity_reg.entities.values():
            if entity.platform != "roon":
                continue
            if not entity.entity_id.startswith("media_player."):
                continue
            if not entity.unique_id or not entity.unique_id.startswith("roon_"):
                continue

            parts = entity.unique_id.split("_", 2)
            if len(parts) < 3:
                continue

            speaker_name = parts[2]
            if speaker_name in seen:
                continue
            seen.add(speaker_name)

            output_id = self._fuzzy_match(speaker_name, ROON_SEED_MAPPINGS)

            self.speakers[SOURCE_ROON][speaker_name] = {
                "name": speaker_name,
                "entity_id": entity.entity_id,
                "output_id": output_id,
                "victrola_id": f"{self.roon_core_id}:{output_id}" if output_id else None,
                "mapped": output_id is not None,
            }

        mapped = sum(1 for s in self.speakers[SOURCE_ROON].values() if s["mapped"])
        _LOGGER.info("Roon: %d speakers discovered (%d mapped)", len(self.speakers[SOURCE_ROON]), mapped)

    # ─────────────────────────────────────────────
    # Sonos
    # ─────────────────────────────────────────────

    async def async_discover_sonos(self):
        """Discover Sonos speakers from HA Sonos integration."""
        entity_reg = er.async_get(self.hass)
        sonos_by_rincon: dict[str, dict] = {}

        for entity in entity_reg.entities.values():
            if entity.platform != "sonos":
                continue
            if not entity.entity_id.startswith("media_player."):
                continue
            if not entity.unique_id:
                continue

            rincon_match = re.search(r"RINCON_[A-F0-9]+", entity.unique_id, re.IGNORECASE)
            if not rincon_match:
                continue

            rincon_id = rincon_match.group(0).upper()
            if rincon_id in sonos_by_rincon:
                continue

            speaker_name = entity.original_name or entity.name or rincon_id

            sonos_by_rincon[rincon_id] = {
                "name": speaker_name,
                "entity_id": entity.entity_id,
                "rincon_id": rincon_id,
                "victrola_id": rincon_id,
                "mapped": True,
            }

        # Key by speaker name for easier lookup
        for info in sonos_by_rincon.values():
            self.speakers[SOURCE_SONOS][info["name"]] = info

        _LOGGER.info("Sonos: %d speakers discovered", len(self.speakers[SOURCE_SONOS]))

    # ─────────────────────────────────────────────
    # UPnP / DLNA
    # ─────────────────────────────────────────────

    async def async_discover_upnp(self):
        """Discover UPnP/DLNA devices from HA DLNA integration."""
        entity_reg = er.async_get(self.hass)

        for entity in entity_reg.entities.values():
            if entity.platform not in ["dlna_dmr", "upnp"]:
                continue
            if not entity.entity_id.startswith("media_player."):
                continue
            if not entity.unique_id:
                continue

            upnp_uuid = None
            if entity.unique_id.startswith("uuid:"):
                upnp_uuid = entity.unique_id
            else:
                match = re.search(r"uuid:[a-fA-F0-9\-]+", entity.unique_id)
                if match:
                    upnp_uuid = match.group(0)

            if not upnp_uuid:
                continue

            speaker_name = entity.original_name or entity.name or upnp_uuid

            self.speakers[SOURCE_UPNP][speaker_name] = {
                "name": speaker_name,
                "entity_id": entity.entity_id,
                "upnp_uuid": upnp_uuid,
                "victrola_id": upnp_uuid,
                "mapped": True,
            }

        _LOGGER.info("UPnP: %d devices discovered", len(self.speakers[SOURCE_UPNP]))

    # ─────────────────────────────────────────────
    # Bluetooth
    # ─────────────────────────────────────────────

    async def async_discover_bluetooth(self):
        """Discover Bluetooth devices from HA Bluetooth integration."""
        entity_reg = er.async_get(self.hass)

        for entity in entity_reg.entities.values():
            if not entity.platform or "bluetooth" not in entity.platform.lower():
                continue
            if not entity.entity_id.startswith("media_player."):
                continue
            if not entity.unique_id:
                continue

            speaker_name = entity.original_name or entity.name or "Unknown"

            mac_match = re.search(
                r"[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}",
                entity.unique_id,
                re.IGNORECASE,
            )
            bt_id = mac_match.group(0).upper() if mac_match else entity.unique_id

            self.speakers[SOURCE_BLUETOOTH][speaker_name] = {
                "name": speaker_name,
                "entity_id": entity.entity_id,
                "bluetooth_id": bt_id,
                "victrola_id": bt_id,
                "mapped": True,
            }

        _LOGGER.info("Bluetooth: %d devices discovered", len(self.speakers[SOURCE_BLUETOOTH]))

    # ─────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────

    def _fuzzy_match(self, name: str, mapping: dict) -> str | None:
        """Fuzzy match speaker name to output ID."""
        n = name.lower().replace(" ", "").replace("-", "").replace("_", "")
        for mapped_name, output_id in mapping.items():
            m = mapped_name.lower().replace(" ", "").replace("-", "").replace("_", "")
            if n == m or n in m or m in n:
                return output_id
        return None

    def get_speakers_for_source(self, source: str) -> dict:
        """Get all speakers for a source type."""
        return self.speakers.get(source, {})

    def get_speaker_victrola_id(self, source: str, speaker_name: str) -> str | None:
        """Get the Victrola ID for a named speaker."""
        speakers = self.speakers.get(source, {})
        speaker = speakers.get(speaker_name)
        return speaker["victrola_id"] if speaker else None

    def add_learned_speaker(self, source: str, speaker_name: str, victrola_id: str):
        """Add a manually learned speaker mapping."""
        if source not in self.speakers:
            self.speakers[source] = {}
        self.speakers[source][speaker_name] = {
            "name": speaker_name,
            "entity_id": None,
            "victrola_id": victrola_id,
            "mapped": True,
            "learned": True,
        }
        _LOGGER.info("Learned speaker: %s/%s = %s", source, speaker_name, victrola_id)

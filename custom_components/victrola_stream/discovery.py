"""Speaker discovery using HA entity registry + seed mappings."""
from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    DEFAULT_ROON_CORE_ID,
    ROON_SEED_MAPPINGS,
    SONOS_SEED_MAPPINGS,
    UPNP_SEED_MAPPINGS,
    SOURCE_ROON, SOURCE_SONOS, SOURCE_UPNP, SOURCE_BLUETOOTH,
)

_LOGGER = logging.getLogger(__name__)


class VictrolaDiscovery:
    """Discovers speakers from HA integrations."""

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.speakers: dict[str, dict] = {
            SOURCE_ROON: {},
            SOURCE_SONOS: {},
            SOURCE_UPNP: {},
            SOURCE_BLUETOOTH: {},
        }
        self.roon_core_id = DEFAULT_ROON_CORE_ID

    async def async_discover_all(self) -> dict:
        await self.async_discover_roon()
        await self.async_discover_sonos()
        await self.async_discover_upnp()
        await self.async_discover_bluetooth()
        return self.speakers

    async def async_discover_roon(self):
        """Discover Roon speakers - merge HA entities with seed mappings."""
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

            # Try seed mapping (has full suffix IDs)
            output_id = self._fuzzy_match(speaker_name, ROON_SEED_MAPPINGS)
            victrola_id = f"{self.roon_core_id}:{output_id}" if output_id else None

            self.speakers[SOURCE_ROON][speaker_name] = {
                "name": speaker_name,
                "entity_id": entity.entity_id,
                "victrola_id": victrola_id,
                "mapped": victrola_id is not None,
            }

        # Add any seed speakers not found in HA
        for name, output_id in ROON_SEED_MAPPINGS.items():
            if name not in self.speakers[SOURCE_ROON]:
                self.speakers[SOURCE_ROON][name] = {
                    "name": name,
                    "entity_id": None,
                    "victrola_id": f"{self.roon_core_id}:{output_id}",
                    "mapped": True,
                }

        mapped = sum(1 for s in self.speakers[SOURCE_ROON].values() if s["mapped"])
        _LOGGER.info("Roon: %d speakers (%d mapped)", len(self.speakers[SOURCE_ROON]), mapped)

    async def async_discover_sonos(self):
        """Discover Sonos speakers."""
        entity_reg = er.async_get(self.hass)
        seen_rincons = set()

        for entity in entity_reg.entities.values():
            if entity.platform != "sonos":
                continue
            if not entity.entity_id.startswith("media_player."):
                continue
            if not entity.unique_id:
                continue

            m = re.search(r"RINCON_[A-F0-9]+", entity.unique_id, re.IGNORECASE)
            if not m:
                continue

            rincon = m.group(0).upper()
            if rincon in seen_rincons:
                continue
            seen_rincons.add(rincon)

            speaker_name = entity.original_name or entity.name or rincon
            # Try to match to seed for clean names
            seed_name = self._fuzzy_match_reverse(rincon, SONOS_SEED_MAPPINGS)

            display_name = seed_name or speaker_name

            self.speakers[SOURCE_SONOS][display_name] = {
                "name": display_name,
                "entity_id": entity.entity_id,
                "victrola_id": rincon,
                "mapped": True,
            }

        # Add any seed speakers not in HA
        for name, rincon in SONOS_SEED_MAPPINGS.items():
            if name not in self.speakers[SOURCE_SONOS]:
                self.speakers[SOURCE_SONOS][name] = {
                    "name": name,
                    "entity_id": None,
                    "victrola_id": rincon,
                    "mapped": True,
                }

        _LOGGER.info("Sonos: %d speakers", len(self.speakers[SOURCE_SONOS]))

    async def async_discover_upnp(self):
        """Discover UPnP/DLNA devices."""
        entity_reg = er.async_get(self.hass)

        for entity in entity_reg.entities.values():
            if entity.platform not in ["dlna_dmr", "upnp"]:
                continue
            if not entity.entity_id.startswith("media_player."):
                continue

            upnp_uuid = None
            if entity.unique_id and entity.unique_id.startswith("uuid:"):
                upnp_uuid = entity.unique_id
            elif entity.unique_id:
                m = re.search(r"uuid:[a-fA-F0-9\-]+", entity.unique_id)
                if m:
                    upnp_uuid = m.group(0)

            if not upnp_uuid:
                continue

            speaker_name = entity.original_name or entity.name or upnp_uuid
            seed_name = self._fuzzy_match_reverse(upnp_uuid, UPNP_SEED_MAPPINGS)
            display_name = seed_name or speaker_name

            self.speakers[SOURCE_UPNP][display_name] = {
                "name": display_name,
                "entity_id": entity.entity_id,
                "victrola_id": upnp_uuid,
                "mapped": True,
            }

        # Add seeds not in HA
        for name, uuid in UPNP_SEED_MAPPINGS.items():
            if name not in self.speakers[SOURCE_UPNP]:
                self.speakers[SOURCE_UPNP][name] = {
                    "name": name,
                    "entity_id": None,
                    "victrola_id": uuid,
                    "mapped": True,
                }

        _LOGGER.info("UPnP: %d devices", len(self.speakers[SOURCE_UPNP]))

    async def async_discover_bluetooth(self):
        """Discover Bluetooth devices."""
        entity_reg = er.async_get(self.hass)

        for entity in entity_reg.entities.values():
            if not entity.platform or "bluetooth" not in entity.platform.lower():
                continue
            if not entity.entity_id.startswith("media_player."):
                continue

            speaker_name = entity.original_name or entity.name or "Unknown"
            m = re.search(
                r"[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}",
                entity.unique_id or "", re.IGNORECASE,
            )
            bt_id = m.group(0).upper() if m else (entity.unique_id or "unknown")

            self.speakers[SOURCE_BLUETOOTH][speaker_name] = {
                "name": speaker_name,
                "entity_id": entity.entity_id,
                "victrola_id": bt_id,
                "mapped": True,
            }

        _LOGGER.info("Bluetooth: %d devices", len(self.speakers[SOURCE_BLUETOOTH]))

    # ─────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────

    def _normalize(self, s: str) -> str:
        return s.lower().replace(" ", "").replace("-", "").replace("_", "")

    def _fuzzy_match(self, name: str, mapping: dict) -> str | None:
        """Match name to a key in mapping, return value."""
        n = self._normalize(name)
        for k, v in mapping.items():
            if n == self._normalize(k) or n in self._normalize(k) or self._normalize(k) in n:
                return v
        return None

    def _fuzzy_match_reverse(self, value: str, mapping: dict) -> str | None:
        """Match a value in mapping, return key (name)."""
        v = self._normalize(value)
        for k, mv in mapping.items():
            if v == self._normalize(mv):
                return k
        return None

    def get_speakers(self, source: str) -> dict:
        return self.speakers.get(source, {})

    def get_speaker_names(self, source: str) -> list[str]:
        return list(self.speakers.get(source, {}).keys())

    def get_victrola_id(self, source: str, speaker_name: str) -> str | None:
        s = self.speakers.get(source, {}).get(speaker_name)
        return s["victrola_id"] if s else None

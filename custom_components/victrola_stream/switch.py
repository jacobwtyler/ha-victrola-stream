"""Switch platform - RCA Fixed Volume toggle."""
from __future__ import annotations
import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VictrolaRCAFixedVolumeSwitch(data, entry)])


class VictrolaRCAFixedVolumeSwitch(CoordinatorEntity, SwitchEntity):
    """RCA Fixed Volume toggle (disables volume control)."""

    _attr_has_entity_name = True
    _attr_name = "RCA Fixed Volume"
    _attr_icon = "mdi:volume-off"

    def __init__(self, data: dict, entry: ConfigEntry):
        super().__init__(data["coordinator"])
        self._api = data["api"]
        self._state_store = data["state_store"]
        self._attr_unique_id = f"{entry.entry_id}_rca_fixed_volume"

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._api.host)}}

    @property
    def is_on(self) -> bool:
        return self._state_store.rca_fixed_volume

    async def async_turn_on(self) -> None:
        """Enable fixed volume (disable volume control)."""
        success = await self._api.async_set_rca_fixed_volume(True)
        if success:
            self._state_store.set_rca_fixed_volume(True)
            self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        """Disable fixed volume (enable volume control)."""
        success = await self._api.async_set_rca_fixed_volume(False)
        if success:
            self._state_store.set_rca_fixed_volume(False)
            self.async_write_ha_state()

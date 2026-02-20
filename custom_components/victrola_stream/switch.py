"""Switch platform - RCA Volume Control toggle."""
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
    async_add_entities([VictrolaRCAVolumeControlSwitch(data, entry)])


class VictrolaRCAVolumeControlSwitch(CoordinatorEntity, SwitchEntity):
    """RCA Volume Control toggle (matches Victrola UI).

    ON = volume control enabled (fixedVolume=False on device)
    OFF = fixed volume / volume control disabled (fixedVolume=True on device)
    """

    _attr_has_entity_name = True
    _attr_name = "RCA Volume Control"
    _attr_icon = "mdi:volume-high"

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
        return not self._state_store.rca_fixed_volume

    async def async_turn_on(self) -> None:
        """Enable volume control (disable fixed volume)."""
        success = await self._api.async_set_rca_fixed_volume(False)
        if success:
            self._state_store.set_rca_fixed_volume(False)
            self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        """Disable volume control (enable fixed volume)."""
        success = await self._api.async_set_rca_fixed_volume(True)
        if success:
            self._state_store.set_rca_fixed_volume(True)
            self.async_write_ha_state()

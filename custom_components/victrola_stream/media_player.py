"""Media player platform - Victrola Stream with volume control."""
from __future__ import annotations
import logging
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, VICTROLA_TYPE_SONOS_QUICKPLAY, SOURCE_SONOS

_LOGGER = logging.getLogger(__name__)

SUPPORTED_FEATURES = (
    MediaPlayerEntityFeature.SELECT_SOUND_MODE
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_MUTE
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VictrolaMediaPlayer(data, entry)])


class VictrolaMediaPlayer(CoordinatorEntity, MediaPlayerEntity):
    """Victrola Stream media player - controls quickplay and volume."""

    _attr_has_entity_name   = True
    _attr_name              = "Victrola Stream"
    _attr_icon              = "mdi:turntable"
    _attr_supported_features = SUPPORTED_FEATURES

    def __init__(self, data: dict, entry: ConfigEntry) -> None:
        super().__init__(data["coordinator"])
        self._api         = data["api"]
        self._state_store = data["state_store"]
        self._discovery   = data["discovery"]
        self._attr_unique_id = f"{entry.entry_id}_media_player"

    @property
    def device_info(self):
        return {
            "identifiers":  {(DOMAIN, self._api.host)},
            "name":         "Victrola Stream Pearl",
            "manufacturer": "Victrola",
            "model":        "Stream Pearl",
        }

    # ── State ─────────────────────────────────────────────────────────

    @property
    def state(self) -> MediaPlayerState:
        if not self._state_store.connected:
            return MediaPlayerState.OFF
        power = self._state_store.power_target
        if power == "networkStandby":
            return MediaPlayerState.IDLE
        if self._state_store.quickplay_speaker:
            return MediaPlayerState.PLAYING
        return MediaPlayerState.IDLE

    @property
    def media_title(self) -> str | None:
        """Currently quickplayed speaker (from device)."""
        return self._state_store.quickplay_speaker

    @property
    def media_artist(self) -> str | None:
        """Current default speaker (from ui: getRows)."""
        return self._state_store.current_default_speaker_name

    @property
    def media_content_type(self) -> str:
        return "music"

    # ── Volume ────────────────────────────────────────────────────────

    @property
    def volume_level(self) -> float | None:
        """Volume 0.0–1.0 from player:volume."""
        if self._state_store.volume is not None:
            return self._state_store.volume / 100.0
        return None

    @property
    def is_volume_muted(self) -> bool | None:
        return self._state_store.muted

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume (0.0–1.0 → 0–100)."""
        vol_int = round(volume * 100)
        if await self._api.async_set_volume(vol_int):
            self._state_store.volume = vol_int
            self.async_write_ha_state()

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute/unmute."""
        if await self._api.async_set_mute(mute):
            self._state_store.muted = mute
            self.async_write_ha_state()

    # ── Sound mode = QuickPlay speaker ────────────────────────────────

    @property
    def sound_mode(self) -> str | None:
        return self._state_store.quickplay_speaker

    @property
    def sound_mode_list(self) -> list[str]:
        """Live speaker list from device."""
        return self._discovery.get_quickplay_speaker_names()

    async def async_select_sound_mode(self, sound_mode: str) -> None:
        """Select quickplay speaker via media player sound mode."""
        speaker_id = self._discovery.get_quickplay_id(sound_mode)
        if not speaker_id:
            return
        if await self._api.async_quickplay(VICTROLA_TYPE_SONOS_QUICKPLAY, speaker_id):
            self._state_store.set_quickplay(SOURCE_SONOS, sound_mode, speaker_id)
            self.async_write_ha_state()

    # ── Extra attributes ──────────────────────────────────────────────

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "quickplay_speaker":    self._state_store.quickplay_speaker,
            "quickplay_speaker_id": self._state_store.quickplay_speaker_id,
            "default_speaker":      self._state_store.current_default_speaker_name,
            "current_source":       self._state_store.current_source,
            "power_target":         self._state_store.power_target,
            "power_reason":         self._state_store.power_reason,
            "volume":               self._state_store.volume,
        }

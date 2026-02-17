"""Config flow for Victrola Stream integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_VICTROLA_IP, CONF_VICTROLA_PORT, CONF_DEVICE_NAME, DEFAULT_PORT
from .victrola_api import VictrolaAPI

_LOGGER = logging.getLogger(__name__)


async def validate_victrola_connection(hass: HomeAssistant, ip: str, port: int) -> dict:
    """Validate Victrola connection and return device info."""
    api = VictrolaAPI(ip, port)
    if await api.async_test_connection():
        return {"title": f"Victrola Stream ({ip})"}
    raise ConnectionError(f"Cannot connect to Victrola at {ip}:{port}")


class VictrolaStreamConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for Victrola Stream."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_victrola_connection(
                    self.hass,
                    user_input[CONF_VICTROLA_IP],
                    user_input.get(CONF_VICTROLA_PORT, DEFAULT_PORT),
                )
                await self.async_set_unique_id(user_input[CONF_VICTROLA_IP])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=info["title"], data=user_input)
            except Exception:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_VICTROLA_IP, default="192.168.35.247"): str,
                vol.Optional(CONF_VICTROLA_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_DEVICE_NAME, default="Victrola Stream Pearl"): str,
            }),
            errors=errors,
        )

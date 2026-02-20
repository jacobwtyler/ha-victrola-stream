"""Conftest - mock homeassistant modules so tests can import integration code."""
import sys
from unittest.mock import MagicMock

# Create mock modules for homeassistant before any integration imports
MOCK_MODULES = [
    "homeassistant",
    "homeassistant.components",
    "homeassistant.components.button",
    "homeassistant.components.media_player",
    "homeassistant.components.number",
    "homeassistant.components.select",
    "homeassistant.components.sensor",
    "homeassistant.components.switch",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.data_entry_flow",
    "homeassistant.helpers",
    "homeassistant.helpers.config_validation",
    "homeassistant.helpers.entity_platform",
    "homeassistant.helpers.update_coordinator",
]

for mod_name in MOCK_MODULES:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

# Set up specific attributes that the code expects
from homeassistant.const import Platform
Platform.MEDIA_PLAYER = "media_player"
Platform.SELECT = "select"
Platform.NUMBER = "number"
Platform.BUTTON = "button"
Platform.SENSOR = "sensor"
Platform.SWITCH = "switch"

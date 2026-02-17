"""Constants for the Victrola Stream integration."""

DOMAIN = "victrola_stream"

# Configuration
CONF_VICTROLA_IP = "victrola_ip"
CONF_VICTROLA_PORT = "victrola_port"
CONF_DEVICE_NAME = "device_name"

# Default values
DEFAULT_PORT = 80
DEFAULT_SCAN_INTERVAL = 30

# Source types
SOURCE_ROON = "roon"
SOURCE_SONOS = "sonos"
SOURCE_UPNP = "upnp"
SOURCE_BLUETOOTH = "bluetooth"

SOURCES = [SOURCE_ROON, SOURCE_SONOS, SOURCE_UPNP, SOURCE_BLUETOOTH]

# Victrola API paths
API_SET_DATA = "/api/setData"
API_GET_DATA = "/api/getData"

# Victrola source type identifiers
VICTROLA_OUTPUT_ROON = "victrolaOutputRoon"
VICTROLA_OUTPUT_SONOS = "victrolaOutputSonos"
VICTROLA_OUTPUT_UPNP = "victrolaOutputUpnp"
VICTROLA_OUTPUT_BLUETOOTH = "victrolaOutputBluetooth"

SOURCE_TYPE_MAP = {
    SOURCE_ROON: VICTROLA_OUTPUT_ROON,
    SOURCE_SONOS: VICTROLA_OUTPUT_SONOS,
    SOURCE_UPNP: VICTROLA_OUTPUT_UPNP,
    SOURCE_BLUETOOTH: VICTROLA_OUTPUT_BLUETOOTH,
}

# Roon Core ID
DEFAULT_ROON_CORE_ID = "44fe722d-c19d-4786-ab03-e23feb2e6148"

# Seed mappings for known Roon speakers
ROON_SEED_MAPPINGS = {
    "Airstream HomePods": "16017c4634641ca696c652e7e11ded6e",
    "Back Field": "16013ce5484620314686cb3284cf1413",
    "Casita": "16014687e2da5c1ba3322d94b6a788da",
    "Front Yard": "160180d32ba9238b284964210fba31d4",
    "Pool Deck": "1601cda2a4e2f810a8c8a65031b463de",
    "Record Player": "1601cbe821d5b0c43381aae694719ab1",
    "All Speakers (Grouped)": "1601f497a849e30de949aa50e04c91af",
}

"""Constants for the Victrola Stream integration."""

DOMAIN = "victrola_stream"

# Configuration
CONF_VICTROLA_IP = "victrola_ip"
CONF_VICTROLA_PORT = "victrola_port"
CONF_DEVICE_NAME = "device_name"

# Defaults
DEFAULT_PORT = 80
DEFAULT_SCAN_INTERVAL = 30

# ─────────────────────────────────────────────
# Source types (HA-facing names)
# ─────────────────────────────────────────────
SOURCE_ROON      = "Roon"
SOURCE_SONOS     = "Sonos"
SOURCE_UPNP      = "UPnP"
SOURCE_BLUETOOTH = "Bluetooth"
SOURCES = [SOURCE_ROON, SOURCE_SONOS, SOURCE_UPNP, SOURCE_BLUETOOTH]

# ─────────────────────────────────────────────
# Victrola API - setData / quickplay types
# ─────────────────────────────────────────────
VICTROLA_TYPE_ROON_DEFAULT      = "victrolaOutputRoon"
VICTROLA_TYPE_SONOS_DEFAULT     = "victrolaOutputSonos"
VICTROLA_TYPE_UPNP_DEFAULT      = "victrolaOutputUpnp"
VICTROLA_TYPE_BLUETOOTH_DEFAULT = "victrolaOutputBluetooth"

VICTROLA_TYPE_ROON_QUICKPLAY      = "victrolaQuickplayRoon"
VICTROLA_TYPE_SONOS_QUICKPLAY     = "victrolaQuickplaySonos"
VICTROLA_TYPE_UPNP_QUICKPLAY      = "victrolaQuickplayUPnP"
VICTROLA_TYPE_BLUETOOTH_QUICKPLAY = "victrolaQuickplayBluetooth"

SOURCE_TO_DEFAULT_TYPE = {
    SOURCE_ROON:      VICTROLA_TYPE_ROON_DEFAULT,
    SOURCE_SONOS:     VICTROLA_TYPE_SONOS_DEFAULT,
    SOURCE_UPNP:      VICTROLA_TYPE_UPNP_DEFAULT,
    SOURCE_BLUETOOTH: VICTROLA_TYPE_BLUETOOTH_DEFAULT,
}

SOURCE_TO_QUICKPLAY_TYPE = {
    SOURCE_ROON:      VICTROLA_TYPE_ROON_QUICKPLAY,
    SOURCE_SONOS:     VICTROLA_TYPE_SONOS_QUICKPLAY,
    SOURCE_UPNP:      VICTROLA_TYPE_UPNP_QUICKPLAY,
    SOURCE_BLUETOOTH: VICTROLA_TYPE_BLUETOOTH_QUICKPLAY,
}

# ─────────────────────────────────────────────
# Correct API paths (from working rest_commands)
# ─────────────────────────────────────────────
PATH_SET_DEFAULT_OUTPUT = "victrola:ui/setDefaultOutput"
PATH_QUICKPLAY          = "victrola:ui/quickplay"
PATH_AUDIO_QUALITY      = "settings:/victrola/forceLowBitrate"
PATH_AUDIO_LATENCY      = "settings:/victrola/wirelessAudioDelay"
PATH_KNOB_BRIGHTNESS    = "settings:/victrola/lightBrightness"
PATH_ROON_ENABLED       = "settings:/victrola/roonEnabled"
PATH_SONOS_ENABLED      = "settings:/victrola/sonosEnabled"
PATH_UPNP_ENABLED       = "settings:/victrola/upnpEnabled"
PATH_BLUETOOTH_ENABLED  = "settings:/victrola/bluetoothEnabled"
PATH_AUTOPLAY           = "settings:/victrola/autoplay"
PATH_REBOOT             = "powermanager:goReboot"

# ─────────────────────────────────────────────
# Audio Quality options (API values → display labels)
# ─────────────────────────────────────────────
AUDIO_QUALITY_LOW      = "connectionQuality"
AUDIO_QUALITY_STANDARD = "soundQuality"
AUDIO_QUALITY_HIGH     = "losslessQuality"

AUDIO_QUALITY_OPTIONS = [
    "Prioritize Connection",
    "Standard",
    "Prioritize Audio (FLAC)",
]

AUDIO_QUALITY_LABEL_TO_API = {
    "Prioritize Connection":    AUDIO_QUALITY_LOW,
    "Standard":                 AUDIO_QUALITY_STANDARD,
    "Prioritize Audio (FLAC)":  AUDIO_QUALITY_HIGH,
}

AUDIO_QUALITY_API_TO_LABEL = {v: k for k, v in AUDIO_QUALITY_LABEL_TO_API.items()}

# ─────────────────────────────────────────────
# Audio Latency options (API values → display labels)
# ─────────────────────────────────────────────
AUDIO_LATENCY_OPTIONS = ["Low", "Medium", "High", "Max"]

AUDIO_LATENCY_LABEL_TO_API = {
    "Low":    "min",
    "Medium": "med",
    "High":   "high",
    "Max":    "max",
}

AUDIO_LATENCY_API_TO_LABEL = {v: k for k, v in AUDIO_LATENCY_LABEL_TO_API.items()}

# ─────────────────────────────────────────────
# Knob brightness: 0-100 integer
# ─────────────────────────────────────────────
BRIGHTNESS_MIN  = 0
BRIGHTNESS_MAX  = 100
BRIGHTNESS_STEP = 1

# ─────────────────────────────────────────────
# Roon Core ID + seed output mappings
# NOTE: IDs include the full suffix (e.g. ...35f2) from rest_commands
# ─────────────────────────────────────────────
DEFAULT_ROON_CORE_ID = "44fe722d-c19d-4786-ab03-e23feb2e6148"

# ─────────────────────────────────────────────
# Sensor labels for last-sent speaker tracking
# ─────────────────────────────────────────────
LAST_DEFAULT_OUTPUT   = "last_default_output"
LAST_QUICKPLAY        = "last_quickplay"

ROON_SEED_MAPPINGS = {
    "Airstream HomePods": "16017c4634641ca696c652e7e11ded6e35f2",
    "Back Field":         "16013ce5484620314686cb3284cf1413498c",
    "Casita":             "16014687e2da5c1ba3322d94b6a788daeb5c",
    "Front Yard":         "160180d32ba9238b284964210fba31d4795f",
    "Pool Deck":          "1601cda2a4e2f810a8c8a65031b463de01b6",
    "Record Player":      "1601cbe821d5b0c43381aae694719ab178e0",
    "All Speakers (Grouped)": "1601f497a849e30de949aa50e04c91af400c",
}

SONOS_SEED_MAPPINGS = {
    "Airstream HomePods":        "RINCON_949F3EB7944801400",
    "Back Field":                "RINCON_C4387559BE9201400",
    "Casita":                    "RINCON_7828CA0AD64A01400",
    "Front Yard":                "RINCON_38420B282C3501400",
    "Pool Deck":                 "RINCON_C43875BD6D2201400",
    "Record Player":             "RINCON_5CAAFD0657CC01400",
}

UPNP_SEED_MAPPINGS = {
    "Victrola Pearl Airstream": "uuid:FF970016-7541-683B-E5CC-8CA0FF970016",
}

"""Constants for the Victrola Stream integration."""

DOMAIN = "victrola_stream"

# Configuration
CONF_VICTROLA_IP   = "victrola_ip"
CONF_VICTROLA_PORT = "victrola_port"
CONF_DEVICE_NAME   = "device_name"

# Defaults
DEFAULT_PORT          = 80
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
# Victrola API - setData value types
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
# API paths
# ─────────────────────────────────────────────
PATH_SET_DEFAULT_OUTPUT  = "victrola:ui/setDefaultOutput"
PATH_QUICKPLAY           = "victrola:ui/quickplay"
PATH_SPEAKER_QUICKPLAY   = "victrola:ui/speakerQuickplay"
PATH_SPEAKER_SELECTION   = "victrola:ui/speakerSelection"
PATH_AUDIO_QUALITY       = "settings:/victrola/forceLowBitrate"
PATH_AUDIO_LATENCY       = "settings:/victrola/wirelessAudioDelay"
PATH_KNOB_BRIGHTNESS     = "settings:/victrola/lightBrightness"
PATH_ROON_ENABLED        = "settings:/victrola/roonEnabled"
PATH_SONOS_ENABLED       = "settings:/victrola/sonosEnabled"
PATH_UPNP_ENABLED        = "settings:/victrola/upnpEnabled"
PATH_BLUETOOTH_ENABLED   = "settings:/victrola/bluetoothEnabled"
PATH_AUTOPLAY            = "settings:/victrola/autoplay"
PATH_REBOOT              = "powermanager:goReboot"
PATH_VOLUME              = "player:volume"
PATH_MUTE                = "settings:/mediaPlayer/mute"
PATH_POWER_TARGET        = "powermanager:target"
PATH_UI                  = "ui:"

# ─────────────────────────────────────────────
# Event queue subscription paths
# ─────────────────────────────────────────────
EVENT_SUBSCRIPTIONS = [
    {"path": "victrola:ui/speakerSelection",          "type": "rows"},
    {"path": "victrola:ui/speakerQuickplay",          "type": "rows"},
    {"path": "settings:/victrola/autoplay",           "type": "itemWithValue"},
    {"path": "powermanager:target",                   "type": "itemWithValue"},
    {"path": "player:volume",                         "type": "itemWithValue"},
    {"path": "settings:/victrola/roonEnabled",        "type": "itemWithValue"},
    {"path": "settings:/victrola/sonosEnabled",       "type": "itemWithValue"},
    {"path": "settings:/victrola/upnpEnabled",        "type": "itemWithValue"},
    {"path": "settings:/victrola/bluetoothEnabled",   "type": "itemWithValue"},
    {"path": "settings:/victrola/forceLowBitrate",    "type": "itemWithValue"},
    {"path": "settings:/victrola/wirelessAudioDelay", "type": "itemWithValue"},
    {"path": "settings:/victrola/lightBrightness",    "type": "itemWithValue"},
    {"path": "settings:/mediaPlayer/mute",             "type": "itemWithValue"},
]

# ─────────────────────────────────────────────
# Audio Quality options
# ─────────────────────────────────────────────
AUDIO_QUALITY_OPTIONS = [
    "Prioritize Connection",
    "Standard",
    "Prioritize Audio (FLAC)",
]
AUDIO_QUALITY_LABEL_TO_API = {
    "Prioritize Connection":   "connectionQuality",
    "Standard":                "soundQuality",
    "Prioritize Audio (FLAC)": "losslessQuality",
}
AUDIO_QUALITY_API_TO_LABEL = {v: k for k, v in AUDIO_QUALITY_LABEL_TO_API.items()}

# ─────────────────────────────────────────────
# Audio Latency options
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
# Knob brightness
# ─────────────────────────────────────────────
BRIGHTNESS_MIN  = 0
BRIGHTNESS_MAX  = 100
BRIGHTNESS_STEP = 1

# ─────────────────────────────────────────────
# Roon Core ID (used for building Roon output IDs)
# ─────────────────────────────────────────────
DEFAULT_ROON_CORE_ID = "44fe722d-c19d-4786-ab03-e23feb2e6148"

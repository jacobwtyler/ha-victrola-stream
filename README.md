# Victrola Stream - Home Assistant Integration

Full control of your Victrola Stream Pearl turntable from Home Assistant.

**Author:** Jacob Tyler (jacobwtyler@gmail.com)

## Entities

### Controls
| Entity | Description |
|--------|-------------|
| `media_player` | Main player - source & speaker |
| `select.audio_source` | Roon / Sonos / UPnP / Bluetooth |
| `select.audio_quality` | Prioritize Connection / Standard / Prioritize Audio (FLAC) |
| `select.audio_latency` | Low / Medium / High / Max |
| `select.roon_speaker` | Choose Roon output |
| `select.sonos_speaker` | Choose Sonos speaker |
| `select.upnp_speaker` | Choose UPnP device |
| `select.bluetooth_speaker` | Choose Bluetooth device |
| `number.knob_brightness` | Knob illumination 0–100% |
| `button.reboot_device` | Reboot the turntable |
| `button.refresh_state` | Force state refresh |

### Sensors
| Entity | Description |
|--------|-------------|
| `sensor.connection_status` | connected / disconnected |
| `sensor.current_source` | Active source |
| `sensor.current_speaker` | Active speaker name |
| `sensor.audio_quality` | Current quality setting |
| `sensor.audio_latency` | Current latency setting |
| `sensor.knob_brightness` | Current brightness % |

## Installation

1. HACS → Integrations → Custom repositories
2. Add `https://github.com/jacobwtyler/ha-victrola-stream`
3. Download and restart HA
4. Settings → Devices & Services → Add Integration → Victrola Stream
5. Enter IP: `192.168.35.247`

# Victrola Stream - Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Full-featured Home Assistant integration for the **Victrola Stream Pearl** (and other Victrola Stream turntables).

**Author:** Jacob Tyler (jacobwtyler@gmail.com)

---

## ✨ Features

- 🎵 **All 4 Source Types**: Roon, Sonos, UPnP/DLNA, Bluetooth
- 🔊 **Dynamic Speaker Discovery**: Auto-discovers speakers from your existing HA integrations
- 🎛️ **Knob Brightness Control**: Adjust the turntable's illuminated knob (0-100%)
- 🎚️ **Audio Quality Selection**: CD / High / Medium / Low
- ⏱️ **Audio Latency Control**: 0–500ms slider
- 🔄 **State Verification Sensors**: Polls device to confirm every change took effect
- 🔁 **Reboot Button**: Restart the device from HA
- 🔌 **Source Enable/Disable Switches**: Toggle each source on/off
- 📡 **Multi-Device Support**: Configure multiple turntables independently

---

## 📦 Entities Created

### Media Player
| Entity | Description |
|--------|-------------|
| `media_player.victrola_stream_pearl` | Main player - source & speaker switching |

### Select
| Entity | Description |
|--------|-------------|
| `select.victrola_stream_pearl_audio_quality` | CD / High / Medium / Low |
| `select.victrola_stream_pearl_roon_speaker` | Choose Roon speaker |
| `select.victrola_stream_pearl_sonos_speaker` | Choose Sonos speaker |
| `select.victrola_stream_pearl_upnp_speaker` | Choose UPnP speaker |
| `select.victrola_stream_pearl_bluetooth_speaker` | Choose Bluetooth speaker |

### Number
| Entity | Description |
|--------|-------------|
| `number.victrola_stream_pearl_audio_latency` | Audio latency in ms (0–500) |

### Light
| Entity | Description |
|--------|-------------|
| `light.victrola_stream_pearl_knob_brightness` | Knob illumination (0–100%) |

### Switch
| Entity | Description |
|--------|-------------|
| `switch.victrola_stream_pearl_roon_enabled` | Enable/disable Roon source |
| `switch.victrola_stream_pearl_sonos_enabled` | Enable/disable Sonos source |
| `switch.victrola_stream_pearl_upnp_enabled` | Enable/disable UPnP source |
| `switch.victrola_stream_pearl_bluetooth_enabled` | Enable/disable Bluetooth source |

### Button
| Entity | Description |
|--------|-------------|
| `button.victrola_stream_pearl_reboot_device` | Reboot the turntable |
| `button.victrola_stream_pearl_refresh_state` | Force state refresh |

### Sensor (State Verification)
| Entity | Description |
|--------|-------------|
| `sensor.victrola_stream_pearl_current_source` | Verified active source from device |
| `sensor.victrola_stream_pearl_current_speaker` | Verified active speaker from device |
| `sensor.victrola_stream_pearl_audio_quality_verified` | Verified audio quality from device |
| `sensor.victrola_stream_pearl_audio_latency_verified` | Verified latency from device |
| `sensor.victrola_stream_pearl_knob_brightness_verified` | Verified brightness from device |
| `sensor.victrola_stream_pearl_connection_status` | Device connection status |

---

## 🔧 Installation

### HACS (Recommended)
1. Open **HACS** → **Integrations**
2. Click **⋮** → **Custom repositories**
3. Add `https://github.com/jacobwtyler/ha-victrola-stream` as **Integration**
4. Search for **"Victrola Stream"** and download
5. Restart Home Assistant

### Manual
Copy `custom_components/victrola_stream/` to your `config/custom_components/` directory and restart.

---

## ⚙️ Configuration

1. **Settings** → **Devices & Services** → **Add Integration**
2. Search **"Victrola Stream"**
3. Enter:
   - **IP Address**: Your Victrola's IP (e.g. `192.168.35.247`)
   - **Port**: `80` (default)
   - **Device Name**: Whatever you want to call it
4. Click **Submit**

---

## 🌐 Network Requirements

- HA must be able to reach your Victrola on port 80
- Works across VLANs as long as HTTP routing is configured
- mDNS/Avahi not required (manual IP entry used)

---

## 💡 Speaker Discovery

The integration automatically discovers speakers from your existing HA integrations:

- **Roon**: Reads from the [Roon integration](https://www.home-assistant.io/integrations/roon/)
- **Sonos**: Reads from the [Sonos integration](https://www.home-assistant.io/integrations/sonos/)
- **UPnP**: Reads from the [DLNA DMR integration](https://www.home-assistant.io/integrations/dlna_dmr/)
- **Bluetooth**: Reads from Bluetooth integrations

New speakers are discovered automatically when HA restarts.

---

## 🐛 Troubleshooting

**Cannot connect**: Verify IP, ensure Victrola is on, check routing between HA and Victrola VLANs.

**Speakers not showing**: Ensure the relevant integration (Roon/Sonos/etc.) is configured in HA first.

**State not updating**: Use the **Refresh State** button or wait up to 30 seconds for the next poll.

---

## 📝 License

MIT License - see [LICENSE](LICENSE)

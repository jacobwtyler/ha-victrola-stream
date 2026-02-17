# Victrola Stream HACS Integration

Home Assistant integration for Victrola Stream turntables.

## Features

- 🎵 **Multi-Source Support**: Roon, Sonos, UPnP/DLNA, Bluetooth
- 🔊 **Dynamic Speaker Discovery**: Automatically discovers speakers from your HA integrations
- 🎛️ **Easy Configuration**: Simple IP-based setup
- 📡 **Multi-Device Support**: Configure multiple turntables
- 🎚️ **Source & Speaker Selection**: Easy switching via UI

## Installation

### HACS (Recommended)

1. Open HACS
2. Go to Integrations
3. Click the three dots menu → Custom repositories
4. Add repository: `https://github.com/jacobwtyler/ha-victrola-stream`
5. Category: Integration
6. Click "Download"
7. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/victrola_stream` directory to your `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "Victrola Stream"
4. Enter your Victrola's IP address (e.g., `192.168.35.247`)
5. Click Submit

## Usage

After configuration, you'll have:

- **Media Player**: `media_player.victrola_stream_pearl`
  - Switch between sources (Roon/Sonos/UPnP/Bluetooth)
  - Select speakers for each source
  
- **Select Entities**:
  - Audio Source selector
  - Speaker selectors for each source type

## Network Requirements

- Victrola Stream must be accessible on your network
- If HA and Victrola are on different VLANs, ensure routing is configured
- Default port: 80

## Supported Sources

- **Roon**: Requires Roon integration in HA
- **Sonos**: Requires Sonos integration in HA
- **UPnP/DLNA**: Requires DLNA DMR integration in HA
- **Bluetooth**: Requires Bluetooth integration in HA

## Troubleshooting

### Cannot Connect
- Verify Victrola IP address
- Ensure Victrola is powered on
- Check network connectivity between HA and Victrola
- Verify port 80 is accessible

### Speakers Not Showing
- Ensure the relevant integration (Roon/Sonos/etc) is set up in HA
- Restart the integration
- Check HA logs for discovery errors

## Support

- **Issues**: https://github.com/jacobwtyler/ha-victrola-stream/issues
- **Author**: Jacob Tyler (jacobwtyler@gmail.com)

## License

MIT License

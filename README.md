# Pi Media Hub

A beautiful, full-screen media center interface for Raspberry Pi, designed to feel like a modern streaming appliance. Access YouTube, Spotify, Jellyfin, and more with a sleek UI optimized for TV viewing and remote control navigation.

![Pi Media Hub](https://img.shields.io/badge/Platform-Raspberry_Pi-C51A4A)
![OS](https://img.shields.io/badge/OS-Pi_OS_Trixie-green)
![License](https://img.shields.io/badge/License-MIT-blue)

## Features

- **Elegant UI** - Smooth animations with glowing orb backgrounds
- **In-App Settings** - Professional TV-style settings interface (no SSH required!)
- **One-Command Install** - Get started in minutes with a single command
- **TV-Optimized** - Designed for HDMI displays with remote control support
- **HDMI-CEC Support** - Control your TV power with the Pi
- **USB Remote Compatible** - Navigate with any USB remote (arrow keys + enter)
- **Performance Modes** - Optimized for Pi 4 and Pi 5
- **Auto-Start** - Boot directly into your media hub
- **Configurable Apps** - Enable/disable apps and customize URLs
- **Smart Launching** - Intelligent app detection (native vs browser)
- **Network Aware** - Automatic offline detection and notification
- **One-Command Install** - Get up and running in seconds

## Screenshots

The interface features:
- Three main apps: YouTube, Spotify, Jellyfin
- Animated orb background with color-coded overlays
- Confirmation dialogs for app launches
- Exit button with configurable behavior (CEC standby, shutdown, etc.)
- Network status indicators

## Supported Apps

| App | Launch Method | Notes |
|-----|---------------|-------|
| **YouTube** | Browser (youtube.com/tv) | Optimized TV interface |
| **Spotify** | Browser (open.spotify.com) | Web player |
| **Jellyfin** | Native or Browser | Auto-detects Jellyfin Media Player |

## Requirements

### Hardware
- Raspberry Pi 4 or 5 (2GB+ RAM recommended)
- MicroSD card (16GB+ recommended)
- HDMI display (TV or monitor)
- USB remote control (optional but recommended)
- Network connection (WiFi or Ethernet)

### Software
- Raspberry Pi OS (Bookworm or Trixie)
- Chromium browser
- Python 3.7+
- CEC-utils (for TV control)

## Quick Start

### 1. One-Command Installation (Recommended)

Install Pi Media Hub with a single command:

```bash
curl -sSL https://raw.githubusercontent.com/flashingcursor/pi-kiosk/master/bootstrap.sh | bash
```

This will:
- Download the latest version
- Install all required dependencies
- Configure system settings (disable screen blanking, etc.)
- Set up HDMI-CEC
- Create systemd service
- Optionally enable auto-start on boot

### Alternative: Manual Installation

Clone the repository and run the installer:

```bash
git clone https://github.com/flashingcursor/pi-kiosk.git
cd pi-kiosk
chmod +x install.sh
./install.sh
```

### 2. Configuration

**Option A: In-App Settings (Recommended)**

Launch the media hub and click the **⚙️ Settings** button (top-right corner) to configure everything from your TV:
- Enable/disable apps
- Set Jellyfin server URL
- Adjust performance mode
- Configure CEC behavior
- Set exit action
- And more!

**Option B: Command-Line Setup**

Run the interactive setup wizard via SSH:

```bash
python3 setup.py
```

### 3. Testing

Run manually to test:

```bash
python3 launcher.py
```

Press **Ctrl+C** to exit.

### 4. Enable Auto-Start

Enable the systemd service to start on boot:

```bash
sudo systemctl enable pi-media-hub
sudo systemctl start pi-media-hub
```

## Configuration

### config.json

The main configuration file. Key sections:

#### Apps
```json
{
  "apps": {
    "youtube": {
      "enabled": true,
      "name": "YouTube",
      "launch_method": "browser",
      "url": "https://www.youtube.com/tv"
    },
    "jellyfin": {
      "enabled": true,
      "url": "http://192.168.1.100:8096",
      "prefer_native": true
    }
  }
}
```

#### Display Settings
```json
{
  "display": {
    "performance_mode": "balanced",
    "animation_quality": "medium",
    "hide_cursor_timeout": 3000,
    "resolution_hint": "1080p"
  }
}
```

**Performance modes:**
- `low` - Minimal animations (Pi 4, 1-2GB RAM)
- `balanced` - Moderate animations (recommended)
- `high` - Full animations (Pi 5)

#### Exit Behavior
```json
{
  "exit": {
    "action": "cec_standby",
    "cec_fallback": "close",
    "show_confirmation": true
  }
}
```

**Exit actions:**
- `cec_standby` - Put TV in standby via HDMI-CEC
- `close` - Just close the app
- `shutdown` - Shutdown the Pi
- `reboot` - Reboot the Pi

## Navigation

### Keyboard/Remote
- **Arrow Keys** - Navigate menu items
- **Enter** - Select/Confirm
- **Escape/Backspace** - Cancel/Go back
- **S key** - Open settings menu
- **~** (tilde) - Toggle offline mode (for testing)

### Mouse (if connected)
- Hover over items to select
- Click to launch
- Click the cog icon (top right) to open settings

### Settings UI

Access the built-in settings interface by:
- Pressing **S** on your keyboard/remote
- Clicking the **cog icon** in the top right corner
- Hovering over the settings button and pressing **Enter**

The settings UI allows you to:
- Enable/disable apps
- Adjust performance mode
- Configure cursor timeout
- Toggle network checking
- Set exit behavior
- Enable/disable CEC control

Changes can be saved and applied immediately, or you can reload the interface to apply all changes at once.

## HDMI-CEC Control

### Setup

The installer configures CEC automatically. To test:

```bash
# Check TV status
./scripts/cec-control.sh status

# Put TV in standby
./scripts/cec-control.sh standby

# Turn TV on
./scripts/cec-control.sh on

# Scan for CEC devices
./scripts/cec-control.sh scan
```

### Troubleshooting CEC

If CEC isn't working:

1. **Enable CEC on TV** - Check your TV settings
2. **Check cable** - Use a high-quality HDMI cable
3. **Reboot** - Power cycle both Pi and TV
4. **Test manually**:
   ```bash
   echo "scan" | cec-client -s -d 1
   ```

## Jellyfin Setup

### Option 1: Local Server

Install Jellyfin server on the same Pi:

```bash
curl https://repo.jellyfin.org/install-debuntu.sh | sudo bash
```

Then configure in `config.json`:
```json
"jellyfin": {
  "enabled": true,
  "url": "http://localhost:8096"
}
```

### Option 2: Remote Server

Point to an existing Jellyfin server:

```bash
python3 setup.py
```

Enter your server URL (e.g., `http://192.168.1.100:8096`)

### Native Player (Recommended)

For best performance, install Jellyfin Media Player:

```bash
# Via Flatpak
flatpak install flathub com.github.iwalton3.jellyfin-media-player
```

The launcher will automatically prefer the native app if `prefer_native: true` in config.

## Customization

### Adding Custom Apps

Edit `config.json`:

```json
{
  "apps": {
    "plex": {
      "enabled": true,
      "name": "Plex",
      "icon": "https://example.com/plex-icon.png",
      "launch_method": "browser",
      "url": "https://app.plex.tv/desktop"
    }
  }
}
```

Then restart:
```bash
sudo systemctl restart pi-media-hub
```

### Changing Icons

Replace icon URLs in `config.json` with your own images.

### Custom Background

The orb animation colors are defined in `index.html`:

```javascript
const baseColors = [
  'rgba(255, 0, 0, 0.04)',      // Red (YouTube)
  'rgba(30, 215, 96, 0.04)',    // Green (Spotify)
  'rgba(138, 43, 226, 0.04)'    // Purple (Jellyfin)
];
```

## System Management

### Service Commands

```bash
# Start
sudo systemctl start pi-media-hub

# Stop
sudo systemctl stop pi-media-hub

# Restart
sudo systemctl restart pi-media-hub

# Status
sudo systemctl status pi-media-hub

# View logs
journalctl -u pi-media-hub -f

# Disable auto-start
sudo systemctl disable pi-media-hub
```

### Manual Launch

```bash
cd /home/pi/pi-kiosk
python3 launcher.py
```

### Logs

- Application log: `/tmp/pi-media-hub.log`
- System log: `journalctl -u pi-media-hub`

## Performance Optimization

### For Pi 4

```json
{
  "display": {
    "performance_mode": "low",
    "resolution_hint": "1080p"
  }
}
```

### For Pi 5

```json
{
  "display": {
    "performance_mode": "high",
    "resolution_hint": "1080p"
  }
}
```

### Reducing Memory Usage

- Disable unused apps in config
- Use `performance_mode: "low"`
- Close other applications
- Use lightweight desktop environment (or no DE)

## Troubleshooting

### Browser doesn't launch

Check Chromium installation:
```bash
chromium-browser --version
```

Try launching manually:
```bash
python3 launcher.py
```

Check logs:
```bash
journalctl -u pi-media-hub -n 50
```

### Screen blanks/sleeps

Verify `.xsession` file:
```bash
cat ~/.xsession
```

Should contain:
```bash
xset s off
xset -dpms
xset s noblank
```

### Network offline warning

Test network:
```bash
./scripts/check-network.sh
```

Check your WiFi/Ethernet connection.

### Apps don't launch

Check `config.json` URLs:
```bash
cat config.json | grep -A 5 "apps"
```

Test browser manually:
```bash
chromium-browser --kiosk https://www.youtube.com/tv
```

### CEC not working

See [HDMI-CEC Control](#hdmi-cec-control) section above.

## Development

### File Structure

```
pi-kiosk/
├── index.html              # Main UI interface
├── launcher.py             # Python launcher and HTTP server
├── setup.py                # Interactive configuration wizard
├── install.sh              # Installation script
├── config.json             # User configuration (created by setup)
├── config.default.json     # Default configuration template
├── pi-media-hub.service    # Systemd service file
├── scripts/
│   ├── cec-control.sh      # CEC command wrapper
│   └── check-network.sh    # Network connectivity check
└── README.md               # This file
```

### Making Changes

1. Edit `config.json` or source files
2. Restart service: `sudo systemctl restart pi-media-hub`
3. Or test manually: `python3 launcher.py`

### Contributing

Pull requests welcome! Please:
- Test on actual Pi hardware
- Follow existing code style
- Update README for new features

## FAQ

**Q: Can I use this without a remote?**
A: Yes, mouse and keyboard work fine.

**Q: Does this work on Pi 3?**
A: Possibly, but not officially supported. Use `performance_mode: "low"`.

**Q: Can I add Netflix?**
A: Netflix requires special DRM support. Better to use a dedicated device or Kodi.

**Q: Why does YouTube look different?**
A: We use youtube.com/tv which is the TV-optimized interface.

**Q: Can I use this on regular Linux?**
A: Yes, though it's optimized for Pi. Just run `./install.sh`.

**Q: How do I uninstall?**
A:
```bash
sudo systemctl stop pi-media-hub
sudo systemctl disable pi-media-hub
sudo rm /etc/systemd/system/pi-media-hub.service
sudo systemctl daemon-reload
```

## License

MIT License - see LICENSE file

## Credits

- Icons from Wikimedia Commons
- Inspired by modern streaming interfaces
- Built for the Raspberry Pi community

## Support

- Issues: [GitHub Issues](https://github.com/flashingcursor/pi-kiosk/issues)
- Discussions: [GitHub Discussions](https://github.com/flashingcursor/pi-kiosk/discussions)

---

**Made with ❤️ for Raspberry Pi**

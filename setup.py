#!/usr/bin/env python3
"""
Pi Media Hub Setup Wizard
Interactive configuration tool
"""

import json
import os
import sys
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
CONFIG_FILE = SCRIPT_DIR / 'config.json'
DEFAULT_CONFIG = SCRIPT_DIR / 'config.default.json'


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")


def print_info(text):
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def get_input(prompt, default=None):
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "

    value = input(f"{Colors.BOLD}{prompt}{Colors.END}").strip()
    return value if value else default


def get_yes_no(prompt, default=True):
    default_str = "Y/n" if default else "y/N"
    response = get_input(f"{prompt} ({default_str})", "").lower()

    if not response:
        return default
    return response in ['y', 'yes', 'true', '1']


def load_config():
    """Load existing config or create from default"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    else:
        with open(DEFAULT_CONFIG) as f:
            return json.load(f)


def save_config(config):
    """Save configuration"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    print_success(f"Configuration saved to {CONFIG_FILE}")


def setup_jellyfin(config):
    """Configure Jellyfin server"""
    print_header("Jellyfin Configuration")

    enabled = get_yes_no("Enable Jellyfin?", config['apps']['jellyfin']['enabled'])
    config['apps']['jellyfin']['enabled'] = enabled

    if enabled:
        print_info("Enter your Jellyfin server URL")
        print_info("Examples: http://192.168.1.100:8096 or http://jellyfin.local:8096")

        url = get_input("Jellyfin server URL", config['apps']['jellyfin']['url'])
        config['apps']['jellyfin']['url'] = url

        prefer_native = get_yes_no(
            "Prefer native Jellyfin Media Player if installed?",
            config['apps']['jellyfin'].get('prefer_native', True)
        )
        config['apps']['jellyfin']['prefer_native'] = prefer_native


def setup_apps(config):
    """Configure which apps are enabled"""
    print_header("App Configuration")

    # YouTube
    yt_enabled = get_yes_no("Enable YouTube?", config['apps']['youtube']['enabled'])
    config['apps']['youtube']['enabled'] = yt_enabled

    # Spotify
    spotify_enabled = get_yes_no("Enable Spotify?", config['apps']['spotify']['enabled'])
    config['apps']['spotify']['enabled'] = spotify_enabled

    # Jellyfin
    setup_jellyfin(config)


def setup_display(config):
    """Configure display settings"""
    print_header("Display Configuration")

    print_info("Performance Modes:")
    print_info("  low      - Minimal animations, best for Pi 4 or lower power")
    print_info("  balanced - Moderate animations (recommended)")
    print_info("  high     - Full animations, best for Pi 5")

    perf_mode = get_input(
        "Performance mode (low/balanced/high)",
        config['display']['performance_mode']
    )

    if perf_mode in ['low', 'balanced', 'high']:
        config['display']['performance_mode'] = perf_mode
    else:
        print_warning(f"Invalid mode, keeping {config['display']['performance_mode']}")

    print_info("\nResolution hints:")
    print_info("  720p  - 1280x720")
    print_info("  1080p - 1920x1080 (recommended)")
    print_info("  4k    - 3840x2160")

    res = get_input("Resolution hint (720p/1080p/4k)", config['display']['resolution_hint'])
    if res in ['720p', '1080p', '4k']:
        config['display']['resolution_hint'] = res


def setup_cec(config):
    """Configure CEC settings"""
    print_header("HDMI-CEC Configuration")

    print_info("CEC allows control of your TV via HDMI")
    print_info("This requires cec-utils to be installed")

    enable_cec = get_yes_no("Enable CEC support?", config['remote']['enable_cec'])
    config['remote']['enable_cec'] = enable_cec

    if enable_cec:
        if not shutil.which('cec-client'):
            print_warning("cec-client not found!")
            print_info("Install with: sudo apt install cec-utils")


def setup_exit_behavior(config):
    """Configure exit behavior"""
    print_header("Exit Behavior Configuration")

    print_info("Exit actions:")
    print_info("  cec_standby - Put TV in standby via CEC (recommended)")
    print_info("  close       - Just close the application")
    print_info("  shutdown    - Shutdown the Pi")
    print_info("  reboot      - Reboot the Pi")

    action = get_input(
        "Exit action",
        config['exit']['action']
    )

    valid_actions = ['cec_standby', 'close', 'shutdown', 'reboot']
    if action in valid_actions:
        config['exit']['action'] = action
    else:
        print_warning(f"Invalid action, keeping {config['exit']['action']}")

    if action == 'cec_standby':
        print_info("\nCEC fallback action if CEC fails:")
        fallback = get_input(
            "Fallback action (close/shutdown/reboot)",
            config['exit'].get('cec_fallback', 'close')
        )
        if fallback in ['close', 'shutdown', 'reboot']:
            config['exit']['cec_fallback'] = fallback


def setup_startup(config):
    """Configure startup behavior"""
    print_header("Startup Configuration")

    autostart = get_yes_no(
        "Enable auto-start on boot?",
        config['startup'].get('autostart', False)
    )
    config['startup']['autostart'] = autostart

    if autostart:
        print_info("\nBoot delay gives the system time to initialize")
        delay = get_input("Boot delay in seconds", str(config['startup']['boot_delay']))
        try:
            config['startup']['boot_delay'] = int(delay)
        except ValueError:
            print_warning("Invalid delay, keeping default")


def check_system():
    """Check system requirements"""
    print_header("System Check")

    checks = {
        'Python 3': sys.version_info >= (3, 7),
        'Chromium': shutil.which('chromium-browser') or shutil.which('chromium'),
        'CEC Utils': shutil.which('cec-client'),
    }

    all_ok = True
    for name, status in checks.items():
        if status:
            print_success(f"{name} - OK")
        else:
            if name == 'CEC Utils':
                print_warning(f"{name} - Not found (optional)")
            else:
                print_error(f"{name} - Not found")
                all_ok = False

    if not all_ok:
        print_error("\nMissing required dependencies!")
        print_info("Run ./install.sh to install dependencies")
        return False

    return True


def main():
    print_header("Pi Media Hub Setup Wizard")

    print_info("This wizard will help you configure your Pi Media Hub")
    print_info("Press Ctrl+C at any time to cancel\n")

    try:
        # Check system
        if not check_system():
            if not get_yes_no("\nContinue anyway?", False):
                sys.exit(1)

        # Load config
        config = load_config()

        # Run setup sections
        setup_apps(config)
        setup_display(config)
        setup_cec(config)
        setup_exit_behavior(config)
        setup_startup(config)

        # Save
        print_header("Summary")
        print(json.dumps(config, indent=2))

        if get_yes_no("\nSave this configuration?", True):
            save_config(config)

            if config['startup']['autostart']:
                print_info("\nTo enable auto-start, run:")
                print_info("  sudo ./install.sh --enable-service")

            print_success("\nSetup complete!")
            print_info("To test the media hub, run: python3 launcher.py")

        else:
            print_info("Configuration not saved")

    except KeyboardInterrupt:
        print_error("\n\nSetup cancelled")
        sys.exit(1)
    except Exception as e:
        print_error(f"\nError: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Pi Media Hub Launcher
Handles app launching, CEC control, and browser management
"""

import json
import os
import sys
import subprocess
import signal
import logging
import time
import shutil
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread
from urllib.parse import urlparse, parse_qs

# Setup
SCRIPT_DIR = Path(__file__).parent.absolute()
CONFIG_FILE = SCRIPT_DIR / 'config.json'
DEFAULT_CONFIG = SCRIPT_DIR / 'config.default.json'
LOG_FILE = '/tmp/pi-media-hub.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MediaHubLauncher:
    def __init__(self):
        self.config = self.load_config()
        self.browser_process = None
        self.app_process = None
        self.http_server = None
        self.http_thread = None
        self.port = 8000

    def load_config(self):
        """Load configuration, fallback to default if needed"""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE) as f:
                    config = json.load(f)
                    logger.info("Loaded user config")
                    return config
            else:
                with open(DEFAULT_CONFIG) as f:
                    config = json.load(f)
                    logger.info("Loaded default config")
                    return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            sys.exit(1)

    def check_dependencies(self):
        """Check if required commands are available"""
        deps = {
            'chromium-browser': ['chromium-browser', 'chromium'],
            'cec-client': ['cec-client'] if self.config['remote']['enable_cec'] else []
        }

        missing = []
        for name, commands in deps.items():
            found = False
            for cmd in commands:
                if shutil.which(cmd):
                    found = True
                    break
            if not found and commands:
                missing.append(name)

        if missing:
            logger.warning(f"Missing dependencies: {', '.join(missing)}")
            if 'cec-client' in missing:
                logger.warning("CEC control will be disabled")

        return len(missing) == 0

    def start_http_server(self):
        """Start local HTTP server for the interface"""
        os.chdir(SCRIPT_DIR)

        class CustomHandler(SimpleHTTPRequestHandler):
            def log_message(self, format, *args):
                # Suppress default logging
                pass

            def do_GET(self_handler):
                # Handle launch protocol
                if self_handler.path.startswith('/launch'):
                    self.handle_launch_request(self_handler.path)
                    self_handler.send_response(200)
                    self_handler.send_header('Content-type', 'text/html')
                    self_handler.end_headers()
                    self_handler.wfile.write(b'<html><body>Launching...</body></html>')
                else:
                    SimpleHTTPRequestHandler.do_GET(self_handler)

        try:
            self.http_server = HTTPServer(('localhost', self.port), CustomHandler)
            self.http_thread = Thread(target=self.http_server.serve_forever, daemon=True)
            self.http_thread.start()
            logger.info(f"HTTP server started on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}")
            sys.exit(1)

    def handle_launch_request(self, path):
        """Handle launch:// protocol requests from browser"""
        logger.info(f"Launch request: {path}")

        if '/launch/exit' in path:
            self.handle_exit()
        elif '/launch/app/' in path:
            app_key = path.split('/launch/app/')[-1].split('?')[0]
            self.launch_app(app_key)

    def find_chromium(self):
        """Find chromium binary"""
        for cmd in ['chromium-browser', 'chromium']:
            path = shutil.which(cmd)
            if path:
                return path
        return None

    def launch_browser(self):
        """Launch Chromium browser in kiosk mode"""
        chromium = self.find_chromium()
        if not chromium:
            logger.error("Chromium not found!")
            sys.exit(1)

        url = f'http://localhost:{self.port}/index.html'
        flags = self.config['advanced']['chromium_flags']

        cmd = [chromium] + flags + [url]

        logger.info(f"Launching browser: {' '.join(cmd)}")

        try:
            # Set display
            env = os.environ.copy()
            if 'DISPLAY' not in env:
                env['DISPLAY'] = ':0'

            self.browser_process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            logger.info("Browser launched successfully")
        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")
            sys.exit(1)

    def launch_app(self, app_key):
        """Launch specific app based on configuration"""
        logger.info(f"Launching app: {app_key}")

        if app_key not in self.config['apps']:
            logger.error(f"Unknown app: {app_key}")
            return

        app = self.config['apps'][app_key]
        if not app.get('enabled', False):
            logger.warning(f"App {app_key} is disabled")
            return

        # Close current browser
        if self.browser_process:
            self.browser_process.terminate()
            time.sleep(0.5)

        # Launch based on method
        method = app.get('launch_method', 'browser')

        if method == 'auto':
            # Try native first, fallback to browser
            if app.get('prefer_native', False):
                if self.launch_native_app(app_key, app):
                    return
            self.launch_browser_app(app)
        elif method == 'native':
            self.launch_native_app(app_key, app)
        else:
            self.launch_browser_app(app)

    def launch_native_app(self, app_key, app):
        """Launch native application if available"""
        native_apps = {
            'jellyfin': ['jellyfinmediaplayer', 'jellyfin-media-player'],
            'spotify': ['spotify'],
        }

        if app_key not in native_apps:
            logger.info(f"No native app defined for {app_key}")
            return False

        for cmd in native_apps[app_key]:
            if shutil.which(cmd):
                logger.info(f"Launching native app: {cmd}")
                try:
                    env = os.environ.copy()
                    if 'DISPLAY' not in env:
                        env['DISPLAY'] = ':0'

                    # Special handling for Jellyfin Media Player
                    if app_key == 'jellyfin':
                        launch_cmd = [cmd, '--fullscreen', f'--platform', 'eglfs']
                    else:
                        launch_cmd = [cmd]

                    self.app_process = subprocess.Popen(
                        launch_cmd,
                        env=env,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )

                    # Wait for app to close, then restart hub
                    self.app_process.wait()
                    logger.info(f"Native app {cmd} closed, restarting hub")
                    self.restart_hub()
                    return True
                except Exception as e:
                    logger.error(f"Failed to launch {cmd}: {e}")
                    return False

        logger.info(f"No native app found for {app_key}")
        return False

    def launch_browser_app(self, app):
        """Launch app in browser"""
        chromium = self.find_chromium()
        if not chromium:
            logger.error("Chromium not found!")
            return

        url = app['url']
        flags = self.config['advanced']['chromium_flags'].copy()

        # Special flags for different apps
        if 'youtube' in url:
            flags.append('--user-agent=Mozilla/5.0 (SMART-TV; Linux; Tizen 5.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.31 TV Safari/537.36')

        cmd = [chromium] + flags + [url]

        logger.info(f"Launching browser app: {url}")

        try:
            env = os.environ.copy()
            if 'DISPLAY' not in env:
                env['DISPLAY'] = ':0'

            self.app_process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Monitor process
            self.app_process.wait()
            logger.info("Browser app closed, restarting hub")
            self.restart_hub()
        except Exception as e:
            logger.error(f"Failed to launch browser app: {e}")

    def restart_hub(self):
        """Restart the main hub interface"""
        logger.info("Restarting hub interface")
        time.sleep(1)
        self.launch_browser()

    def cec_command(self, command):
        """Send CEC command to TV"""
        if not self.config['remote']['enable_cec']:
            logger.info("CEC is disabled")
            return False

        if not shutil.which('cec-client'):
            logger.warning("cec-client not found")
            return False

        cec_commands = {
            'standby': 'standby 0',
            'on': 'on 0',
            'status': 'pow 0'
        }

        if command not in cec_commands:
            logger.warning(f"Unknown CEC command: {command}")
            return False

        try:
            logger.info(f"Sending CEC command: {command}")
            cmd = f'echo "{cec_commands[command]}" | cec-client -s -d 1'
            subprocess.run(cmd, shell=True, timeout=5, capture_output=True)
            return True
        except Exception as e:
            logger.error(f"CEC command failed: {e}")
            return False

    def handle_exit(self):
        """Handle exit request"""
        logger.info("Exit requested")

        action = self.config['exit']['action']

        if action == 'cec_standby':
            if self.cec_command('standby'):
                logger.info("TV standby command sent")
            else:
                logger.warning("CEC standby failed, using fallback")
                action = self.config['exit'].get('cec_fallback', 'close')

        if action == 'shutdown':
            logger.info("Shutting down system")
            subprocess.run(['sudo', 'shutdown', '-h', 'now'])
        elif action == 'reboot':
            logger.info("Rebooting system")
            subprocess.run(['sudo', 'reboot'])
        else:
            logger.info("Closing application")
            self.cleanup()
            sys.exit(0)

    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up...")

        if self.browser_process:
            self.browser_process.terminate()
            self.browser_process.wait()

        if self.app_process:
            self.app_process.terminate()
            self.app_process.wait()

        if self.http_server:
            self.http_server.shutdown()

    def signal_handler(self, signum, frame):
        """Handle interrupt signals"""
        logger.info(f"Received signal {signum}")
        self.cleanup()
        sys.exit(0)

    def run(self):
        """Main run loop"""
        logger.info("Starting Pi Media Hub")

        # Check dependencies
        self.check_dependencies()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        # Start HTTP server
        self.start_http_server()

        # Wait a moment for server to be ready
        time.sleep(1)

        # Launch browser
        self.launch_browser()

        # Wait for browser process
        try:
            if self.browser_process:
                self.browser_process.wait()
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()


def main():
    launcher = MediaHubLauncher()
    launcher.run()


if __name__ == '__main__':
    main()

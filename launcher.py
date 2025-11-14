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
import socket
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

        # Store reference to parent launcher for use in handler
        launcher = self

        class CustomHandler(SimpleHTTPRequestHandler):
            def log_message(self, format, *args):
                # Log to our logger instead of suppressing
                logger.info(f"HTTP: {format % args}")

            def log_error(self, format, *args):
                # Log errors
                logger.error(f"HTTP Error: {format % args}")

            def do_GET(self):
                try:
                    # Handle API: Get config
                    if self.path == '/api/config':
                        launcher.send_config(self)
                    # Handle launch protocol
                    elif self.path.startswith('/launch'):
                        launcher.handle_launch_request(self.path)
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        self.wfile.write(b'<html><body>Launching...</body></html>')
                    else:
                        SimpleHTTPRequestHandler.do_GET(self)
                except Exception as e:
                    logger.error(f"Error in do_GET: {e}", exc_info=True)
                    try:
                        self.send_response(500)
                        self.end_headers()
                    except:
                        pass

            def do_POST(self):
                try:
                    # Handle API: Save config
                    if self.path == '/api/config':
                        launcher.save_config_api(self)
                    else:
                        self.send_response(404)
                        self.end_headers()
                except Exception as e:
                    logger.error(f"Error in do_POST: {e}", exc_info=True)
                    try:
                        self.send_response(500)
                        self.end_headers()
                    except:
                        pass

        try:
            # Bind to 127.0.0.1 explicitly instead of 'localhost' to avoid IPv6 issues
            self.http_server = HTTPServer(('127.0.0.1', self.port), CustomHandler)
            logger.info(f"HTTP server created, binding to 127.0.0.1:{self.port}")

            def server_thread_wrapper():
                try:
                    logger.info("HTTP server thread starting...")
                    self.http_server.serve_forever()
                except Exception as e:
                    logger.error(f"HTTP server thread crashed: {e}", exc_info=True)

            self.http_thread = Thread(target=server_thread_wrapper, daemon=True)
            self.http_thread.start()
            logger.info(f"HTTP server thread started")
        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}", exc_info=True)
            sys.exit(1)

    def wait_for_server_ready(self, timeout=10):
        """Wait for HTTP server to be ready to accept connections"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Try to connect to the server
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', self.port))
                sock.close()

                if result == 0:
                    logger.info(f"HTTP server is ready and accepting connections on 127.0.0.1:{self.port}")
                    return True

                logger.info(f"Server not ready yet, waiting... ({int(time.time() - start_time)}s/{timeout}s)")
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"Error checking server readiness: {e}")
                time.sleep(0.5)

        logger.error(f"Server failed to become ready within {timeout} seconds")
        # Check if thread is still alive
        if self.http_thread and self.http_thread.is_alive():
            logger.error("HTTP thread is running but not accepting connections")
        else:
            logger.error("HTTP thread has died")
        return False

    def send_config(self, handler):
        """Send config to client"""
        try:
            # Reload config to get latest
            self.config = self.load_config()

            handler.send_response(200)
            handler.send_header('Content-type', 'application/json')
            handler.send_header('Access-Control-Allow-Origin', '*')
            handler.end_headers()
            handler.wfile.write(json.dumps(self.config).encode())
            logger.info("Config sent to client")
        except Exception as e:
            logger.error(f"Failed to send config: {e}")
            handler.send_response(500)
            handler.end_headers()

    def save_config_api(self, handler):
        """Save config from client"""
        try:
            content_length = int(handler.headers['Content-Length'])
            post_data = handler.rfile.read(content_length)
            new_config = json.loads(post_data.decode())

            # Save to file
            with open(CONFIG_FILE, 'w') as f:
                json.dump(new_config, f, indent=2)

            # Reload config
            self.config = new_config

            handler.send_response(200)
            handler.send_header('Content-type', 'application/json')
            handler.send_header('Access-Control-Allow-Origin', '*')
            handler.end_headers()
            handler.wfile.write(json.dumps({'success': True}).encode())
            logger.info("Config saved successfully")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            handler.send_response(500)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode())

    def handle_launch_request(self, path):
        """Handle launch:// protocol requests from browser"""
        logger.info(f"Launch request: {path}")

        if '/launch/exit' in path:
            self.handle_exit()
        elif '/launch/app/' in path:
            app_key = path.split('/launch/app/')[-1].split('?')[0]
            self.launch_app(app_key)

    def handle_get_config(self, handler):
        """Handle GET /api/config - Return current configuration"""
        try:
            handler.send_response(200)
            handler.send_header('Content-Type', 'application/json')
            handler.send_header('Access-Control-Allow-Origin', '*')
            handler.end_headers()

            config_json = json.dumps(self.config, indent=2)
            handler.wfile.write(config_json.encode())
            logger.info("Config sent to client")
        except Exception as e:
            logger.error(f"Error sending config: {e}")
            handler.send_response(500)
            handler.end_headers()

    def handle_save_config(self, handler):
        """Handle POST /api/config - Save new configuration"""
        try:
            content_length = int(handler.headers['Content-Length'])
            post_data = handler.rfile.read(content_length)
            new_config = json.loads(post_data.decode())

            # Validate config structure
            required_keys = ['apps', 'display', 'startup', 'exit', 'remote', 'advanced']
            if not all(key in new_config for key in required_keys):
                handler.send_response(400)
                handler.end_headers()
                handler.wfile.write(b'Invalid config structure')
                return

            # Save to config.json
            with open(CONFIG_FILE, 'w') as f:
                json.dump(new_config, f, indent=2)

            # Update in-memory config
            self.config = new_config

            handler.send_response(200)
            handler.send_header('Content-Type', 'application/json')
            handler.send_header('Access-Control-Allow-Origin', '*')
            handler.end_headers()
            handler.wfile.write(b'{"status": "success"}')

            logger.info("Config saved successfully")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            handler.send_response(500)
            handler.end_headers()
            handler.wfile.write(f'{{"error": "{str(e)}"}}'.encode())

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

        url = f'http://127.0.0.1:{self.port}/index.html'
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
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info(f"Browser process started (PID: {self.browser_process.pid})")
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

        # Wait for server to be ready
        if not self.wait_for_server_ready(timeout=10):
            logger.error("HTTP server failed to start properly")
            sys.exit(1)

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

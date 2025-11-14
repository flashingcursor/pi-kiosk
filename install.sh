#!/bin/bash
# Pi Media Hub Installation Script
# For Raspberry Pi OS (Trixie and later)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$SCRIPT_DIR"
USERNAME="${SUDO_USER:-$USER}"
SERVICE_FILE="pi-media-hub.service"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print functions
print_header() {
    echo -e "\n${CYAN}============================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}============================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check if running on Raspberry Pi
check_platform() {
    print_header "Checking Platform"

    if [ ! -f /proc/device-tree/model ]; then
        print_warning "Cannot determine if this is a Raspberry Pi"
        print_info "Continuing anyway..."
        return 0
    fi

    MODEL=$(cat /proc/device-tree/model)
    print_info "Detected: $MODEL"

    if echo "$MODEL" | grep -qi "raspberry pi"; then
        print_success "Running on Raspberry Pi"
        return 0
    else
        print_warning "This doesn't appear to be a Raspberry Pi"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Update package list
update_packages() {
    print_header "Updating Package List"
    sudo apt update
    print_success "Package list updated"
}

# Install dependencies
install_dependencies() {
    print_header "Installing Dependencies"

    PACKAGES=(
        "chromium"
        "python3"
        "python3-pip"
        "cec-utils"
        "x11-xserver-utils"
        "unclutter"
        "xdotool"
    )

    print_info "Installing: ${PACKAGES[*]}"
    sudo apt install -y "${PACKAGES[@]}"

    print_success "Core dependencies installed"

    # Optional: Jellyfin Media Player
    print_info "\nOptional: Jellyfin Media Player (native app)"
    read -p "Install Jellyfin Media Player? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command -v flatpak &> /dev/null || sudo apt install -y flatpak; then
            print_info "Installing Jellyfin Media Player via Flatpak..."
            flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo || true
            flatpak install -y flathub com.github.iwalton3.jellyfin-media-player || true
            print_success "Jellyfin Media Player installed"
        else
            print_warning "Flatpak installation failed, skipping Jellyfin Media Player"
        fi
    fi
}

# Configure system
configure_system() {
    print_header "Configuring System"

    # Disable screen blanking
    print_info "Disabling screen blanking..."

    # For X11
    if [ ! -f /home/$USERNAME/.xsession ]; then
        cat > /home/$USERNAME/.xsession << 'EOF'
# Disable screen blanking
xset s off
xset -dpms
xset s noblank

# Hide cursor after 3 seconds of inactivity
unclutter -idle 3 &
EOF
        chown $USERNAME:$USERNAME /home/$USERNAME/.xsession
        chmod +x /home/$USERNAME/.xsession
        print_success "Created .xsession file"
    else
        print_info ".xsession already exists, skipping"
    fi

    # Autostart X on login (optional)
    if [ ! -f /home/$USERNAME/.bash_profile ]; then
        cat > /home/$USERNAME/.bash_profile << 'EOF'
# Start X at login
if [ -z "$DISPLAY" ] && [ "$XDG_VTNR" = "1" ]; then
    exec startx
fi
EOF
        chown $USERNAME:$USERNAME /home/$USERNAME/.bash_profile
        print_info "Created .bash_profile for auto-startx"
    fi

    print_success "System configuration complete"
}

# Make scripts executable
setup_scripts() {
    print_header "Setting Up Scripts"

    chmod +x "$INSTALL_DIR/launcher.py"
    chmod +x "$INSTALL_DIR/setup.py"
    chmod +x "$INSTALL_DIR/uninstall.sh"
    chmod +x "$INSTALL_DIR/scripts/cec-control.sh"
    chmod +x "$INSTALL_DIR/scripts/check-network.sh"

    print_success "Scripts are now executable"
}

# Install systemd service
install_service() {
    print_header "Installing Systemd Service"

    # Create service file with correct paths
    sed -e "s|%USERNAME%|$USERNAME|g" \
        -e "s|%INSTALL_DIR%|$INSTALL_DIR|g" \
        "$INSTALL_DIR/$SERVICE_FILE" > "/tmp/$SERVICE_FILE"

    sudo mv "/tmp/$SERVICE_FILE" "/etc/systemd/system/$SERVICE_FILE"
    sudo systemctl daemon-reload

    print_success "Service installed: $SERVICE_FILE"
    print_info "To enable auto-start: sudo systemctl enable $SERVICE_FILE"
    print_info "To start now: sudo systemctl start $SERVICE_FILE"
}

# Enable service
enable_service() {
    print_header "Enabling Service"

    sudo systemctl enable $SERVICE_FILE
    print_success "Service enabled - will start on boot"

    read -p "Start service now? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo systemctl start $SERVICE_FILE
        print_success "Service started"
        print_info "Check status: sudo systemctl status $SERVICE_FILE"
    fi
}

# Test CEC
test_cec() {
    print_header "Testing HDMI-CEC"

    if command -v cec-client &> /dev/null; then
        print_info "Scanning for CEC devices..."
        echo "scan" | cec-client -s -d 1 | grep -i "device\|vendor\|osd"
        print_success "CEC scan complete"
        print_info "To test TV control: ./scripts/cec-control.sh status"
    else
        print_warning "cec-client not found, skipping CEC test"
    fi
}

# Create initial config
create_config() {
    print_header "Configuration"

    if [ -f "$INSTALL_DIR/config.json" ]; then
        print_info "config.json already exists"
        read -p "Run setup wizard to reconfigure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python3 "$INSTALL_DIR/setup.py"
        fi
    else
        print_info "No config.json found"
        read -p "Run setup wizard now? (Y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            python3 "$INSTALL_DIR/setup.py"
        else
            # Copy default config
            cp "$INSTALL_DIR/config.default.json" "$INSTALL_DIR/config.json"
            print_info "Using default configuration"
            print_warning "Run './setup.py' to customize settings"
        fi
    fi
}

# Print completion message
print_completion() {
    print_header "Installation Complete!"

    echo -e "${GREEN}Pi Media Hub is ready!${NC}\n"

    print_info "Quick Start:"
    echo "  • Run manually:    python3 launcher.py"
    echo "  • Configure:       python3 setup.py"
    echo "  • Enable service:  sudo systemctl enable pi-media-hub"
    echo "  • Start service:   sudo systemctl start pi-media-hub"
    echo "  • Check status:    sudo systemctl status pi-media-hub"
    echo "  • View logs:       journalctl -u pi-media-hub -f"
    echo ""

    print_info "CEC Control:"
    echo "  • Test CEC:        ./scripts/cec-control.sh status"
    echo "  • TV standby:      ./scripts/cec-control.sh standby"
    echo "  • TV on:           ./scripts/cec-control.sh on"
    echo ""

    print_info "Jellyfin Setup:"
    echo "  1. Install Jellyfin server (if not already running)"
    echo "  2. Run: python3 setup.py"
    echo "  3. Enter your Jellyfin server URL"
    echo ""

    print_success "Enjoy your Pi Media Hub!"
}

# Main installation flow
main() {
    print_header "Pi Media Hub Installer"

    # Parse arguments
    ENABLE_SERVICE=false
    SKIP_DEPS=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --enable-service)
                ENABLE_SERVICE=true
                shift
                ;;
            --skip-deps)
                SKIP_DEPS=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --enable-service  Enable and start systemd service"
                echo "  --skip-deps       Skip dependency installation"
                echo "  --help           Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Check platform
    check_platform

    # Install dependencies
    if [ "$SKIP_DEPS" = false ]; then
        update_packages
        install_dependencies
    else
        print_warning "Skipping dependency installation"
    fi

    # Setup
    configure_system
    setup_scripts
    install_service
    test_cec
    create_config

    # Enable service if requested
    if [ "$ENABLE_SERVICE" = true ]; then
        enable_service
    fi

    # Done
    print_completion
}

# Run main installation
main "$@"

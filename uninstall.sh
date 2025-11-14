#!/bin/bash
# Pi Media Hub Uninstallation Script
# Cleanly removes Pi Media Hub from your system

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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

# Welcome message
print_header "Pi Media Hub - Uninstaller"

print_warning "This will remove Pi Media Hub from your system"
echo ""
read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Uninstallation cancelled"
    exit 0
fi

# Stop and disable service
print_header "Removing Systemd Service"

if systemctl is-active --quiet $SERVICE_FILE 2>/dev/null; then
    print_info "Stopping service..."
    sudo systemctl stop $SERVICE_FILE
    print_success "Service stopped"
fi

if systemctl is-enabled --quiet $SERVICE_FILE 2>/dev/null; then
    print_info "Disabling service..."
    sudo systemctl disable $SERVICE_FILE
    print_success "Service disabled"
fi

if [ -f "/etc/systemd/system/$SERVICE_FILE" ]; then
    print_info "Removing service file..."
    sudo rm "/etc/systemd/system/$SERVICE_FILE"
    sudo systemctl daemon-reload
    print_success "Service file removed"
else
    print_info "Service file not found (already removed or never installed)"
fi

# Remove installation directory
print_header "Removing Installation Files"

echo ""
read -p "Remove installation directory ($SCRIPT_DIR)? (Y/n) " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    # Backup config if it exists
    if [ -f "$SCRIPT_DIR/config.json" ]; then
        BACKUP_DIR="$HOME/pi-media-hub-backup-$(date +%Y%m%d-%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        cp "$SCRIPT_DIR/config.json" "$BACKUP_DIR/config.json"
        print_success "Configuration backed up to $BACKUP_DIR"
    fi

    print_info "Removing installation directory..."
    cd "$HOME"
    rm -rf "$SCRIPT_DIR"
    print_success "Installation directory removed"

    REMOVED_DIR=true
else
    print_info "Installation directory kept at $SCRIPT_DIR"
    REMOVED_DIR=false
fi

# Clean up user configuration files
print_header "Cleaning Up User Configuration"

echo ""
read -p "Remove user configuration files (.xsession, .bash_profile)? (y/N) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f "$HOME/.xsession" ]; then
        print_warning "Removing .xsession (screen blanking will be re-enabled)"
        rm "$HOME/.xsession"
        print_success "Removed .xsession"
    fi

    if [ -f "$HOME/.bash_profile" ]; then
        print_warning "Removing .bash_profile (auto-startx disabled)"
        rm "$HOME/.bash_profile"
        print_success "Removed .bash_profile"
    fi
else
    print_info "User configuration files kept"
fi

# Optionally remove packages
print_header "Package Cleanup"

echo ""
print_warning "The following packages were installed by Pi Media Hub:"
echo "  - chromium"
echo "  - python3"
echo "  - python3-pip"
echo "  - cec-utils"
echo "  - x11-xserver-utils"
echo "  - unclutter"
echo "  - xdotool"
echo ""
print_warning "These packages may be used by other applications!"
echo ""
read -p "Remove these packages? (y/N) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Removing packages..."

    PACKAGES=(
        "chromium"
        "cec-utils"
        "unclutter"
        "xdotool"
    )

    # Don't remove python3, python3-pip, or x11-xserver-utils as they're likely used by other apps
    print_warning "Keeping python3, python3-pip, and x11-xserver-utils (commonly used by other apps)"

    if command -v apt-get &> /dev/null; then
        sudo apt-get remove -y "${PACKAGES[@]}" || true
        sudo apt-get autoremove -y || true
        print_success "Packages removed"
    else
        print_warning "Could not detect apt-get, skipping package removal"
    fi
else
    print_info "Packages kept (recommended)"
fi

# Clean up logs
print_header "Cleaning Up Logs"

if [ -f "/tmp/pi-media-hub.log" ]; then
    rm "/tmp/pi-media-hub.log"
    print_success "Removed application log"
fi

# Final message
print_header "Uninstallation Complete"

if [ "$REMOVED_DIR" = true ]; then
    echo -e "${GREEN}Pi Media Hub has been completely removed from your system.${NC}\n"
else
    echo -e "${GREEN}Pi Media Hub service has been removed.${NC}"
    print_info "Installation files remain at: $SCRIPT_DIR"
    print_info "To remove them manually: rm -rf $SCRIPT_DIR"
    echo ""
fi

print_info "Thank you for using Pi Media Hub!"
echo ""
print_info "To reinstall in the future:"
echo "  curl -sSL https://raw.githubusercontent.com/flashingcursor/pi-kiosk/master/bootstrap.sh | bash"
echo ""

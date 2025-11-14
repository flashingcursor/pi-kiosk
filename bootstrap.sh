#!/bin/bash
# Pi Media Hub Bootstrap Installer
# One-command installer for Raspberry Pi
#
# Usage: curl -sSL https://raw.githubusercontent.com/flashingcursor/pi-kiosk/main/bootstrap.sh | bash

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/flashingcursor/pi-kiosk.git"
INSTALL_DIR="$HOME/pi-media-hub"
BRANCH="main"

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

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please do not run this script as root"
    print_info "Run without sudo: curl -sSL https://... | bash"
    exit 1
fi

# Welcome message
clear
print_header "Pi Media Hub - One-Command Installer"
echo -e "${CYAN}A beautiful media center for your Raspberry Pi${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Check if git is installed
if ! command -v git &> /dev/null; then
    print_warning "Git is not installed"
    print_info "Installing git..."
    sudo apt update
    sudo apt install -y git
    print_success "Git installed"
fi

# Check if running on Raspberry Pi
print_header "System Check"

if [ -f /proc/device-tree/model ]; then
    MODEL=$(cat /proc/device-tree/model)
    print_info "Detected: $MODEL"

    if echo "$MODEL" | grep -qi "raspberry pi"; then
        print_success "Running on Raspberry Pi"
    else
        print_warning "This doesn't appear to be a Raspberry Pi"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
else
    print_warning "Cannot determine hardware type"
fi

# Check for existing installation
if [ -d "$INSTALL_DIR" ]; then
    print_warning "Pi Media Hub is already installed at $INSTALL_DIR"
    echo ""
    read -p "Do you want to update it? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Backing up existing configuration..."
        if [ -f "$INSTALL_DIR/config.json" ]; then
            cp "$INSTALL_DIR/config.json" "$INSTALL_DIR/config.json.backup"
            print_success "Config backed up to config.json.backup"
        fi

        print_info "Updating repository..."
        cd "$INSTALL_DIR"
        git pull origin $BRANCH
        print_success "Repository updated"

        print_info "Restoring configuration..."
        if [ -f "$INSTALL_DIR/config.json.backup" ]; then
            mv "$INSTALL_DIR/config.json.backup" "$INSTALL_DIR/config.json"
            print_success "Configuration restored"
        fi

        UPDATE_MODE=true
    else
        print_info "Installation cancelled"
        exit 0
    fi
else
    # Clone repository
    print_header "Downloading Pi Media Hub"
    print_info "Cloning from $REPO_URL..."

    git clone --depth 1 --branch $BRANCH "$REPO_URL" "$INSTALL_DIR"

    if [ $? -eq 0 ]; then
        print_success "Repository cloned successfully"
    else
        print_error "Failed to clone repository"
        exit 1
    fi

    UPDATE_MODE=false
fi

# Navigate to install directory
cd "$INSTALL_DIR"

# Make scripts executable
chmod +x install.sh
chmod +x launcher.py
chmod +x setup.py
chmod +x scripts/*.sh 2>/dev/null || true

# Run the main installer
print_header "Running Installer"
print_info "The main installation script will now run..."
print_info "This will install all required dependencies\n"

sleep 2

# Ask about auto-start
read -p "Do you want the media hub to start automatically on boot? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    AUTO_START="--enable-service"
else
    AUTO_START=""
fi

# Run installer
if [ "$UPDATE_MODE" = true ]; then
    ./install.sh --skip-deps $AUTO_START
else
    ./install.sh $AUTO_START
fi

# Final message
print_header "Installation Complete!"
echo -e "${GREEN}Pi Media Hub has been successfully installed!${NC}\n"

print_info "Installation directory: $INSTALL_DIR"
print_info "Configuration file: $INSTALL_DIR/config.json"
echo ""

print_info "Next Steps:"
echo "  1. Configure your settings:"
echo "     ${CYAN}cd $INSTALL_DIR && python3 setup.py${NC}"
echo ""
echo "  2. Test the media hub:"
echo "     ${CYAN}python3 $INSTALL_DIR/launcher.py${NC}"
echo ""
echo "  3. If auto-start was enabled, reboot your Pi:"
echo "     ${CYAN}sudo reboot${NC}"
echo ""

if [ "$AUTO_START" != "--enable-service" ]; then
    print_info "To enable auto-start later:"
    echo "  ${CYAN}cd $INSTALL_DIR && sudo ./install.sh --enable-service${NC}"
    echo ""
fi

print_info "For help and documentation:"
echo "  ${CYAN}https://github.com/flashingcursor/pi-kiosk${NC}"
echo ""

print_success "Enjoy your Pi Media Hub!"
echo ""

#!/bin/bash
#
# Pi Media Hub - Quick Installation Script
# Run with: curl -fsSL https://raw.githubusercontent.com/flashingcursor/pi-kiosk/main/quick-install.sh | bash
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/flashingcursor/pi-kiosk.git"
INSTALL_DIR="$HOME/pi-media-hub"
BRANCH="main"

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════╗"
echo "║      Pi Media Hub - Quick Installer       ║"
echo "╚════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running on Raspberry Pi (optional - works on any Linux)
if [ -f /proc/device-tree/model ]; then
    MODEL=$(tr -d '\0' < /proc/device-tree/model)
    echo -e "${GREEN}✓${NC} Detected: $MODEL"
fi

# Check for required commands
echo ""
echo -e "${YELLOW}Checking dependencies...${NC}"

MISSING_DEPS=()

if ! command -v git &> /dev/null; then
    MISSING_DEPS+=("git")
fi

if ! command -v python3 &> /dev/null; then
    MISSING_DEPS+=("python3")
fi

if ! command -v chromium-browser &> /dev/null && ! command -v chromium &> /dev/null; then
    MISSING_DEPS+=("chromium")
fi

# Install missing dependencies
if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo -e "${YELLOW}Installing missing dependencies: ${MISSING_DEPS[*]}${NC}"

    # Detect package manager
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y "${MISSING_DEPS[@]}"
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y "${MISSING_DEPS[@]}"
    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm "${MISSING_DEPS[@]}"
    else
        echo -e "${RED}✗ Could not detect package manager. Please install manually: ${MISSING_DEPS[*]}${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓${NC} All dependencies satisfied"
fi

# Clone or update repository
echo ""
echo -e "${YELLOW}Installing Pi Media Hub...${NC}"

if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Directory $INSTALL_DIR already exists.${NC}"
    read -p "Do you want to update it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd "$INSTALL_DIR"
        git pull origin "$BRANCH"
        echo -e "${GREEN}✓${NC} Updated to latest version"
    fi
else
    git clone "$REPO_URL" "$INSTALL_DIR"
    echo -e "${GREEN}✓${NC} Cloned repository"
fi

cd "$INSTALL_DIR"

# Make scripts executable
chmod +x install.sh
chmod +x launcher.py
chmod +x setup.py

# Run installation script
echo ""
echo -e "${YELLOW}Running installation...${NC}"
./install.sh

echo ""
echo -e "${GREEN}"
echo "╔════════════════════════════════════════════╗"
echo "║     Installation Complete!                ║"
echo "╚════════════════════════════════════════════╝"
echo -e "${NC}"

echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""
echo "1. Configure your media hub:"
echo -e "   ${YELLOW}python3 $INSTALL_DIR/setup.py${NC}"
echo ""
echo "2. Start the launcher:"
echo -e "   ${YELLOW}python3 $INSTALL_DIR/launcher.py${NC}"
echo ""
echo "3. Enable autostart (optional):"
echo -e "   ${YELLOW}sudo systemctl enable pi-media-hub${NC}"
echo -e "   ${YELLOW}sudo systemctl start pi-media-hub${NC}"
echo ""
echo -e "${GREEN}Enjoy your Pi Media Hub!${NC}"
echo ""

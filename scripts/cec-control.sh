#!/bin/bash
# CEC Control Script for Pi Media Hub
# Controls TV power via HDMI-CEC

CEC_CLIENT=$(command -v cec-client)

if [ -z "$CEC_CLIENT" ]; then
    echo "Error: cec-client not found. Install with: sudo apt install cec-utils"
    exit 1
fi

# Function to send CEC command
send_cec_command() {
    local command=$1
    echo "$command" | $CEC_CLIENT -s -d 1 2>&1
}

# Main command handler
case "$1" in
    on|power-on)
        echo "Turning TV on..."
        send_cec_command "on 0"
        ;;
    off|standby)
        echo "Putting TV in standby..."
        send_cec_command "standby 0"
        ;;
    status)
        echo "Checking TV power status..."
        send_cec_command "pow 0"
        ;;
    scan)
        echo "Scanning CEC devices..."
        echo "scan" | $CEC_CLIENT -s -d 1
        ;;
    volume-up)
        echo "Volume up..."
        send_cec_command "volup"
        ;;
    volume-down)
        echo "Volume down..."
        send_cec_command "voldown"
        ;;
    mute)
        echo "Mute toggle..."
        send_cec_command "mute"
        ;;
    *)
        echo "Pi Media Hub CEC Control"
        echo ""
        echo "Usage: $0 {on|off|standby|status|scan|volume-up|volume-down|mute}"
        echo ""
        echo "Commands:"
        echo "  on/power-on    - Turn TV on"
        echo "  off/standby    - Put TV in standby mode"
        echo "  status         - Check TV power status"
        echo "  scan           - Scan for CEC devices"
        echo "  volume-up      - Increase volume"
        echo "  volume-down    - Decrease volume"
        echo "  mute           - Toggle mute"
        exit 1
        ;;
esac

exit 0

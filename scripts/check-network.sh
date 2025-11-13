#!/bin/bash
# Network check script for Pi Media Hub

TIMEOUT=5
MAX_RETRIES=3

check_connection() {
    local retry=0

    while [ $retry -lt $MAX_RETRIES ]; do
        # Try to ping Google DNS
        if timeout $TIMEOUT ping -c 1 8.8.8.8 &> /dev/null; then
            return 0
        fi

        # Try to ping Cloudflare DNS
        if timeout $TIMEOUT ping -c 1 1.1.1.1 &> /dev/null; then
            return 0
        fi

        retry=$((retry + 1))
        sleep 2
    done

    return 1
}

if check_connection; then
    echo "Network is online"
    exit 0
else
    echo "Network is offline"
    exit 1
fi

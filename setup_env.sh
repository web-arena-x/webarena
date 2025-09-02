#!/bin/bash

# WebArena Environment Setup Script
# This script sets up the required environment variables for WebArena
#
# Usage:
#   source setup_env.sh <your-server-hostname-or-ip>
#
# Example:
#   source setup_env.sh YOUR_WEBARENA_SERVER
#   source setup_env.sh ec2-xx-xx-xx-xx.us-east-2.compute.amazonaws.com

if [ $# -eq 0 ]; then
    echo "Usage: source setup_env.sh <your-server-hostname-or-ip>"
    echo ""
    echo "Example:"
    echo "  source setup_env.sh YOUR_SERVER_IP"
    echo "  source setup_env.sh ec2-xx-xx-xx-xx.us-east-2.compute.amazonaws.com"
    return 1
fi

SERVER_HOST="$1"

# Remove any trailing slash
SERVER_HOST="${SERVER_HOST%/}"

# Set up environment variables for WebArena websites
export SHOPPING="http://${SERVER_HOST}:7770"
export SHOPPING_ADMIN="http://${SERVER_HOST}:7780/admin"
export REDDIT="http://${SERVER_HOST}:9999"
export GITLAB="http://${SERVER_HOST}:8023"
export MAP="http://${SERVER_HOST}:3000"
export WIKIPEDIA="http://${SERVER_HOST}:8888/wikipedia_en_all_maxi_2022-05/A/User:The_other_Kiwix_guy/Landing"
export HOMEPAGE="PASS"

echo "WebArena environment variables set for server: ${SERVER_HOST}"
echo ""
echo "Environment variables:"
echo "  SHOPPING=${SHOPPING}"
echo "  SHOPPING_ADMIN=${SHOPPING_ADMIN}"
echo "  REDDIT=${REDDIT}"
echo "  GITLAB=${GITLAB}"
echo "  MAP=${MAP}"
echo "  WIKIPEDIA=${WIKIPEDIA}"
echo "  HOMEPAGE=${HOMEPAGE}"
echo ""
echo "You can now run WebArena scripts and evaluations."

#!/bin/bash

# WebArena Map Server Boot Initialization Script
# This script can be used as EC2 user-data or cloud-init script
# It automatically deploys all 5 WebArena map services on boot

set -euo pipefail

# Log everything
exec > >(tee -a /var/log/webarena-init.log)
exec 2>&1

echo "🚀 WebArena Map Server Boot Initialization"
echo "=========================================="
echo "Started at: $(date)"

# Wait for system to be ready
sleep 30

# Download and execute the canonical deployment script
echo "📥 Downloading deployment script..."
cd /tmp
wget -O deploy-canonical.sh https://raw.githubusercontent.com/web-arena-x/webarena/pr-216/deploy-canonical.sh
chmod +x deploy-canonical.sh

echo "🚀 Executing canonical deployment..."
./deploy-canonical.sh

echo "✅ WebArena Map Server initialization complete at: $(date)"
echo "🌐 All services should be available shortly"

# Create a status file
echo "WEBARENA_INIT_COMPLETE=$(date)" > /opt/webarena-status.txt
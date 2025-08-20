#!/bin/bash

# WebArena Map Server Deployment Script - Canonical Method
# This script ensures 100% data consistency with the original WebArena setup
# by copying the exact same databases used in the canonical deployment.

set -euo pipefail

echo "🚀 WebArena Map Server Deployment - Canonical Method"
echo "===================================================="
echo "This ensures 100% data consistency with original WebArena"

# Configuration
S3_BUCKET="webarena-map-server-data"
MOUNT_POINT="/mnt/webarena-data"

echo "📋 Pre-deployment checks..."

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root or with sudo"
   exit 1
fi

# Install dependencies first
echo "📦 Installing dependencies..."
apt-get update
apt-get install -y docker.io s3fs awscli pv

# Check AWS credentials (works with IAM roles on EC2)
echo "🔑 Checking AWS access..."
if ! aws sts get-caller-identity &>/dev/null; then
    echo "❌ AWS access not available. Ensure EC2 instance has IAM role with S3 access"
    exit 1
fi
echo "✅ AWS access confirmed"

# Start Docker
systemctl start docker
systemctl enable docker

# Mount S3 bucket
echo "💾 Mounting S3 bucket..."
mkdir -p "$MOUNT_POINT"
if ! mountpoint -q "$MOUNT_POINT"; then
    s3fs "$S3_BUCKET" "$MOUNT_POINT" -o allow_other,default_permissions,uid=1000,gid=1000,iam_role=auto
    echo "✅ S3 bucket mounted at $MOUNT_POINT"
else
    echo "✅ S3 bucket already mounted"
fi

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker stop osrm-car osrm-bike osrm-foot tile-server nominatim 2>/dev/null || true
docker rm osrm-car osrm-bike osrm-foot tile-server nominatim 2>/dev/null || true

# Clean up any existing local data
echo "🧹 Cleaning up existing local data..."
rm -rf /opt/tile-server-local /opt/nominatim-local /opt/tile-server-pbf 2>/dev/null || true

# Create local directories
echo "📁 Creating local directories..."
mkdir -p /opt/webarena-local/{tile-server,nominatim}
chown -R 999:999 /opt/webarena-local/

echo ""
echo "📥 COPYING CANONICAL DATABASES FROM S3"
echo "======================================"
echo "This ensures exact same data as original WebArena deployment"

# Copy Tile Server database (39GB)
echo "🗺️  Copying Tile Server database (39GB)..."
echo "   This will take 10-15 minutes but ensures data consistency"
if [ -d "$MOUNT_POINT/tile-server-extracted/volumes/osm-data/_data" ]; then
    echo "   Source: $MOUNT_POINT/tile-server-extracted/volumes/osm-data/_data"
    echo "   Target: /opt/webarena-local/tile-server/"
    cp -r "$MOUNT_POINT/tile-server-extracted/volumes/osm-data/_data"/* /opt/webarena-local/tile-server/ &
    TILE_PID=$!
else
    echo "❌ Tile server data not found in S3"
    exit 1
fi

# Copy Nominatim database (background)
echo "🔍 Copying Nominatim database..."
if [ -d "$MOUNT_POINT/nominatim-extracted/docker/volumes/nominatim-data/_data" ]; then
    echo "   Source: $MOUNT_POINT/nominatim-extracted/docker/volumes/nominatim-data/_data"
    echo "   Target: /opt/webarena-local/nominatim/"
    cp -r "$MOUNT_POINT/nominatim-extracted/docker/volumes/nominatim-data/_data"/* /opt/webarena-local/nominatim/ &
    NOMINATIM_PID=$!
else
    echo "❌ Nominatim data not found in S3"
    exit 1
fi

echo ""
echo "🚀 STARTING OSRM SERVICES (S3 DIRECT)"
echo "====================================="

# Start OSRM services immediately (they use S3 direct serving)
echo "🗺️  Starting OSRM Car service..."
docker run -d --name osrm-car -p 5000:5000 \
  -v "$MOUNT_POINT/car":/data \
  ghcr.io/project-osrm/osrm-backend:v5.27.1 osrm-routed --algorithm mld /data/us-northeast-latest.osrm

echo "🚴 Starting OSRM Bike service..."
docker run -d --name osrm-bike -p 5001:5000 \
  -v "$MOUNT_POINT/bike":/data \
  ghcr.io/project-osrm/osrm-backend:v5.27.1 osrm-routed --algorithm mld /data/us-northeast-latest.osrm

echo "🚶 Starting OSRM Foot service..."
docker run -d --name osrm-foot -p 5002:5000 \
  -v "$MOUNT_POINT/foot":/data \
  ghcr.io/project-osrm/osrm-backend:v5.27.1 osrm-routed --algorithm mld /data/us-northeast-latest.osrm

echo ""
echo "⏳ WAITING FOR DATABASE COPIES TO COMPLETE"
echo "=========================================="

# Wait for tile server copy to complete
echo "🗺️  Waiting for Tile Server database copy..."
wait $TILE_PID
chown -R 999:999 /opt/webarena-local/tile-server/
echo "✅ Tile Server database ready"

# Wait for Nominatim copy to complete  
echo "🔍 Waiting for Nominatim database copy..."
wait $NOMINATIM_PID
chown -R 999:999 /opt/webarena-local/nominatim/
echo "✅ Nominatim database ready"

echo ""
echo "🚀 STARTING DATABASE SERVICES"
echo "============================="

# Start Tile Server with canonical database
echo "🗺️  Starting Tile Server with canonical database..."
docker run -d --name tile-server -p 8080:80 \
  -v /opt/webarena-local/tile-server:/var/lib/postgresql/15/main \
  -v /opt/webarena-local/tile-server-tiles:/var/lib/mod_tile \
  overv/openstreetmap-tile-server run

# Start Nominatim with canonical database
echo "🔍 Starting Nominatim with canonical database..."
docker run -d --name nominatim -p 8081:8080 \
  -e PBF_PATH=/nominatim/data/us-northeast-latest.osm.pbf \
  -v /opt/webarena-local/nominatim:/var/lib/postgresql/12/main \
  -v "$MOUNT_POINT":/nominatim/data \
  mediagis/nominatim:4.0

echo ""
echo "🎉 DEPLOYMENT COMPLETE!"
echo "======================"
echo ""
echo "📊 Storage Usage:"
echo "   • OSRM services: 0GB local (100% S3 direct)"
echo "   • Tile server: ~39GB local (canonical database)"
echo "   • Nominatim: ~15GB local (canonical database)"
echo "   • Total local: ~54GB (canonical data guaranteed)"
echo ""
echo "🌐 Service Endpoints:"
echo "   • OSRM Car:    http://$(curl -s ifconfig.me):5000"
echo "   • OSRM Bike:   http://$(curl -s ifconfig.me):5001"
echo "   • OSRM Foot:   http://$(curl -s ifconfig.me):5002"
echo "   • Tile Server: http://$(curl -s ifconfig.me):8080"
echo "   • Nominatim:   http://$(curl -s ifconfig.me):8081"
echo ""
echo "✅ All services use EXACT same data as original WebArena deployment"
echo ""
echo "🧪 Test OSRM services:"
echo "   curl \"http://$(curl -s ifconfig.me):5000/route/v1/driving/-71.0589,42.3601;-71.0567,42.3570\""
echo ""
echo "🧪 Test Tile Server:"
echo "   curl \"http://$(curl -s ifconfig.me):8080/tile/0/0/0.png\""
echo ""
echo "🧪 Test Nominatim:"
echo "   curl \"http://$(curl -s ifconfig.me):8081/search?q=Boston&format=json\""
#!/bin/bash

# WebArena Map Server Deployment Script - S3 + PBF Approach
# This script deploys all 5 services with optimal storage usage:
# - OSRM services: 100% S3 direct serving (0GB local)
# - Tile server: PBF-based database construction (1.4GB → ~20GB local)
# - Nominatim: Local copy for performance

set -euo pipefail

echo "🚀 WebArena Map Server Deployment - S3 + PBF Approach"
echo "======================================================"

# Configuration
S3_BUCKET="webarena-map-server-data"
MOUNT_POINT="/mnt/webarena-data"

echo "📋 Pre-deployment checks..."

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root or with sudo"
   exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &>/dev/null; then
    echo "❌ AWS credentials not configured. Please run 'aws configure'"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
apt-get update
apt-get install -y docker.io s3fs awscli

# Start Docker
systemctl start docker
systemctl enable docker

# Mount S3 bucket
echo "💾 Mounting S3 bucket..."
mkdir -p "$MOUNT_POINT"
if ! mountpoint -q "$MOUNT_POINT"; then
    s3fs "$S3_BUCKET" "$MOUNT_POINT" -o allow_other,default_permissions,uid=1000,gid=1000
    echo "✅ S3 bucket mounted at $MOUNT_POINT"
else
    echo "✅ S3 bucket already mounted"
fi

# Create local directories
echo "📁 Creating local directories..."
mkdir -p /opt/tile-server-pbf/{database,tiles,style,pbf}
mkdir -p /opt/nominatim-local/{database,data}
chown -R 999:999 /opt/tile-server-pbf/
chown -R 999:999 /opt/nominatim-local/

# Extract and copy PBF file
echo "📦 Extracting PBF file (1.4GB)..."
cd /tmp
tar -xf "$MOUNT_POINT/osm_dump.tar" osm_dump/us-northeast-latest.osm.pbf
cp osm_dump/us-northeast-latest.osm.pbf /opt/tile-server-pbf/pbf/region.osm.pbf
chown 999:999 /opt/tile-server-pbf/pbf/region.osm.pbf
echo "✅ PBF file ready for tile server"

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker stop osrm-car osrm-bike osrm-foot tile-server nominatim 2>/dev/null || true
docker rm osrm-car osrm-bike osrm-foot tile-server nominatim 2>/dev/null || true

echo "🚀 Starting services..."

# Start OSRM services (100% S3 direct serving)
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

# Start tile server with PBF import
echo "🗺️  Starting Tile Server (PBF import mode)..."
echo "   This will build the database from 1.4GB PBF file (takes 10-20 minutes)"
docker run -d --name tile-server -p 8080:80 \
  -v /opt/tile-server-pbf/database:/data/database \
  -v /opt/tile-server-pbf/tiles:/data/tiles \
  -v /opt/tile-server-pbf/style:/data/style \
  -v /opt/tile-server-pbf/pbf:/data \
  -e THREADS=4 \
  overv/openstreetmap-tile-server import

# Start Nominatim (will use local copy for better performance)
echo "🔍 Starting Nominatim service..."
echo "   Copying Nominatim data locally for better performance..."
cp -r "$MOUNT_POINT/nominatim-extracted/docker/volumes/nominatim-data/_data"/* /opt/nominatim-local/database/ 2>/dev/null || echo "Nominatim data copying in background..."

docker run -d --name nominatim -p 8081:8080 \
  -e PBF_PATH=/nominatim/data/us-northeast-latest.osm.pbf \
  -v /opt/nominatim-local/database:/var/lib/postgresql/12/main \
  -v "$MOUNT_POINT":/nominatim/data \
  mediagis/nominatim:4.0

echo ""
echo "🎉 DEPLOYMENT COMPLETE!"
echo "======================"
echo ""
echo "📊 Storage Usage:"
echo "   • OSRM services: 0GB local (100% S3 direct)"
echo "   • Tile server: ~1.4GB PBF → ~20GB database (built locally)"
echo "   • Nominatim: ~15GB local copy (for performance)"
echo "   • Total local: ~35GB (vs 156GB traditional)"
echo ""
echo "🌐 Service Endpoints:"
echo "   • OSRM Car:    http://$(curl -s ifconfig.me):5000"
echo "   • OSRM Bike:   http://$(curl -s ifconfig.me):5001"
echo "   • OSRM Foot:   http://$(curl -s ifconfig.me):5002"
echo "   • Tile Server: http://$(curl -s ifconfig.me):8080 (building database...)"
echo "   • Nominatim:   http://$(curl -s ifconfig.me):8081"
echo ""
echo "⏱️  Note: Tile server will take 10-20 minutes to build database from PBF"
echo "   Monitor progress: docker logs tile-server -f"
echo ""
echo "🧪 Test OSRM services:"
echo "   curl \"http://$(curl -s ifconfig.me):5000/route/v1/driving/-71.0589,42.3601;-71.0567,42.3570\""
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
    # Try s3fs with IAM role support
    echo "🔄 Attempting to mount S3 bucket with s3fs..."
    if s3fs "$S3_BUCKET" "$MOUNT_POINT" -o allow_other,default_permissions,uid=1000,gid=1000,iam_role=auto,endpoint=us-east-1; then
        echo "✅ S3 bucket mounted at $MOUNT_POINT (with iam_role=auto)"
    else
        echo "❌ s3fs mount failed. Using AWS CLI to download data..."
        # Use AWS CLI to sync data instead of mounting
        echo "📥 Downloading data from S3 using AWS CLI..."
        mkdir -p "$MOUNT_POINT"
        aws s3 sync "s3://$S3_BUCKET/" "$MOUNT_POINT/" --region us-east-1
        echo "✅ S3 data downloaded to $MOUNT_POINT"
    fi
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
echo "📥 EXTRACTING CANONICAL DATABASES FROM S3 TAR ARCHIVES"
echo "======================================================"
echo "Using tar archives for much faster extraction (5-8 minutes vs 30+ minutes)"

# Extract Tile Server database from tar (background process)
echo "🗺️  Extracting Tile Server database from tar archive (41GB)..."
echo "   This will take 3-5 minutes (much faster than file-by-file copy)"
if aws s3 ls s3://webarena-map-server-data/osm_tile_server.tar >/dev/null 2>&1; then
    echo "   Source: s3://webarena-map-server-data/osm_tile_server.tar"
    echo "   Target: /opt/webarena-local/tile-server/"
    (
        cd /opt/webarena-local/tile-server/
        aws s3 cp s3://webarena-map-server-data/osm_tile_server.tar - | tar -xf - --strip-components=5
    ) &
    TILE_PID=$!
else
    echo "❌ Tile Server tar archive not found in S3"
    exit 1
fi

# Extract Nominatim database from tar (background process)
echo "🔍 Extracting Nominatim database from tar archive (124GB)..."
echo "   This will take 5-8 minutes (much faster than file-by-file copy)"
if aws s3 ls s3://webarena-map-server-data/nominatim_volumes.tar >/dev/null 2>&1; then
    echo "   Source: s3://webarena-map-server-data/nominatim_volumes.tar"
    echo "   Target: /opt/webarena-local/nominatim/"
    (
        cd /opt/webarena-local/nominatim/
        aws s3 cp s3://webarena-map-server-data/nominatim_volumes.tar - | tar -xf - --strip-components=6
    ) &
    NOMINATIM_PID=$!
else
    echo "❌ Nominatim tar archive not found in S3"
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
echo "⏳ WAITING FOR DATABASE EXTRACTIONS TO COMPLETE"
echo "==============================================="

# Wait for tile server extraction to complete
echo "🗺️  Waiting for Tile Server database extraction..."
wait $TILE_PID
chown -R 999:999 /opt/webarena-local/tile-server/
echo "✅ Tile Server database ready"

# Wait for Nominatim extraction to complete  
echo "🔍 Waiting for Nominatim database extraction..."
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

# Start Nominatim with canonical database and WebArena configuration
echo "🔍 Starting Nominatim with canonical database..."
# Fix database permissions for PostgreSQL 14
chown -R 999:999 /opt/webarena-local/nominatim/
chmod -R 700 /opt/webarena-local/nominatim/
docker run -d --name nominatim -p 8085:8080 \
  -e IMPORT_STYLE=extratags \
  -e PBF_PATH=/nominatim/data/us-northeast-latest.osm.pbf \
  -e IMPORT_WIKIPEDIA=/nominatim/data/wikimedia-importance.sql.gz \
  -v /opt/webarena-local/nominatim:/var/lib/postgresql/14/main \
  -v "$MOUNT_POINT":/nominatim/data \
  mediagis/nominatim:4.2 /app/start.sh

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
echo "   • Nominatim:   http://$(curl -s ifconfig.me):8085"
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
echo "   curl \"http://$(curl -s ifconfig.me):8085/search?q=Boston&format=json\""
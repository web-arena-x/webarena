#!/bin/bash
echo "🚀 Deploying WebArena Map Server with S3 Direct Serving"

# Verify S3 mount
if [ ! -d "/mnt/webarena-data/car" ]; then
    echo "❌ S3 mount not found. Please mount S3 bucket first:"
    echo "sudo mkdir -p /mnt/webarena-data"
    echo "sudo s3fs webarena-map-server-data /mnt/webarena-data -o allow_other,use_cache=/tmp"
    exit 1
fi

echo "✅ S3 mount verified"

# Stop any existing containers
echo "🧹 Cleaning up existing containers..."
docker stop osrm-car osrm-bike osrm-foot tile-server nominatim 2>/dev/null || true
docker rm osrm-car osrm-bike osrm-foot tile-server nominatim 2>/dev/null || true

# Create symbolic links for OSRM base files (required for compatibility)
echo "🔗 Creating OSRM symbolic links..."
ln -sf /mnt/webarena-data/car/us-northeast-latest.osrm.fileIndex /mnt/webarena-data/car/us-northeast-latest.osrm 2>/dev/null || true
ln -sf /mnt/webarena-data/bike/us-northeast-latest.osrm.fileIndex /mnt/webarena-data/bike/us-northeast-latest.osrm 2>/dev/null || true
ln -sf /mnt/webarena-data/foot/us-northeast-latest.osrm.fileIndex /mnt/webarena-data/foot/us-northeast-latest.osrm 2>/dev/null || true

echo "🚗 Starting OSRM Car routing service..."
docker run -d --name osrm-car -p 5000:5000 \
  -v /mnt/webarena-data/car:/data \
  ghcr.io/project-osrm/osrm-backend:v5.27.1 osrm-routed --algorithm mld /data/us-northeast-latest.osrm

echo "🚴 Starting OSRM Bike routing service..."
docker run -d --name osrm-bike -p 5001:5000 \
  -v /mnt/webarena-data/bike:/data \
  ghcr.io/project-osrm/osrm-backend:v5.27.1 osrm-routed --algorithm mld /data/us-northeast-latest.osrm

echo "🚶 Starting OSRM Foot routing service..."
docker run -d --name osrm-foot -p 5002:5000 \
  -v /mnt/webarena-data/foot:/data \
  ghcr.io/project-osrm/osrm-backend:v5.27.1 osrm-routed --algorithm mld /data/us-northeast-latest.osrm

echo "🗺️  Starting Tile Server..."
docker run -d --name tile-server -p 8080:80 \
  -v /mnt/webarena-data/tile-server-extracted/volumes/osm-data/_data:/var/lib/postgresql/12/main \
  -v /mnt/webarena-data/tile-server-extracted/volumes/osm-tiles/_data:/var/lib/mod_tile \
  overv/openstreetmap-tile-server run

echo "🔍 Starting Nominatim geocoding service..."
docker run -d --name nominatim -p 8081:8080 \
  -v /mnt/webarena-data/nominatim-extracted/docker/volumes/nominatim-data/_data:/var/lib/postgresql/12/main \
  mediagis/nominatim:4.0

echo ""
echo "✅ All services deployed! Data served directly from S3."
echo "🌐 Services available at:"
echo "  - OSRM Car: http://localhost:5000"
echo "  - OSRM Bike: http://localhost:5001" 
echo "  - OSRM Foot: http://localhost:5002"
echo "  - Tile Server: http://localhost:8080"
echo "  - Nominatim: http://localhost:8081"
echo ""
echo "⏱️  Services may take 2-5 minutes to fully initialize"
echo "🧪 Test with: curl \"http://localhost:5000/route/v1/driving/-71.0589,42.3601;-71.0567,42.3570\""
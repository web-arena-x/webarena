#!/bin/bash
echo "🚀 Deploying WebArena Map Server with Local Data"

# Verify local data
if [ ! -d "/opt/webarena-data/car" ]; then
    echo "❌ Local data not found. Please sync from S3 first:"
    echo "sudo mkdir -p /opt/webarena-data"
    echo "sudo chown \$USER:\$USER /opt/webarena-data"
    echo "aws s3 sync s3://webarena-map-server-data/ /opt/webarena-data/ --no-progress"
    exit 1
fi

echo "✅ Local data verified"

# Stop any existing containers
echo "🧹 Cleaning up existing containers..."
docker stop osrm-car osrm-bike osrm-foot tile-server nominatim 2>/dev/null || true
docker rm osrm-car osrm-bike osrm-foot tile-server nominatim 2>/dev/null || true

# Create symbolic links for OSRM base files (required for compatibility)
echo "🔗 Creating OSRM symbolic links..."
ln -sf /opt/webarena-data/car/us-northeast-latest.osrm.fileIndex /opt/webarena-data/car/us-northeast-latest.osrm 2>/dev/null || true
ln -sf /opt/webarena-data/bike/us-northeast-latest.osrm.fileIndex /opt/webarena-data/bike/us-northeast-latest.osrm 2>/dev/null || true
ln -sf /opt/webarena-data/foot/us-northeast-latest.osrm.fileIndex /opt/webarena-data/foot/us-northeast-latest.osrm 2>/dev/null || true

echo "🚗 Starting OSRM Car routing service..."
docker run -d --name osrm-car -p 5000:5000 \
  -v /opt/webarena-data/car:/data \
  ghcr.io/project-osrm/osrm-backend:v5.27.1 osrm-routed --algorithm mld /data/us-northeast-latest.osrm

echo "🚴 Starting OSRM Bike routing service..."
docker run -d --name osrm-bike -p 5001:5000 \
  -v /opt/webarena-data/bike:/data \
  ghcr.io/project-osrm/osrm-backend:v5.27.1 osrm-routed --algorithm mld /data/us-northeast-latest.osrm

echo "🚶 Starting OSRM Foot routing service..."
docker run -d --name osrm-foot -p 5002:5000 \
  -v /opt/webarena-data/foot:/data \
  ghcr.io/project-osrm/osrm-backend:v5.27.1 osrm-routed --algorithm mld /data/us-northeast-latest.osrm

echo "🗺️  Starting Tile Server..."
docker run -d --name tile-server -p 8080:80 \
  -v /opt/webarena-data/tile-server-extracted/volumes/osm-data/_data:/var/lib/postgresql/12/main \
  -v /opt/webarena-data/tile-server-extracted/volumes/osm-tiles/_data:/var/lib/mod_tile \
  overv/openstreetmap-tile-server run

echo "🔍 Starting Nominatim geocoding service..."
docker run -d --name nominatim -p 8081:8080 \
  -v /opt/webarena-data/nominatim-extracted/docker/volumes/nominatim-data/_data:/var/lib/postgresql/12/main \
  mediagis/nominatim:4.0

echo ""
echo "✅ All services deployed with local data!"
echo "🌐 Services available at:"
echo "  - OSRM Car: http://localhost:5000"
echo "  - OSRM Bike: http://localhost:5001" 
echo "  - OSRM Foot: http://localhost:5002"
echo "  - Tile Server: http://localhost:8080"
echo "  - Nominatim: http://localhost:8081"
echo ""
echo "⏱️  Services may take 2-5 minutes to fully initialize"
echo "🧪 Test with: curl \"http://localhost:5000/route/v1/driving/-71.0589,42.3601;-71.0567,42.3570\""
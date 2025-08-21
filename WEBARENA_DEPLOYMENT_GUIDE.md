# WebArena Complete Deployment Guide

This guide provides step-by-step instructions for deploying both the WebArena map backend server and the WebArena frontend AMI, based on successful deployment analysis.

## Overview

The WebArena deployment consists of two main components:

1. **Map Backend Server**: Provides tile server, geocoding, and routing services
2. **WebArena Frontend AMI**: Hosts the main WebArena applications including the map interface

## Prerequisites

- AWS Account with EC2 access
- AWS CLI configured or access to AWS Console
- SSH key pair for EC2 access

## Part 1: Deploy Map Backend Server

### Step 1: Launch Map Backend EC2 Instance

1. **Instance Configuration**:
   - **AMI**: Ubuntu 24.04 LTS (ami-0ea3c35c5c3284d82 or latest)
   - **Instance Type**: `t3a.xlarge` (4 vCPU, 16 GB RAM) - **minimum required**
   - **Storage**: 1000 GB gp3 EBS volume (required for data)
   - **Region**: `us-east-2` (recommended, matches successful deployment)

2. **Security Group**: Create or use security group with these inbound rules:
   ```
   SSH (22): 0.0.0.0/0
   HTTP (8080): 0.0.0.0/0  # Tile server
   HTTP (8085): 0.0.0.0/0  # Geocoding server
   HTTP (5000): 0.0.0.0/0  # OSRM car routing
   HTTP (5001): 0.0.0.0/0  # OSRM bike routing
   HTTP (5002): 0.0.0.0/0  # OSRM foot routing
   ```

3. **User Data**: Copy the entire contents of `webarena-map-backend-boot-init.yaml` into the "User data" field during instance launch.

4. **Key Pair**: Select or create an SSH key pair for access.

5. **Launch the instance** and note the **Instance ID** and **Public IP**.

### Step 2: Monitor Map Backend Deployment

The bootstrap process takes **60-90 minutes** due to large data downloads (~180GB total).

**Monitor progress via SSH**:
```bash
# SSH into the instance
ssh -i your-key.pem ubuntu@<map-backend-public-ip>

# Monitor bootstrap progress
sudo tail -f /var/log/webarena-map-bootstrap.log

# Check service status
docker ps

# Check system resources
free -h
df -h
```

**Expected timeline**:
- 0-10 min: Package installation and setup
- 10-40 min: Data downloads from S3
- 40-70 min: Data extraction (memory intensive)
- 70-90 min: Docker container startup and verification

### Step 3: Verify Map Backend Services

Once bootstrap completes, verify all services are running:

```bash
# Check all containers are running
docker ps

# Test endpoints (replace <PUBLIC_IP> with your instance's public IP)
curl -I "http://<PUBLIC_IP>:8080/tile/0/0/0.png"  # Should return 200
curl "http://<PUBLIC_IP>:8085/search?q=Pittsburgh&format=json&limit=1"  # Should return JSON
curl "http://<PUBLIC_IP>:5000/route/v1/driving/-79.9959,40.4406;-79.9,40.45?overview=false"  # Should return route
```

**Save the Map Backend Public IP** - you'll need it for the frontend configuration.

## Part 2: Deploy WebArena Frontend AMI

### Step 4: Launch WebArena AMI Instance

1. **Instance Configuration**:
   - **AMI**: `ami-06290d70feea35450` (WebArena AMI in us-east-2)
   - **Instance Type**: `t3a.xlarge` (4 vCPU, 16 GB RAM)
   - **Storage**: 1000 GB EBS root volume
   - **Region**: `us-east-2`

2. **Security Group**: Create security group allowing all inbound traffic:
   ```
   All Traffic: 0.0.0.0/0
   ```

3. **Key Pair**: Use the same SSH key pair as the backend server.

4. **Launch the instance** and note the **Instance ID** and **Public IP**.

5. **Create and associate an Elastic IP** for stable hostname:
   ```bash
   # Via AWS CLI
   aws ec2 allocate-address --domain vpc --region us-east-2
   aws ec2 associate-address --instance-id <INSTANCE_ID> --allocation-id <ALLOCATION_ID>
   ```

### Step 5: Start WebArena Services

SSH into the WebArena AMI instance:

```bash
ssh -i your-key.pem ubuntu@<webarena-frontend-public-ip>
```

Start all Docker services:
```bash
# Start core services
docker start gitlab
docker start shopping
docker start shopping_admin
docker start forum
docker start kiwix33

# Start OpenStreetMap website
cd /home/ubuntu/openstreetmap-website/
docker compose start
```

Wait ~1 minute for services to start, then configure them:

```bash
# Configure shopping sites (replace <your-server-hostname> with your public hostname)
docker exec shopping /var/www/magento2/bin/magento setup:store-config:set --base-url="http://<your-server-hostname>:7770"
docker exec shopping mysql -u magentouser -pMyPassword magentodb -e 'UPDATE core_config_data SET value="http://<your-server-hostname>:7770/" WHERE path = "web/secure/base_url";'
docker exec shopping_admin php /var/www/magento2/bin/magento config:set admin/security/password_is_forced 0
docker exec shopping_admin php /var/www/magento2/bin/magento config:set admin/security/password_lifetime 0
docker exec shopping /var/www/magento2/bin/magento cache:flush

docker exec shopping_admin /var/www/magento2/bin/magento setup:store-config:set --base-url="http://<your-server-hostname>:7780"
docker exec shopping_admin mysql -u magentouser -pMyPassword magentodb -e 'UPDATE core_config_data SET value="http://<your-server-hostname>:7780/" WHERE path = "web/secure/base_url";'
docker exec shopping_admin /var/www/magento2/bin/magento cache:flush

# Configure GitLab
docker exec gitlab sed -i "s|^external_url.*|external_url 'http://<your-server-hostname>:8023'|" /etc/gitlab/gitlab.rb
docker exec gitlab gitlab-ctl reconfigure
```

### Step 6: Configure Map Frontend to Use Backend Server

**Critical Step**: Configure the map frontend to use your map backend server.

Replace `<MAP_BACKEND_IP>` with the public IP of your map backend server from Step 3.

```bash
# Update tile server URL
sudo sed -i 's|http://ogma.lti.cs.cmu.edu:8080|http://<MAP_BACKEND_IP>:8080|g' /home/ubuntu/openstreetmap-website/vendor/assets/leaflet/leaflet.osm.js

# Update geocoding and routing server URLs
sudo sed -i 's|metis.lti.cs.cmu.edu:8085|<MAP_BACKEND_IP>:8085|g' /home/ubuntu/openstreetmap-website/config/settings.yml
sudo sed -i 's|metis.lti.cs.cmu.edu:|<MAP_BACKEND_IP>:|g' /home/ubuntu/openstreetmap-website/config/settings.yml

# Restart the OpenStreetMap web service to apply changes
cd /home/ubuntu/openstreetmap-website/
docker compose restart web
```

Wait ~30 seconds for the web service to restart.

## Part 3: Verify Complete Setup

### Step 7: Test All Services

**WebArena Services** (replace `<FRONTEND_IP>` with your frontend public IP):
- OpenStreetMap: `http://<FRONTEND_IP>:3000`
- Shopping: `http://<FRONTEND_IP>:7770`
- Shopping Admin: `http://<FRONTEND_IP>:7780/admin`
- Forum: `http://<FRONTEND_IP>:9999`
- GitLab: `http://<FRONTEND_IP>:8023/explore`
- Wikipedia: `http://<FRONTEND_IP>:8888/wikipedia_en_all_maxi_2022-05/A/User:The_other_Kiwix_guy/Landing`

**Map Functionality Test**:
1. Navigate to `http://<FRONTEND_IP>:3000`
2. Verify that actual map tiles load (not gray panels)
3. Search for "New York City" in the search box
4. Click on a result to verify geocoding works
5. Get directions from "New York City" to "Pittsburgh"
6. Verify that route appears on the map

### Step 8: Success Criteria

✅ **Complete Success** when:
- All WebArena services are accessible
- Map displays actual geographic data (not gray panels)
- Search functionality works (can find "New York City")
- Routing works (can get directions from NYC to Pittsburgh)
- Directions are displayed on the map interface

## Troubleshooting

### Map Backend Issues

**If services don't start**:
```bash
# Check bootstrap log
sudo tail -100 /var/log/webarena-map-bootstrap.log

# Check individual container logs
docker logs tile
docker logs nominatim
docker logs osrm-car

# Check system resources
free -h
df -h
```

**Common issues**:
- **Out of memory**: Ensure instance has at least 16GB RAM and swap is enabled
- **Out of disk space**: Ensure at least 1TB storage
- **Download failures**: Check internet connectivity and S3 access

### Frontend Issues

**If maps show gray panels**:
```bash
# Verify backend connectivity
curl -I "http://<MAP_BACKEND_IP>:8080/tile/0/0/0.png"

# Check configuration files
grep -r "<MAP_BACKEND_IP>" /home/ubuntu/openstreetmap-website/

# Restart web service
cd /home/ubuntu/openstreetmap-website/
docker compose restart web
```

**If search doesn't work**:
```bash
# Test geocoding directly
curl "http://<MAP_BACKEND_IP>:8085/search?q=test&format=json&limit=1"

# Check settings.yml configuration
cat /home/ubuntu/openstreetmap-website/config/settings.yml | grep -A5 -B5 nominatim
```

## Resource Requirements

### Map Backend Server
- **Instance**: t3a.xlarge minimum (16GB RAM required)
- **Storage**: 1000GB EBS (required for data)
- **Network**: High bandwidth for initial data download
- **Time**: 60-90 minutes for complete setup

### WebArena Frontend
- **Instance**: t3a.xlarge recommended
- **Storage**: 1000GB EBS
- **Time**: 10-15 minutes for setup

## Cost Considerations

- **Data Transfer**: ~180GB download from S3 (one-time)
- **Storage**: 1TB EBS volumes for both instances
- **Compute**: Two t3a.xlarge instances running
- **Elastic IPs**: Recommended for stable endpoints

## Security Notes

- Both instances use security groups allowing broad access for testing
- For production, restrict access to specific IP ranges
- Consider using VPC and private subnets for backend services
- Rotate any AWS credentials used during setup

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review logs: `/var/log/webarena-map-bootstrap.log` on backend
3. Verify all configuration changes were applied correctly
4. Ensure both instances are in the same AWS region for optimal performance
#!/bin/bash

# Script to create a new WebArena AMI with fixed map configuration
# This creates an AMI that automatically configures map backend URLs via environment variables

set -e

# Configuration
ORIGINAL_AMI="ami-06290d70feea35450"  # Original WebArena AMI
INSTANCE_TYPE="t3a.xlarge"
REGION="us-east-2"
KEY_NAME="webarena-key"  # Use existing key
SECURITY_GROUP="sg-0c79f57bb4880f5dc"  # webarena-all-traffic security group

# Get current date for naming
DATE=$(date +%Y%m%d-%H%M)
INSTANCE_NAME="webarena-ami-builder-$DATE"
AMI_NAME="webarena-with-configurable-map-backend-$DATE"

echo "Creating temporary instance to build new AMI..."

# Launch temporary instance with map configuration
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $ORIGINAL_AMI \
  --instance-type $INSTANCE_TYPE \
  --key-name $KEY_NAME \
  --security-group-ids $SECURITY_GROUP \
  --user-data file://webarena-frontend-map-config.yaml \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":1000,"VolumeType":"gp3"}}]' \
  --region $REGION \
  --query 'Instances[0].InstanceId' \
  --output text)

echo "Launched instance: $INSTANCE_ID"
echo "Waiting for instance to be running..."

# Wait for instance to be running
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION

echo "Instance is running. Waiting for initialization to complete..."
sleep 300  # Wait 5 minutes for cloud-init to complete

echo "Stopping instance to create AMI..."
aws ec2 stop-instances --instance-ids $INSTANCE_ID --region $REGION
aws ec2 wait instance-stopped --instance-ids $INSTANCE_ID --region $REGION

echo "Creating AMI from instance..."
AMI_ID=$(aws ec2 create-image \
  --instance-id $INSTANCE_ID \
  --name "$AMI_NAME" \
  --description "WebArena AMI with configurable map backend URLs via MAP_BACKEND_IP environment variable" \
  --region $REGION \
  --query 'ImageId' \
  --output text)

echo "Created AMI: $AMI_ID"
echo "Waiting for AMI to be available..."

# Wait for AMI to be available
aws ec2 wait image-available --image-ids $AMI_ID --region $REGION

echo "Terminating temporary instance..."
aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region $REGION

echo "✅ Successfully created new WebArena AMI!"
echo "AMI ID: $AMI_ID"
echo "AMI Name: $AMI_NAME"
echo "Region: $REGION"
echo ""
echo "To use this AMI:"
echo "1. Launch an instance from AMI $AMI_ID"
echo "2. Set environment variable MAP_BACKEND_IP to your map backend IP"
echo "3. The frontend will automatically configure itself on boot"
echo ""
echo "Example launch command:"
echo "aws ec2 run-instances \\"
echo "  --image-id $AMI_ID \\"
echo "  --instance-type t3a.xlarge \\"
echo "  --key-name your-key-name \\"
echo "  --security-group-ids your-security-group \\"
echo "  --user-data 'MAP_BACKEND_IP=18.208.187.221' \\"
echo "  --region $REGION"

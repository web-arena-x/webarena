#!/bin/bash

# Test script for the new WebArena AMI with configurable map backend

set -e

NEW_AMI="ami-08a862bf98e3bd7aa"
INSTANCE_TYPE="t3a.xlarge"
REGION="us-east-2"
KEY_NAME="webarena-key"
SECURITY_GROUP="sg-0c79f57bb4880f5dc"
MAP_BACKEND_IP="18.208.187.221"  # Current map backend IP

# Get current date for naming
DATE=$(date +%Y%m%d-%H%M)
INSTANCE_NAME="webarena-test-$DATE"

echo "Testing new WebArena AMI with configurable map backend..."
echo "AMI: $NEW_AMI"
echo "Map Backend IP: $MAP_BACKEND_IP"

# Create user data script to set the environment variable
cat > user-data.txt << EOF
#!/bin/bash
export MAP_BACKEND_IP=$MAP_BACKEND_IP
echo "MAP_BACKEND_IP=$MAP_BACKEND_IP" >> /etc/environment
EOF

# Launch test instance
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $NEW_AMI \
  --instance-type $INSTANCE_TYPE \
  --key-name $KEY_NAME \
  --security-group-ids $SECURITY_GROUP \
  --user-data file://user-data.txt \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":1000,"VolumeType":"gp3"}}]' \
  --region $REGION \
  --query 'Instances[0].InstanceId' \
  --output text)

echo "Launched test instance: $INSTANCE_ID"
echo "Waiting for instance to be running..."

# Wait for instance to be running
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION

# Get instance public IP
PUBLIC_IP=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --region $REGION --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

echo "✅ Test instance is running!"
echo "Instance ID: $INSTANCE_ID"
echo "Public IP: $PUBLIC_IP"
echo "Instance Name: $INSTANCE_NAME"
echo ""
echo "The instance should automatically configure itself to use map backend: $MAP_BACKEND_IP"
echo "Wait a few minutes for initialization to complete, then test the WebArena services."
echo ""
echo "To check the configuration log:"
echo "ssh -i your-key.pem ubuntu@$PUBLIC_IP 'sudo cat /var/log/map-config.log'"
echo ""
echo "To terminate this test instance later:"
echo "aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region $REGION"

# Clean up user data file
rm -f user-data.txt

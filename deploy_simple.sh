#!/bin/bash
# Simplified deploy script - run container directly without docker-compose

set -e

cd /mnt/c/Users/staro/Projects/Chronica/Chronica

echo "Building Docker image..."
docker build -t chronica-bot:latest .

echo "Saving image to file..."
docker save -o chronica-bot.tar chronica-bot:latest

echo "Creating directory on server..."
ssh ubuntu@192.168.1.125 "mkdir -p /home/ubuntu/chronica"

echo "Copying image to server..."
scp chronica-bot.tar ubuntu@192.168.1.125:/home/ubuntu/chronica/

echo "Deploying on server (running container directly)..."
ssh ubuntu@192.168.1.125 << 'EOF'
cd /home/ubuntu/chronica

echo "Stopping existing container..."
sudo docker stop chronica-bot 2>/dev/null || true
sudo docker rm chronica-bot 2>/dev/null || true

echo "Loading Docker image..."
sudo docker load -i chronica-bot.tar

echo "Removing image file..."
rm chronica-bot.tar

echo "Starting container..."
sudo docker run -d \
  --name chronica-bot \
  --restart unless-stopped \
  -v /tmp/chronica:/tmp/chronica \
  -e PYTHONUNBUFFERED=1 \
  --log-driver json-file \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  chronica-bot:latest

echo "Container started!"
echo ""
echo "Checking status..."
sudo docker ps | grep chronica-bot

echo ""
echo "Recent logs:"
sudo docker logs --tail=20 chronica-bot

echo ""
echo "Deploy completed!"
EOF

echo "Removing local image file..."
rm chronica-bot.tar

echo "All done!"

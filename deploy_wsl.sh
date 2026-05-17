#!/bin/bash
# Build and deploy script for WSL

set -e

cd /mnt/c/Users/staro/Projects/Chronica/Chronica

echo "Building Docker image..."
docker build -t chronica-bot:latest .

echo "Saving image to file..."
docker save -o chronica-bot.tar chronica-bot:latest

echo "Creating directory on server..."
ssh ubuntu@192.168.1.125 "mkdir -p /home/ubuntu/chronica"

echo "Copying to server..."
scp chronica-bot.tar ubuntu@192.168.1.125:/home/ubuntu/chronica/
scp docker-compose.yml ubuntu@192.168.1.125:/home/ubuntu/chronica/

echo "Deploying on server..."
ssh ubuntu@192.168.1.125 << 'EOF'
cd /home/ubuntu/chronica
echo "Stopping existing container..."
sudo docker-compose down 2>/dev/null || true
sudo docker stop chronica-bot 2>/dev/null || true
sudo docker rm chronica-bot 2>/dev/null || true

echo "Loading Docker image..."
sudo docker load -i chronica-bot.tar

echo "Removing image file..."
rm chronica-bot.tar

echo "Starting container..."
sudo docker-compose up -d

echo "Checking status..."
sudo docker-compose ps

echo "Recent logs:"
sudo docker-compose logs --tail=20 chronica-bot

echo "Deploy completed!"
EOF

echo "Removing local image file..."
rm chronica-bot.tar

echo "All done!"

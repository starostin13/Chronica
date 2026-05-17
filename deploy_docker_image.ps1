# Deploy Chronica bot to remote Ubuntu server
# Build image in WSL2 and transfer to server

$SERVER = "ubuntu@192.168.1.125"
$SERVER_DIR = "/home/ubuntu/chronica"
$IMAGE_NAME = "chronica-bot"
$IMAGE_TAG = "latest"
$IMAGE_FILE = "chronica-bot.tar"

Write-Host "Building and deploying Chronica bot..." -ForegroundColor Green

# Check required files
$requiredFiles = @(
    "bot.py",
    "yaHelper.py",
    "stringHelper.py",
    "messageHandlerHelper.py",
    "credentials.py",
    "requirements.txt",
    "Dockerfile"
)

foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Host "Error: File $file not found!" -ForegroundColor Red
        exit 1
    }
}

Write-Host "All required files found" -ForegroundColor Green

# Get current Windows path and convert to WSL path
$currentPath = (Get-Location).Path
$wslPath = $currentPath -replace '^([A-Z]):', { '/mnt/' + $_.Groups[1].Value.ToLower() }
$wslPath = $wslPath -replace '\\', '/'

# Build Docker image in WSL2
Write-Host "Building Docker image in WSL2..." -ForegroundColor Cyan
Write-Host "Working directory: $wslPath" -ForegroundColor Cyan
wsl.exe bash -c "cd '$wslPath' && docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error building image!" -ForegroundColor Red
    exit 1
}

Write-Host "Image built successfully" -ForegroundColor Green

# Save image to file
Write-Host "Saving image to file..." -ForegroundColor Cyan
wsl.exe bash -c "cd '$wslPath' && docker save -o $IMAGE_FILE ${IMAGE_NAME}:${IMAGE_TAG}"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error saving image!" -ForegroundColor Red
    exit 1
}

Write-Host "Image saved to $IMAGE_FILE" -ForegroundColor Green

# Get file size
$fileSize = wsl.exe bash -c "cd '$wslPath' && ls -lh $IMAGE_FILE"
Write-Host "File size: $fileSize" -ForegroundColor Cyan

# Create directory on server
Write-Host "Creating directory on server..." -ForegroundColor Cyan
ssh $SERVER "mkdir -p $SERVER_DIR"

# Copy image to server
Write-Host "Copying image to server (this may take a while)..." -ForegroundColor Cyan
wsl.exe bash -c "cd '$wslPath' && scp $IMAGE_FILE ${SERVER}:${SERVER_DIR}/"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error copying to server!" -ForegroundColor Red
    wsl rm $IMAGE_FILE
    exit 1
}

# Copy docker-compose.yml
Write-Host "Copying docker-compose.yml..." -ForegroundColor Cyan
scp docker-compose.yml ${SERVER}:${SERVER_DIR}/

# Remove local image file
Write-Host "Removing local image file..." -ForegroundColor Cyan
wsl.exe bash -c "cd '$wslPath' && rm $IMAGE_FILE"

# Load image on server and start
Write-Host "Loading image and starting on server..." -ForegroundColor Cyan
$deployScript = @'
cd /home/ubuntu/chronica
echo 'Stopping existing container...'
sudo docker-compose down 2>/dev/null || true
sudo docker stop chronica-bot 2>/dev/null || true
sudo docker rm chronica-bot 2>/dev/null || true

echo 'Loading Docker image...'
sudo docker load -i chronica-bot.tar

echo 'Removing image file...'
rm chronica-bot.tar

echo 'Starting container...'
sudo docker-compose up -d

echo 'Checking status...'
sudo docker-compose ps

echo 'Recent logs:'
sudo docker-compose logs --tail=20 chronica-bot

echo 'Deploy completed!'
'@

ssh $SERVER $deployScript

Write-Host ""
Write-Host "Deploy completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Yellow
Write-Host "  Real-time logs:" -ForegroundColor White
Write-Host "    ssh $SERVER `"cd $SERVER_DIR; sudo docker-compose logs -f chronica-bot`"" -ForegroundColor Gray
Write-Host ""
Write-Host "  Restart bot:" -ForegroundColor White
Write-Host "    ssh $SERVER `"cd $SERVER_DIR; sudo docker-compose restart`"" -ForegroundColor Gray
Write-Host ""
Write-Host "  Stop bot:" -ForegroundColor White
Write-Host "    ssh $SERVER `"cd $SERVER_DIR; sudo docker-compose down`"" -ForegroundColor Gray
Write-Host ""
Write-Host "  Container status:" -ForegroundColor White
Write-Host "    ssh $SERVER `"cd $SERVER_DIR; sudo docker-compose ps`"" -ForegroundColor Gray
Write-Host ""

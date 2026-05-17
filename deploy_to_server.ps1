# Deployment script for Chronica bot to a remote Ubuntu server.
# Run from the project root directory.

$SERVER = "ubuntu@192.168.1.125"
$SERVER_DIR = "/home/ubuntu/chronica"

Write-Host "Starting Chronica deployment to $SERVER ..." -ForegroundColor Green

$requiredFiles = @(
    "bot.py",
    "yaHelper.py",
    "stringHelper.py",
    "messageHandlerHelper.py",
    "credentials.py",
    "requirements.txt",
    "Dockerfile",
    "docker-compose.yml",
    "deploy.sh"
)

foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Host "Missing required file: $file" -ForegroundColor Red
        exit 1
    }
}

Write-Host "All required files found" -ForegroundColor Green

Write-Host "Creating target directory on server ..." -ForegroundColor Cyan
ssh $SERVER "mkdir -p $SERVER_DIR"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to create remote directory" -ForegroundColor Red
    exit 1
}

Write-Host "Copying files to server ..." -ForegroundColor Cyan
scp bot.py yaHelper.py stringHelper.py messageHandlerHelper.py credentials.py requirements.txt Dockerfile docker-compose.yml deploy.sh ${SERVER}:${SERVER_DIR}/
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to copy files to server" -ForegroundColor Red
    exit 1
}

Write-Host "Running remote deploy script ..." -ForegroundColor Cyan
ssh $SERVER "cd $SERVER_DIR; chmod +x deploy.sh; ./deploy.sh"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Remote deploy script failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Deployment finished successfully" -ForegroundColor Green
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Yellow
Write-Host "  Logs:" -ForegroundColor White
Write-Host ('    ssh {0} "cd {1}; sudo docker-compose logs -f chronica-bot"' -f $SERVER, $SERVER_DIR) -ForegroundColor Gray
Write-Host "  Restart:" -ForegroundColor White
Write-Host ('    ssh {0} "cd {1}; sudo docker-compose restart"' -f $SERVER, $SERVER_DIR) -ForegroundColor Gray
Write-Host "  Stop:" -ForegroundColor White
Write-Host ('    ssh {0} "cd {1}; sudo docker-compose down"' -f $SERVER, $SERVER_DIR) -ForegroundColor Gray

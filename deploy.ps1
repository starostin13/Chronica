# Скрипт для деплоя Chronica бота на Ubuntu сервер
# Использование: .\deploy.ps1

param(
    [string]$ServerIP = "192.168.1.125",
    [string]$Username = "ubuntu",  # изменить на ваш username
    [string]$RemotePath = "/home/ubuntu/chronica"
)

Write-Host "🚀 Начинаем деплой Chronica бота на сервер $ServerIP" -ForegroundColor Green

# Проверяем наличие необходимых файлов
$RequiredFiles = @("bot.py", "yaHelper.py", "stringHelper.py", "requirements.txt", "Dockerfile", "docker-compose.yml")
foreach ($file in $RequiredFiles) {
    if (!(Test-Path $file)) {
        Write-Host "❌ Отсутствует файл: $file" -ForegroundColor Red
        exit 1
    }
}

Write-Host "✅ Все необходимые файлы найдены" -ForegroundColor Green

# Создаем временный архив
$TempArchive = "chronica-deploy.tar.gz"
Write-Host "📦 Создаем архив для деплоя..." -ForegroundColor Yellow

# Создаем tar архив (требует WSL или tar.exe)
$FilesToArchive = $RequiredFiles + @("messageHandlerHelper.py", "docker-compose.yml")
$ExistingFiles = $FilesToArchive | Where-Object { Test-Path $_ }

if (Get-Command tar -ErrorAction SilentlyContinue) {
    tar -czf $TempArchive @ExistingFiles
} else {
    Write-Host "⚠️ tar не найден. Используем PowerShell для копирования файлов..." -ForegroundColor Yellow
}

Write-Host "🔧 Деплоим на сервер..." -ForegroundColor Yellow

# SSH команды для деплоя
$SSHCommands = @"
# Останавливаем существующий контейнер
sudo docker-compose -f $RemotePath/docker-compose.yml down 2>/dev/null || true

# Создаем директорию если не существует
mkdir -p $RemotePath

# Переходим в директорию проекта
cd $RemotePath

# Удаляем старые образы
sudo docker system prune -f

# Строим новый образ
sudo docker-compose build --no-cache

# Запускаем контейнер
sudo docker-compose up -d

# Проверяем статус
sudo docker-compose ps
sudo docker-compose logs --tail=20 chronica-bot
"@

Write-Host "📋 Команды для выполнения на сервере:" -ForegroundColor Cyan
Write-Host $SSHCommands -ForegroundColor Gray

Write-Host "🔑 Подключаемся к серверу для выполнения деплоя..." -ForegroundColor Yellow
Write-Host "Выполните следующие команды:" -ForegroundColor White

Write-Host "`n1. Скопируйте файлы на сервер:" -ForegroundColor Yellow
Write-Host "scp -r *.py requirements.txt Dockerfile docker-compose.yml $Username@$ServerIP`:$RemotePath/" -ForegroundColor White

Write-Host "`n2. Подключитесь к серверу:" -ForegroundColor Yellow  
Write-Host "ssh $Username@$ServerIP" -ForegroundColor White

Write-Host "`n3. Выполните деплой:" -ForegroundColor Yellow
Write-Host $SSHCommands -ForegroundColor White

Write-Host "`n✅ Инструкции готовы! Выполните команды выше для завершения деплоя." -ForegroundColor Green
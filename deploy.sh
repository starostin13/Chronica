#!/bin/bash
# Скрипт деплоя для выполнения на Ubuntu сервере
# Сохраните этот файл как deploy.sh на сервере

SERVER_DIR="/home/ubuntu/chronica"
CONTAINER_NAME="chronica-bot"

echo "🚀 Запуск деплоя Chronica бота..."

# Переходим в директорию проекта
cd "$SERVER_DIR" || { echo "❌ Не могу найти директорию $SERVER_DIR"; exit 1; }

echo "🛑 Останавливаем существующий контейнер..."
sudo docker-compose down 2>/dev/null || true

echo "🧹 Очищаем старые образы..."
sudo docker system prune -f

echo "🔨 Собираем новый образ..."
sudo docker-compose build --no-cache

echo "🚀 Запускаем контейнер..."
sudo docker-compose up -d

echo "📊 Проверяем статус..."
sudo docker-compose ps

echo "📝 Последние логи:"
sudo docker-compose logs --tail=20 chronica-bot

echo "✅ Деплой завершён!"
echo "Для просмотра логов в реальном времени:"
echo "sudo docker-compose logs -f chronica-bot"
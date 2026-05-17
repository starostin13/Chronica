FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Создаём рабочую директорию
WORKDIR /app

# Копируем requirements.txt и устанавливаем Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY bot.py .
COPY yaHelper.py .
COPY stringHelper.py .
COPY messageHandlerHelper.py .
COPY credentials.py .

# Создаём директорию для временных файлов
RUN mkdir -p /tmp/chronica

# Запускаем бота
CMD ["python", "-u", "bot.py"]
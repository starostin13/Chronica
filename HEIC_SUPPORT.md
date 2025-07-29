# Поддержка HEIC файлов

## Проблема
Telegram API не поддерживает формат HEIC (High Efficiency Image Container), который используется устройствами Apple. При попытке отправить HEIC файл возникают ошибки:
- `cannot identify image file`
- `Bad Request: failed to get HTTP URL content`
- `Bad Request: wrong type of the web page content`

## Решение
Бот теперь автоматически обнаруживает HEIC файлы и конвертирует их в JPEG перед отправкой.

## Установка поддержки HEIC

### Для Linux/Ubuntu:
```bash
# Установить системные зависимости
sudo apt update
sudo apt install libheif-dev

# Установить Python библиотеку
pip install pillow-heif
```

### Для macOS:
```bash
# Установить libheif через Homebrew
brew install libheif

# Установить Python библиотеку
pip install pillow-heif
```

### Для Windows:
```bash
# Установить Python библиотеку (включает предкомпилированные бинарники)
pip install pillow-heif
```

## Альтернативные решения

Если установка pillow-heif невозможна, бот:
1. Выведет сообщение о том, что HEIC не поддерживается
2. Отправит текстовое уведомление вместо изображения
3. Продолжит работу с другими форматами

## Поддерживаемые форматы
- **С конвертацией**: HEIC → JPEG
- **Нативно**: JPEG, PNG, GIF, BMP, TIFF, WebP

## Логирование
Бот выводит подробную информацию о процессе обработки HEIC файлов:
```
Обнаружен HEIC файл: IMG_3491.heic
HEIC изображение успешно открыто: 4032x3024
HEIC конвертирован в JPEG: /temp/heic_converted.jpg
```

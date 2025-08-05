# Настройка поиска по датам

## Проблема
Поиск по датам не работает из-за неправильно настроенного токена Яндекс.Диска.

## Исправление
1. **Откройте файл `credentials.py`** и замените значения:
   ```python
   yandex_token = "your_real_yandex_disk_token"
   bot_token = "your_real_telegram_bot_token"
   chat_ids = "your_real_chat_id"
   main_dirrectory = "disk:/Изображения/YourRealFolder"
   temp_folder = "/tmp/"
   ```

2. **Получите токен Яндекс.Диска:**
   - Перейдите на https://oauth.yandex.ru/authorize?response_type=token&client_id=23cabbbdc6cd418abb4b39c32c41195d
   - Разрешите доступ к Яндекс.Диску
   - Скопируйте токен из URL

3. **Проверьте путь к папке:**
   - Убедитесь, что `main_dirrectory` указывает на правильную папку на Яндекс.Диске
   - Формат: `disk:/Изображения/НазваниеВашейПапки`

## Тестирование
- **В терминале:** `python tests\test_search.py`
- **В Telegram боте:** `/test_date`

## Ожидаемый результат
```
=== Тестирование поиска по датам ===
Текущая дата: 5.8.2025
1. Тестируем точное совпадение (день 5, месяц 8):
Найдено X файлов с точным совпадением
  - photo1.jpg от 05.08.2021
  - photo2.jpg от 05.08.2022
```

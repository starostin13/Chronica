#!/usr/bin/python3.11
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fileencoding=utf-8
from datetime import date, datetime, timedelta
import os
import random
from random import randrange
from PIL import Image, ExifTags
import sched
import signal
import time
import threading
import pytz
import requests
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import credentials
from yaHelper import (
    createFolder,
    createFolderWithName,
    downloadFile,
    getLastUpdatedFolder,
    saveFileTo,
    find_available_photos,
)
from stringHelper import numberToMonthNameRu
import shutil

bot_token = credentials.bot_token
bot = telebot.TeleBot(bot_token)
dst = credentials.temp_folder
schedule = sched.scheduler(time.time, time.sleep)

# Событие для корректной остановки бота
shutdown_event = threading.Event()

# Словарь для хранения контекста сообщений с изображениями
# Ключ - chat_id, значение - словарь с данными о сообщении
message_context = {}


def signal_handler(sig, frame):
    """Обработчик сигнала прерывания (Ctrl+C)"""
    print("\n🛑 Получен сигнал остановки. Завершаем работу бота...")
    shutdown_event.set()

    # Принудительный выход
    import sys

    sys.exit(0)


# Устанавливаем обработчик сигнала
signal.signal(signal.SIGINT, signal_handler)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    """Обработчик выбора папки для загрузки файлов"""
    print("Answer from inline is " + call.data)
    chat_id = call.message.chat.id

    # Определяем имя папки в зависимости от выбора
    folder_name = None

    if call.data == "new_random":
        # Создать новую папку со случайным именем
        folder_name = createFolder()
    elif call.data == "new_from_text":
        # Создать папку с именем из текста сообщения
        context = message_context.get(chat_id, {})
        text = context.get("text", "").strip()
        if text:
            folder_name = createFolderWithName(text)
        else:
            bot.answer_callback_query(
                call.id,
                "Ошибка: текст сообщения не найден",
            )
            return
    elif call.data == "new_from_date":
        # Создать папку с именем из сегодняшней даты
        today_str = date.today().strftime("%Y-%m-%d")
        folder_name = createFolderWithName(today_str)
    elif call.data == "decline":
        # Отмена - удаляем скачанные файлы
        if os.path.exists(dst):
            for entry in os.listdir(dst):
                file_path = os.path.join(dst, entry)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        if chat_id in message_context:
            del message_context[chat_id]
        bot.answer_callback_query(call.id, "Загрузка отменена")
        bot.edit_message_text(
            "Загрузка отменена",
            call.message.chat.id,
            call.message.message_id,
        )
        return
    else:
        # Использовать существующую папку
        folder_name = call.data

    # Загружаем все файлы из временной папки
    uploaded_count = 0
    if os.path.exists(dst):
        for entry in os.listdir(dst):
            file_path = os.path.join(dst, entry)
            if os.path.isfile(file_path):
                # Используем forward slash для путей Yandex Disk
                yandex_path = f"{folder_name}/{entry}"
                saveFileTo(file_path, yandex_path)
                os.remove(file_path)
                uploaded_count += 1

    # Очищаем контекст
    if chat_id in message_context:
        del message_context[chat_id]

    # Отправляем подтверждение
    bot.answer_callback_query(
        call.id,
        f"Загружено {uploaded_count} файлов в папку {folder_name}",
    )
    bot.edit_message_text(
        f"✅ Успешно загружено {uploaded_count} файлов в папку {folder_name}",
        call.message.chat.id,
        call.message.message_id,
    )


def generate_photo_caption(photo):
    """Генерирует подпись для фотографии на основе её метаданных"""
    photo_path_splited = photo.path.split("/")
    folder_name = photo_path_splited[len(photo_path_splited) - 2]

    if photo.photoslice_time is None:
        return f"Это {folder_name}"

    from datetime import date

    today = date.today()
    photo_date = photo.photoslice_time.date()

    # Проверяем, совпадает ли дата фото с сегодняшним днем и месяцем
    if (
        photo_date.day == today.day
        and photo_date.month == today.month
        and photo_date.year == today.year
    ):
        return f"Это {folder_name}. Произошло сегодня!"
    elif photo_date.day == today.day and photo_date.month == today.month:
        return f"Это {folder_name}. Дело было в этот день в {photo.photoslice_time.year} году"
    else:
        month_name = numberToMonthNameRu(photo.photoslice_time.month)
        return f"Это {folder_name}. Дело было в {month_name} {photo.photoslice_time.year} года"


def try_send_large_image(chat_id, photo, comment, available_photos):
    """
    Пытается отправить большое изображение (>= 5MB)
    Возвращает True если успешно отправлено, False если нужно попробовать другой файл
    """
    memorySizeRatio = 5 / ((photo.size / 1000) / 1024)

    # Проверяем успешность скачивания
    if not downloadFile(photo.file, photo.name, photo.path):
        print(f"Не удалось скачать большой файл {photo.name}")
        available_photos.remove(photo)
        return False

    # Проверяем, что файл существует после скачивания
    if not os.path.exists(dst + photo.name):
        print(f"Файл {photo.name} не найден после скачивания")
        available_photos.remove(photo)
        return False

    temp_compressed = dst + "compressed.jpg"

    # Обработка HEIC файлов
    if photo.name.lower().endswith(".heic"):
        print(f"Обнаружен большой HEIC файл: {photo.name}")
        try:
            import pillow_heif

            pillow_heif.register_heif_opener()

            with Image.open(dst + photo.name) as my_image:
                if my_image.mode != "RGB":
                    my_image = my_image.convert("RGB")
                my_image = process_image_with_validation(
                    my_image, memorySizeRatio
                )
                my_image.save(
                    temp_compressed, "JPEG", quality=85, optimize=True
                )

            bot.send_photo(
                chat_id, open(temp_compressed, "rb"), caption=comment
            )
            # Отправка успешна - удаляем файлы
            os.remove(dst + photo.name)
            os.remove(temp_compressed)
            return True

        except ImportError:
            print("pillow-heif не установлен, пропускаем HEIC файл")
            bot.send_message(
                chat_id, f"Формат HEIC не поддерживается: {comment}"
            )
            if os.path.exists(temp_compressed):
                os.remove(temp_compressed)
            available_photos.remove(photo)
            return False
        except Exception as e:
            print(f"Ошибка при обработке HEIC файла: {str(e)}")
            bot.send_message(
                chat_id, f"Ошибка обработки изображения: {comment}"
            )
            if os.path.exists(temp_compressed):
                os.remove(temp_compressed)
            available_photos.remove(photo)
            return False
    else:
        # Обычная обработка для поддерживаемых форматов
        try:
            with Image.open(dst + photo.name) as my_image:
                my_image = process_image_with_validation(
                    my_image, memorySizeRatio
                )
                my_image.save(temp_compressed, quality=85, optimize=True)

            bot.send_photo(
                chat_id, open(temp_compressed, "rb"), caption=comment
            )
            # Отправка успешна - удаляем файлы
            os.remove(dst + photo.name)
            os.remove(temp_compressed)
            return True
        except Exception as e:
            print(f"Ошибка при обработке изображения: {str(e)}")
            bot.send_message(chat_id, f"Изображение повреждено: {comment}")
            if os.path.exists(temp_compressed):
                os.remove(temp_compressed)
            available_photos.remove(photo)
            return False


def try_send_small_image(chat_id, photo, comment, available_photos):
    """
    Пытается отправить небольшое изображение (< 5MB)
    Возвращает True если успешно отправлено, False если нужно попробовать другой файл
    """
    temp_heic = dst + "heic_converted.jpg"
    temp_validated = dst + "validated.jpg"

    try:
        # Проверяем успешность скачивания
        if not downloadFile(photo.file, photo.name, photo.path):
            print(f"Не удалось скачать файл {photo.name}")
            bot.send_message(
                chat_id, f"Не удалось скачать изображение: {comment}"
            )
            available_photos.remove(photo)
            return False

        # Проверяем, что файл существует после скачивания
        if not os.path.exists(dst + photo.name):
            print(f"Файл {photo.name} не найден после скачивания")
            bot.send_message(
                chat_id, f"Изображение повреждено при загрузке: {comment}"
            )
            available_photos.remove(photo)
            return False

        # Проверяем, является ли файл HEIC
        if photo.name.lower().endswith(".heic"):
            print(f"Обнаружен небольшой HEIC файл: {photo.name}")
            try:
                import pillow_heif

                pillow_heif.register_heif_opener()

                with Image.open(dst + photo.name) as heic_image:
                    if heic_image.mode != "RGB":
                        heic_image = heic_image.convert("RGB")
                    validated_img = apply_size_validation(heic_image)
                    validated_img.save(
                        temp_heic, "JPEG", quality=85, optimize=True
                    )

                bot.send_photo(chat_id, open(temp_heic, "rb"), caption=comment)
                # Отправка успешна - удаляем файлы
                os.remove(temp_heic)
                os.remove(dst + photo.name)
                return True

            except ImportError:
                print("pillow-heif не установлен, пропускаем HEIC файл")
                bot.send_message(
                    chat_id, f"Формат HEIC не поддерживается: {comment}"
                )
                available_photos.remove(photo)
                return False
            except Exception as e:
                print(f"Ошибка при обработке HEIC файла: {str(e)}")
                bot.send_message(chat_id, f"Ошибка обработки HEIC: {comment}")
                if os.path.exists(temp_heic):
                    os.remove(temp_heic)
                available_photos.remove(photo)
                return False
        else:
            # Используем нашу функцию валидации для обычных форматов
            if validate_and_fix_image(dst + photo.name, temp_validated):
                # Изображение было исправлено
                bot.send_photo(
                    chat_id, open(temp_validated, "rb"), caption=comment
                )
                os.remove(temp_validated)
                os.remove(dst + photo.name)
                return True
            else:
                # Изображение корректно, отправляем локальный файл
                with open(dst + photo.name, "rb") as f:
                    bot.send_photo(chat_id, f, caption=comment)
                os.remove(dst + photo.name)
                return True

    except Exception as e:
        print(f"Ошибка при проверке размеров изображения: {str(e)}")
        # Удаляем только временные файлы если они были созданы
        if os.path.exists(temp_heic):
            os.remove(temp_heic)
        if os.path.exists(temp_validated):
            os.remove(temp_validated)

        # Fallback - пытаемся отправить локальный файл как есть
        if not photo.name.lower().endswith(".heic"):
            try:
                with open(dst + photo.name, "rb") as f:
                    bot.send_photo(chat_id, f, caption=comment)
                os.remove(dst + photo.name)
                return True
            except Exception as fallback_e:
                print(f"Не удалось отправить изображение: {str(fallback_e)}")
                bot.send_message(
                    chat_id, f"Изображение слишком большое: {comment}"
                )
        else:
            bot.send_message(
                chat_id, f"Формат HEIC не поддерживается: {comment}"
            )

        available_photos.remove(photo)
        return False


def try_send_video(chat_id, photo, comment, available_photos):
    """
    Пытается отправить видео
    Возвращает True если успешно отправлено, False если нужно попробовать другой файл
    """
    # Проверяем успешность скачивания видео
    if not downloadFile(photo.file, photo.name, photo.path):
        print(f"Не удалось скачать видео файл {photo.name}")
        bot.send_message(chat_id, f"Не удалось скачать видео: {comment}")
        available_photos.remove(photo)
        return False

    # Проверяем, что файл существует после скачивания
    if not os.path.exists(dst + photo.name):
        print(f"Видео файл {photo.name} не найден после скачивания")
        bot.send_message(chat_id, f"Видео повреждено при загрузке: {comment}")
        available_photos.remove(photo)
        return False

    try:
        bot.send_video(chat_id, open(dst + photo.name, "rb"), caption=comment)
        # Отправка успешна - удаляем файл
        os.remove(dst + photo.name)
        return True
    except Exception as video_e:
        print(f"Ошибка при отправке видео: {str(video_e)}")
        bot.send_message(
            chat_id, f"Видео слишком большое для отправки: {comment}"
        )
        available_photos.remove(photo)
        return False


@bot.message_handler(commands=["start", "hello"])
def send_welcome(message):
    # Проверяем, из какого чата пришла команда
    chat_id = str(message.chat.id)
    configured_chat_ids = [
        id.strip() for id in credentials.chat_ids.split(",")
    ]

    # Выбираем стратегию поиска в зависимости от чата
    if chat_id in configured_chat_ids:
        print(f"Команда из настроенного чата {chat_id} - ищем случайные файлы")
        search_by_date = False
    else:
        print(f"Команда из стороннего чата {chat_id} - ищем файлы по дате")
        search_by_date = True

    # Выполняем поиск файлов с выбранной стратегией
    print("Начинаем поиск доступных фотографий...")
    available_photos = find_available_photos(search_by_date)

    if not available_photos:
        # Если не найдено ни одного файла, отправляем сообщение в чат, откуда пришла команда
        bot.send_message(
            chat_id,
            "Извините, не удалось найти фотографии из-за проблем с соединением или их отсутствия.",
        )
        return

    print(f"Найдено {len(available_photos)} доступных фотографий")

    # Пытаемся отправить фото, перебирая доступные до успешной отправки
    max_attempts = 10  # Ограничиваем количество попыток
    attempts = 0

    while attempts < max_attempts:
        attempts += 1

        # Проверяем, остались ли доступные фото
        if not available_photos:
            bot.send_message(
                chat_id, "Закончились доступные фотографии для отправки."
            )
            return

        # Выбираем случайное фото из доступных
        photo = random.choice(available_photos)

        # Проверяем, что photo не None
        if photo is None:
            if photo in available_photos:
                available_photos.remove(photo)
            continue

        print(f"Попытка {attempts}: Sending {photo.file}")

        # Генерируем подпись для фото
        comment = generate_photo_caption(photo)

        try:
            # Обрабатываем в зависимости от типа медиа
            photo_size_mb = (photo.size / 1000) / 1024
            success = False

            if photo.media_type == "image":
                if photo_size_mb >= 5:
                    # Большое изображение
                    success = try_send_large_image(
                        chat_id, photo, comment, available_photos
                    )
                else:
                    # Небольшое изображение
                    success = try_send_small_image(
                        chat_id, photo, comment, available_photos
                    )
            elif photo.media_type == "video":
                # Видео
                success = try_send_video(
                    chat_id, photo, comment, available_photos
                )

            # Если отправка успешна, выходим из цикла попыток
            if success:
                return

        except Exception as exc:
            exceptionText = getattr(exc, "description", str(exc))
            print(f"Ошибка при отправке файла: {exceptionText}")
            # Убираем проблемный файл из списка доступных
            if photo in available_photos:
                available_photos.remove(photo)
            # Продолжаем цикл для следующей попытки
            continue

    # Если все попытки исчерпаны
    bot.send_message(
        chat_id, "Не удалось отправить фотографию после нескольких попыток."
    )


@bot.message_handler(commands=["stop"])
def stop_bot(message):
    """Команда для остановки бота"""

    # Проверяем, что команда пришла от разрешенного чата
    chat_id = str(message.chat.id)
    configured_chat_ids = [
        id.strip() for id in credentials.chat_ids.split(",")
    ]
    
    if chat_id in configured_chat_ids:
        print(f"🛑 Получена команда остановки от разрешенного чата {chat_id}")
        bot.send_message(chat_id, "🛑 Останавливаю бота...")
        shutdown_event.set()

        # Выходим из процесса
        import sys

        sys.exit(0)
    else:
        print(f"❌ Попытка остановки от неразрешенного чата {chat_id}")
        bot.send_message(chat_id, "❌ У вас нет прав для остановки бота")


@bot.message_handler(content_types=["video"])
def echo_video(message):
    """Обработчик видео - загружает видео и предлагает выбрать папку"""
    try:
        # Сохраняем контекст сообщения
        chat_id = message.chat.id
        message_context[chat_id] = {
            "text": message.caption if message.caption else "",
        }

        file = bot.get_file_url(message.video.file_id)
        recievingFile(file, message)

    except Exception as exc:
        exceptionText = getattr(exc, "description", str(exc))
        bot.reply_to(message, "Не вышло: " + exceptionText)


@bot.message_handler(content_types=["image", "photo"])
def echo_photo(message):
    """Обработчик фото - загружает все фото из сообщения и предлагает выбрать папку"""
    try:
        # Сохраняем контекст сообщения (текст/подпись)
        chat_id = message.chat.id
        message_context[chat_id] = {
            "text": message.caption if message.caption else "",
        }

        # Если в сообщении несколько фото, обрабатываем все
        if hasattr(message, "photo") and message.photo:
            # Берем фото лучшего качества (последнее в списке)
            file = bot.get_file_url(message.photo[-1].file_id)
            recievingFile(file, message)
        else:
            bot.reply_to(message, "Не удалось найти изображение в сообщении")

    except Exception as exc:
        exceptionText = getattr(exc, "description", str(exc))
        bot.reply_to(message, "Не вышло: " + exceptionText)


@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    print(message.text)
    if "да" == message.text:
        bot.reply_to(message, "хуй на")

    if "300" == message.text:
        bot.reply_to(message, "Отсоси у тракториста")

    # bot.reply_to(message, message.text)


@bot.message_handler(commands=["test"])
def echo_test(message):
    print("TEST: " + message.text)
    # bot.send_animation()


def process_image_with_validation(my_image, memorySizeRatio):
    """
    Обрабатывает изображение: поворот по EXIF, валидация размеров, сжатие
    """
    # Обработка EXIF для поворота
    if hasattr(my_image, "_getexif"):
        exif = my_image._getexif()
        if exif:
            for tag, label in ExifTags.TAGS.items():
                if label == "Orientation":
                    orientation = tag
                    break
            if orientation in exif:
                if exif[orientation] == 3:
                    my_image = my_image.rotate(180, expand=True)
                elif exif[orientation] == 6:
                    my_image = my_image.rotate(270, expand=True)
                elif exif[orientation] == 8:
                    my_image = my_image.rotate(90, expand=True)

    # Получаем размеры изображения
    image_height = float(my_image.height)
    image_width = float(my_image.width)

    # Проверяем размеры изображения для соответствия требованиям Telegram
    max_dimension = 10000
    min_dimension = 1

    # Проверяем максимальные размеры
    if image_width > max_dimension or image_height > max_dimension:
        scale_factor = min(
            max_dimension / image_width, max_dimension / image_height
        )
        new_width = int(image_width * scale_factor)
        new_height = int(image_height * scale_factor)
        print(
            f"Уменьшаем изображение с {int(image_width)}x{int(image_height)} до {new_width}x{new_height}"
        )
        my_image = my_image.resize((new_width, new_height), Image.LANCZOS)
        image_width = float(new_width)
        image_height = float(new_height)

    # Проверяем минимальные размеры
    if image_width < min_dimension or image_height < min_dimension:
        new_width = max(int(image_width), min_dimension)
        new_height = max(int(image_height), min_dimension)
        print(
            f"Увеличиваем изображение с {int(image_width)}x{int(image_height)} до {new_width}x{new_height}"
        )
        my_image = my_image.resize((new_width, new_height), Image.LANCZOS)
        image_width = float(new_width)
        image_height = float(new_height)

    # Проверяем соотношение сторон (не более чем 20:1)
    aspect_ratio = max(image_width / image_height, image_height / image_width)
    if aspect_ratio > 20:
        if image_width > image_height:
            new_width = int(image_height * 20)
            new_height = int(image_height)
        else:
            new_width = int(image_width)
            new_height = int(image_width * 20)
        print(
            f"Корректируем соотношение сторон с {int(image_width)}x{int(image_height)} до {new_width}x{new_height}"
        )
        my_image = my_image.resize((new_width, new_height), Image.LANCZOS)
        image_width = float(new_width)
        image_height = float(new_height)

    # Сжимаем изображение
    my_image = my_image.resize(
        (
            int(image_width / (2 * memorySizeRatio)),
            int(image_height / (2 * memorySizeRatio)),
        ),
        Image.LANCZOS,
    )

    # Финальная проверка размеров после сжатия
    final_width, final_height = my_image.size
    if final_width < 1 or final_height < 1:
        print(
            f"Размеры после сжатия слишком малы: {final_width}x{final_height}, устанавливаем минимальные"
        )
        my_image = my_image.resize(
            (max(final_width, 1), max(final_height, 1)), Image.LANCZOS
        )

    print(
        f"Итоговые размеры изображения: {my_image.size[0]}x{my_image.size[1]}"
    )
    return my_image


def validate_and_fix_image(image_path, output_path):
    """
    Проверяет и исправляет размеры изображения для соответствия требованиям Telegram
    Поддерживает конвертацию HEIC файлов в JPEG
    """
    try:
        # Проверяем, является ли файл HEIC
        if image_path.lower().endswith(".heic"):
            print(f"Обнаружен HEIC файл: {image_path}")
            try:
                # Пытаемся использовать pillow-heif для чтения HEIC
                import pillow_heif

                pillow_heif.register_heif_opener()

                with Image.open(image_path) as img:
                    # Конвертируем в RGB если необходимо
                    if img.mode != "RGB":
                        img = img.convert("RGB")

                    width, height = img.size
                    print(
                        f"HEIC изображение успешно открыто: {width}x{height}"
                    )

                    # Применяем валидацию размеров
                    validated_img = apply_size_validation(img)

                    # Сохраняем как JPEG
                    validated_img.save(
                        output_path, "JPEG", quality=85, optimize=True
                    )
                    print(f"HEIC конвертирован в JPEG: {output_path}")
                    return True

            except ImportError:
                print(
                    "pillow-heif не установлен, пытаемся альтернативный метод"
                )
                # Альтернативный метод - пропускаем файл
                print(f"Пропускаем HEIC файл (нет поддержки): {image_path}")
                return False
            except Exception as e:
                print(f"Ошибка при обработке HEIC файла: {str(e)}")
                return False

        # Обычная обработка для других форматов
        with Image.open(image_path) as img:
            width, height = img.size
            print(f"Исходные размеры: {width}x{height}")

            validated_img = apply_size_validation(img)

            if validated_img != img:  # Если изображение было изменено
                validated_img.save(output_path, quality=85, optimize=True)
                print(
                    f"Изображение сохранено с размерами: {validated_img.size[0]}x{validated_img.size[1]}"
                )
                return True
            else:
                print("Размеры изображения корректны")
                return False

    except Exception as e:
        print(f"Ошибка при валидации изображения: {str(e)}")
        return False


def apply_size_validation(img):
    """
    Применяет валидацию размеров к изображению PIL
    """
    width, height = img.size
    max_dimension = 10000
    min_dimension = 1

    # Проверяем максимальные размеры
    if width > max_dimension or height > max_dimension:
        scale_factor = min(max_dimension / width, max_dimension / height)
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        print(
            f"Уменьшаем изображение с {width}x{height} до {new_width}x{new_height}"
        )
        return img.resize((new_width, new_height), Image.LANCZOS)

    # Проверяем минимальные размеры
    if width < min_dimension or height < min_dimension:
        new_width = max(width, min_dimension)
        new_height = max(height, min_dimension)
        print(
            f"Увеличиваем изображение с {width}x{height} до {new_width}x{new_height}"
        )
        return img.resize((new_width, new_height), Image.LANCZOS)

    # Проверяем соотношение сторон
    aspect_ratio = max(width / height, height / width)
    if aspect_ratio > 20:
        if width > height:
            new_width = int(height * 20)
            new_height = height
        else:
            new_width = width
            new_height = int(width * 20)
        print(
            f"Корректируем соотношение сторон с {width}x{height} до {new_width}x{new_height}"
        )
        return img.resize((new_width, new_height), Image.LANCZOS)

    return img


def send_image_file(chat_id, photo, comment):
    """Отправляет изображение в чат"""
    file_path = None
    temp_file = None
    try:
        # Скачиваем файл
        if not downloadFile(photo.file, photo.name, photo.path):
            print(f"Не удалось скачать файл {photo.name}")
            return False

        # Проверяем что файл существует
        file_path = dst + photo.name
        if not os.path.exists(file_path):
            print(f"Файл {photo.name} не найден после скачивания")
            return False

        # Проверяем размер файла
        photoSizeMb = (photo.size / 1000) / 1024

        # Для больших файлов применяем сжатие
        if photoSizeMb >= 5:
            memorySizeRatio = 5 / photoSizeMb

            # Обработка HEIC файлов
            if photo.name.lower().endswith(".heic"):
                try:
                    import pillow_heif

                    pillow_heif.register_heif_opener()

                    temp_file = dst + "compressed.jpg"
                    with Image.open(file_path) as my_image:
                        if my_image.mode != "RGB":
                            my_image = my_image.convert("RGB")
                        my_image = process_image_with_validation(
                            my_image, memorySizeRatio
                        )
                        my_image.save(
                            temp_file,
                            "JPEG",
                            quality=85,
                            optimize=True,
                        )
                        bot.send_photo(
                            chat_id,
                            open(temp_file, "rb"),
                            caption=comment,
                        )
                    # Отправка успешна - удаляем файлы
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    os.remove(file_path)
                    return True
                except Exception as e:
                    print(f"Ошибка при обработке HEIC: {str(e)}")
                    # Удаляем только временный файл, оригинал оставляем для диагностики
                    if temp_file and os.path.exists(temp_file):
                        os.remove(temp_file)
                    return False
            else:
                # Обычные изображения
                try:
                    temp_file = dst + "compressed.jpg"
                    with Image.open(file_path) as my_image:
                        my_image = process_image_with_validation(
                            my_image, memorySizeRatio
                        )
                        my_image.save(temp_file, quality=85, optimize=True)
                        bot.send_photo(
                            chat_id,
                            open(temp_file, "rb"),
                            caption=comment,
                        )
                    # Отправка успешна - удаляем файлы
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    os.remove(file_path)
                    return True
                except Exception as e:
                    print(f"Ошибка при сжатии изображения: {str(e)}")
                    # Удаляем только временный файл, оригинал оставляем для диагностики
                    if temp_file and os.path.exists(temp_file):
                        os.remove(temp_file)
                    return False
        else:
            # Небольшие файлы отправляем напрямую
            if photo.name.lower().endswith(".heic"):
                try:
                    import pillow_heif

                    pillow_heif.register_heif_opener()

                    temp_file = dst + "heic_converted.jpg"
                    with Image.open(file_path) as heic_image:
                        if heic_image.mode != "RGB":
                            heic_image = heic_image.convert("RGB")
                        validated_img = apply_size_validation(heic_image)
                        validated_img.save(
                            temp_file,
                            "JPEG",
                            quality=85,
                            optimize=True,
                        )
                        bot.send_photo(
                            chat_id,
                            open(temp_file, "rb"),
                            caption=comment,
                        )
                    # Отправка успешна - удаляем файлы
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    os.remove(file_path)
                    return True
                except Exception as e:
                    print(f"Ошибка при конвертации HEIC: {str(e)}")
                    # Удаляем только временный файл, оригинал оставляем для диагностики
                    if temp_file and os.path.exists(temp_file):
                        os.remove(temp_file)
                    return False
            else:
                # Пытаемся отправить локальный файл
                try:
                    with open(file_path, "rb") as f:
                        bot.send_photo(chat_id, f, caption=comment)
                    # Отправка успешна - удаляем файл
                    os.remove(file_path)
                    return True
                except:
                    # Если не получилось, валидируем и пробуем снова
                    temp_file = dst + "validated.jpg"
                    try:
                        if validate_and_fix_image(file_path, temp_file):
                            bot.send_photo(
                                chat_id,
                                open(temp_file, "rb"),
                                caption=comment,
                            )
                            # Отправка успешна - удаляем файлы
                            os.remove(temp_file)
                            os.remove(file_path)
                            return True
                        else:
                            # В крайнем случае пробуем отправить как есть
                            with open(file_path, "rb") as f:
                                bot.send_photo(chat_id, f, caption=comment)
                            # Отправка успешна - удаляем файл
                            os.remove(file_path)
                            return True
                    except Exception as e:
                        print(f"Ошибка при отправке после валидации: {str(e)}")
                        # Удаляем только временный файл, оригинал оставляем для диагностики
                        if temp_file and os.path.exists(temp_file):
                            os.remove(temp_file)
                        return False

    except Exception as e:
        print(f"Ошибка при отправке изображения: {str(e)}")
        # Не удаляем file_path - оставляем для диагностики
        # Удаляем только временные файлы
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
        return False


def send_video_file(chat_id, photo, comment):
    """Отправляет видео в чат"""
    file_path = None
    try:
        # Скачиваем видео файл
        if not downloadFile(photo.file, photo.name, photo.path):
            print(f"Не удалось скачать видео {photo.name}")
            return False

        file_path = dst + photo.name
        if not os.path.exists(file_path):
            print(f"Видео файл {photo.name} не найден после скачивания")
            return False

        try:
            bot.send_video(chat_id, open(file_path, "rb"), caption=comment)
            # Отправка успешна - удаляем файл
            os.remove(file_path)
            return True
        except Exception as e:
            print(f"Ошибка при отправке видео: {str(e)}")
            # Не удаляем файл - оставляем для диагностики
            return False

    except Exception as e:
        print(f"Ошибка при обработке видео: {str(e)}")
        # Не удаляем файл - оставляем для диагностики
        return False


def scheduled_photo_sender():
    """Отправляет фото по расписанию во все настроенные чаты"""
    try:
        current_time = datetime.now()
        print(
            f"📸 Запуск автоматической отправки фото по расписанию в {current_time.strftime('%d/%m/%Y %H:%M:%S')} (локальное время)"
        )

        # Получаем список настроенных чатов
        configured_chats = credentials.chat_ids.split(",")
        configured_chats = [chat.strip() for chat in configured_chats]

        if not configured_chats:
            print("Не найдено настроенных чатов для отправки")
            return

        print(
            f"Найдено {len(configured_chats)} настроенных чатов: {configured_chats}"
        )

        # Ищем фотографии по дате (тот же день и месяц любого года)
        print("Поиск фотографий для текущей даты...")
        available_photos = find_available_photos(search_by_date=True)

        if not available_photos:
            print(
                "Не найдено подходящих фотографий для отправки по расписанию"
            )
            return

        print(f"Найдено {len(available_photos)} подходящих фотографий")

        # Отправляем разные фото в каждый чат
        for chat_id in configured_chats:
            if not available_photos:
                print(f"Закончились доступные фото для чата {chat_id}")
                break

            # Выбираем случайное фото из доступных
            photo = random.choice(available_photos)
            available_photos.remove(photo)  # Убираем чтобы не повторяться

            print(f"Отправка фото {photo.name} в чат {chat_id}")

            try:
                # Формируем комментарий
                photo_path_splited = photo.path.split("/")
                if photo.photoslice_time is None:
                    comment = (
                        "Это "
                        + photo_path_splited[len(photo_path_splited) - 2]
                    )
                else:
                    today = date.today()
                    photo_date = photo.photoslice_time.date()

                    if (
                        photo_date.day == today.day
                        and photo_date.month == today.month
                        and photo_date.year == today.year
                    ):
                        comment = (
                            "Это %s. Произошло сегодня!"
                            % photo_path_splited[len(photo_path_splited) - 2]
                        )
                    elif (
                        photo_date.day == today.day
                        and photo_date.month == today.month
                    ):
                        comment = "Это %s. Дело было в этот день в %s году" % (
                            photo_path_splited[len(photo_path_splited) - 2],
                            photo.photoslice_time.year,
                        )
                    else:
                        comment = "Это %s. Дело было в %s %s года" % (
                            photo_path_splited[len(photo_path_splited) - 2],
                            numberToMonthNameRu(photo.photoslice_time.month),
                            photo.photoslice_time.year,
                        )

                # Отправляем файл
                success = False
                if photo.media_type == "image":
                    success = send_image_file(chat_id, photo, comment)
                elif photo.media_type == "video":
                    success = send_video_file(chat_id, photo, comment)

                if success:
                    print(f"✅ Успешно отправлено в чат {chat_id}")
                else:
                    print(f"❌ Не удалось отправить в чат {chat_id}")

            except Exception as e:
                print(f"❌ Ошибка при отправке в чат {chat_id}: {str(e)}")
                continue

        completion_time = datetime.now()
        print(
            f"✅ Завершена автоматическая отправка фото по расписанию в {completion_time.strftime('%H:%M:%S')} (локальное время)"
        )

    except Exception as e:
        print(f"❌ Ошибка в scheduled_photo_sender: {str(e)}")


def schedule_first_photo():
    """Планирует первую отправку фото через несколько минут (для быстрого тестирования)"""
    skip_time_minutes = randrange(1, 6)  # От 1 до 5 минут для первой отправки
    now = datetime.now()
    next_time = now + timedelta(minutes=skip_time_minutes)

    print(f"🚀 Планирование ПЕРВОЙ отправки через {skip_time_minutes} минут")
    print(
        f"   Первая отправка запустится в {next_time.strftime('%d/%m/%Y %H:%M:%S')} (локальное время)"
    )

    # Создаем задачу в планировщике (время в секундах)
    schedule.enter(
        skip_time_minutes * 60, 1, scheduled_photo_sender_with_reschedule, ()
    )


def schedule_next_photo():
    """Планирует следующую отправку фото через случайное количество часов"""
    skip_time = randrange(1, 14)  # От 1 до 13 часов
    now = datetime.now()
    next_time = now + timedelta(hours=skip_time)

    print(f"⏰ Планирование следующей отправки через {skip_time} часов")
    print(
        f"   Следующая отправка запустится в {next_time.strftime('%d/%m/%Y %H:%M:%S')} (локальное время)"
    )

    # Создаем задачу в планировщике
    schedule.enter(
        skip_time * 3600, 1, scheduled_photo_sender_with_reschedule, ()
    )


def scheduled_photo_sender_with_reschedule():
    """Отправляет фото и автоматически планирует следующую отправку"""
    # Выводим время запуска текущей задачи
    current_time = datetime.now()
    print(
        f"🕐 Запуск запланированной отправки в {current_time.strftime('%d/%m/%Y %H:%M:%S')} (локальное время)"
    )

    scheduled_photo_sender()
    schedule_next_photo()


def run_scheduler():
    """Запускает планировщик в отдельном потоке"""
    try:
        print("✅ Планировщик задач запущен в фоновом потоке")
        schedule.run()
    except Exception as e:
        print(f"❌ Ошибка в планировщике: {str(e)}")


def recievingFile(fileLink, message):
    """Загружает файл из Telegram и предлагает выбрать папку для загрузки на Яндекс Диск"""
    fileName = fileLink.split("/")[-1]

    downloadResponse = requests.get(fileLink)

    if downloadResponse.status_code == 200:
        # Убеждаемся, что папка назначения существует
        os.makedirs(dst, exist_ok=True)

        filePath = dst + fileName

        with open(filePath, "wb") as file:
            file.write(downloadResponse.content)

        # Получаем последнюю обновленную папку
        lastFolder = getLastUpdatedFolder()
        print(f"Последняя обновленная папка: {lastFolder}")

        # Создание клавиатуры с вариантами
        markup = InlineKeyboardMarkup()

        # Вариант 1: Последняя созданная папка
        markup.add(
            InlineKeyboardButton(
                f"📁 В последнюю папку ({lastFolder})",
                callback_data=lastFolder,
            )
        )

        # Вариант 2: Новая папка с именем из текста сообщения
        chat_id = message.chat.id
        context = message_context.get(chat_id, {})
        message_text = context.get("text", "").strip()

        if message_text:
            # Ограничиваем длину текста для отображения в кнопке
            display_text = (
                message_text[:30] + "..."
                if len(message_text) > 30
                else message_text
            )
            markup.add(
                InlineKeyboardButton(
                    f"📝 Новая папка: {display_text}",
                    callback_data="new_from_text",
                )
            )

        # Вариант 3: Новая папка с названием из сегодняшней даты
        today_str = date.today().strftime("%Y-%m-%d")
        markup.add(
            InlineKeyboardButton(
                f"📅 Новая папка: {today_str}",
                callback_data="new_from_date",
            )
        )

        # Вариант 4: Новая папка со случайным именем (старое поведение)
        markup.add(
            InlineKeyboardButton(
                "🎲 Новая папка (случайное имя)",
                callback_data="new_random",
            )
        )

        # Кнопка отмены
        markup.add(InlineKeyboardButton("❌ Отмена", callback_data="decline"))

        bot.send_message(
            message.chat.id,
            "Куда сохранить файл?",
            reply_markup=markup,
        )
    else:
        print(f"Ошибка при скачивании файла: {downloadResponse.status_code}")


def schedule_checker():
    while True:
        schedule.run_pending()
        time.sleep(1)


def periodic_task():
    """Устаревшая функция для совместимости - отправляет фото по расписанию"""
    print("=" * 60)
    print(
        f"⏰ Срабатывание периодической задачи в {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )

    # Получаем список ID чатов из конфигурации
    chat_ids = [id.strip() for id in credentials.chat_ids.split(",")]
    print(f"📱 Настроено чатов для отправки: {len(chat_ids)}")

    # Отправляем фото во все настроенные чаты с правильной логикой
    scheduled_photo_sender()

    # Планируем следующий запуск через случайный интервал от 1 до 24 часов
    delay_hours = random.randint(1, 24)
    delay_seconds = delay_hours * 3600
    next_time = datetime.now() + timedelta(seconds=delay_seconds)

    print(
        f"⏰ Следующая автоматическая отправка запланирована через {delay_hours} часов"
    )
    print(
        f"   Следующая отправка в: {next_time.strftime('%d/%m/%Y %H:%M:%S')}"
    )
    print("=" * 60)

    schedule.enter(delay_seconds, 1, periodic_task)


if __name__ == "__main__":
    print("=" * 60)
    print("🤖 Запуск бота Chronica")
    print("=" * 60)

    # Планируем первую отправку через 1-5 минут
    initial_delay_seconds = random.randint(60, 300)
    now = datetime.now()
    first_send_time = now + timedelta(seconds=initial_delay_seconds)

    print(f"📅 Текущее время: {now.strftime('%d/%m/%Y %H:%M:%S')}")
    print(
        f"⏰ Первая автоматическая отправка запланирована через {initial_delay_seconds / 60:.2f} минут"
    )
    print(
        f"   Первая отправка в: {first_send_time.strftime('%d/%m/%Y %H:%M:%S')}"
    )

    schedule.enter(initial_delay_seconds, 1, periodic_task)

    # Запускаем планировщик в отдельном потоке
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("✅ Планировщик запущен в фоновом потоке")
    print("=" * 60)

    # Запускаем бота
    print("🔄 Бот запущен и ожидает сообщений...")

    try:
        # Используем infinity_polling который лучше поддерживает остановку
        bot.infinity_polling(
            timeout=10, long_polling_timeout=10, skip_pending=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Остановка по Ctrl+C...")
        shutdown_event.set()
    except Exception as e:
        if not shutdown_event.is_set():
            print(f"❌ Ошибка: {e}")
        shutdown_event.set()

    print("🔴 Бот остановлен")

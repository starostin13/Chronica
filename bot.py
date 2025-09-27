"""Главный файл бота"""
# !/usr/bin/python3.11
# -*- coding: utf-8 -*-
# vim:fileencoding=utf-8
from datetime import date, datetime, timedelta
import os
import random
import sched
import time
import threading
from random import randrange
import pytz
from PIL import Image, ExifTags
import requests
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import credentials
from yaHelper import (createFolder, downloadFile, getLastUpdatedFolder,
                      saveFileTo, find_available_photos, clear_photo_cache)
from stringHelper import numberToMonthNameRu

bot_token = credentials.bot_token
bot = telebot.TeleBot(bot_token)
dst = credentials.temp_folder
schedule = sched.scheduler(time.time, time.sleep)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    print("Answer from inline is " + call.data)
    if call.data == "new":
        newFolderName = createFolder()
    for entry in os.listdir(dst):
        if os.path.isfile(os.path.join(dst, entry)):
            if call.data == "new":
                saveFileTo(os.path.join(dst, entry),
                           newFolderName + "/" + entry)
            elif call.data != "decline":
                saveFileTo(os.path.join(dst, entry), call.data + "/" + entry)
            os.remove(os.path.join(dst, entry))


@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    # Получаем ID чата, из которого пришла команда
    chat_id = str(message.chat.id)

    # Проверяем, нужно ли искать по дате или сразу случайные файлы
    configured_chats = credentials.chat_ids.split(",")
    if chat_id in configured_chats:
        print(f"Команда из настроенного чата {chat_id} - ищем случайные файлы")
        search_by_date = False
    else:
        print(f"Команда из стороннего чата {chat_id} - ищем файлы по дате")
        search_by_date = True

    # Выполняем поиск файлов с выбранной стратегией
    print("Начинаем поиск доступных фотографий...")
    available_photos = find_available_photos(search_by_date)

    if not available_photos:
        bot.send_message(
            chat_id,
            "Не удалось найти фотографии."
        )
        return

    print(f"Найдено {len(available_photos)} доступных фотографий")

    # Пытаемся отправить фото, перебирая доступные до успешной отправки
    max_attempts = min(10, len(available_photos))
    attempts = 0

    while attempts < max_attempts and available_photos:
        attempts += 1
        try:
            photo = random.choice(available_photos)
            available_photos.remove(photo)

            if photo is None:
                continue

            print(f"Попытка {attempts}: Отправляем {photo.name}")

            # Формируем комментарий
            photo_path_splited = photo.path.split("/")
            if photo.photoslice_time is None:
                comment = "Это " + \
                    photo_path_splited[len(photo_path_splited) - 2]
            else:
                today = date.today()
                photo_date = photo.photoslice_time.date()

                if (photo_date.day == today.day and
                    photo_date.month == today.month and
                        photo_date.year == today.year):
                    comment = "Это %s. Произошло сегодня!" % photo_path_splited[len(
                        photo_path_splited) - 2]
                elif (photo_date.day == today.day and
                      photo_date.month == today.month):
                    comment = "Это %s. Дело было в этот день в %s году" % (
                        photo_path_splited[len(photo_path_splited) - 2],
                        photo.photoslice_time.year
                    )
                else:
                    comment = "Это %s. Дело было в %s %s года" % (
                        photo_path_splited[len(photo_path_splited) - 2],
                        numberToMonthNameRu(photo.photoslice_time.month),
                        photo.photoslice_time.year
                    )

            # Обрабатываем файл
            if photo.media_type == "image":
                if send_image_file(chat_id, photo, comment):
                    print(f"Успешно отправлено изображение {photo.name}")
                    return
                else:
                    print(f"Не удалось отправить изображение {photo.name}")
                    continue

            elif photo.media_type == "video":
                if send_video_file(chat_id, photo, comment):
                    print(f"Успешно отправлено видео {photo.name}")
                    return
                else:
                    print(f"Не удалось отправить видео {photo.name}")
                    continue

        except Exception as e:
            error_photo = photo.name if 'photo' in locals() else 'неизвестно'
            print(f"Ошибка при обработке файла {error_photo}: {str(e)}")
            continue

    # Если дошли до сюда, значит не смогли отправить ни один файл
    bot.send_message(
        chat_id,
        "Извините, не удалось отправить ни одного файла. Попробуйте позже."
    )


def send_image_file(chat_id, photo, comment):
    """Отправляет изображение, возвращает True при успехе"""
    try:
        photoSizeMb = ((photo.size / 1000) / 1024)

        if photoSizeMb >= 5:
            # Большой файл - нужно скачать и сжать
            memorySizeRatio = 5 / photoSizeMb

            if not downloadFile(photo.file, photo.name):
                print(f"Не удалось скачать большой файл {photo.name}")
                return False

            if not os.path.exists(dst + photo.name):
                print(f"Файл {photo.name} не найден после скачивания")
                return False

            # Обрабатываем HEIC файлы
            if photo.name.lower().endswith('.heic'):
                try:
                    import pillow_heif
                    pillow_heif.register_heif_opener()

                    with Image.open(dst + photo.name) as my_image:
                        if my_image.mode != 'RGB':
                            my_image = my_image.convert('RGB')
                        my_image = process_image_with_validation(
                            my_image, memorySizeRatio
                        )
                        my_image.save(
                            dst + 'compressed.jpg', 'JPEG',
                            quality=85, optimize=True
                        )

                    with open(dst + 'compressed.jpg', 'rb') as f:
                        bot.send_photo(chat_id, f, caption=comment)

                    os.remove(dst + photo.name)
                    os.remove(dst + 'compressed.jpg')
                    return True

                except ImportError:
                    print("pillow-heif не установлен")
                    os.remove(dst + photo.name)
                    return False
                except Exception as e:
                    print(f"Ошибка при обработке HEIC: {str(e)}")
                    if os.path.exists(dst + photo.name):
                        os.remove(dst + photo.name)
                    return False
            else:
                # Обычное изображение
                try:
                    with Image.open(dst + photo.name) as my_image:
                        my_image = process_image_with_validation(
                            my_image, memorySizeRatio
                        )
                        my_image.save(dst + 'compressed.jpg',
                                      quality=85, optimize=True)

                    with open(dst + 'compressed.jpg', 'rb') as f:
                        bot.send_photo(chat_id, f, caption=comment)

                    os.remove(dst + photo.name)
                    os.remove(dst + 'compressed.jpg')
                    return True

                except Exception as e:
                    print(f"Ошибка при обработке изображения: {str(e)}")
                    if os.path.exists(dst + photo.name):
                        os.remove(dst + photo.name)
                    return False
        else:
            # Небольшой файл
            if not downloadFile(photo.file, photo.name):
                return False

            if not os.path.exists(dst + photo.name):
                return False

            # Проверяем HEIC
            if photo.name.lower().endswith('.heic'):
                try:
                    import pillow_heif
                    pillow_heif.register_heif_opener()

                    with Image.open(dst + photo.name) as heic_image:
                        if heic_image.mode != 'RGB':
                            heic_image = heic_image.convert('RGB')
                        validated_img = apply_size_validation(heic_image)
                        validated_img.save(
                            dst + 'heic_converted.jpg', 'JPEG',
                            quality=85, optimize=True
                        )

                    with open(dst + 'heic_converted.jpg', 'rb') as f:
                        bot.send_photo(chat_id, f, caption=comment)

                    os.remove(dst + photo.name)
                    os.remove(dst + 'heic_converted.jpg')
                    return True

                except ImportError:
                    print("pillow-heif не установлен")
                    os.remove(dst + photo.name)
                    return False
                except Exception as e:
                    print(f"Ошибка при обработке HEIC: {str(e)}")
                    if os.path.exists(dst + photo.name):
                        os.remove(dst + photo.name)
                    return False
            else:
                # Обычное изображение небольшого размера
                try:
                    if validate_and_fix_image(dst + photo.name,
                                              dst + 'validated.jpg'):
                        with open(dst + 'validated.jpg', 'rb') as f:
                            bot.send_photo(chat_id, f, caption=comment)
                        os.remove(dst + 'validated.jpg')
                    else:
                        bot.send_photo(chat_id, photo.file, caption=comment)

                    os.remove(dst + photo.name)
                    return True

                except Exception as e:
                    print(f"Ошибка при отправке изображения: {str(e)}")
                    if os.path.exists(dst + photo.name):
                        os.remove(dst + photo.name)
                    return False
    except Exception as e:
        print(f"Общая ошибка при отправке изображения: {str(e)}")
        return False


def send_video_file(chat_id, photo, comment):
    """Отправляет видео, возвращает True при успехе"""
    try:
        if "gp3" in photo.name or "mp4" in photo.name or "avi" in photo.name:
            if not downloadFile(photo.file, photo.name):
                return False

            if not os.path.exists(dst + photo.name):
                return False

            try:
                with open(dst + photo.name, 'rb') as f:
                    bot.send_video(chat_id, f, caption=comment)
                os.remove(dst + photo.name)
                return True
            except Exception as e:
                print(f"Ошибка при отправке видео: {str(e)}")
                if os.path.exists(dst + photo.name):
                    os.remove(dst + photo.name)
                return False
        else:
            # Отправляем по ссылке
            try:
                bot.send_video(chat_id, photo.file, caption=comment)
                return True
            except Exception as e:
                print(f"Ошибка при отправке видео по ссылке: {str(e)}")
                return False
    except Exception as e:
        print(f"Общая ошибка при отправке видео: {str(e)}")
        return False


@bot.message_handler(content_types=['video'])
def echo_video(message):
    try:
        file = bot.get_file_url(message.video.file_id)
        recievingFile(file, message)
    except Exception as exc:
        exceptionText = getattr(exc, 'description', str(exc))
        bot.reply_to(message, "Не вышло: " + exceptionText)


@bot.message_handler(content_types=['image', 'photo'])
def echo_photo(message):
    try:
        file = bot.get_file_url(message.photo[-1].file_id)
        recievingFile(file, message)
    except Exception as exc:
        exceptionText = getattr(exc, 'description', str(exc))
        bot.reply_to(message, "Не вышло: " + exceptionText)


@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    print(message.text)
    if "да" == message.text:
        bot.reply_to(message, "хуй на")
    if "300" == message.text:
        bot.reply_to(message, "Отсоси у тракториста")


@bot.message_handler(commands=['test'])
def echo_test(message):
    print("TEST: " + message.text)


def process_image_with_validation(my_image, memorySizeRatio):
    """
    Обрабатывает изображение: поворот по EXIF, валидация размеров, сжатие
    """
    # Обработка EXIF для поворота
    if hasattr(my_image, '_getexif'):
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break

            exif = my_image._getexif()
            if exif is not None:
                orientation_value = exif.get(orientation)
                if orientation_value == 3:
                    my_image = my_image.rotate(180, expand=True)
                elif orientation_value == 6:
                    my_image = my_image.rotate(270, expand=True)
                elif orientation_value == 8:
                    my_image = my_image.rotate(90, expand=True)
        except (AttributeError, KeyError, TypeError):
            pass

    # Применяем валидацию размеров
    my_image = apply_size_validation(my_image)

    # Применяем сжатие если нужно
    if memorySizeRatio < 1:
        width, height = my_image.size
        new_width = int(width * memorySizeRatio)
        new_height = int(height * memorySizeRatio)
        my_image = my_image.resize((new_width, new_height), Image.LANCZOS)

    return my_image


def apply_size_validation(image):
    """Проверяет и корректирует размеры изображения для Telegram"""
    width, height = image.size
    max_dimension = 10000

    # Проверяем максимальные размеры
    if width > max_dimension or height > max_dimension:
        # Вычисляем коэффициент масштабирования
        scale_factor = min(max_dimension / width, max_dimension / height)
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        image = image.resize((new_width, new_height), Image.LANCZOS)

    return image


def validate_and_fix_image(input_path, output_path):
    """
    Проверяет изображение и исправляет его при необходимости
    Возвращает True, если изображение было исправлено и сохранено в output_path
    Возвращает False, если изображение корректно и не требует исправления
    """
    try:
        with Image.open(input_path) as img:
            fixed_img = apply_size_validation(img)

            # Проверяем, изменилось ли изображение
            if fixed_img.size != img.size:
                fixed_img.save(output_path, quality=85, optimize=True)
                return True
            else:
                return False
    except Exception as e:
        print(f"Ошибка при валидации изображения {input_path}: {str(e)}")
        return False


def scheduled_photo_sender():
    """Отправляет фото по расписанию во все настроенные чаты"""
    try:
        current_time = datetime.now()
        print(f"📸 Запуск автоматической отправки фото по расписанию в {current_time.strftime('%d/%m/%Y %H:%M:%S')} (локальное время)")
        
        # Получаем список настроенных чатов
        configured_chats = credentials.chat_ids.split(",")
        configured_chats = [chat.strip() for chat in configured_chats]
        
        if not configured_chats:
            print("Не найдено настроенных чатов для отправки")
            return
            
        print(f"Найдено {len(configured_chats)} настроенных чатов: {configured_chats}")
        
        # Ищем фотографии по дате (тот же день и месяц любого года)
        print("Поиск фотографий для текущей даты...")
        available_photos = find_available_photos(search_by_date=True)
        
        if not available_photos:
            print("Не найдено подходящих фотографий для отправки по расписанию")
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
                    comment = "Это " + photo_path_splited[len(photo_path_splited) - 2]
                else:
                    today = date.today()
                    photo_date = photo.photoslice_time.date()

                    if (photo_date.day == today.day and
                        photo_date.month == today.month and
                        photo_date.year == today.year):
                        comment = "Это %s. Произошло сегодня!" % photo_path_splited[len(photo_path_splited) - 2]
                    elif (photo_date.day == today.day and
                          photo_date.month == today.month):
                        comment = "Это %s. Дело было в этот день в %s году" % (
                            photo_path_splited[len(photo_path_splited) - 2],
                            photo.photoslice_time.year
                        )
                    else:
                        comment = "Это %s. Дело было в %s %s года" % (
                            photo_path_splited[len(photo_path_splited) - 2],
                            numberToMonthNameRu(photo.photoslice_time.month),
                            photo.photoslice_time.year
                        )

                # Отправляем файл
                success = False
                if photo.media_type == "image":
                    success = send_image_file(chat_id, photo, comment)
                elif photo.media_type == "video":
                    success = send_video_file(chat_id, photo, comment)
                    
                if success:
                    print(f"Успешно отправлено в чат {chat_id}")
                else:
                    print(f"Не удалось отправить в чат {chat_id}")
                    
            except Exception as e:
                print(f"Ошибка при отправке в чат {chat_id}: {str(e)}")
                continue
                
        completion_time = datetime.now()
        print(f"✅ Завершена автоматическая отправка фото по расписанию в {completion_time.strftime('%H:%M:%S')} (локальное время)")
        
    except Exception as e:
        print(f"Ошибка в scheduled_photo_sender: {str(e)}")


def schedule_first_photo():
    """Планирует первую отправку фото через несколько минут (для быстрого тестирования)"""
    skip_time_minutes = randrange(1, 6)  # От 1 до 5 минут для первой отправки
    now = datetime.now()
    next_time = now + timedelta(minutes=skip_time_minutes)
    
    print(f"🚀 Планирование ПЕРВОЙ отправки через {skip_time_minutes} минут")
    print(f"Первая отправка запустится в {next_time.strftime('%d/%m/%Y %H:%M:%S')} (локальное время)")
    
    # Создаем задачу в планировщике (время в секундах)
    schedule.enter(skip_time_minutes * 60, 1, scheduled_photo_sender_with_reschedule, ())


def schedule_next_photo():
    """Планирует следующую отправку фото через случайное количество часов"""
    skip_time = randrange(1, 14)  # От 1 до 13 часов
    now = datetime.now()
    next_time = now + timedelta(hours=skip_time)
    
    print(f"⏰ Планирование следующей отправки через {skip_time} часов")
    print(f"Следующая отправка запустится в {next_time.strftime('%d/%m/%Y %H:%M:%S')} (локальное время)")
    
    # Создаем задачу в планировщике
    schedule.enter(skip_time * 3600, 1, scheduled_photo_sender_with_reschedule, ())


def scheduled_photo_sender_with_reschedule():
    """Отправляет фото и автоматически планирует следующую отправку"""
    # Выводим время запуска текущей задачи
    current_time = datetime.now()
    print(f"🕐 Запуск запланированной отправки в {current_time.strftime('%d/%m/%Y %H:%M:%S')} (локальное время)")
    
    scheduled_photo_sender()
    schedule_next_photo()


def run_scheduler():
    """Запускает планировщик в отдельном потоке"""
    try:
        print("Запуск планировщика задач...")
        schedule.run()
    except Exception as e:
        print(f"Ошибка в планировщике: {str(e)}")


def recievingFile(fileLink, message):
    fileName = fileLink.split("/")[-1]

    downloadResponse = requests.get(fileLink)

    if downloadResponse.status_code == 200:
        filePath = dst + fileName

        with open(filePath, 'wb') as file:
            file.write(downloadResponse.content)

        foundedFolders = getLastUpdatedFolder()
        print(foundedFolders)

        # Создание клавиатуры
        markup = InlineKeyboardMarkup()

        for item in foundedFolders:
            markup.add(InlineKeyboardButton(item, callback_data=item))

        # Добавляем кнопку для создания новой папки
        markup.add(InlineKeyboardButton(
            "Создать новую папку", callback_data="new"))
        # Добавляем кнопку для отказа
        markup.add(InlineKeyboardButton("Отмена", callback_data="decline"))

        bot.send_message(message.chat.id, "Куда сохранить файл?",
                         reply_markup=markup)
    else:
        print(f"Ошибка при скачивании файла: {downloadResponse.status_code}")


if __name__ == '__main__':
    # Запускаем планировщик в отдельном потоке
    print("Инициализация планировщика автоматической отправки...")
    schedule_first_photo()  # Планируем первую задачу через минуты
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("Планировщик запущен в фоновом режиме")
    
    while True:
        try:
            # Очищаем кеш при запуске
            clear_photo_cache()

            print("Bot started")
            bot.polling()
        except Exception as e:
            print(f"Bot error: {str(e)}")
            time.sleep(5)  # Ждем 5 секунд перед перезапуском

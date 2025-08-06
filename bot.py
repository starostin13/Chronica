#!/usr/bin/python3.11
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fileencoding=utf-8
from datetime import datetime, timedelta, date
import os
from random import randrange
import random
from PIL import Image, ExifTags
import sched
import time
from threading import Thread
import PIL
import requests
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import credentials
from yaHelper import createFolder, downloadFile, getLastUpdatedFolder, getPhoto, saveFileTo, find_available_photos, clear_photo_cache
from stringHelper import numberToMonthNameRu
import shutil

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
                saveFileTo(os.path.join(dst, entry), newFolderName + "/" + entry)
            elif call.data != "decline":
                saveFileTo(os.path.join(dst, entry), call.data + "/" + entry)
            os.remove(os.path.join(dst, entry))


@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    # Выполняем поиск файлов один раз для всех чатов
    print("Начинаем поиск доступных фотографий...")
    available_photos = find_available_photos()
    
    if not available_photos:
        # Если не найдено ни одного файла, отправляем сообщение во все чаты
        for chat_id in credentials.chat_ids.split(","):
            bot.send_message(chat_id, "Извините, не удалось найти фотографии из-за проблем с соединением или их отсутствия.")
        return
    
    print(f"Найдено {len(available_photos)} доступных фотографий")
    
    # Теперь отправляем случайные фото в каждый чат
    for chat_id in credentials.chat_ids.split(","):
        try:
            # Выбираем случайное фото из доступных
            photo = random.choice(available_photos)
            
            # Проверяем, что photo не None
            if photo is None:
                bot.send_message(chat_id, "Извините, не удалось получить фото из-за проблем с соединением. Попробуйте позже.")
                continue

            print("Sending " + photo.file)
            photo_path_splited = photo.path.split("/")
            if photo.photoslice_time is None:
                comment = "Это " + photo_path_splited[len(photo_path_splited) - 2]
            else:
                from datetime import date
                today = date.today()
                photo_date = photo.photoslice_time.date()
                
                # Проверяем, совпадает ли дата фото с сегодняшним днем и месяцем
                if (photo_date.day == today.day and 
                    photo_date.month == today.month and 
                    photo_date.year == today.year):
                    comment = "Это %s. Произошло сегодня!" % photo_path_splited[len(photo_path_splited) - 2]
                elif (photo_date.day == today.day and 
                      photo_date.month == today.month):
                    comment = "Это %s. Дело было в этот день в %s году" % (photo_path_splited[len(photo_path_splited) - 2], photo.photoslice_time.year)
                else:
                    comment = "Это %s. Дело было в %s %s года" % (photo_path_splited[len(photo_path_splited) - 2], numberToMonthNameRu(photo.photoslice_time.month), photo.photoslice_time.year)

            photoSizeMb = ((photo.size / 1000) / 1024)
            if photo.media_type == "image":
                if photoSizeMb  >= 5:
                    memorySizeRatio = 5 / photoSizeMb
                    
                    # Проверяем успешность скачивания
                    if not downloadFile(photo.file, photo.name):
                        print(f"Не удалось скачать большой файл {photo.name}")
                        bot.send_message(chat_id, f"Не удалось скачать изображение (проблемы с сетью): {comment}")
                        continue
                    
                    # Проверяем, что файл существует после скачивания
                    if not os.path.exists(dst + photo.name):
                        print(f"Файл {photo.name} не найден после скачивания")
                        bot.send_message(chat_id, f"Изображение повреждено при загрузке: {comment}")
                        continue
                    
                    # Проверяем формат файла
                    if photo.name.lower().endswith('.heic'):
                        print(f"Обнаружен большой HEIC файл: {photo.name}")
                        try:
                            import pillow_heif
                            pillow_heif.register_heif_opener()
                            
                            with Image.open(dst + photo.name) as my_image:
                                # Конвертируем в RGB если необходимо
                                if my_image.mode != 'RGB':
                                    my_image = my_image.convert('RGB')
                                
                                # Применяем обработку EXIF и изменение размеров
                                my_image = process_image_with_validation(my_image, memorySizeRatio)
                                
                                # Сохраняем как JPEG
                                my_image.save(dst + 'compressed.jpg', 'JPEG', quality=85, optimize=True)
                                bot.send_photo(chat_id, open(dst + 'compressed.jpg', 'rb'), caption = comment)
                                os.remove(dst + photo.name)
                                os.remove(dst + 'compressed.jpg')
                                
                        except ImportError:
                            print("pillow-heif не установлен, пропускаем HEIC файл")
                            bot.send_message(chat_id, f"Формат HEIC не поддерживается: {comment}")
                            os.remove(dst + photo.name)
                        except Exception as e:
                            print(f"Ошибка при обработке HEIC файла: {str(e)}")
                            bot.send_message(chat_id, f"Ошибка обработки изображения: {comment}")
                            os.remove(dst + photo.name)
                    else:
                        # Обычная обработка для поддерживаемых форматов
                        try:
                            with Image.open(dst + photo.name) as my_image:
                                my_image = process_image_with_validation(my_image, memorySizeRatio)
                                my_image.save(dst + 'compressed.jpg', quality=85, optimize=True)
                                bot.send_photo(chat_id, open(dst + 'compressed.jpg', 'rb'), caption = comment)
                                os.remove(dst + photo.name)
                                os.remove(dst + 'compressed.jpg')
                        except Exception as e:
                            print(f"Ошибка при обработке изображения: {str(e)}")
                            bot.send_message(chat_id, f"Изображение повреждено: {comment}")
                            os.remove(dst + photo.name)
                else:
                    # Для небольших файлов тоже проверяем размеры перед отправкой
                    try:
                        # Проверяем успешность скачивания
                        if not downloadFile(photo.file, photo.name):
                            print(f"Не удалось скачать файл {photo.name}")
                            bot.send_message(chat_id, f"Не удалось скачать изображение: {comment}")
                            continue
                        
                        # Проверяем, что файл существует после скачивания
                        if not os.path.exists(dst + photo.name):
                            print(f"Файл {photo.name} не найден после скачивания")
                            bot.send_message(chat_id, f"Изображение повреждено при загрузке: {comment}")
                            continue
                        
                        # Проверяем, является ли файл HEIC
                        if photo.name.lower().endswith('.heic'):
                            print(f"Обнаружен небольшой HEIC файл: {photo.name}")
                            try:
                                import pillow_heif
                                pillow_heif.register_heif_opener()
                                
                                with Image.open(dst + photo.name) as heic_image:
                                    # Конвертируем в RGB если необходимо
                                    if heic_image.mode != 'RGB':
                                        heic_image = heic_image.convert('RGB')
                                    
                                    # Применяем валидацию размеров
                                    validated_img = apply_size_validation(heic_image)
                                    
                                    # Сохраняем как JPEG
                                    validated_img.save(dst + 'heic_converted.jpg', 'JPEG', quality=85, optimize=True)
                                    bot.send_photo(chat_id, open(dst + 'heic_converted.jpg', 'rb'), caption = comment)
                                    os.remove(dst + 'heic_converted.jpg')
                                    
                            except ImportError:
                                print("pillow-heif не установлен, пропускаем HEIC файл")
                                bot.send_message(chat_id, f"Формат HEIC не поддерживается: {comment}")
                            except Exception as e:
                                print(f"Ошибка при обработке HEIC файла: {str(e)}")
                                bot.send_message(chat_id, f"Ошибка обработки HEIC: {comment}")
                        else:
                            # Используем нашу функцию валидации для обычных форматов
                            if validate_and_fix_image(dst + photo.name, dst + 'validated.jpg'):
                                # Изображение было исправлено
                                bot.send_photo(chat_id, open(dst + 'validated.jpg', 'rb'), caption = comment)
                                os.remove(dst + 'validated.jpg')
                            else:
                                # Изображение корректно, отправляем как есть
                                bot.send_photo(chat_id, photo.file, caption = comment)
                        
                        os.remove(dst + photo.name)
                    except Exception as e:
                        print(f"Ошибка при проверке размеров изображения: {str(e)}")
                        # Fallback - пытаемся отправить как есть, но только если это не HEIC
                        if not photo.name.lower().endswith('.heic'):
                            try:
                                bot.send_photo(chat_id, photo.file, caption = comment)
                            except Exception as fallback_e:
                                print(f"Не удалось отправить изображение: {str(fallback_e)}")
                                bot.send_message(chat_id, f"Изображение слишком большое: {comment}")
                        else:
                            bot.send_message(chat_id, f"Формат HEIC не поддерживается: {comment}")
            if photo.media_type == "video":
                if "gp3" in photo.name or "mp4" in photo.name  or "avi" in photo.name:
                    # Проверяем успешность скачивания видео
                    if not downloadFile(photo.file, photo.name):
                        print(f"Не удалось скачать видео файл {photo.name}")
                        bot.send_message(chat_id, f"Не удалось скачать видео: {comment}")
                        continue
                    
                    # Проверяем, что файл существует после скачивания
                    if not os.path.exists(dst + photo.name):
                        print(f"Видео файл {photo.name} не найден после скачивания")
                        bot.send_message(chat_id, f"Видео повреждено при загрузке: {comment}")
                        continue
                    
                    try:
                        bot.send_video(chat_id, open(dst + photo.name, 'rb'), caption = comment)
                        os.remove(dst + photo.name)
                    except Exception as video_e:
                        print(f"Ошибка при отправке видео: {str(video_e)}")
                        bot.send_message(chat_id, f"Видео слишком большое для отправки: {comment}")
                        if os.path.exists(dst + photo.name):
                            os.remove(dst + photo.name)
                else:
                    bot.send_video(chat_id, photo.file, caption = comment)
        except Exception as exc:
            exceptionText = getattr(exc, 'description', str(exc))
            print(f"Ошибка при отправке файла: {exceptionText}")
            bot.send_message(chat_id, f"Произошла ошибка при отправке файла. Попробуем в следующий раз.")
        except AttributeError as ae:
            print(f"Ошибка атрибутов: {str(ae)}")
            bot.send_message(chat_id, f'Временные проблемы с файлом. Попробуем позже.')


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

    #bot.reply_to(message, message.text)


@bot.message_handler(commands=['test'])
def echo_test(message):
    print("TEST: " + message.text)
    #bot.send_animation()


def process_image_with_validation(my_image, memorySizeRatio):
    """
    Обрабатывает изображение: поворот по EXIF, валидация размеров, сжатие
    """
    # Обработка EXIF для поворота
    if hasattr(my_image, '_getexif'):
        exif = my_image._getexif()
        if exif:
            for tag, label in ExifTags.TAGS.items():
                if label == 'Orientation':
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
        scale_factor = min(max_dimension / image_width, max_dimension / image_height)
        new_width = int(image_width * scale_factor)
        new_height = int(image_height * scale_factor)
        print(f"Уменьшаем изображение с {int(image_width)}x{int(image_height)} до {new_width}x{new_height}")
        my_image = my_image.resize((new_width, new_height), PIL.Image.LANCZOS)
        image_width = float(new_width)
        image_height = float(new_height)
    
    # Проверяем минимальные размеры
    if image_width < min_dimension or image_height < min_dimension:
        new_width = max(int(image_width), min_dimension)
        new_height = max(int(image_height), min_dimension)
        print(f"Увеличиваем изображение с {int(image_width)}x{int(image_height)} до {new_width}x{new_height}")
        my_image = my_image.resize((new_width, new_height), PIL.Image.LANCZOS)
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
        print(f"Корректируем соотношение сторон с {int(image_width)}x{int(image_height)} до {new_width}x{new_height}")
        my_image = my_image.resize((new_width, new_height), PIL.Image.LANCZOS)
        image_width = float(new_width)
        image_height = float(new_height)
    
    # Сжимаем изображение
    my_image = my_image.resize((int(image_width / (2 * memorySizeRatio)), int(image_height / (2 * memorySizeRatio))), PIL.Image.LANCZOS)
    
    # Финальная проверка размеров после сжатия
    final_width, final_height = my_image.size
    if final_width < 1 or final_height < 1:
        print(f"Размеры после сжатия слишком малы: {final_width}x{final_height}, устанавливаем минимальные")
        my_image = my_image.resize((max(final_width, 1), max(final_height, 1)), PIL.Image.LANCZOS)
    
    print(f"Итоговые размеры изображения: {my_image.size[0]}x{my_image.size[1]}")
    return my_image


def validate_and_fix_image(image_path, output_path):
    """
    Проверяет и исправляет размеры изображения для соответствия требованиям Telegram
    Поддерживает конвертацию HEIC файлов в JPEG
    """
    try:
        # Проверяем, является ли файл HEIC
        if image_path.lower().endswith('.heic'):
            print(f"Обнаружен HEIC файл: {image_path}")
            try:
                # Пытаемся использовать pillow-heif для чтения HEIC
                import pillow_heif
                pillow_heif.register_heif_opener()
                
                with Image.open(image_path) as img:
                    # Конвертируем в RGB если необходимо
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    width, height = img.size
                    print(f"HEIC изображение успешно открыто: {width}x{height}")
                    
                    # Применяем валидацию размеров
                    validated_img = apply_size_validation(img)
                    
                    # Сохраняем как JPEG
                    validated_img.save(output_path, 'JPEG', quality=85, optimize=True)
                    print(f"HEIC конвертирован в JPEG: {output_path}")
                    return True
                    
            except ImportError:
                print("pillow-heif не установлен, пытаемся альтернативный метод")
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
                print(f"Изображение сохранено с размерами: {validated_img.size[0]}x{validated_img.size[1]}")
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
    # Константы для Telegram
    MAX_DIMENSION = 10000
    MIN_DIMENSION = 1
    MAX_ASPECT_RATIO = 20
    
    width, height = img.size
    needs_resize = False
    new_width, new_height = width, height
    
    # Проверяем максимальные размеры
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        scale_factor = min(MAX_DIMENSION / width, MAX_DIMENSION / height)
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        needs_resize = True
        print(f"Превышены максимальные размеры, масштабируем к: {new_width}x{new_height}")
    
    # Проверяем минимальные размеры
    if new_width < MIN_DIMENSION or new_height < MIN_DIMENSION:
        new_width = max(new_width, MIN_DIMENSION)
        new_height = max(new_height, MIN_DIMENSION)
        needs_resize = True
        print(f"Размеры слишком малы, увеличиваем к: {new_width}x{new_height}")
    
    # Проверяем соотношение сторон
    aspect_ratio = max(new_width / new_height, new_height / new_width) if new_height > 0 else 1
    if aspect_ratio > MAX_ASPECT_RATIO:
        if new_width > new_height:
            new_width = int(new_height * MAX_ASPECT_RATIO)
        else:
            new_height = int(new_width * MAX_ASPECT_RATIO)
        needs_resize = True
        print(f"Некорректное соотношение сторон, корректируем к: {new_width}x{new_height}")
    
    if needs_resize:
        return img.resize((new_width, new_height), PIL.Image.LANCZOS)
    else:
        return img


def main_loop():
    scheduledThread = Thread(target=schedule_random_photo)
    scheduledThread.start()

    bot.infinity_polling()


def recievingFile(file, message):
    uploadedFileName = message.caption if message.caption != None else file.split('/')[-1]

    print("Saving file " + uploadedFileName + " locally")
        # writing to a custom file
    with requests.get(file, stream=True) as r:
        with open(dst + uploadedFileName, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

    bot.reply_to(message, "Мне это сохранить что ли?")

    lastUpdatedFolder = getLastUpdatedFolder()

    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton(lastUpdatedFolder, callback_data=lastUpdatedFolder),
                                InlineKeyboardButton("Не нада", callback_data="decline"),
                                InlineKeyboardButton("Новое", callback_data="new"))

    bot.reply_to(message, text="Куда сохранять-то?", reply_markup=markup)

    for entry in os.listdir(dst):
        if os.path.isfile(os.path.join(dst, entry)):
            print(entry)


def dump_prin():
    send_welcome("dump message")
    now = datetime.now()
    skip_time = randrange(1,14)
    next_in = now + timedelta(minutes=skip_time)
    print("Sending random photo. Next will be send at " + next_in.strftime("%d/%m/%Y %H:%M:%S") + " after " + str(skip_time) + " hours")
    schedule.enter(skip_time * 3600,1, dump_prin, ())


def schedule_random_photo():
    now = datetime.now()
    skip_time = randrange(1,12)
    next_in = now + timedelta(minutes=skip_time)
    print("Schedulling. Next will be send at " + next_in.strftime("%d/%m/%Y %H:%M:%S") + " after " + str(skip_time) + " hours")
    schedule.enter(skip_time * 3600,1, dump_prin, ())
    schedule.run()


main_loop()
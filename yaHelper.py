#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fileencoding=utf-8
from datetime import date, timedelta
import os
from pickle import NONE, TRUE
import credentials
import random
import yadisk
import time

from stringHelper import get_random_string

dst = credentials.temp_folder

y = yadisk.YaDisk(token=credentials.yandex_token)

# Кэш для результатов поиска фотографий
_photo_cache = {
    'photos': [],
    'cache_time': 0,
    'cache_duration': 300  # Кэш на 5 минут
}


def createFolder():
    try:
        newFolderName = get_random_string(date.today().day)
        y.mkdir(credentials.main_dirrectory + '/' + newFolderName)
        print(f"Папка {newFolderName} успешно создана")
        return newFolderName
    except Exception as e:
        print(f"Ошибка при создании папки: {str(e)}")
        return "ErrorFolder_" + str(date.today().day)

def digToSubfolder(item):
    if item.type == "dir":
        li = list(y.listdir(item.path))
        random.shuffle(li)
        rand = random.choice(li)
        return digToSubfolder(rand)
    if item.media_type == "image" or item.media_type == "video":
        return item;
    return NONE


def downloadFile(url, fileName):
    try:
        y.download_by_link(url, dst + fileName)
        print(f"Файл {fileName} успешно скачан")
    except Exception as e:
        print(f"Ошибка при скачивании файла {fileName}: {str(e)}")
    

def getLastUpdatedFolder():
    try:
        if y.check_token():
            folders = (list(y.listdir(credentials.main_dirrectory)))
            folders.sort(key=lambda dt: dt.modified)
            return folders[-1].name
    except Exception as e:
        print(f"Ошибка при получении последней обновленной папки: {str(e)}")
        return "DefaultFolder"


def getPhoto():
    # Проверка токена Яндекс.Диска
    try:
        if not y.check_token():
            print("Invalid token")
            return None
    except Exception as e:
        print(f"Ошибка при проверке токена Яндекс.Диска: {str(e)}")
        return None
    
    # Информация о текущем использовании диска
    try:
        print("You already use " + str(y.get_disk_info().used_space * (10 ** (-9))))
    except Exception as e:
        print(f"Ошибка при получении информации о диске: {str(e)}")

    # Получаем текущую дату
    today = date.today()
    
    # Сначала ищем точное совпадение по дню и месяцу
    try:
        exact_matches = find_files_by_date_range(today, 0)
        if exact_matches:
            selected_file = random.choice(exact_matches)
            print(f"Найдено точное совпадение по дате: {selected_file.name}")
            return selected_file
    except Exception as e:
        print(f"Ошибка при поиске точного совпадения: {str(e)}")
    
    # Если точного совпадения нет, ищем в диапазоне ±1 день
    try:
        print("Точного совпадения не найдено, ищем в диапазоне ±1 день")
        range_matches = find_files_by_date_range(today, 1)
        if range_matches:
            selected_file = random.choice(range_matches)
            print(f"Найдено совпадение в диапазоне ±1 день: {selected_file.name}")
            return selected_file
    except Exception as e:
        print(f"Ошибка при поиске в диапазоне ±1 день: {str(e)}")
    
    # Если и в диапазоне ничего нет, ищем в более широком диапазоне ±2 дня
    try:
        print("В диапазоне ±1 день не найдено, ищем в диапазоне ±2 дня")
        wider_matches = find_files_by_date_range(today, 2)
        if wider_matches:
            selected_file = random.choice(wider_matches)
            print(f"Найдено совпадение в диапазоне ±2 дня: {selected_file.name}")
            return selected_file
    except Exception as e:
        print(f"Ошибка при поиске в диапазоне ±2 дня: {str(e)}")
    
    # Если не найдено ни одного совпадающего файла, используем обычную логику
    try:
        print("Файлов с совпадающими датами не найдено, выбираем случайный файл")
        subfolders = list(y.listdir(credentials.main_dirrectory))
        random.shuffle(subfolders)
        return digToSubfolder(random.choice(subfolders))
    except Exception as e:
        print(f"Ошибка при выборе случайного файла: {str(e)}")
        return None


def getPhoto():
    """
    Совместимость со старым кодом - возвращает одно случайное фото
    """
    available_photos = find_available_photos()
    if available_photos:
        return random.choice(available_photos)
    return None


def find_available_photos():
    """
    Ищет все доступные фотографии/видео по приоритету:
    1. Точное совпадение по дате (день.месяц)
    2. Диапазон ±1 день
    3. Диапазон ±2 дня
    4. Случайные файлы
    Возвращает список найденных файлов
    Использует кэширование для ускорения повторных запросов
    """
    global _photo_cache
    
    # Проверяем кэш
    current_time = time.time()
    if (current_time - _photo_cache['cache_time'] < _photo_cache['cache_duration'] 
        and _photo_cache['photos']):
        print(f"Используем кэшированные данные ({len(_photo_cache['photos'])} фотографий)")
        return _photo_cache['photos']
    
    print("Кэш устарел или пуст, выполняем поиск...")
    
    # Проверка токена Яндекс.Диска
    try:
        if not y.check_token():
            print("Invalid token")
            return []
    except Exception as e:
        print(f"Ошибка при проверке токена Яндекс.Диска: {str(e)}")
        return []
    
    # Информация о текущем использовании диска
    try:
        print("You already use " + str(y.get_disk_info().used_space * (10 ** (-9))))
    except Exception as e:
        print(f"Ошибка при получении информации о диске: {str(e)}")

    # Получаем текущую дату
    today = date.today()
    found_photos = []
    
    # Сначала ищем точное совпадение по дню и месяцу
    try:
        exact_matches = find_files_by_date_range(today, 0)
        if exact_matches:
            print(f"Найдено {len(exact_matches)} файлов с точным совпадением по дате")
            found_photos = exact_matches
        else:
            print("Точного совпадения не найдено, ищем в диапазоне ±1 день")
            range_matches = find_files_by_date_range(today, 1)
            if range_matches:
                print(f"Найдено {len(range_matches)} файлов в диапазоне ±1 день")
                found_photos = range_matches
            else:
                print("В диапазоне ±1 день не найдено, ищем в диапазоне ±2 дня")
                wider_matches = find_files_by_date_range(today, 2)
                if wider_matches:
                    print(f"Найдено {len(wider_matches)} файлов в диапазоне ±2 дня")
                    found_photos = wider_matches
                else:
                    print("Файлов с совпадающими датами не найдено, собираем все доступные файлы")
                    all_files = collect_all_media_files()
                    if all_files:
                        print(f"Найдено {len(all_files)} файлов всего")
                        found_photos = all_files
    except Exception as e:
        print(f"Ошибка при поиске файлов: {str(e)}")
        found_photos = []
    
    # Обновляем кэш
    _photo_cache['photos'] = found_photos
    _photo_cache['cache_time'] = current_time
    
    return found_photos


def collect_all_media_files():
    """
    Собирает все медиа файлы из всех папок
    """
    all_files = []
    try:
        subfolders = list(y.listdir(credentials.main_dirrectory))
        
        for folder in subfolders:
            try:
                files = list(y.listdir(folder.path))
                for file in files:
                    if file.media_type in ["image", "video"]:
                        all_files.append(file)
            except Exception as e:
                print(f"Ошибка при обработке папки {folder.path}: {str(e)}")
                continue
    except Exception as e:
        print(f"Ошибка при сборе всех медиа файлов: {str(e)}")
    
    return all_files


def clear_photo_cache():
    """
    Принудительно очищает кэш фотографий
    """
    global _photo_cache
    _photo_cache['photos'] = []
    _photo_cache['cache_time'] = 0
    print("Кэш фотографий очищен")


def find_files_by_date_range(target_date, day_range):
    """
    Ищет файлы, созданные в диапазоне ±day_range дней от target_date в любой другой год
    """
    matching_files = []
    
    try:
        # Создаем список дат для поиска
        search_dates = []
        for i in range(-day_range, day_range + 1):
            search_date = target_date + timedelta(days=i)
            search_dates.append((search_date.day, search_date.month))
        
        print(f"Ищем файлы для дат: {search_dates} (исключая {target_date.year} год)")
        
        # Получаем список всех подпапок в основной директории
        subfolders = list(y.listdir(credentials.main_dirrectory))
        
        # Проходим через все папки и подпапки
        for folder in subfolders:
            try:
                files = list(y.listdir(folder.path))
                for file in files:
                    # Проверка, является ли файл изображением или видео
                    if file.media_type in ["image", "video"]:
                        # Получаем дату создания файла
                        if hasattr(file, 'created') and file.created:
                            created_date = file.created
                            file_date_tuple = (created_date.day, created_date.month)
                            
                            # Проверяем, попадает ли дата файла в наш диапазон и не в текущий год
                            if file_date_tuple in search_dates and created_date.year != target_date.year:
                                matching_files.append(file)
                                print(f"Найден файл: {file.name}, создан {created_date.strftime('%d.%m.%Y')}")
            except Exception as e:
                print(f"Ошибка при обработке папки {folder.path}: {str(e)}")
                continue
    
    except Exception as e:
        print(f"Ошибка при поиске файлов по дате: {str(e)}")
        return []
    
    return matching_files


def saveFileTo(localpath, yandexFolder):
    try:
        if(y.check_token()):
            if(os.path.isfile(localpath)):
                y.upload(localpath, credentials.main_dirrectory + "/" + yandexFolder, overwrite=TRUE)
                print(f"Файл {localpath} успешно загружен в {yandexFolder}")
            else:
                print(f"Локальный файл {localpath} не найден")
        else:
            print("Ошибка токена при загрузке файла")
    except Exception as e:
        print(f"Ошибка при загрузке файла {localpath}: {str(e)}")
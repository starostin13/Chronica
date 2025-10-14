#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fileencoding=utf-8
from datetime import date, timedelta, datetime
import os
from pickle import NONE, TRUE
import credentials
import random
from random import randrange
import yadisk
import time

from stringHelper import get_random_string

dst = credentials.temp_folder

y = yadisk.YaDisk(token=credentials.yandex_token)

# Глобальный кеш для результатов сканирования папок
_folder_scan_cache = {
    "all_files": [],  # Все найденные медиа файлы
    "scan_time": 0,  # Время последнего сканирования
    "cache_expires": 0,  # Время истечения кеша (случайное от 1 до 5 дней)
    "folders_scanned": 0,  # Количество отсканированных папок
}


def clear_photo_cache():
    """
    Очищает кеш сканирования папок, принудительно заставляя пересканировать при следующем запросе
    """
    global _folder_scan_cache
    _folder_scan_cache["all_files"] = []
    _folder_scan_cache["scan_time"] = 0
    _folder_scan_cache["cache_expires"] = 0
    _folder_scan_cache["folders_scanned"] = 0
    print("🗑️ Кеш сканирования папок очищен")


def createFolder():
    try:
        newFolderName = get_random_string(date.today().day)
        y.mkdir(credentials.main_dirrectory + "/" + newFolderName)
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
        return item
    return NONE


def downloadFile(url, fileName, max_retries=3):
    """
    Скачивает файл с Yandex Disk с повторными попытками
    """
    for attempt in range(max_retries):
        try:
            # Убеждаемся, что папка назначения существует
            os.makedirs(dst, exist_ok=True)

            # Проверяем доступность токена
            if not y.check_token():
                print(
                    f"Ошибка токена при скачивании {fileName} (попытка {attempt + 1})"
                )
                if attempt < max_retries - 1:
                    time.sleep(2)  # Ждем перед повторной попыткой
                    continue
                return False

            file_path = dst + fileName

            # Удаляем файл, если он уже существует (для повторной попытки)
            if os.path.exists(file_path):
                os.remove(file_path)

            print(f"Попытка скачивания {fileName} (попытка {attempt + 1})")

            # Скачиваем файл
            y.download_by_link(url, file_path)

            # Проверяем, что файл действительно скачался
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                file_size = os.path.getsize(file_path)
                print(f"Файл {fileName} успешно скачан ({file_size} байт)")
                return True
            else:
                print(
                    f"Файл {fileName} не скачался или имеет нулевой размер (попытка {attempt + 1})"
                )
                if attempt < max_retries - 1:
                    time.sleep(3)  # Ждем дольше перед повторной попыткой
                    continue

        except Exception as e:
            print(
                f"Ошибка при скачивании файла {fileName} (попытка {attempt + 1}): {str(e)}"
            )
            if attempt < max_retries - 1:
                time.sleep(5)  # Ждем перед повторной попыткой при ошибке
                continue

    print(f"Не удалось скачать файл {fileName} после {max_retries} попыток")
    return False


def getLastUpdatedFolder():
    try:
        if y.check_token():
            folders = list(y.listdir(credentials.main_dirrectory))
            folders.sort(key=lambda dt: dt.modified)
            return folders[-1].name
    except Exception as e:
        print(f"Ошибка при получении последней обновленной папки: {str(e)}")
        return "DefaultFolder"


def getPhoto():
    """
    Совместимость со старым кодом - возвращает одно случайное фото
    """
    available_photos = find_available_photos(search_by_date=True)
    if available_photos:
        return random.choice(available_photos)
    return None


def find_available_photos(search_by_date=True):
    """
    Ищет все доступные фотографии/видео по приоритету:
    1. Если search_by_date=True: точное совпадение по дате (день.месяц) из любого года
    2. Если search_by_date=False или нет совпадений по дате: случайные файлы
    Возвращает список найденных файлов
    Использует умное кеширование результатов сканирования папок на 1-5 дней
    """
    global _folder_scan_cache

    # Проверяем актуальность кеша
    current_time = time.time()
    cache_valid = (
        current_time < _folder_scan_cache["cache_expires"]
        and len(_folder_scan_cache["all_files"]) > 0
    )

    if cache_valid:
        print(f"📦 Используем кешированные данные сканирования папок")
        print(
            f"📊 В кеше: {len(_folder_scan_cache['all_files'])} файлов из {_folder_scan_cache['folders_scanned']} папок"
        )
        all_files = _folder_scan_cache["all_files"]
    else:
        print("🔄 Кеш устарел или пуст, выполняем полное сканирование папок...")
        all_files = perform_full_folder_scan()

    if not all_files:
        print("❌ Файлов не найдено")
        return []

    # Теперь фильтруем уже загруженные файлы по дате
    if search_by_date:
        today = date.today()
        print(f"🔍 Фильтруем файлы по дате: {today.day}.{today.month} (любой год)")

        date_matches = filter_files_by_date(all_files, today, 0)

        if date_matches:
            print(
                f"✅ Найдено {len(date_matches)} файлов с совпадением по дате {today.day}.{today.month}"
            )
            return date_matches
        else:
            print(f"❌ Файлов с совпадающими датами не найдено")
            print(f"✅ Используем случайный выбор из {len(all_files)} доступных файлов")
            return all_files
    else:
        print(f"🎲 Случайный выбор из {len(all_files)} файлов")
        return all_files


def scan_folder_recursively(folder_path, folder_name="", depth=0):
    """
    Рекурсивно сканирует папку и все её подпапки, собирая медиа файлы

    Args:
        folder_path: Путь к папке для сканирования
        folder_name: Имя папки (для логирования)
        depth: Текущая глубина рекурсии (для отступов в логах)

    Returns:
        Список найденных медиа файлов
    """
    indent = "  " * depth
    media_files = []

    try:
        items = list(y.listdir(folder_path))
        print(
            f"{indent}📂 Сканируем {folder_name or folder_path}: {len(items)} элементов"
        )

        for item in items:
            try:
                if item.type == "dir":
                    # Рекурсивно сканируем подпапку
                    subfolder_files = scan_folder_recursively(
                        item.path, item.name, depth + 1
                    )
                    media_files.extend(subfolder_files)
                elif item.media_type in ["image", "video"]:
                    # Это медиа файл - добавляем его
                    media_files.append(item)
            except Exception as e:
                print(f"{indent}❌ Ошибка при обработке {item.path}: {str(e)}")
                continue

        if depth == 0 or len(media_files) > 0:
            print(
                f"{indent}✅ В {folder_name or folder_path}: {len(media_files)} медиа файлов"
            )

    except Exception as e:
        print(f"{indent}❌ Ошибка при сканировании папки {folder_path}: {str(e)}")

    return media_files


def perform_full_folder_scan():
    """
    Выполняет полное рекурсивное сканирование всех папок и кеширует результат на случайное время (1-5 дней)
    """
    global _folder_scan_cache

    # Проверка токена Яндекс.Диска
    try:
        if not y.check_token():
            print("❌ Invalid token")
            return []
    except Exception as e:
        print(f"❌ Ошибка при проверке токена Яндекс.Диска: {str(e)}")
        return []

    # Информация о текущем использовании диска
    try:
        disk_usage = y.get_disk_info().used_space * (10 ** (-9))
        print(f"💾 Использование диска: {disk_usage:.2f} GB")
    except Exception as e:
        print(f"⚠️ Ошибка при получении информации о диске: {str(e)}")

    all_files = []

    try:
        # Получаем список всех подпапок в основной директории
        subfolders = list(y.listdir(credentials.main_dirrectory))
        print(
            f"📁 Найдено {len(subfolders)} папок верхнего уровня для рекурсивного сканирования"
        )

        # Рекурсивно проходим через все папки и собираем ВСЕ медиа файлы
        for folder in subfolders:
            try:
                folder_files = scan_folder_recursively(
                    folder.path, folder.name, depth=0
                )
                all_files.extend(folder_files)
            except Exception as e:
                print(f"❌ Ошибка при сканировании папки {folder.path}: {str(e)}")
                continue

    except Exception as e:
        print(f"❌ Ошибка при сканировании папок: {str(e)}")
        return []

    # Обновляем кеш с новыми данными
    current_time = time.time()
    cache_days = randrange(1, 6)  # От 1 до 5 дней
    cache_duration = cache_days * 24 * 60 * 60  # В секундах

    _folder_scan_cache["all_files"] = all_files
    _folder_scan_cache["scan_time"] = current_time
    _folder_scan_cache["cache_expires"] = current_time + cache_duration
    _folder_scan_cache["folders_scanned"] = len(subfolders)

    cache_expire_date = datetime.fromtimestamp(_folder_scan_cache["cache_expires"])
    print(
        f"💾 Кеш обновлен: {len(all_files)} файлов, действителен до {cache_expire_date.strftime('%d.%m.%Y %H:%M')} ({cache_days} дней)"
    )

    return all_files


def filter_files_by_date(all_files, target_date, day_range):
    """
    Фильтрует уже загруженный список файлов по дате
    """
    matching_files = []

    # Создаем список дат для поиска
    search_dates = []
    for i in range(-day_range, day_range + 1):
        search_date = target_date + timedelta(days=i)
        search_dates.append((search_date.day, search_date.month))

    print(f"🔍 Фильтруем по датам: {search_dates}")

    for file in all_files:
        # Получаем дату съёмки фото (приоритет)
        if hasattr(file, "photoslice_time") and file.photoslice_time:
            photo_date = file.photoslice_time
            file_date_tuple = (photo_date.day, photo_date.month)

            if file_date_tuple in search_dates:
                matching_files.append(file)
                print(
                    f"✅ Совпадение: {file.name}, снят {photo_date.strftime('%d.%m.%Y')}"
                )
        elif hasattr(file, "created") and file.created:
            # Fallback на дату создания файла
            created_date = file.created
            file_date_tuple = (created_date.day, created_date.month)

            if file_date_tuple in search_dates:
                matching_files.append(file)
                print(
                    f"✅ Совпадение (дата создания): {file.name}, создан {created_date.strftime('%d.%m.%Y')}"
                )

    return matching_files


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


def find_files_with_date_filtering(target_date, day_range):
    """
    ЭФФЕКТИВНАЯ функция: за один проход собирает ВСЕ файлы и фильтрует по дате
    Возвращает: (все_файлы, файлы_по_дате)
    """
    all_files = []
    matching_files = []

    try:
        # Создаем список дат для поиска
        search_dates = []
        for i in range(-day_range, day_range + 1):
            search_date = target_date + timedelta(days=i)
            search_dates.append((search_date.day, search_date.month))

        print(f"🔍 Ищем файлы для дат: {search_dates}")

        # Получаем список всех подпапок в основной директории
        subfolders = list(y.listdir(credentials.main_dirrectory))
        print(f"📁 Найдено {len(subfolders)} папок для поиска")

        # Проходим через все папки и подпапки ОДИН РАЗ
        for folder in subfolders:
            try:
                files = list(y.listdir(folder.path))
                print(f"📂 Обрабатываем папку {folder.name}: {len(files)} файлов")
                folder_all_media = 0
                folder_date_matches = 0

                for file in files:
                    # Проверка, является ли файл изображением или видео
                    if file.media_type in ["image", "video"]:
                        all_files.append(file)  # Добавляем ВСЕ медиа файлы
                        folder_all_media += 1

                        # Проверяем совпадение по дате
                        file_matches_date = False

                        # Получаем дату съёмки фото (не дату создания файла)
                        if hasattr(file, "photoslice_time") and file.photoslice_time:
                            photo_date = file.photoslice_time
                            file_date_tuple = (photo_date.day, photo_date.month)

                            # Проверяем, попадает ли дата файла в наш диапазон
                            if file_date_tuple in search_dates:
                                matching_files.append(file)
                                folder_date_matches += 1
                                print(
                                    f"✅ Совпадение по дате: {file.name}, снят {photo_date.strftime('%d.%m.%Y')}"
                                )
                                file_matches_date = True

                        if (
                            not file_matches_date
                            and hasattr(file, "created")
                            and file.created
                        ):
                            # Fallback на дату создания файла, если нет даты съёмки
                            created_date = file.created
                            file_date_tuple = (created_date.day, created_date.month)

                            if file_date_tuple in search_dates:
                                matching_files.append(file)
                                folder_date_matches += 1
                                print(
                                    f"✅ Совпадение по дате создания: {file.name}, создан {created_date.strftime('%d.%m.%Y')}"
                                )

                print(
                    f"📂 В папке {folder.name}: {folder_all_media} медиа файлов, {folder_date_matches} совпадений по дате"
                )

            except Exception as e:
                print(f"❌ Ошибка при обработке папки {folder.path}: {str(e)}")
                continue

    except Exception as e:
        print(f"❌ Ошибка при поиске файлов: {str(e)}")
        return [], []

    print(
        f"🎯 ИТОГО: {len(all_files)} всех медиа файлов, {len(matching_files)} совпадений по дате {target_date.day}.{target_date.month}"
    )
    return all_files, matching_files


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

        print(f"🔍 Ищем файлы для дат: {search_dates}")

        # Получаем список всех подпапок в основной директории
        subfolders = list(y.listdir(credentials.main_dirrectory))
        print(f"📁 Найдено {len(subfolders)} папок для поиска")

        # Проходим через все папки и подпапки
        for folder in subfolders:
            try:
                files = list(y.listdir(folder.path))
                print(f"📂 Обрабатываем папку {folder.name}: {len(files)} файлов")
                folder_matches = 0

                for file in files:
                    # Проверка, является ли файл изображением или видео
                    if file.media_type in ["image", "video"]:
                        # Получаем дату съёмки фото (не дату создания файла)
                        if hasattr(file, "photoslice_time") and file.photoslice_time:
                            photo_date = file.photoslice_time
                            file_date_tuple = (photo_date.day, photo_date.month)

                            # Проверяем, попадает ли дата файла в наш диапазон
                            if file_date_tuple in search_dates:
                                matching_files.append(file)
                                folder_matches += 1
                                print(
                                    f"✅ Найден файл: {file.name}, снят {photo_date.strftime('%d.%m.%Y')}"
                                )
                        elif hasattr(file, "created") and file.created:
                            # Fallback на дату создания файла, если нет даты съёмки
                            created_date = file.created
                            file_date_tuple = (created_date.day, created_date.month)

                            if file_date_tuple in search_dates:
                                matching_files.append(file)
                                folder_matches += 1
                                print(
                                    f"✅ Найден файл (по дате создания): {file.name}, создан {created_date.strftime('%d.%m.%Y')}"
                                )

                if folder_matches > 0:
                    print(
                        f"📂 В папке {folder.name} найдено {folder_matches} подходящих файлов"
                    )

            except Exception as e:
                print(f"❌ Ошибка при обработке папки {folder.path}: {str(e)}")
                continue

    except Exception as e:
        print(f"❌ Ошибка при поиске файлов по дате: {str(e)}")
        return []

    print(
        f"🎯 Итого найдено {len(matching_files)} файлов по дате {target_date.day}.{target_date.month}"
    )
    return matching_files


def saveFileTo(localpath, yandexFolder):
    try:
        if y.check_token():
            if os.path.isfile(localpath):
                y.upload(
                    localpath,
                    credentials.main_dirrectory + "/" + yandexFolder,
                    overwrite=TRUE,
                )
                print(f"Файл {localpath} успешно загружен в {yandexFolder}")
            else:
                print(f"Локальный файл {localpath} не найден")
        else:
            print("Ошибка токена при загрузке файла")
    except Exception as e:
        print(f"Ошибка при загрузке файла {localpath}: {str(e)}")

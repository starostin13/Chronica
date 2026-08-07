#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fileencoding=utf-8
from datetime import date, timedelta, datetime
import json
import os
import credentials
import random
from random import randrange
import yadisk
import time

from stringHelper import get_random_string

dst = credentials.temp_folder
SIZE_CACHE_FILE = os.path.join(dst, "folder_scan_cache.json")

y = yadisk.YaDisk(
    token=credentials.yandex_token,
)

# Глобальный кеш для результатов сканирования папок
_folder_scan_cache = {
    "all_files": [],  # Все найденные медиа файлы
    "scan_time": 0,  # Время последнего сканирования
    "cache_expires": 0,  # Время истечения кеша (случайное от 1 до 5 дней)
    "folders_scanned": 0,  # Количество отсканированных папок
    "max_file_size": None,  # Максимальный размер файла в байтах
    "file_sizes": {},  # Размеры файлов по их пути на Яндекс.Диске
}


def _save_size_cache():
    """
    Сохраняет ограничения по размеру и известные размеры файлов в файл кеша.
    """
    try:
        cache_dir = os.path.dirname(SIZE_CACHE_FILE)
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)

        with open(SIZE_CACHE_FILE, "w", encoding="utf-8") as cache_file:
            json.dump(
                {
                    "max_file_size": _folder_scan_cache["max_file_size"],
                    "file_sizes": _folder_scan_cache["file_sizes"],
                },
                cache_file,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
    except Exception as e:
        print(f"⚠️ Не удалось сохранить кеш размеров: {str(e)}")


def _load_size_cache():
    """Загружает ограничения по размеру и кеш размеров файлов из файла."""
    if not os.path.exists(SIZE_CACHE_FILE):
        return

    try:
        with open(SIZE_CACHE_FILE, "r", encoding="utf-8") as cache_file:
            cached_data = json.load(cache_file)
    except Exception as e:
        print(f"⚠️ Не удалось загрузить кеш размеров: {str(e)}")
        return

    max_file_size = cached_data.get("max_file_size")
    if isinstance(max_file_size, int) and max_file_size > 0:
        _folder_scan_cache["max_file_size"] = max_file_size
    else:
        _folder_scan_cache["max_file_size"] = None

    cached_sizes = cached_data.get("file_sizes", {})
    normalized_sizes = {}
    if isinstance(cached_sizes, dict):
        for file_path, file_size in cached_sizes.items():
            if (
                isinstance(file_path, str)
                and isinstance(file_size, int)
                and file_size > 0
            ):
                normalized_sizes[file_path] = file_size

    _folder_scan_cache["file_sizes"] = normalized_sizes
    print(
        "📦 Загружен кеш размеров: "
        f"{len(normalized_sizes)} файлов, "
        f"max_file_size={_folder_scan_cache['max_file_size']}"
    )


def _remember_file_size(file_path, file_size_bytes, save_cache=True):
    """
    Сохраняет известный размер файла по его пути на Яндекс.Диске.

    Args:
        file_path: Путь к файлу на Яндекс.Диске
        file_size_bytes: Размер файла в байтах
        save_cache: Нужно ли сразу сохранять изменения в файл кеша
    """
    if not file_path:
        return False

    if not isinstance(file_size_bytes, int) or file_size_bytes <= 0:
        return False

    current_size = _folder_scan_cache["file_sizes"].get(file_path)
    if current_size == file_size_bytes:
        return False

    _folder_scan_cache["file_sizes"][file_path] = file_size_bytes
    if save_cache:
        _save_size_cache()
    return True


def clear_photo_cache():
    """
    Очищает кеш сканирования папок и заставляет пересканировать их
    при следующем запросе.
    """
    _folder_scan_cache["all_files"] = []
    _folder_scan_cache["scan_time"] = 0
    _folder_scan_cache["cache_expires"] = 0
    _folder_scan_cache["folders_scanned"] = 0
    _folder_scan_cache["max_file_size"] = None
    _folder_scan_cache["file_sizes"] = {}
    _save_size_cache()
    print("🗑️ Кеш сканирования папок очищен")


def set_max_file_size(file_size_bytes):
    """
    Устанавливает максимальный размер файла, который можно отправить в Telegram.
    Вызывается, когда Telegram отклоняет файл из-за размера.

    Args:
        file_size_bytes: Размер файла в байтах
    """
    current_max = _folder_scan_cache["max_file_size"]

    if current_max is None or file_size_bytes < current_max:
        _folder_scan_cache["max_file_size"] = file_size_bytes
        _save_size_cache()
        file_size_mb = file_size_bytes / (1024 * 1024)
        print(
            f"📏 Установлен максимальный размер файла: "
            f"{file_size_mb:.2f} MB ({file_size_bytes} байт)"
        )


def get_max_file_size():
    """
    Возвращает текущий максимальный размер файла в байтах.

    Returns:
        int or None: Максимальный размер в байтах или None если ограничения нет
    """
    return _folder_scan_cache["max_file_size"]


def get_known_file_size(file_obj):
    """
    Возвращает известный размер файла из API Яндекс.Диска или файлового кеша.

    Args:
        file_obj: Объект файла

    Returns:
        int or None: Размер файла в байтах или None если он неизвестен
    """
    file_size = getattr(file_obj, "size", None)
    if isinstance(file_size, int) and file_size > 0:
        file_path = getattr(file_obj, "path", None)
        if file_path:
            _remember_file_size(file_path, file_size, save_cache=False)
        return file_size

    file_path = getattr(file_obj, "path", None)
    if file_path:
        return _folder_scan_cache["file_sizes"].get(file_path)

    return None


def remove_file_from_cache(file_obj):
    """
    Удаляет выбранный файл из кеша all_files.

    Args:
        file_obj: Объект файла (ожидается атрибут path). Может быть None.

    Returns:
        None
    """
    if file_obj is None:
        print("⚠️ Попытка удалить None из кеша")
        return

    all_files = _folder_scan_cache["all_files"]

    if file_obj in all_files:
        all_files.remove(file_obj)
        print("🗑️ Выбранный файл удален из кеша по объекту")
        return

    file_path = getattr(file_obj, "path", None)
    if file_path:
        for cached_file in list(all_files):
            if getattr(cached_file, "path", None) == file_path:
                all_files.remove(cached_file)
                print(f"🗑️ Выбранный файл удален из кеша по пути: {file_path}")
                break
        else:
            print(f"⚠️ Файл не найден в кеше для удаления: {file_path}")


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
        if not li:
            return None
        random.shuffle(li)
        rand = random.choice(li)
        return digToSubfolder(rand)
    if item.media_type == "image" or item.media_type == "video":
        return item
    return None


def createFolderWithName(folder_name):
    """
    Создает папку на Яндекс Диске с указанным именем

    Args:
        folder_name: Имя создаваемой папки
    """
    try:
        cleaned_name = (folder_name or "").strip()
        if not cleaned_name:
            cleaned_name = f"Folder_{date.today().strftime('%Y%m%d')}"

        if not y.check_token():
            print("Ошибка токена при создании папки")
            return f"ErrorFolder_{date.today().day}"

        y.mkdir(credentials.main_dirrectory + "/" + cleaned_name)
        print(f"Папка {cleaned_name} успешно создана")
        return cleaned_name
    except Exception as e:
        print(f"Ошибка при создании папки {folder_name}: {str(e)}")
        return f"ErrorFolder_{date.today().day}"


def get_fresh_download_link(file_path_on_disk):
    """Получает свежую ссылку на скачивание файла с Яндекс.Диска."""
    try:
        if not file_path_on_disk:
            return None
        if not y.check_token():
            print("Ошибка токена при обновлении ссылки")
            return None
        return y.get_download_link(file_path_on_disk)
    except Exception as e:
        print(f"Ошибка при получении свежей ссылки: {str(e)}")
        return None


def downloadFile(url, fileName, file_path_on_disk=None, max_retries=3):
    """
    Скачивает файл с Yandex Disk с повторными попытками и обработкой устаревших ссылок

    Args:
        url: Ссылка для скачивания
        fileName: Имя файла для сохранения
        file_path_on_disk: Путь к файлу на Яндекс.Диске (для получения свежей ссылки)
        max_retries: Максимальное количество попыток
    """
    current_url = url

    for attempt in range(max_retries):
        try:
            # Убеждаемся, что папка назначения существует
            os.makedirs(dst, exist_ok=True)

            # Проверяем доступность токена
            if not y.check_token():
                print(
                    f"Ошибка токена при скачивании {fileName} "
                    f"(попытка {attempt + 1})"
                )
                if attempt < max_retries - 1:
                    # Экспоненциальная задержка: 2, 4, 8, 16 секунд
                    backoff_time = 2 ** (attempt + 1)
                    print(
                        f"⏳ Ожидание {backoff_time} секунд "
                        f"перед повторной попыткой..."
                    )
                    time.sleep(backoff_time)
                    continue
                return False

            file_path = dst + fileName

            # Удаляем файл, если он уже существует (для повторной попытки)
            if os.path.exists(file_path):
                os.remove(file_path)

            print(f"Попытка скачивания {fileName} (попытка {attempt + 1})")

            # Скачиваем файл
            y.download_by_link(current_url, file_path)

            # Проверяем, что файл действительно скачался
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                file_size = os.path.getsize(file_path)
                if file_path_on_disk:
                    _remember_file_size(file_path_on_disk, file_size)
                print(f"✅ Файл {fileName} успешно скачан ({file_size} байт)")
                return True
            print(
                f"⚠️ Файл {fileName} не скачался или имеет нулевой размер "
                f"(попытка {attempt + 1})"
            )
            if attempt < max_retries - 1:
                # Экспоненциальная задержка
                backoff_time = 2 ** (attempt + 1)
                print(
                    f"⏳ Ожидание {backoff_time} секунд " f"перед повторной попыткой..."
                )
                time.sleep(backoff_time)
                continue

        except Exception as e:
            error_msg = str(e)
            print(
                f"❌ Ошибка при скачивании файла {fileName} "
                f"(попытка {attempt + 1}): {error_msg}"
            )

            # Если ссылка устарела/протухла — пытаемся получить свежую
            unknown_expired_error = (
                hasattr(yadisk, "exceptions")
                and hasattr(yadisk.exceptions, "UnknownYaDiskError")
                and isinstance(e, yadisk.exceptions.UnknownYaDiskError)
            )
            text_expired_error = "expired" in error_msg.lower()

            if file_path_on_disk and (unknown_expired_error or text_expired_error):
                fresh_link = get_fresh_download_link(file_path_on_disk)
                if fresh_link:
                    current_url = fresh_link
                    print("🔄 Получена свежая ссылка, повторяем скачивание...")
                    continue

            if attempt < max_retries - 1:
                # Экспоненциальная задержка с увеличенным временем при ошибках
                backoff_time = 2 ** (attempt + 2)
                print(
                    f"⏳ Ожидание {backoff_time} секунд " f"перед повторной попыткой..."
                )
                time.sleep(backoff_time)
                continue

    print(f"❌ Не удалось скачать файл {fileName} после {max_retries} попыток")
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
    # Проверяем актуальность кеша
    current_time = time.time()
    cache_valid = (
        current_time < _folder_scan_cache["cache_expires"]
        and len(_folder_scan_cache["all_files"]) > 0
    )

    if cache_valid:
        print("📦 Используем кешированные данные сканирования папок")
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

    # Фильтруем файлы по максимальному размеру
    max_size = _folder_scan_cache["max_file_size"]
    if max_size is not None:
        original_count = len(all_files)
        all_files = [
            f
            for f in all_files
            if ((file_size := get_known_file_size(f)) is None or file_size <= max_size)
        ]
        filtered_count = original_count - len(all_files)
        if filtered_count > 0:
            max_size_mb = max_size / (1024 * 1024)
            print(
                f"📏 Отфильтровано {filtered_count} файлов, превышающих "
                f"максимальный размер {max_size_mb:.2f} MB"
            )

        if not all_files:
            print(
                "❌ Все файлы превышают максимальный размер, "
                "возвращаем пустой список"
            )
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
            print("❌ Файлов с совпадающими датами не найдено")
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
    Выполняет полное сканирование всех папок и кеширует результат на случайное время (1-5 дней)
    С улучшенной обработкой ошибок сети
    """
    # Проверка токена Яндекс.Диска с повторными попытками
    max_token_retries = 3
    for attempt in range(max_token_retries):
        try:
            if not y.check_token():
                print("❌ Invalid token")
                return []
            break  # Токен валидный, выходим из цикла
        except Exception as e:
            print(
                f"❌ Ошибка при проверке токена Яндекс.Диска "
                f"(попытка {attempt + 1}): {str(e)}"
            )
            if attempt < max_token_retries - 1:
                backoff_time = 2 ** (attempt + 1)
                print(f"⏳ Повтор через {backoff_time} секунд...")
                time.sleep(backoff_time)
            else:
                return []

    # Информация о текущем использовании диска
    try:
        disk_usage = y.get_disk_info().used_space * (10 ** (-9))
        print(f"💾 Использование диска: {disk_usage:.2f} GB")
    except Exception as e:
        print(f"⚠️ Ошибка при получении информации о диске: {str(e)}")

    all_files = []
    size_cache_changed = False

    try:
        # Получаем список всех подпапок в основной директории с повторными попытками
        subfolders = None
        max_listdir_retries = 3
        for attempt in range(max_listdir_retries):
            try:
                subfolders = list(y.listdir(credentials.main_dirrectory))
                break
            except Exception as e:
                print(
                    f"❌ Ошибка при получении списка папок "
                    f"(попытка {attempt + 1}): {str(e)}"
                )
                if attempt < max_listdir_retries - 1:
                    backoff_time = 2 ** (attempt + 1)
                    print(f"⏳ Повтор через {backoff_time} секунд...")
                    time.sleep(backoff_time)
                else:
                    return []

        if not subfolders:
            print("❌ Не удалось получить список папок")
            return []

        print(f"📁 Найдено {len(subfolders)} папок для сканирования")

        # Проходим через все папки и собираем ВСЕ медиа файлы
        for folder in subfolders:
            max_folder_retries = 2
            for attempt in range(max_folder_retries):
                try:
                    print(
                        f"📂 Рекурсивно сканируем папку {folder.name} "
                        f"({folder.path})"
                    )
                    folder_media_count = 0
                    paths_to_scan = [folder.path]

                    while paths_to_scan:
                        current_path = paths_to_scan.pop()
                        try:
                            entries = list(y.listdir(current_path))
                        except Exception as inner_e:
                            print(
                                "❌ Ошибка при сканировании вложенной папки "
                                f"{current_path}: {str(inner_e)}"
                            )
                            continue

                        for entry in entries:
                            if getattr(entry, "type", None) == "dir":
                                paths_to_scan.append(entry.path)
                            elif entry.media_type in ["image", "video"]:
                                all_files.append(entry)
                                folder_media_count += 1
                                if _remember_file_size(
                                    entry.path,
                                    getattr(entry, "size", None),
                                    save_cache=False,
                                ):
                                    size_cache_changed = True

                    print(
                        "📂 В папке {name} (с учётом подпапок): "
                        "{count} медиа файлов".format(
                            name=folder.name,
                            count=folder_media_count,
                        )
                    )
                    break  # Успешно обработали папку

                except Exception as e:
                    print(
                        f"❌ Ошибка при сканировании папки {folder.path} "
                        f"(попытка {attempt + 1}): {str(e)}"
                    )
                    if attempt < max_folder_retries - 1:
                        backoff_time = 2**attempt
                        print(f"⏳ Повтор через {backoff_time} секунд...")
                        time.sleep(backoff_time)
                    else:
                        print(f"⚠️ Пропускаем папку {folder.path}")
                        continue

    except Exception as e:
        print(f"❌ Критическая ошибка при сканировании папок: {str(e)}")
        return []

    # Обновляем кеш с новыми данными
    current_time = time.time()
    cache_days = randrange(1, 6)  # От 1 до 5 дней
    cache_duration = cache_days * 24 * 60 * 60  # В секундах

    _folder_scan_cache["all_files"] = all_files
    _folder_scan_cache["scan_time"] = current_time
    _folder_scan_cache["cache_expires"] = current_time + cache_duration
    _folder_scan_cache["folders_scanned"] = len(subfolders)

    if size_cache_changed:
        _save_size_cache()

    cache_expire_date = datetime.fromtimestamp(_folder_scan_cache["cache_expires"])
    print(
        f"💾 Кеш обновлен: {len(all_files)} файлов, "
        f"действителен до {cache_expire_date.strftime('%d.%m.%Y %H:%M')} "
        f"({cache_days} дней)"
    )

    return all_files


_load_size_cache()


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
                            file_date_tuple = (
                                photo_date.day,
                                photo_date.month,
                            )

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
                            file_date_tuple = (
                                created_date.day,
                                created_date.month,
                            )

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
    Использует кешированный список файлов для эффективности
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
                            file_date_tuple = (
                                photo_date.day,
                                photo_date.month,
                            )

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
                            file_date_tuple = (
                                created_date.day,
                                created_date.month,
                            )

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

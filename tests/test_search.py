#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

# ВАЖНО: Добавляем путь к родительской директории ДО импорта любых модулей
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Теперь импортируем наши модули
from datetime import date
from yaHelper import find_available_photos, clear_photo_cache, find_files_by_date_range

def test_date_search():
    print("=== Тестирование поиска по датам ===")
    print(f"Родительская директория: {parent_dir}")
    print(f"Проверяем наличие credentials.py: {os.path.exists(os.path.join(parent_dir, 'credentials.py'))}")
    
    # Очищаем кэш
    clear_photo_cache()
    
    today = date.today()
    print(f"Текущая дата: {today.day}.{today.month}.{today.year}")
    
    # Тестируем каждый уровень поиска
    print("\n1. Тестируем точное совпадение (день 5, месяц 8):")
    exact_matches = find_files_by_date_range(today, 0)
    print(f"Найдено {len(exact_matches)} файлов с точным совпадением")
    
    if exact_matches:
        for i, photo in enumerate(exact_matches[:3]):
            if hasattr(photo, 'created') and photo.created:
                print(f"  - {photo.name} от {photo.created.strftime('%d.%m.%Y')}")
            else:
                print(f"  - {photo.name} (дата неизвестна)")
    
    print("\n2. Тестируем диапазон ±1 день:")
    range1_matches = find_files_by_date_range(today, 1)
    print(f"Найдено {len(range1_matches)} файлов в диапазоне ±1 день")
    
    print("\n3. Тестируем диапазон ±2 дня:")
    range2_matches = find_files_by_date_range(today, 2)
    print(f"Найдено {len(range2_matches)} файлов в диапазоне ±2 дня")
    
    print("\n4. Общий поиск через find_available_photos():")
    all_photos = find_available_photos()
    print(f"Найдено {len(all_photos)} фотографий общим поиском")
    
    if all_photos:
        print("Примеры найденных файлов:")
        for i, photo in enumerate(all_photos[:5]):
            if hasattr(photo, 'created') and photo.created:
                print(f"  {i+1}. {photo.name} от {photo.created.strftime('%d.%m.%Y')}")
            elif hasattr(photo, 'photoslice_time') and photo.photoslice_time:
                print(f"  {i+1}. {photo.name} от {photo.photoslice_time.strftime('%d.%m.%Y')}")
            else:
                print(f"  {i+1}. {photo.name} (дата неизвестна)")

if __name__ == "__main__":
    test_date_search()
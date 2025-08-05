#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

# Добавляем родительскую директорию в путь Python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from yaHelper import find_available_photos, clear_photo_cache
import credentials
import yadisk

def debug_file_attributes():
    print("=== Отладка атрибутов файлов ===")
    
    # Подключаемся к Яндекс.Диску
    y = yadisk.YaDisk(token=credentials.yandex_token)
    
    try:
        # Получаем список папок
        subfolders = list(y.listdir(credentials.main_dirrectory))
        print(f"Найдено {len(subfolders)} папок")
        
        # Берём первую папку для примера
        if subfolders:
            first_folder = subfolders[0]
            print(f"Исследуем папку: {first_folder.name}")
            
            files = list(y.listdir(first_folder.path))
            print(f"В папке {len(files)} файлов")
            
            # Берём первые 3 файла для анализа
            for i, file in enumerate(files[:3]):
                if file.media_type in ["image", "video"]:
                    print(f"\n--- Файл {i+1}: {file.name} ---")
                    print(f"Тип: {file.media_type}")
                    
                    # Проверяем все доступные атрибуты времени
                    if hasattr(file, 'created'):
                        print(f"created: {file.created}")
                    if hasattr(file, 'modified'):
                        print(f"modified: {file.modified}")
                    if hasattr(file, 'photoslice_time'):
                        print(f"photoslice_time: {file.photoslice_time}")
                    if hasattr(file, 'exif'):
                        print(f"exif: {file.exif}")
                    
                    # Показываем все атрибуты объекта
                    print("Все атрибуты файла:")
                    for attr in dir(file):
                        if not attr.startswith('_'):
                            try:
                                value = getattr(file, attr)
                                if not callable(value):
                                    print(f"  {attr}: {value}")
                            except:
                                pass
                    
                    if i >= 2:  # Ограничиваем до 3 файлов
                        break
                        
    except Exception as e:
        print(f"Ошибка: {str(e)}")

if __name__ == "__main__":
    debug_file_attributes()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тест для проверки разного поведения команды /start в зависимости от chat_id
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import credentials
from yaHelper import find_available_photos

def test_date_behavior():
    """Тестируем поиск по датам"""
    print("=== Тест поиска по дате ===")
    
    photos = find_available_photos(search_by_date=True)
    print(f"Найдено фотографий при поиске по дате: {len(photos)}")
    
    if photos:
        print("Примеры:")
        for i, photo in enumerate(photos[:3]):
            date_info = ""
            if hasattr(photo, 'photoslice_time') and photo.photoslice_time:
                date_info = f" (снято {photo.photoslice_time.strftime('%d.%m.%Y')})"
            elif hasattr(photo, 'created') and photo.created:
                date_info = f" (создано {photo.created.strftime('%d.%m.%Y')})"
            print(f"  {i+1}. {photo.name}{date_info}")

def test_random_behavior():
    """Тестируем случайный поиск"""
    print("\n=== Тест случайного поиска ===")
    
    photos = find_available_photos(search_by_date=False)
    print(f"Найдено фотографий при случайном поиске: {len(photos)}")
    
    if photos:
        print("Примеры:")
        for i, photo in enumerate(photos[:3]):
            date_info = ""
            if hasattr(photo, 'photoslice_time') and photo.photoslice_time:
                date_info = f" (снято {photo.photoslice_time.strftime('%d.%m.%Y')})"
            elif hasattr(photo, 'created') and photo.created:
                date_info = f" (создано {photo.created.strftime('%d.%m.%Y')})"
            print(f"  {i+1}. {photo.name}{date_info}")

def test_chat_id_logic():
    """Тестируем логику определения типа чата"""
    print("\n=== Тест логики chat_id ===")
    
    configured_chat_ids = [id.strip() for id in credentials.chat_ids.split(",")]
    print(f"Настроенные chat_ids: {configured_chat_ids}")
    
    # Тестируем разные chat_id
    test_cases = [
        ("-1001710464481", "должен быть случайный поиск"),
        ("-247157106", "должен быть случайный поиск"), 
        ("12345", "должен быть поиск по дате"),
        ("-999999", "должен быть поиск по дате")
    ]
    
    for chat_id, expected in test_cases:
        if chat_id in configured_chat_ids:
            behavior = "случайный поиск"
        else:
            behavior = "поиск по дате"
        
        status = "✅" if behavior in expected else "❌"
        print(f"  {status} chat_id {chat_id}: {behavior} ({expected})")

if __name__ == "__main__":
    try:
        test_chat_id_logic()
        test_date_behavior()
        test_random_behavior()
        print("\n=== Тесты завершены ===")
    except Exception as e:
        print(f"Ошибка при тестировании: {str(e)}")

#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

# Добавляем путь к родительской директории
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from yaHelper import (
    mark_file_as_sent,
    get_cache_stats,
    clear_photo_cache,
    _folder_scan_cache,
)


def test_mark_file_as_sent():
    """
    Тестирует функцию пометки файлов как отправленных
    """
    print("=== Тест: mark_file_as_sent ===")

    # Очищаем кеш перед тестом
    clear_photo_cache()

    # Проверяем начальное состояние
    stats = get_cache_stats()
    print(f"Начальное состояние: {stats}")
    assert stats["sent_files"] == 0, "Кеш должен быть пуст"

    # Помечаем файл как отправленный
    test_file_path = "/test/path/photo1.jpg"
    mark_file_as_sent(test_file_path)

    # Проверяем, что файл добавлен
    stats = get_cache_stats()
    print(f"После добавления одного файла: {stats}")
    assert stats["sent_files"] == 1, "Должен быть один отправленный файл"
    assert (
        test_file_path in _folder_scan_cache["sent_files"]
    ), "Файл должен быть в списке отправленных"

    # Добавляем еще несколько файлов
    mark_file_as_sent("/test/path/photo2.jpg")
    mark_file_as_sent("/test/path/photo3.jpg")

    stats = get_cache_stats()
    print(f"После добавления трех файлов: {stats}")
    assert stats["sent_files"] == 3, "Должно быть три отправленных файла"

    # Проверяем, что повторное добавление не увеличивает счетчик (множество)
    mark_file_as_sent(test_file_path)
    stats = get_cache_stats()
    print(f"После повторного добавления: {stats}")
    assert (
        stats["sent_files"] == 3
    ), "Повторное добавление не должно увеличивать счетчик"

    print("✅ Тест mark_file_as_sent пройден")


def test_clear_cache_clears_sent_files():
    """
    Тестирует, что очистка кеша также очищает список отправленных файлов
    """
    print("\n=== Тест: clear_cache_clears_sent_files ===")

    # Сначала очищаем кеш для чистого теста
    clear_photo_cache()

    # Добавляем несколько файлов
    mark_file_as_sent("/test/path/photo1.jpg")
    mark_file_as_sent("/test/path/photo2.jpg")

    stats = get_cache_stats()
    print(f"До очистки: {stats}")
    assert stats["sent_files"] == 2, "Должно быть два отправленных файла"

    # Очищаем кеш
    clear_photo_cache()

    # Проверяем, что список отправленных файлов очищен
    stats = get_cache_stats()
    print(f"После очистки: {stats}")
    assert (
        stats["sent_files"] == 0
    ), "Список отправленных файлов должен быть пуст"

    print("✅ Тест clear_cache_clears_sent_files пройден")


def test_get_cache_stats():
    """
    Тестирует функцию получения статистики кеша
    """
    print("\n=== Тест: get_cache_stats ===")

    # Очищаем кеш
    clear_photo_cache()

    # Получаем статистику
    stats = get_cache_stats()
    print(f"Статистика пустого кеша: {stats}")

    # Проверяем структуру возвращаемых данных
    assert "total_files" in stats, "Должно быть поле total_files"
    assert "sent_files" in stats, "Должно быть поле sent_files"
    assert "available_files" in stats, "Должно быть поле available_files"
    assert "folders_scanned" in stats, "Должно быть поле folders_scanned"

    # Проверяем начальные значения
    assert stats["total_files"] == 0, "Файлов в кеше не должно быть"
    assert stats["sent_files"] == 0, "Отправленных файлов не должно быть"
    assert stats["available_files"] == 0, "Доступных файлов не должно быть"

    print("✅ Тест get_cache_stats пройден")


if __name__ == "__main__":
    try:
        test_mark_file_as_sent()
        test_clear_cache_clears_sent_files()
        test_get_cache_stats()

        print("\n" + "=" * 50)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n❌ Тест провален: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении теста: {e}")
        sys.exit(1)

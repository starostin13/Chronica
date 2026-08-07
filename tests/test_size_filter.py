#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тесты для функциональности фильтрации по размеру файла
"""

import sys
import os
from unittest.mock import MagicMock, patch

# Добавляем путь к родительской директории
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

credentials_mock = MagicMock()
credentials_mock.temp_folder = "/tmp/"
credentials_mock.yandex_token = "test-token"
credentials_mock.main_dirrectory = "/disk"

with patch.dict(
    "sys.modules",
    {"yadisk": MagicMock(), "credentials": credentials_mock},
):
    import yaHelper

set_max_file_size = yaHelper.set_max_file_size
get_max_file_size = yaHelper.get_max_file_size
_folder_scan_cache = yaHelper._folder_scan_cache
clear_photo_cache = yaHelper.clear_photo_cache


class MockFile:
    """Mock объект для тестирования файлов с размером"""

    def __init__(self, name, size, path="/test/path"):
        self.name = name
        self.size = size
        self.path = path
        self.media_type = "image"


def test_set_max_file_size():
    """Тест установки максимального размера файла"""
    # Очищаем кеш перед тестом
    clear_photo_cache()

    # Устанавливаем первый максимум
    set_max_file_size(10 * 1024 * 1024)  # 10 MB
    assert get_max_file_size() == 10 * 1024 * 1024

    # Устанавливаем меньший максимум - должен обновиться
    set_max_file_size(5 * 1024 * 1024)  # 5 MB
    assert get_max_file_size() == 5 * 1024 * 1024

    # Устанавливаем больший максимум - не должен обновиться
    set_max_file_size(15 * 1024 * 1024)  # 15 MB
    assert get_max_file_size() == 5 * 1024 * 1024

    print("✅ test_set_max_file_size passed")


def test_get_max_file_size_default():
    """Тест получения максимального размера по умолчанию"""
    # Очищаем кеш
    clear_photo_cache()

    # По умолчанию должен быть None
    assert get_max_file_size() is None

    print("✅ test_get_max_file_size_default passed")


def test_filter_files_by_size():
    """Тест фильтрации файлов по размеру"""
    # Очищаем кеш
    clear_photo_cache()

    # Создаем тестовые файлы разных размеров
    files = [
        MockFile("small.jpg", 1 * 1024 * 1024),  # 1 MB
        MockFile("medium.jpg", 5 * 1024 * 1024),  # 5 MB
        MockFile("large.jpg", 10 * 1024 * 1024),  # 10 MB
        MockFile("xlarge.jpg", 20 * 1024 * 1024),  # 20 MB
    ]

    # Устанавливаем максимум 6 MB
    set_max_file_size(6 * 1024 * 1024)
    max_size = get_max_file_size()

    # Фильтруем файлы
    filtered_files = [
        f
        for f in files
        if not hasattr(f, "size") or f.size is None or f.size <= max_size
    ]

    # Должны остаться только файлы размером <= 6 MB
    assert len(filtered_files) == 2
    assert filtered_files[0].name == "small.jpg"
    assert filtered_files[1].name == "medium.jpg"

    print("✅ test_filter_files_by_size passed")


def test_filter_files_without_size():
    """Тест фильтрации файлов без атрибута size"""
    # Очищаем кеш
    clear_photo_cache()

    # Создаем файл без size
    class FileWithoutSize:
        def __init__(self, name):
            self.name = name
            self.path = "/test"
            self.media_type = "image"

    files = [
        MockFile("with_size.jpg", 5 * 1024 * 1024),
        FileWithoutSize("without_size.jpg"),
    ]

    # Устанавливаем максимум
    set_max_file_size(10 * 1024 * 1024)
    max_size = get_max_file_size()

    # Фильтруем файлы
    filtered_files = [
        f
        for f in files
        if not hasattr(f, "size") or f.size is None or f.size <= max_size
    ]

    # Файл без size не должен отбрасываться только из-за отсутствия метаданных
    assert len(filtered_files) == 2
    assert filtered_files[0].name == "with_size.jpg"
    assert filtered_files[1].name == "without_size.jpg"

    print("✅ test_filter_files_without_size passed")


def test_no_filter_when_max_is_none():
    """Тест что фильтрация не применяется когда max_size = None"""
    # Очищаем кеш
    clear_photo_cache()

    files = [
        MockFile("file1.jpg", 1 * 1024 * 1024),
        MockFile("file2.jpg", 100 * 1024 * 1024),
    ]

    max_size = get_max_file_size()
    assert max_size is None

    # Когда max_size is None, все файлы должны проходить
    # (в реальном коде фильтрация не применяется)
    filtered_files = (
        files
        if max_size is None
        else [
            f
            for f in files
            if hasattr(f, "size") and f.size is not None and f.size <= max_size
        ]
    )

    assert len(filtered_files) == 2

    print("✅ test_no_filter_when_max_is_none passed")


if __name__ == "__main__":
    test_get_max_file_size_default()
    test_set_max_file_size()
    test_filter_files_by_size()
    test_filter_files_without_size()
    test_no_filter_when_max_is_none()
    print("\n✅ All size filter tests passed!")

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Интеграционный тест для проверки фильтрации по размеру файла
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


class MockFile:
    """Mock объект для тестирования файлов"""

    def __init__(self, name, size, path="/test/path"):
        self.name = name
        self.size = size
        self.path = path
        self.media_type = "image"
        self.photoslice_time = None
        self.created = None


def test_integration_filter_by_size():
    """
    Интеграционный тест: симулирует работу бота с фильтрацией по размеру
    """
    # Очищаем кеш
    yaHelper.clear_photo_cache()

    # Создаем mock файлы разных размеров
    all_files = [
        MockFile("photo1.jpg", 2 * 1024 * 1024),  # 2 MB
        MockFile("photo2.jpg", 8 * 1024 * 1024),  # 8 MB
        MockFile("photo3.jpg", 15 * 1024 * 1024),  # 15 MB
        MockFile("photo4.jpg", 3 * 1024 * 1024),  # 3 MB
    ]

    # Шаг 1: Без ограничений, все файлы доступны
    max_size = yaHelper.get_max_file_size()
    assert max_size is None
    available = [
        f
        for f in all_files
        if max_size is None
        or (hasattr(f, "size") and f.size is not None and f.size <= max_size)
    ]
    assert len(available) == 4
    print("✅ Шаг 1: Без ограничений доступны все 4 файла")

    # Шаг 2: Telegram отклоняет файл размером 8 MB
    rejected_file = all_files[1]  # photo2.jpg - 8 MB
    yaHelper.set_max_file_size(rejected_file.size)
    max_size = yaHelper.get_max_file_size()
    assert max_size == 8 * 1024 * 1024
    print(f"✅ Шаг 2: Установлен максимум {max_size / (1024*1024):.0f} MB")

    # Шаг 3: Фильтруем файлы - должны остаться только <= 8 MB
    available = [
        f
        for f in all_files
        if hasattr(f, "size") and f.size is not None and f.size <= max_size
    ]
    assert len(available) == 3
    assert available[0].name == "photo1.jpg"
    assert available[1].name == "photo2.jpg"
    assert available[2].name == "photo4.jpg"
    print("✅ Шаг 3: Отфильтровано, доступны 3 файла (2MB, 8MB, 3MB)")

    # Шаг 4: Telegram отклоняет файл размером 3 MB
    rejected_file2 = all_files[3]  # photo4.jpg - 3 MB
    yaHelper.set_max_file_size(rejected_file2.size)
    max_size = yaHelper.get_max_file_size()
    assert max_size == 3 * 1024 * 1024
    print(f"✅ Шаг 4: Максимум уменьшен до {max_size / (1024*1024):.0f} MB")

    # Шаг 5: Теперь доступны только файлы <= 3 MB
    available = [
        f
        for f in all_files
        if hasattr(f, "size") and f.size is not None and f.size <= max_size
    ]
    assert len(available) == 2
    assert available[0].name == "photo1.jpg"
    assert available[1].name == "photo4.jpg"
    print("✅ Шаг 5: Остались только 2 файла (2MB, 3MB)")

    # Шаг 6: Попытка установить больший максимум не должна изменить текущий
    yaHelper.set_max_file_size(10 * 1024 * 1024)
    max_size = yaHelper.get_max_file_size()
    assert max_size == 3 * 1024 * 1024
    print("✅ Шаг 6: Максимум не изменился при попытке увеличить")

    print("\n✅ Интеграционный тест пройден успешно!")


if __name__ == "__main__":
    test_integration_filter_by_size()

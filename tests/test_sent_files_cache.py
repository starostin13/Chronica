#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from types import SimpleNamespace
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

clear_photo_cache = yaHelper.clear_photo_cache
remove_file_from_cache = yaHelper.remove_file_from_cache
_folder_scan_cache = yaHelper._folder_scan_cache


def test_remove_file_from_cache_by_object():
    """Проверяет удаление выбранного файла из кеша по объекту."""
    clear_photo_cache()

    photo1 = SimpleNamespace(path="/disk/photo1.jpg")
    photo2 = SimpleNamespace(path="/disk/photo2.jpg")
    _folder_scan_cache["all_files"] = [photo1, photo2]

    remove_file_from_cache(photo1)

    assert len(_folder_scan_cache["all_files"]) == 1
    assert _folder_scan_cache["all_files"][0].path == "/disk/photo2.jpg"


def test_remove_file_from_cache_by_path_fallback():
    """Проверяет удаление из кеша по совпадению path, если объект другой."""
    clear_photo_cache()

    cached_photo = SimpleNamespace(path="/disk/photo3.jpg")
    _folder_scan_cache["all_files"] = [cached_photo]

    external_photo_obj = SimpleNamespace(path="/disk/photo3.jpg")
    remove_file_from_cache(external_photo_obj)

    assert _folder_scan_cache["all_files"] == []


if __name__ == "__main__":
    test_remove_file_from_cache_by_object()
    test_remove_file_from_cache_by_path_fallback()
    print("✅ Тесты удаления файлов из кеша пройдены")

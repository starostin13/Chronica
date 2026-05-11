#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тест для проверки обработки истекших ссылок Yandex.Disk
"""

import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Добавляем путь к родительской директории
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


def test_get_fresh_download_link():
    """Тест функции получения свежей ссылки"""
    print("\n=== Тестирование получения свежей ссылки ===")

    # Мокаем модуль yadisk перед импортом
    with patch.dict("sys.modules", {"yadisk": MagicMock()}):
        # Создаем мок для y.check_token и y.get_download_link
        import yaHelper

        yaHelper.y = Mock()
        yaHelper.y.check_token = Mock(return_value=True)
        yaHelper.y.get_download_link = Mock(return_value="https://fresh.link/file123")

        from yaHelper import get_fresh_download_link

        # Тест успешного получения ссылки
        result = get_fresh_download_link("/test/path/file.jpg")

        assert result == "https://fresh.link/file123", "Ссылка должна быть получена"
        print("✅ Успешное получение свежей ссылки работает")

        # Тест ошибки токена
        yaHelper.y.check_token = Mock(return_value=False)
        result = get_fresh_download_link("/test/path/file.jpg")

        assert result is None, "При ошибке токена должен вернуться None"
        print("✅ Обработка ошибки токена работает")

        # Тест исключения при получении ссылки
        yaHelper.y.check_token = Mock(return_value=True)
        yaHelper.y.get_download_link = Mock(side_effect=Exception("API error"))
        result = get_fresh_download_link("/test/path/file.jpg")

        assert result is None, "При исключении должен вернуться None"
        print("✅ Обработка исключений работает")


def test_downloadFile_with_expired_link():
    """Тест функции downloadFile с обработкой истекших ссылок"""
    print("\n=== Тестирование downloadFile с истекшими ссылками ===")

    # Создаем мок для UnknownYaDiskError
    class UnknownYaDiskError(Exception):
        pass

    # Создаем полноценный мок для yadisk с exceptions
    yadisk_mock = MagicMock()
    yadisk_exceptions_mock = MagicMock()
    yadisk_exceptions_mock.UnknownYaDiskError = UnknownYaDiskError
    yadisk_mock.exceptions = yadisk_exceptions_mock

    with patch.dict(
        "sys.modules",
        {"yadisk": yadisk_mock, "yadisk.exceptions": yadisk_exceptions_mock},
    ):
        import yaHelper

        # Мокаем зависимости
        yaHelper.y = Mock()
        yaHelper.y.check_token = Mock(return_value=True)
        yaHelper.dst = "/tmp/test/"

        # Устанавливаем UnknownYaDiskError в модуль yadisk
        yaHelper.yadisk = yadisk_mock

        from yaHelper import downloadFile

        # Мокаем os.makedirs, os.path.exists, os.path.getsize, os.remove
        with patch("os.makedirs"), patch("os.path.exists") as mock_exists, patch(
            "os.path.getsize"
        ) as mock_size, patch("os.remove"):

            mock_exists.return_value = True
            mock_size.return_value = 1000

            # Тест 1: Первая попытка с UnknownYaDiskError, вторая успешна
            # Используем side_effect с последовательностью значений
            yaHelper.y.download_by_link = Mock(
                side_effect=[UnknownYaDiskError("Link expired"), None]
            )
            yaHelper.y.get_download_link = Mock(return_value="https://fresh.link/new")

            result = downloadFile(
                "https://old.link/expired",
                "test.jpg",
                "/disk/path/test.jpg",
                max_retries=3,
            )

            # Проверяем, что была попытка получить свежую ссылку
            yaHelper.y.get_download_link.assert_called_once_with("/disk/path/test.jpg")
            print("✅ При UnknownYaDiskError вызывается get_download_link")

            # Должно быть 2 попытки скачивания
            assert yaHelper.y.download_by_link.call_count == 2, "Должно быть 2 попытки"
            print("✅ Повторная попытка со свежей ссылкой выполнена")

            # Проверяем, что вторая попытка использовала свежую ссылку
            second_call_args = yaHelper.y.download_by_link.call_args_list[1][0]
            assert (
                second_call_args[0] == "https://fresh.link/new"
            ), "Вторая попытка должна использовать свежую ссылку"
            print("✅ Свежая ссылка используется для повторной попытки")


def test_downloadFile_signature():
    """Проверка сигнатуры функции downloadFile"""
    print("\n=== Проверка сигнатуры downloadFile ===")

    with patch.dict("sys.modules", {"yadisk": MagicMock()}):
        from yaHelper import downloadFile
        import inspect

        sig = inspect.signature(downloadFile)
        params = list(sig.parameters.keys())

        expected = ["url", "fileName", "file_path_on_disk", "max_retries"]
        assert (
            params == expected
        ), f"Ожидаемые параметры: {expected}, получены: {params}"
        print(f"✅ Сигнатура функции корректна: {params}")

        # Проверяем значения по умолчанию
        assert (
            sig.parameters["file_path_on_disk"].default is None
        ), "file_path_on_disk должен иметь значение по умолчанию None"
        assert (
            sig.parameters["max_retries"].default == 3
        ), "max_retries должен иметь значение по умолчанию 3"
        print("✅ Значения по умолчанию корректны")


if __name__ == "__main__":
    try:
        test_get_fresh_download_link()
        test_downloadFile_with_expired_link()
        test_downloadFile_signature()
        print("\n" + "=" * 60)
        print("✅ Все тесты пройдены успешно!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ Тест провален: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении теста: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

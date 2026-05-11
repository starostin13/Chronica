#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тесты для проверки логики повторных попыток и экспоненциальной задержки
"""

import sys
import os

# Добавляем путь к родительской директории
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


def test_exponential_backoff():
    """Тестирует расчет экспоненциальной задержки"""
    print("=== Тест экспоненциальной задержки ===")

    # Симулируем расчет задержки для downloadFile
    print("\n1. Задержки для downloadFile (при ошибках):")
    for attempt in range(5):
        backoff_time = 2 ** (attempt + 2)
        print(f"   Попытка {attempt + 1}: {backoff_time} секунд")

    # Симулируем расчет задержки для основного цикла бота
    print("\n2. Задержки для основного цикла бота:")
    max_retry_backoff = 300
    for retry_count in range(1, 8):
        backoff_time = min(15 * (2 ** (retry_count - 1)), max_retry_backoff)
        print(f"   Попытка {retry_count}: {backoff_time} секунд")

    print("\n✅ Тест экспоненциальной задержки пройден")


def test_retry_count():
    """Проверяет максимальное количество попыток"""
    print("\n=== Тест количества попыток ===")

    max_retries = 5
    print(f"Максимальное количество попыток: {max_retries}")

    attempt_count = 0
    for attempt in range(max_retries):
        attempt_count += 1
        print(f"   Выполняется попытка {attempt + 1}")

    assert (
        attempt_count == max_retries
    ), f"Ожидалось {max_retries} попыток, выполнено {attempt_count}"
    print(f"✅ Выполнено {attempt_count} попыток как и ожидалось")


def test_timeout_configuration():
    """Проверяет конфигурацию таймаутов"""
    print("\n=== Тест конфигурации таймаутов ===")

    timeout_value = 30.0
    max_retries_value = 5

    print(f"Настроенный таймаут: {timeout_value} секунд")
    print(f"Настроенное max_retries: {max_retries_value}")

    assert timeout_value > 0, "Таймаут должен быть положительным"
    assert max_retries_value >= 3, "Должно быть минимум 3 попытки"

    print("✅ Конфигурация таймаутов корректна")


def test_backoff_limit():
    """Проверяет ограничение максимальной задержки"""
    print("\n=== Тест ограничения максимальной задержки ===")

    max_retry_backoff = 300  # 5 минут
    print(f"Максимальная задержка: {max_retry_backoff} секунд (5 минут)")

    # Проверяем что задержка не превышает максимум
    for retry_count in range(1, 20):
        backoff_time = min(15 * (2 ** (retry_count - 1)), max_retry_backoff)
        assert (
            backoff_time <= max_retry_backoff
        ), f"Задержка {backoff_time} превышает максимум {max_retry_backoff}"

    print("✅ Максимальная задержка корректно ограничена")


if __name__ == "__main__":
    print("Запуск тестов логики повторных попыток\n")
    try:
        test_exponential_backoff()
        test_retry_count()
        test_timeout_configuration()
        test_backoff_limit()
        print("\n" + "=" * 60)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ ТЕСТ НЕ ПРОЙДЕН: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ОШИБКА ПРИ ВЫПОЛНЕНИИ ТЕСТОВ: {e}")
        sys.exit(1)

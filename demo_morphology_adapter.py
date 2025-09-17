#!/usr/bin/env python3
"""
Демонстрационный скрипт для MorphologyAdapter.

Показывает основные возможности нового адаптера:
- Кэширование и производительность
- Поддержка UK словарей
- Fallback поведение
- Интеграция с NormalizationService
"""

import time
import statistics
from typing import List, Tuple

from src.ai_service.layers.normalization.morphology_adapter import (
    MorphologyAdapter,
    get_global_adapter,
    clear_global_cache,
)
from src.ai_service.layers.normalization.normalization_service import NormalizationService


def demo_basic_functionality():
    """Демонстрация базовой функциональности адаптера."""
    print("=== Демонстрация базовой функциональности MorphologyAdapter ===")
    
    # Создаем адаптер
    adapter = MorphologyAdapter(cache_size=1000)
    
    # Тестовые токены
    test_cases = [
        ("Иванова", "ru"),
        ("Ивановой", "ru"), 
        ("Анна", "ru"),
        ("Олена", "uk"),
        ("Ковальська", "uk"),
        ("Ковальською", "uk"),
    ]
    
    print("\n1. Парсинг токенов:")
    for token, lang in test_cases:
        parses = adapter.parse(token, lang)
        print(f"  {token} ({lang}): {len(parses)} разборов")
        for parse in parses[:2]:  # Показываем первые 2 разбора
            print(f"    - {parse.normal} | {parse.tag} | {parse.gender} | {parse.case}")
    
    print("\n2. Конвертация в номинатив:")
    for token, lang in test_cases:
        nominative = adapter.to_nominative(token, lang)
        print(f"  {token} -> {nominative}")
    
    print("\n3. Определение рода:")
    for token, lang in test_cases:
        gender = adapter.detect_gender(token, lang)
        print(f"  {token}: {gender}")


def demo_caching_performance():
    """Демонстрация производительности кэширования."""
    print("\n=== Демонстрация производительности кэширования ===")
    
    # Очищаем глобальный кэш
    clear_global_cache()
    
    # Получаем глобальный адаптер
    adapter = get_global_adapter(cache_size=50000)
    
    # Генерируем тестовые токены
    test_tokens = [
        ("Анна", "ru"), ("Мария", "ru"), ("Иван", "ru"), ("Сергей", "ru"),
        ("Иванова", "ru"), ("Петрова", "ru"), ("Сидоров", "ru"), ("Кузнецов", "ru"),
        ("Олена", "uk"), ("Ірина", "uk"), ("Марія", "uk"), ("Іван", "uk"),
        ("Ковальська", "uk"), ("Шевченко", "uk"), ("Петренко", "uk"), ("Новак", "uk"),
    ] * 10  # Повторяем для тестирования кэша
    
    print(f"\nТестируем {len(test_tokens)} операций...")
    
    # Тест без прогрева кэша
    print("\n1. Без прогрева кэша:")
    times = []
    for token, lang in test_tokens[:50]:  # Первые 50 для холодного кэша
        start = time.perf_counter()
        adapter.parse(token, lang)
        end = time.perf_counter()
        times.append((end - start) * 1000)
    
    avg_cold = statistics.mean(times)
    p95_cold = statistics.quantiles(times, n=20)[18]
    print(f"  Среднее время: {avg_cold:.2f}ms")
    print(f"  P95 время: {p95_cold:.2f}ms")
    
    # Тест с прогревом кэша
    print("\n2. С прогревом кэша:")
    adapter.warmup(test_tokens[:100])  # Прогреваем кэш
    
    times = []
    for token, lang in test_tokens:
        start = time.perf_counter()
        adapter.parse(token, lang)
        end = time.perf_counter()
        times.append((end - start) * 1000)
    
    avg_warm = statistics.mean(times)
    p95_warm = statistics.quantiles(times, n=20)[18]
    print(f"  Среднее время: {avg_warm:.2f}ms")
    print(f"  P95 время: {p95_warm:.2f}ms")
    
    # Статистика кэша
    stats = adapter.get_cache_stats()
    print(f"\n3. Статистика кэша:")
    print(f"  Размер кэша парсинга: {stats['parse_cache_size']}")
    print(f"  Попадания в кэш: {stats['parse_cache_hits']}")
    print(f"  Промахи кэша: {stats['parse_cache_misses']}")
    
    hit_ratio = stats['parse_cache_hits'] / (stats['parse_cache_hits'] + stats['parse_cache_misses'])
    print(f"  Коэффициент попаданий: {hit_ratio:.2%}")


def demo_uk_support():
    """Демонстрация поддержки украинского языка."""
    print("\n=== Демонстрация поддержки украинского языка ===")
    
    adapter = MorphologyAdapter()
    
    # Проверяем доступность UK словаря
    uk_available = adapter.is_uk_available()
    print(f"Украинский словарь доступен: {uk_available}")
    
    # Тестовые украинские токены
    uk_tokens = [
        ("Олена", "uk"),
        ("Ірина", "uk"),
        ("Марія", "uk"),
        ("Ковальська", "uk"),
        ("Ковальською", "uk"),
        ("Шевченко", "uk"),
        ("Петренко", "uk"),
    ]
    
    print("\nОбработка украинских токенов:")
    for token, lang in uk_tokens:
        nominative = adapter.to_nominative(token, lang)
        gender = adapter.detect_gender(token, lang)
        print(f"  {token} -> {nominative} ({gender})")


def demo_integration_with_service():
    """Демонстрация интеграции с NormalizationService."""
    print("\n=== Демонстрация интеграции с NormalizationService ===")
    
    # Создаем сервис нормализации
    service = NormalizationService()
    
    # Тестовые тексты
    test_texts = [
        "Анна Ивановой",
        "Мария Петрова",
        "Олена Ковальською",
        "Ірина Шевченко",
    ]
    
    print("\nНормализация текстов:")
    for text in test_texts:
        result = service.normalize(text)
        print(f"  '{text}' -> '{result.normalized}'")
        print(f"    Язык: {result.language}, Уверенность: {result.confidence}")
        print(f"    Токены: {result.tokens}")
        print()


def demo_fallback_behavior():
    """Демонстрация fallback поведения."""
    print("\n=== Демонстрация fallback поведения ===")
    
    # Тестируем с недопустимыми языками
    adapter = MorphologyAdapter()
    
    print("\n1. Недопустимые языки:")
    invalid_cases = [
        ("тест", "en"),
        ("тест", "invalid"),
        ("", "ru"),
        ("   ", "ru"),
    ]
    
    for token, lang in invalid_cases:
        result = adapter.parse(token, lang)
        nominative = adapter.to_nominative(token, lang)
        gender = adapter.detect_gender(token, lang)
        print(f"  '{token}' ({lang}): parse={len(result)}, nom={nominative}, gender={gender}")
    
    print("\n2. Пустые токены:")
    empty_cases = ["", "   ", None]
    for token in empty_cases:
        if token is not None:
            result = adapter.parse(token, "ru")
            print(f"  '{token}': {len(result)} разборов")


def demo_thread_safety():
    """Демонстрация потокобезопасности."""
    print("\n=== Демонстрация потокобезопасности ===")
    
    import threading
    import queue
    
    adapter = get_global_adapter()
    
    # Результаты от разных потоков
    results = queue.Queue()
    
    def worker(worker_id: int, tokens: List[Tuple[str, str]]):
        """Рабочая функция для тестирования потокобезопасности."""
        worker_results = []
        for token, lang in tokens:
            try:
                result = adapter.parse(token, lang)
                worker_results.append((worker_id, token, len(result)))
            except Exception as e:
                worker_results.append((worker_id, token, f"ERROR: {e}"))
        results.put(worker_results)
    
    # Создаем несколько потоков
    tokens_per_worker = [
        [("Анна", "ru"), ("Мария", "ru")],
        [("Иван", "ru"), ("Сергей", "ru")],
        [("Олена", "uk"), ("Ірина", "uk")],
    ]
    
    threads = []
    for i, worker_tokens in enumerate(tokens_per_worker):
        thread = threading.Thread(target=worker, args=(i, worker_tokens))
        threads.append(thread)
    
    # Запускаем все потоки
    start_time = time.perf_counter()
    for thread in threads:
        thread.start()
    
    # Ждем завершения
    for thread in threads:
        thread.join()
    end_time = time.perf_counter()
    
    # Собираем результаты
    all_results = []
    while not results.empty():
        worker_results = results.get()
        all_results.extend(worker_results)
    
    print(f"Выполнено {len(all_results)} операций в {len(threads)} потоках за {(end_time - start_time) * 1000:.2f}ms")
    print("Результаты:")
    for worker_id, token, result in all_results:
        print(f"  Поток {worker_id}: {token} -> {result}")


def main():
    """Главная функция демонстрации."""
    print("Демонстрация MorphologyAdapter")
    print("=" * 50)
    
    try:
        demo_basic_functionality()
        demo_caching_performance()
        demo_uk_support()
        demo_integration_with_service()
        demo_fallback_behavior()
        demo_thread_safety()
        
        print("\n" + "=" * 50)
        print("Демонстрация завершена успешно!")
        
    except Exception as e:
        print(f"\nОшибка во время демонстрации: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

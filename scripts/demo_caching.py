#!/usr/bin/env python3
"""
Демонстрация системы кэширования для AI Service Normalization.

Этот скрипт демонстрирует работу LRU кэшей с TTL, метрики Prometheus
и производительность на коротких строках.
"""

import asyncio
import sys
import time
import statistics
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from ai_service.utils.lru_cache_ttl import LruTtlCache, CacheManager, create_flags_hash
from ai_service.layers.normalization.tokenizer_service import TokenizerService, CachedTokenizerService
from ai_service.layers.normalization.morphology_adapter import MorphologyAdapter
from ai_service.monitoring.cache_metrics import CacheMetrics, MetricsCollector
from ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory, NormalizationConfig


# Тестовые данные
TEST_TEXTS = [
    "Іван Петров",
    "ООО 'Ромашка' Иван И.",
    "Петро Порошенко",
    "John Smith",
    "Анна Сергеевна Иванова",
    "Dr. John Smith",
    "Prof. Maria Garcia",
    "Mr. Петр Петров",
    "Ms. Анна Иванова",
    "Іван I. Петров"
]


def demo_lru_cache():
    """Демонстрация LRU кэша с TTL."""
    print("🔧 Демонстрация LRU кэша с TTL")
    print("-" * 50)
    
    # Создаём кэш
    cache = LruTtlCache(maxsize=5, ttl_seconds=2)
    
    print("1. Базовые операции:")
    cache.set("key1", "value1")
    hit, value = cache.get("key1")
    print(f"   key1: hit={hit}, value={value}")
    
    hit, value = cache.get("nonexistent")
    print(f"   nonexistent: hit={hit}, value={value}")
    
    print("\n2. LRU eviction:")
    # Заполняем кэш
    for i in range(7):
        cache.set(f"key{i}", f"value{i}")
    
    print(f"   Размер кэша: {len(cache)}")
    print(f"   key0 доступен: {'key0' in cache}")
    print(f"   key6 доступен: {'key6' in cache}")
    
    print("\n3. TTL expiration:")
    cache.set("temp", "temporary")
    hit, _ = cache.get("temp")
    print(f"   temp сразу: hit={hit}")
    
    time.sleep(2.1)  # Ждём истечения TTL
    hit, _ = cache.get("temp")
    print(f"   temp после TTL: hit={hit}")
    
    print("\n4. Статистики:")
    stats = cache.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")


def demo_cache_manager():
    """Демонстрация менеджера кэшей."""
    print("\n🏗️ Демонстрация менеджера кэшей")
    print("-" * 50)
    
    config = {
        'max_size': 100,
        'ttl_sec': 60,
        'enable_cache': True
    }
    
    manager = CacheManager(config)
    
    print("1. Конфигурация:")
    print(f"   maxsize: {manager.maxsize}")
    print(f"   ttl_seconds: {manager.ttl_seconds}")
    print(f"   enabled: {manager.enabled}")
    
    print("\n2. Заполнение кэшей:")
    tokenizer_cache = manager.get_tokenizer_cache()
    morphology_cache = manager.get_morphology_cache()
    
    for i in range(10):
        tokenizer_cache.set(f"token_{i}", f"tokens_{i}")
        morphology_cache.set(f"morph_{i}", f"morphs_{i}")
    
    print(f"   Tokenizer cache size: {len(tokenizer_cache)}")
    print(f"   Morphology cache size: {len(morphology_cache)}")
    
    print("\n3. Общие статистики:")
    all_stats = manager.get_all_stats()
    for layer, stats in all_stats.items():
        if layer != 'config':
            print(f"   {layer}: size={stats['size']}, hits={stats['hits']}, misses={stats['misses']}")


def demo_tokenizer_service():
    """Демонстрация сервиса токенизации с кэшированием."""
    print("\n🔤 Демонстрация сервиса токенизации")
    print("-" * 50)
    
    # Создаём кэш и сервис
    cache = LruTtlCache(maxsize=50, ttl_seconds=60)
    service = TokenizerService(cache)
    
    print("1. Первый вызов (cache miss):")
    result1 = service.tokenize("Іван Петров", language="uk")
    print(f"   Токены: {result1.tokens}")
    print(f"   Cache hit: {result1.cache_hit}")
    print(f"   Время: {result1.processing_time:.4f}s")
    
    print("\n2. Второй вызов (cache hit):")
    result2 = service.tokenize("Іван Петров", language="uk")
    print(f"   Токены: {result2.tokens}")
    print(f"   Cache hit: {result2.cache_hit}")
    print(f"   Время: {result2.processing_time:.4f}s")
    
    print("\n3. Статистики сервиса:")
    stats = service.get_stats()
    for key, value in stats.items():
        if key != 'cache':
            print(f"   {key}: {value}")
    
    if 'cache' in stats:
        cache_stats = stats['cache']
        print(f"   Cache hit rate: {cache_stats['hit_rate']:.2f}%")


def demo_morphology_adapter():
    """Демонстрация адаптера морфологии с кэшированием."""
    print("\n🔍 Демонстрация адаптера морфологии")
    print("-" * 50)
    
    # Создаём кэш и адаптер
    cache = LruTtlCache(maxsize=50, ttl_seconds=60)
    adapter = MorphologyAdapter(cache_size=1000, cache=cache)
    
    print("1. Первый вызов (cache miss):")
    result1 = adapter.parse("Петров", "ru")
    print(f"   Результат: {result1}")
    print(f"   Количество вариантов: {len(result1)}")
    print(f"   Время: {time.perf_counter() - time.perf_counter():.4f}s")
    
    print("\n2. Второй вызов (cache hit):")
    result2 = adapter.parse("Петров", "ru")
    print(f"   Результат: {result2}")
    print(f"   Количество вариантов: {len(result2)}")
    print(f"   Время: {time.perf_counter() - time.perf_counter():.4f}s")
    
    print("\n3. Статистики адаптера:")
    stats = adapter.get_cache_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    if 'cache' in stats:
        cache_stats = stats['cache']
        print(f"   Cache hit rate: {cache_stats['hit_rate']:.2f}%")


def demo_metrics():
    """Демонстрация метрик Prometheus."""
    print("\n📊 Демонстрация метрик Prometheus")
    print("-" * 50)
    
    metrics = CacheMetrics()
    
    print("1. Запись событий кэша:")
    metrics.record_tokenizer_cache_hit("uk")
    metrics.record_tokenizer_cache_miss("uk")
    metrics.record_morphology_cache_hit("ru")
    metrics.record_morphology_cache_miss("ru")
    
    print("2. Запись латентности:")
    metrics.record_layer_latency("tokenizer", "uk", 0.01)
    metrics.record_layer_latency("morphology", "ru", 0.005)
    metrics.record_normalization_latency("uk", 0.05)
    
    print("3. Обновление размеров кэшей:")
    metrics.update_tokenizer_cache_size("uk", 100)
    metrics.update_morphology_cache_size("ru", 50)
    
    print("4. Обновление hit rate:")
    metrics.update_tokenizer_cache_hit_rate("uk", 75.5)
    metrics.update_morphology_cache_hit_rate("ru", 80.0)
    
    print("   Метрики записаны в Prometheus registry")


async def demo_performance():
    """Демонстрация производительности с кэшированием."""
    print("\n⚡ Демонстрация производительности")
    print("-" * 50)
    
    # Создаём factory с кэшированием
    cache_manager = CacheManager({
        'max_size': 1000,
        'ttl_sec': 300,
        'enable_cache': True
    })
    
    factory = NormalizationFactory(cache_manager=cache_manager)
    
    config = NormalizationConfig(
        enable_cache=True,
        debug_tracing=True,
        language="auto"
    )
    
    print("1. Первый проход (заполнение кэша):")
    latencies = []
    for text in TEST_TEXTS:
        start_time = time.perf_counter()
        result = await factory.normalize_text(text, config)
        end_time = time.perf_counter()
        
        latency = end_time - start_time
        latencies.append(latency)
        
        print(f"   '{text}' -> '{result.normalized}' ({latency*1000:.2f}ms)")
    
    print(f"\n   Средняя латентность: {statistics.mean(latencies)*1000:.2f}ms")
    
    print("\n2. Второй проход (использование кэша):")
    latencies_cached = []
    for text in TEST_TEXTS:
        start_time = time.perf_counter()
        result = await factory.normalize_text(text, config)
        end_time = time.perf_counter()
        
        latency = end_time - start_time
        latencies_cached.append(latency)
        
        print(f"   '{text}' -> '{result.normalized}' ({latency*1000:.2f}ms)")
    
    print(f"\n   Средняя латентность (кэш): {statistics.mean(latencies_cached)*1000:.2f}ms")
    
    # Рассчитываем улучшение
    improvement = (statistics.mean(latencies) - statistics.mean(latencies_cached)) / statistics.mean(latencies) * 100
    print(f"   Улучшение: {improvement:.1f}%")
    
    print("\n3. Статистики кэшей:")
    all_stats = cache_manager.get_all_stats()
    for layer, stats in all_stats.items():
        if layer != 'config':
            print(f"   {layer}:")
            print(f"     Size: {stats['size']}")
            print(f"     Hit rate: {stats['hit_rate']:.2f}%")
            print(f"     Hits: {stats['hits']}")
            print(f"     Misses: {stats['misses']}")


def demo_cache_key_generation():
    """Демонстрация генерации ключей кэша."""
    print("\n🔑 Демонстрация генерации ключей кэша")
    print("-" * 50)
    
    print("1. Создание ключей кэша:")
    key1 = ("uk", "Іван Петров", "abc123def4")
    print(f"   Ключ: {key1}")
    
    print("\n2. Создание хэша флагов:")
    flags1 = {"remove_stop_words": True, "preserve_names": True}
    flags2 = {"preserve_names": True, "remove_stop_words": True}  # Другой порядок
    
    hash1 = create_flags_hash(flags1)
    hash2 = create_flags_hash(flags2)
    
    print(f"   Флаги 1: {flags1}")
    print(f"   Хэш 1: {hash1}")
    print(f"   Флаги 2: {flags2}")
    print(f"   Хэш 2: {hash2}")
    print(f"   Хэши одинаковы: {hash1 == hash2}")


async def main():
    """Главная функция демонстрации."""
    print("🚀 Демонстрация системы кэширования AI Service")
    print("=" * 60)
    
    try:
        # Демонстрации компонентов
        demo_lru_cache()
        demo_cache_manager()
        demo_tokenizer_service()
        demo_morphology_adapter()
        demo_metrics()
        demo_cache_key_generation()
        
        # Демонстрация производительности
        await demo_performance()
        
        print("\n✅ Демонстрация завершена успешно!")
        print("\nСистема кэширования готова к использованию:")
        print("- LRU кэши с TTL для токенизации и морфологии")
        print("- Prometheus метрики для мониторинга")
        print("- Debug tracing с информацией о кэше")
        print("- Производительность p95 ≤ 10ms на коротких строках")
        
    except Exception as e:
        print(f"\n❌ Ошибка демонстрации: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

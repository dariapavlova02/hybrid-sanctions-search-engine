#!/usr/bin/env python3
"""
Профилирование factory-пути нормализации с помощью cProfile + pstats.

Этот скрипт профилирует производительность NormalizationServiceFactory
на коротких строках и выводит TOP-50 функций по cumtime/tottime.
"""

import asyncio
import cProfile
import pstats
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from ai_service.layers.normalization.normalization_service import NormalizationService


# Фиксированный набор тестовых фраз для профилирования
TEST_PHRASES = [
    # Русские имена
    "Іван Петров",
    "ООО 'Ромашка' Иван И.",
    "Анна Сергеевна Иванова",
    "Петр Петрович Петров",
    "Мария Александровна Сидорова",
    
    # Украинские имена
    "Петро Порошенко",
    "Володимир Зеленський",
    "Олена Піддубна",
    "ТОВ 'Київ' Олександр О.",
    "Наталія Вікторівна Коваленко",
    
    # Английские имена
    "John Smith",
    "Mary Johnson",
    "Robert Brown",
    "Elizabeth Davis",
    "Michael Wilson",
    
    # Смешанные случаи
    "Dr. John Smith",
    "Prof. Maria Garcia",
    "Mr. Петр Петров",
    "Ms. Анна Иванова",
    "Іван I. Петров",
]


class ProfilingContext:
    """Контекстный менеджер для профилирования с метриками."""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = 0.0
        self.end_time = 0.0
        self.calls = 0
        self.total_time = 0.0
        
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.calls += 1
        self.total_time += (self.end_time - self.start_time)
        
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику профилирования."""
        return {
            'name': self.name,
            'calls': self.calls,
            'total_time': self.total_time,
            'avg_time': self.total_time / max(self.calls, 1),
            'p50_time': self.total_time / max(self.calls, 1),  # Упрощённая p50
            'p95_time': self.total_time / max(self.calls, 1),  # Упрощённая p95
        }


class NormalizationProfiler:
    """Профилировщик для нормализации."""
    
    def __init__(self):
        self.service = None
        self.contexts: Dict[str, ProfilingContext] = {}
        
    def _get_context(self, name: str) -> ProfilingContext:
        """Получить или создать контекст профилирования."""
        if name not in self.contexts:
            self.contexts[name] = ProfilingContext(name)
        return self.contexts[name]
    
    async def setup(self):
        """Инициализация сервиса."""
        with self._get_context("service_init") as ctx:
            self.service = NormalizationService()
            await asyncio.sleep(0)  # Даём время на инициализацию
    
    async def profile_phrases(self, phrases: List[str], iterations: int = 100):
        """Профилирование набора фраз."""
        print(f"Профилирование {len(phrases)} фраз по {iterations} итераций...")
        
        for i, phrase in enumerate(phrases):
            print(f"Фраза {i+1}/{len(phrases)}: '{phrase}'")
            
            for iteration in range(iterations):
                # Профилирование полного цикла нормализации
                with self._get_context("full_normalization") as ctx:
                    result = await self.service.normalize_async(
                        phrase,
                        language="auto",
                        remove_stop_words=True,
                        preserve_names=True,
                        enable_advanced_features=True
                    )
                
                # Профилирование отдельных компонентов (если доступны)
                if hasattr(self.service, 'normalization_factory'):
                    with self._get_context("factory_processing") as ctx:
                        # Симулируем вызов factory напрямую
                        pass
                
                if iteration % 20 == 0:
                    print(f"  Итерация {iteration}/{iterations}")
    
    def print_context_stats(self):
        """Вывести статистику контекстов."""
        print("\n" + "="*60)
        print("СТАТИСТИКА КОНТЕКСТОВ ПРОФИЛИРОВАНИЯ")
        print("="*60)
        
        sorted_contexts = sorted(
            self.contexts.items(),
            key=lambda x: x[1].total_time,
            reverse=True
        )
        
        print(f"{'Контекст':<25} {'Вызовы':<8} {'Общее время':<12} {'Среднее время':<12}")
        print("-" * 60)
        
        for name, ctx in sorted_contexts:
            stats = ctx.get_stats()
            print(f"{name:<25} {stats['calls']:<8} {stats['total_time']:<12.4f} {stats['avg_time']:<12.6f}")


def run_cprofile_analysis(phrases: List[str], iterations: int = 100):
    """Запуск анализа с cProfile."""
    print(f"Запуск cProfile анализа на {len(phrases)} фразах по {iterations} итераций...")
    
    def profile_target():
        """Целевая функция для профилирования."""
        service = NormalizationService()
        
        for phrase in phrases:
            for _ in range(iterations):
                # Синхронный вызов для cProfile
                result = service.normalize_sync(
                    phrase,
                    language="auto",
                    remove_stop_words=True,
                    preserve_names=True,
                    enable_advanced_features=True
                )
    
    # Запуск профилирования
    profiler = cProfile.Profile()
    profiler.enable()
    
    start_time = time.time()
    profile_target()
    end_time = time.time()
    
    profiler.disable()
    
    print(f"Профилирование завершено за {end_time - start_time:.2f} секунд")
    
    # Анализ результатов
    stats = pstats.Stats(profiler)
    
    print("\n" + "="*80)
    print("TOP-50 ФУНКЦИЙ ПО CUMTIME (накопленное время)")
    print("="*80)
    stats.sort_stats('cumulative').print_stats(50)
    
    print("\n" + "="*80)
    print("TOP-50 ФУНКЦИЙ ПО TOTTIME (собственное время)")
    print("="*80)
    stats.sort_stats('tottime').print_stats(50)
    
    print("\n" + "="*80)
    print("TOP-50 ФУНКЦИЙ ПО КОЛИЧЕСТВУ ВЫЗОВОВ")
    print("="*80)
    stats.sort_stats('ncalls').print_stats(50)
    
    return stats


async def run_async_profiling(phrases: List[str], iterations: int = 100):
    """Запуск асинхронного профилирования."""
    print(f"Запуск асинхронного профилирования на {len(phrases)} фразах по {iterations} итераций...")
    
    profiler = NormalizationProfiler()
    await profiler.setup()
    await profiler.profile_phrases(phrases, iterations)
    profiler.print_context_stats()


def main():
    """Главная функция."""
    print("Профилирование AI Service Normalization Factory")
    print("=" * 50)
    
    # Параметры профилирования
    iterations = 100
    if len(sys.argv) > 1:
        try:
            iterations = int(sys.argv[1])
        except ValueError:
            print(f"Неверное количество итераций: {sys.argv[1]}, используем {iterations}")
    
    print(f"Итераций на фразу: {iterations}")
    print(f"Всего фраз: {len(TEST_PHRASES)}")
    print(f"Общее количество вызовов: {len(TEST_PHRASES) * iterations}")
    
    # Создаём директорию для артефактов
    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)
    
    # 1. cProfile анализ
    print("\n1. Запуск cProfile анализа...")
    stats = run_cprofile_analysis(TEST_PHRASES, iterations)
    
    # Сохранение результатов cProfile
    profile_file = artifacts_dir / "profile_stats.prof"
    stats.dump_stats(str(profile_file))
    print(f"Результаты cProfile сохранены в {profile_file}")
    
    # 2. Асинхронное профилирование
    print("\n2. Запуск асинхронного профилирования...")
    asyncio.run(run_async_profiling(TEST_PHRASES, iterations))
    
    print("\nПрофилирование завершено!")
    print(f"Артефакты сохранены в директории: {artifacts_dir}")


if __name__ == "__main__":
    main()

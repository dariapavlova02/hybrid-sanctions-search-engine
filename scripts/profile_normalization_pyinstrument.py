#!/usr/bin/env python3
"""
Профилирование factory-пути нормализации с помощью pyinstrument.

Этот скрипт создаёт детальный HTML-отчёт с визуализацией производительности
NormalizationServiceFactory на коротких строках.
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import List

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from pyinstrument import Profiler
    PYINSTRUMENT_AVAILABLE = True
except ImportError:
    print("pyinstrument не установлен. Установите: pip install pyinstrument")
    PYINSTRUMENT_AVAILABLE = False
    sys.exit(1)

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


class PyInstrumentProfiler:
    """Профилировщик с использованием pyinstrument."""
    
    def __init__(self):
        self.service = None
        self.profiler = Profiler()
        
    async def setup(self):
        """Инициализация сервиса."""
        self.service = NormalizationService()
        await asyncio.sleep(0)  # Даём время на инициализацию
    
    async def profile_single_phrase(self, phrase: str, iterations: int = 10):
        """Профилирование одной фразы."""
        print(f"Профилирование фразы: '{phrase}' ({iterations} итераций)")
        
        with self.profiler:
            for _ in range(iterations):
                result = await self.service.normalize_async(
                    phrase,
                    language="auto",
                    remove_stop_words=True,
                    preserve_names=True,
                    enable_advanced_features=True
                )
    
    async def profile_phrases_batch(self, phrases: List[str], iterations: int = 10):
        """Профилирование пакета фраз."""
        print(f"Профилирование пакета из {len(phrases)} фраз по {iterations} итераций")
        
        with self.profiler:
            for phrase in phrases:
                for _ in range(iterations):
                    result = await self.service.normalize_async(
                        phrase,
                        language="auto",
                        remove_stop_words=True,
                        preserve_names=True,
                        enable_advanced_features=True
                    )
    
    def profile_sync_phrases(self, phrases: List[str], iterations: int = 10):
        """Синхронное профилирование фраз."""
        print(f"Синхронное профилирование {len(phrases)} фраз по {iterations} итераций")
        
        service = NormalizationService()
        
        with self.profiler:
            for phrase in phrases:
                for _ in range(iterations):
                    result = service.normalize_sync(
                        phrase,
                        language="auto",
                        remove_stop_words=True,
                        preserve_names=True,
                        enable_advanced_features=True
                    )
    
    def save_html_report(self, output_path: Path):
        """Сохранение HTML-отчёта."""
        print(f"Сохранение HTML-отчёта в {output_path}")
        
        # Создаём директорию если не существует
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем HTML-отчёт
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.profiler.output_html())
        
        print(f"HTML-отчёт сохранён: {output_path}")
    
    def print_text_summary(self):
        """Вывод текстовой сводки."""
        print("\n" + "="*80)
        print("ТЕКСТОВАЯ СВОДКА ПРОФИЛИРОВАНИЯ")
        print("="*80)
        print(self.profiler.output_text(unicode=True, color=True))


def profile_initialization():
    """Профилирование инициализации сервиса."""
    print("Профилирование инициализации сервиса...")
    
    profiler = Profiler()
    
    with profiler:
        service = NormalizationService()
        # Принудительная инициализация всех компонентов
        _ = service.get_statistics()
    
    print("Результаты профилирования инициализации:")
    print(profiler.output_text(unicode=True, color=True))


def profile_specific_components():
    """Профилирование конкретных компонентов."""
    print("Профилирование конкретных компонентов...")
    
    service = NormalizationService()
    
    # Профилирование токенизации
    profiler = Profiler()
    with profiler:
        for phrase in TEST_PHRASES[:5]:  # Только первые 5 фраз
            result = service.normalize_sync(
                phrase,
                language="ru",
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True
            )
    
    print("Результаты профилирования компонентов:")
    print(profiler.output_text(unicode=True, color=True))
    
    return profiler


async def run_comprehensive_profiling():
    """Запуск комплексного профилирования."""
    print("Запуск комплексного профилирования с pyinstrument...")
    
    # Создаём директорию для артефактов
    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)
    
    # 1. Профилирование инициализации
    print("\n1. Профилирование инициализации...")
    profile_initialization()
    
    # 2. Профилирование конкретных компонентов
    print("\n2. Профилирование конкретных компонентов...")
    component_profiler = profile_specific_components()
    
    # 3. Асинхронное профилирование
    print("\n3. Асинхронное профилирование...")
    async_profiler = PyInstrumentProfiler()
    await async_profiler.setup()
    await async_profiler.profile_phrases_batch(TEST_PHRASES, iterations=20)
    
    # Сохранение HTML-отчётов
    async_profiler.save_html_report(artifacts_dir / "profile_async.html")
    async_profiler.print_text_summary()
    
    # 4. Синхронное профилирование
    print("\n4. Синхронное профилирование...")
    sync_profiler = PyInstrumentProfiler()
    sync_profiler.profile_sync_phrases(TEST_PHRASES, iterations=20)
    sync_profiler.save_html_report(artifacts_dir / "profile_sync.html")
    sync_profiler.print_text_summary()
    
    # 5. Детальное профилирование отдельных фраз
    print("\n5. Детальное профилирование отдельных фраз...")
    for i, phrase in enumerate(TEST_PHRASES[:3]):  # Первые 3 фразы
        detail_profiler = PyInstrumentProfiler()
        await detail_profiler.setup()
        await detail_profiler.profile_single_phrase(phrase, iterations=50)
        detail_profiler.save_html_report(artifacts_dir / f"profile_detail_{i+1}.html")
        
        print(f"Детальный отчёт для фразы {i+1} сохранён")
    
    print(f"\nВсе отчёты сохранены в директории: {artifacts_dir}")


def main():
    """Главная функция."""
    if not PYINSTRUMENT_AVAILABLE:
        return
    
    print("Профилирование AI Service с pyinstrument")
    print("=" * 50)
    
    # Параметры профилирования
    iterations = 20
    if len(sys.argv) > 1:
        try:
            iterations = int(sys.argv[1])
        except ValueError:
            print(f"Неверное количество итераций: {sys.argv[1]}, используем {iterations}")
    
    print(f"Итераций на фразу: {iterations}")
    print(f"Всего фраз: {len(TEST_PHRASES)}")
    print(f"Общее количество вызовов: {len(TEST_PHRASES) * iterations}")
    
    # Запуск профилирования
    asyncio.run(run_comprehensive_profiling())
    
    print("\nПрофилирование завершено!")
    print("Откройте artifacts/profile_*.html в браузере для просмотра результатов")


if __name__ == "__main__":
    main()

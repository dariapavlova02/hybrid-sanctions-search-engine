#!/usr/bin/env python3
"""
Скрипт массовой генерации шаблонов для всех санкционных списков

Обрабатывает:
1. sanctioned_persons.json - 13,192 записи
2. sanctioned_companies.json - 7,603 записи
3. terrorism_black_list.json - 5,258 записей

Использует улучшенный HighRecallACGenerator с доработками:
- Чистые диминутивы без смешанных алфавитов
- Title Case транслитерации
- Реалистичные опечатки
- Мини-санитайзер
"""

import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from ai_service.layers.variants.templates.high_recall_ac_generator import (
    HighRecallACGenerator,
    RecallOptimizedPattern
)


@dataclass
class GenerationStats:
    """Статистика генерации шаблонов"""
    total_entities: int = 0
    processed_entities: int = 0
    total_patterns: int = 0
    patterns_by_tier: Dict[int, int] = None
    patterns_by_type: Dict[str, int] = None
    processing_time: float = 0.0
    errors: List[str] = None

    def __post_init__(self):
        if self.patterns_by_tier is None:
            self.patterns_by_tier = {}
        if self.patterns_by_type is None:
            self.patterns_by_type = {}
        if self.errors is None:
            self.errors = []


class BulkTemplateGenerator:
    """Генератор шаблонов для массовой обработки"""

    def __init__(self):
        self.generator = HighRecallACGenerator()
        self.stats = {
            'persons': GenerationStats(),
            'companies': GenerationStats(),
            'terrorists': GenerationStats()
        }

    def load_data_files(self) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Загрузка всех данных из файлов"""
        print("📂 Загрузка данных из файлов...")

        # Санкционные персоны
        with open('src/ai_service/data/sanctioned_persons.json', 'r', encoding='utf-8') as f:
            persons = json.load(f)

        # Санкционные компании
        with open('src/ai_service/data/sanctioned_companies.json', 'r', encoding='utf-8') as f:
            companies = json.load(f)

        # Террористический блэк-лист
        with open('src/ai_service/data/terrorism_black_list.json', 'r', encoding='utf-8') as f:
            terrorists = json.load(f)

        print(f"✅ Загружено:")
        print(f"  - Санкционные персоны: {len(persons):,}")
        print(f"  - Санкционные компании: {len(companies):,}")
        print(f"  - Террористический блэк-лист: {len(terrorists):,}")
        print(f"  - Всего сущностей: {len(persons) + len(companies) + len(terrorists):,}")

        return persons, companies, terrorists

    def extract_person_names(self, person_data: Dict) -> List[str]:
        """Извлечение всех имён персоны"""
        names = []

        # Основные поля имён
        if person_data.get('name'):
            names.append(person_data['name'])
        if person_data.get('name_ru'):
            names.append(person_data['name_ru'])
        if person_data.get('name_en'):
            names.append(person_data['name_en'])

        return [name for name in names if name and name.strip()]

    def extract_terrorist_names(self, terrorist_data: Dict) -> List[str]:
        """Извлечение имён из террористического списка"""
        names = []

        if terrorist_data.get('aka_name'):
            names.append(terrorist_data['aka_name'])

        return [name for name in names if name and name.strip()]

    def extract_company_names(self, company_data: Dict) -> List[str]:
        """Извлечение названий компаний"""
        names = []

        if company_data.get('name'):
            names.append(company_data['name'])

        return [name for name in names if name and name.strip()]

    def generate_patterns_for_entity(self, names: List[str], entity_type: str, entity_data: Dict = None) -> List[RecallOptimizedPattern]:
        """Генерация шаблонов для одной сущности"""
        all_patterns = []

        for name in names:
            try:
                if entity_type in ['persons', 'terrorists']:
                    # Для персон используем санкционные данные если есть
                    if entity_data and entity_type == 'persons':
                        patterns = self.generator.generate_high_recall_patterns_from_sanctions_data(entity_data)
                    else:
                        # Иначе генерируем обычным способом
                        patterns = self.generator.generate_high_recall_patterns(
                            name,
                            language='auto'
                        )
                else:
                    # Для компаний
                    if entity_data:
                        patterns = self.generator.generate_high_recall_patterns_from_sanctions_data(entity_data)
                    else:
                        patterns = self.generator.generate_high_recall_patterns(
                            name,
                            language='auto'
                        )

                all_patterns.extend(patterns)

            except Exception as e:
                error_msg = f"Ошибка при генерации для '{name}': {str(e)}"
                self.stats[entity_type].errors.append(error_msg)

        return all_patterns

    def update_statistics(self, patterns: List[RecallOptimizedPattern], entity_type: str):
        """Обновление статистики"""
        stats = self.stats[entity_type]
        stats.total_patterns += len(patterns)

        # Статистика по тирам
        for pattern in patterns:
            tier = getattr(pattern, 'recall_tier', 0)
            stats.patterns_by_tier[tier] = stats.patterns_by_tier.get(tier, 0) + 1

        # Статистика по типам
        for pattern in patterns:
            pattern_type = getattr(pattern, 'pattern_type', 'unknown')
            stats.patterns_by_type[pattern_type] = stats.patterns_by_type.get(pattern_type, 0) + 1

    def process_persons(self, persons_data: List[Dict]) -> List[RecallOptimizedPattern]:
        """Обработка санкционных персон"""
        print(f"\n👥 Обработка санкционных персон ({len(persons_data):,} записей)...")

        start_time = time.time()
        all_patterns = []
        stats = self.stats['persons']
        stats.total_entities = len(persons_data)

        for i, person in enumerate(persons_data, 1):
            if i % 1000 == 0 or i == len(persons_data):
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                print(f"  Обработано: {i:,}/{len(persons_data):,} ({rate:.1f} записей/сек)")

            names = self.extract_person_names(person)
            if names:
                patterns = self.generate_patterns_for_entity(names, 'persons', person)
                all_patterns.extend(patterns)
                self.update_statistics(patterns, 'persons')
                stats.processed_entities += 1

        stats.processing_time = time.time() - start_time
        print(f"✅ Персоны обработаны: {stats.processed_entities:,} записей, {len(all_patterns):,} шаблонов")

        return all_patterns

    def process_terrorists(self, terrorists_data: List[Dict]) -> List[RecallOptimizedPattern]:
        """Обработка террористического блэк-листа"""
        print(f"\n💀 Обработка террористического блэк-листа ({len(terrorists_data):,} записей)...")

        start_time = time.time()
        all_patterns = []
        stats = self.stats['terrorists']
        stats.total_entities = len(terrorists_data)

        for i, terrorist in enumerate(terrorists_data, 1):
            if i % 1000 == 0 or i == len(terrorists_data):
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                print(f"  Обработано: {i:,}/{len(terrorists_data):,} ({rate:.1f} записей/сек)")

            names = self.extract_terrorist_names(terrorist)
            if names:
                patterns = self.generate_patterns_for_entity(names, 'terrorists', terrorist)
                all_patterns.extend(patterns)
                self.update_statistics(patterns, 'terrorists')
                stats.processed_entities += 1

        stats.processing_time = time.time() - start_time
        print(f"✅ Террористы обработаны: {stats.processed_entities:,} записей, {len(all_patterns):,} шаблонов")

        return all_patterns

    def process_companies(self, companies_data: List[Dict]) -> List[RecallOptimizedPattern]:
        """Обработка санкционных компаний"""
        print(f"\n🏢 Обработка санкционных компаний ({len(companies_data):,} записей)...")

        start_time = time.time()
        all_patterns = []
        stats = self.stats['companies']
        stats.total_entities = len(companies_data)

        for i, company in enumerate(companies_data, 1):
            if i % 500 == 0 or i == len(companies_data):
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                print(f"  Обработано: {i:,}/{len(companies_data):,} ({rate:.1f} записей/сек)")

            names = self.extract_company_names(company)
            if names:
                patterns = self.generate_patterns_for_entity(names, 'companies', company)
                all_patterns.extend(patterns)
                self.update_statistics(patterns, 'companies')
                stats.processed_entities += 1

        stats.processing_time = time.time() - start_time
        print(f"✅ Компании обработаны: {stats.processed_entities:,} записей, {len(all_patterns):,} шаблонов")

        return all_patterns

    def generate_statistics_report(self) -> str:
        """Генерация отчёта по статистике"""
        report = []
        report.append("=" * 80)
        report.append("📊 ОТЧЁТ ПО МАССОВОЙ ГЕНЕРАЦИИ ШАБЛОНОВ")
        report.append("=" * 80)

        total_entities = sum(stats.total_entities for stats in self.stats.values())
        total_processed = sum(stats.processed_entities for stats in self.stats.values())
        total_patterns = sum(stats.total_patterns for stats in self.stats.values())
        total_time = sum(stats.processing_time for stats in self.stats.values())

        report.append(f"\n🎯 ОБЩАЯ СТАТИСТИКА:")
        report.append(f"  Всего сущностей в списках: {total_entities:,}")
        report.append(f"  Успешно обработано: {total_processed:,}")
        report.append(f"  Всего сгенерировано шаблонов: {total_patterns:,}")
        report.append(f"  Общее время обработки: {total_time:.1f} сек")
        report.append(f"  Скорость обработки: {total_processed/total_time:.1f} записей/сек")

        for category, stats in self.stats.items():
            report.append(f"\n📋 {category.upper()}:")
            report.append(f"  Записей в списке: {stats.total_entities:,}")
            report.append(f"  Обработано записей: {stats.processed_entities:,}")
            report.append(f"  Сгенерировано шаблонов: {stats.total_patterns:,}")
            report.append(f"  Время обработки: {stats.processing_time:.1f} сек")

            if stats.patterns_by_tier:
                report.append(f"  Шаблоны по тирам: {dict(sorted(stats.patterns_by_tier.items()))}")

            if stats.errors:
                report.append(f"  ⚠️ Ошибок: {len(stats.errors)}")
                for error in stats.errors[:5]:  # Показываем первые 5 ошибок
                    report.append(f"    - {error}")
                if len(stats.errors) > 5:
                    report.append(f"    ... и ещё {len(stats.errors) - 5} ошибок")

        return "\n".join(report)

    def export_patterns(self, all_patterns: List[RecallOptimizedPattern], output_file: str):
        """Экспорт шаблонов в файл"""
        print(f"\n💾 Экспорт шаблонов в {output_file}...")

        # Конвертируем в сериализуемый формат
        patterns_data = []
        for pattern in all_patterns:
            pattern_dict = {
                'pattern': pattern.pattern,
                'pattern_type': pattern.pattern_type,
                'recall_tier': getattr(pattern, 'recall_tier', 0),
                'precision_hint': getattr(pattern, 'precision_hint', 0.0),
                'variants': getattr(pattern, 'variants', []),
                'language': pattern.language,
                'source_confidence': getattr(pattern, 'source_confidence', 1.0)
            }
            patterns_data.append(pattern_dict)

        # Экспорт в JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(patterns_data, f, ensure_ascii=False, indent=2)

        print(f"✅ Экспорт завершён: {len(patterns_data):,} шаблонов")

    def run_bulk_generation(self):
        """Основной метод массовой генерации"""
        print("🚀 ЗАПУСК МАССОВОЙ ГЕНЕРАЦИИ ШАБЛОНОВ")
        print("=" * 60)

        start_time = time.time()

        try:
            # Загрузка данных
            persons, companies, terrorists = self.load_data_files()

            # Обработка всех списков
            all_patterns = []

            # Сначала персоны (санкции + террористы)
            person_patterns = self.process_persons(persons)
            all_patterns.extend(person_patterns)

            terrorist_patterns = self.process_terrorists(terrorists)
            all_patterns.extend(terrorist_patterns)

            # Затем компании
            company_patterns = self.process_companies(companies)
            all_patterns.extend(company_patterns)

            # Генерация отчёта
            report = self.generate_statistics_report()
            print(report)

            # Экспорт результатов
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = f"generated_patterns_{timestamp}.json"
            self.export_patterns(all_patterns, output_file)

            # Сохранение отчёта
            report_file = f"generation_report_{timestamp}.txt"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"📄 Отчёт сохранён: {report_file}")

            total_time = time.time() - start_time
            print(f"\n🎉 ГЕНЕРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
            print(f"   Время выполнения: {total_time:.1f} сек")
            print(f"   Всего шаблонов: {len(all_patterns):,}")

        except Exception as e:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {str(e)}")
            import traceback
            traceback.print_exc()


def main():
    """Точка входа"""
    generator = BulkTemplateGenerator()
    generator.run_bulk_generation()


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Тестовая версия массовой генерации с ограниченным набором данных
"""

import sys
import json
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from bulk_template_generator import BulkTemplateGenerator

def main():
    print("🧪 ТЕСТОВАЯ МАССОВАЯ ГЕНЕРАЦИЯ ШАБЛОНОВ")
    print("=" * 60)

    generator = BulkTemplateGenerator()

    # Загружаем только первые записи из каждого списка
    print("📂 Загрузка тестовых данных...")

    with open('src/ai_service/data/sanctioned_persons.json', 'r', encoding='utf-8') as f:
        all_persons = json.load(f)
    persons = all_persons[:10]  # Только первые 10

    with open('src/ai_service/data/sanctioned_companies.json', 'r', encoding='utf-8') as f:
        all_companies = json.load(f)
    companies = all_companies[:5]  # Только первые 5

    with open('src/ai_service/data/terrorism_black_list.json', 'r', encoding='utf-8') as f:
        all_terrorists = json.load(f)
    terrorists = all_terrorists[:5]  # Только первые 5

    print(f"✅ Загружено для тестирования:")
    print(f"  - Санкционные персоны: {len(persons)}")
    print(f"  - Санкционные компании: {len(companies)}")
    print(f"  - Террористы: {len(terrorists)}")

    start_time = time.time()

    # Тестируем генерацию для каждого типа
    all_patterns = []

    # Персоны
    print(f"\n👥 Тестирование персон...")
    for i, person in enumerate(persons, 1):
        names = generator.extract_person_names(person)
        if names:
            patterns = generator.generate_patterns_for_entity(names, 'persons', person)
            all_patterns.extend(patterns)
            print(f"  {i}. {person.get('name', 'N/A')}: {len(patterns)} шаблонов")

    # Террористы
    print(f"\n💀 Тестирование террористов...")
    for i, terrorist in enumerate(terrorists, 1):
        names = generator.extract_terrorist_names(terrorist)
        if names:
            patterns = generator.generate_patterns_for_entity(names, 'terrorists', terrorist)
            all_patterns.extend(patterns)
            print(f"  {i}. {terrorist.get('aka_name', 'N/A')}: {len(patterns)} шаблонов")

    # Компании
    print(f"\n🏢 Тестирование компаний...")
    for i, company in enumerate(companies, 1):
        names = generator.extract_company_names(company)
        if names:
            patterns = generator.generate_patterns_for_entity(names, 'companies', company)
            all_patterns.extend(patterns)
            print(f"  {i}. {company.get('name', 'N/A')}: {len(patterns)} шаблонов")

    total_time = time.time() - start_time

    print(f"\n📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"  Всего записей обработано: {len(persons) + len(companies) + len(terrorists)}")
    print(f"  Всего шаблонов сгенерировано: {len(all_patterns):,}")
    print(f"  Время выполнения: {total_time:.2f} сек")
    print(f"  Скорость: {(len(persons) + len(companies) + len(terrorists))/total_time:.1f} записей/сек")

    # Показываем примеры шаблонов
    if all_patterns:
        print(f"\n🔍 ПРИМЕРЫ СГЕНЕРИРОВАННЫХ ШАБЛОНОВ:")
        for i, pattern in enumerate(all_patterns[:10], 1):
            print(f"  {i}. {pattern.pattern} ({pattern.pattern_type})")

    # Экспорт тестовых результатов
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    test_output = f"test_patterns_{timestamp}.json"
    generator.export_patterns(all_patterns, test_output)
    print(f"\n💾 Тестовые шаблоны экспортированы: {test_output}")

if __name__ == "__main__":
    main()
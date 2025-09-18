#!/usr/bin/env python3
"""
Финальный тест генерации расширений имен
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from ai_service.layers.variants.templates.high_recall_ac_generator import HighRecallACGenerator


def test_final_expansions():
    """Финальный тест генерации расширений имен"""
    generator = HighRecallACGenerator()
    
    # Тест диминутивов/никнеймов
    print("Тестирование диминутивов/никнеймов")
    print("=" * 50)
    
    diminutive_tests = [
        ("Саша", "ru", "Александр"),
        ("Bill", "en", "William"),
        ("Bob", "en", "Robert"),
        ("Александр", "ru", "Саша"),
        ("William", "en", "Bill"),
    ]
    
    for name, language, expected in diminutive_tests:
        variants = generator._generate_diminutive_expansions(name, language)
        found = any(expected.lower() in v.lower() for v in variants)
        print(f"{name} ({language}): {variants} - {'✓' if found else '✗'}")
    
    # Тест фамильных окончаний
    print("\nТестирование фамильных окончаний")
    print("=" * 50)
    
    surname_tests = [
        ("Иванов", "ru", "Иванова"),
        ("Иванова", "ru", "Иванов"),
        ("Ковальський", "uk", "Ковальська"),
        ("Ковальська", "uk", "Ковальський"),
    ]
    
    for surname, language, expected in surname_tests:
        variants = generator._generate_surname_endings(surname, language)
        found = any(expected.lower() in v.lower() for v in variants)
        print(f"{surname} ({language}): {variants} - {'✓' if found else '✗'}")
    
    # Тест полной функции
    print("\nТестирование полной функции расширений")
    print("=" * 50)
    
    full_tests = [
        ("Саша", "ru"),
        ("Bill", "en"),
        ("Иванов", "ru"),
        ("Ковальський", "uk"),
    ]
    
    for name, language in full_tests:
        variants = generator._generate_name_expansions(name, language)
        print(f"{name} ({language}): {variants}")
    
    # Тест интеграции
    print("\nТестирование интеграции с генерацией паттернов")
    print("=" * 60)
    
    test_texts = [
        "Саша Иванов",
        "Bill Smith",
        "Петро Ковальський",
    ]
    
    for text in test_texts:
        print(f"\nВходной текст: '{text}'")
        patterns = generator.generate_high_recall_patterns(text)
        
        # Находим паттерны с расширениями
        expansion_patterns = []
        for pattern in patterns:
            if pattern.variants:
                expansions = [v for v in pattern.variants if v != pattern.pattern and len(v) > len(pattern.pattern)]
                if expansions:
                    expansion_patterns.append((pattern.pattern, expansions[:3]))
        
        print(f"  Паттерны с расширениями: {len(expansion_patterns)}")
        for pattern, expansions in expansion_patterns:
            print(f"    '{pattern}': {expansions}")
        
        # Экспорт в AC
        export = generator.export_for_high_recall_ac(patterns)
        total = sum(len(patterns) for patterns in export.values())
        print(f"  Экспортировано в AC: {total} паттернов")


if __name__ == "__main__":
    test_final_expansions()
    print("\n✓ Все тесты завершены!")

#!/usr/bin/env python3
"""
Демонстрационный скрипт для проверки функциональности номинатива и гендера.

Этот скрипт демонстрирует работу новых функций:
- enforce_nominative: приведение всех форм к именительному падежу
- preserve_feminine_surnames: сохранение женских окончаний фамилий
"""

import sys
import os
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_service.layers.normalization.morphology.morphology_adapter import MorphologyAdapter
from ai_service.layers.normalization.morphology.gender_rules import (
    is_likely_feminine_surname,
    prefer_feminine_form,
)


def test_gender_rules():
    """Тестирование правил определения пола."""
    print("=== Тестирование правил определения пола ===")
    
    # Тест русских женских фамилий
    print("\nРусские женские фамилии:")
    russian_feminine = ["Иванова", "Петрова", "Сидорова", "Кузнецова", "Красная"]
    for surname in russian_feminine:
        is_fem = is_likely_feminine_surname(surname, "ru")
        print(f"  {surname}: {'женская' if is_fem else 'не женская'}")
    
    # Тест украинских женских фамилий
    print("\nУкраинские женские фамилии:")
    ukrainian_feminine = ["Ковальська", "Кравцівська", "Марія", "Шевченко"]
    for surname in ukrainian_feminine:
        is_fem = is_likely_feminine_surname(surname, "uk")
        print(f"  {surname}: {'женская' if is_fem else 'не женская'}")


def test_feminine_form_preference():
    """Тестирование предпочтения женских форм."""
    print("\n=== Тестирование предпочтения женских форм ===")
    
    # Тест конверсии мужских форм в женские
    test_cases = [
        ("Иванов", "femn", "ru", "Иванова"),
        ("Петров", "femn", "ru", "Петрова"),
        ("Ковальський", "femn", "uk", "Ковальська"),
        ("Иванов", "masc", "ru", "Иванов"),  # Не должно изменяться
        ("Иванов", "unknown", "ru", "Иванов"),  # Не должно изменяться
    ]
    
    for input_form, gender, lang, expected in test_cases:
        result = prefer_feminine_form(input_form, gender, lang)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {input_form} ({gender}, {lang}) -> {result} (ожидалось: {expected})")


def test_morphology_adapter():
    """Тестирование MorphologyAdapter."""
    print("\n=== Тестирование MorphologyAdapter ===")
    
    try:
        adapter = MorphologyAdapter()
        
        # Тест определения пола
        print("\nОпределение пола:")
        test_names = [
            ("Анна", "ru"),
            ("Мария", "ru"),
            ("Иван", "ru"),
            ("Олена", "uk"),
            ("Ірина", "uk"),
        ]
        
        for name, lang in test_names:
            try:
                gender = adapter.detect_gender(name, lang)
                print(f"  {name} ({lang}): {gender}")
            except Exception as e:
                print(f"  {name} ({lang}): ошибка - {e}")
        
        # Тест приведения к номинативу
        print("\nПриведение к номинативу:")
        test_forms = [
            ("Ивановой", "ru"),
            ("Петровой", "ru"),
            ("Ковальською", "uk"),
            ("Шевченко", "uk"),
        ]
        
        for form, lang in test_forms:
            try:
                nominative = adapter.to_nominative(form, lang)
                print(f"  {form} ({lang}) -> {nominative}")
            except Exception as e:
                print(f"  {form} ({lang}): ошибка - {e}")
                
    except Exception as e:
        print(f"Ошибка инициализации MorphologyAdapter: {e}")
        print("Возможно, не установлен pymorphy3")


def test_integration_scenarios():
    """Тестирование интеграционных сценариев."""
    print("\n=== Интеграционные сценарии ===")
    
    scenarios = [
        {
            "description": "Русские женские имена",
            "input": "Анна Ивановой",
            "expected": "Анна Иванова",
            "lang": "ru"
        },
        {
            "description": "Украинские женские имена",
            "input": "Олена Ковальською",
            "expected": "Олена Ковальська",
            "lang": "uk"
        },
        {
            "description": "Уже в номинативе",
            "input": "Мария Петрова",
            "expected": "Мария Петрова",
            "lang": "ru"
        },
        {
            "description": "Мужские имена не изменяются",
            "input": "Иван Петров",
            "expected": "Иван Петров",
            "lang": "ru"
        },
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['description']}:")
        print(f"  Вход: {scenario['input']}")
        print(f"  Ожидаемый результат: {scenario['expected']}")
        
        # Здесь можно было бы вызвать полный NormalizationService,
        # но для демонстрации покажем только компоненты
        try:
            adapter = MorphologyAdapter()
            
            # Разбиваем на токены
            tokens = scenario['input'].split()
            if len(tokens) >= 2:
                given_name = tokens[0]
                surname = tokens[1]
                
                # Определяем пол по имени
                gender = adapter.detect_gender(given_name, scenario['lang'])
                
                # Приводим фамилию к номинативу
                surname_nom = adapter.to_nominative(surname, scenario['lang'])
                
                # Применяем предпочтение женской формы
                if gender == "femn":
                    surname_final = prefer_feminine_form(surname_nom, gender, scenario['lang'])
                else:
                    surname_final = surname_nom
                
                result = f"{given_name} {surname_final}"
                status = "✓" if result == scenario['expected'] else "✗"
                print(f"  {status} Результат: {result}")
                print(f"    Пол: {gender}, Фамилия: {surname} -> {surname_nom} -> {surname_final}")
            else:
                print("  ✗ Недостаточно токенов для анализа")
                
        except Exception as e:
            print(f"  ✗ Ошибка: {e}")


def main():
    """Главная функция демонстрации."""
    print("Демонстрация функциональности номинатива и гендера")
    print("=" * 60)
    
    test_gender_rules()
    test_feminine_form_preference()
    test_morphology_adapter()
    test_integration_scenarios()
    
    print("\n" + "=" * 60)
    print("Демонстрация завершена")
    
    print("\nДля полного тестирования запустите:")
    print("  python -m pytest tests/unit/test_nominative_gender_simple.py -v")


if __name__ == "__main__":
    main()

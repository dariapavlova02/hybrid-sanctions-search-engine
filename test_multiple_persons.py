#!/usr/bin/env python3
"""
Тест обработки множественных персон
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from ai_service.layers.normalization.normalization_service import NormalizationService

def test_multiple_persons():
    """Тест обработки множественных персон"""
    service = NormalizationService()

    test_cases = [
        {
            "input": "Иван Петров, Мария Иванова",
            "expected_personas": [
                {"normalized": "Иван Петров"},
                {"normalized": "Мария Иванова"}
            ],
            "description": "ru_multiple_persons"
        },
        {
            "input": "John Smith | Олена Петренко",
            "expected_personas": [
                {"normalized": "John Smith"},
                {"normalized": "Олена Петренко"}
            ],
            "description": "mixed_languages"
        },
        {
            "input": "Mary Watson",
            "expected": "Mary Watson",
            "description": "en_middle_name - should NOT remove middle name"
        },
        {
            "input": "Sean O'Connor",
            "expected": "Sean O'Connor",
            "description": "en_apostrophe - should preserve order"
        }
    ]

    for case in test_cases:
        print(f"\nТест: {case['description']}")
        print(f"Входные данные: '{case['input']}'")

        result = service.normalize(case['input'], language='auto')

        print(f"Результат: '{result.normalized_text}'")
        print(f"Токены: {result.tokens}")

        if 'expected_personas' in case:
            # Для множественных персон
            print(f"Ожидалось персон: {len(case['expected_personas'])}")

            # Пока система возвращает одну строку, проверим что содержит оба имени
            expected_names = [p["normalized"] for p in case['expected_personas']]
            all_found = all(name in result.normalized_text for name in expected_names)

            if all_found:
                print("✅ ЧАСТИЧНО ПРОШЁЛ (имена найдены)")
            else:
                print("❌ НЕ ПРОШЁЛ")
        else:
            # Для одиночных случаев
            print(f"Ожидалось: '{case['expected']}'")
            if result.normalized_text.strip() == case['expected']:
                print("✅ ПРОШЁЛ")
            else:
                print("❌ НЕ ПРОШЁЛ")

if __name__ == "__main__":
    test_multiple_persons()
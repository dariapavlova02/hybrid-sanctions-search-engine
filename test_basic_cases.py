#!/usr/bin/env python3
"""
Тест базовых кейсов нормализации
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from ai_service.layers.normalization.normalization_service import NormalizationService

def test_basic_cases():
    """Тест базовых кейсов"""
    service = NormalizationService()

    test_cases = [
        {
            "input": "Mary Jane Watson",
            "expected": "Mary Watson",
            "description": "en_middle_name - should remove middle name"
        },
        {
            "input": "O'Connor, Sean",
            "expected": "Sean O'Connor",
            "description": "en_apostrophe - comma reversal"
        },
        {
            "input": "Оплата ТОВ \"ПРИВАТБАНК\" Ивану Петрову, 1980-01-01",
            "expected": "Іван Петров",  # Ukrainian expected
            "description": "mixed_org_noise - filter org and dates"
        },
        {
            "input": "Café José → оплата Івану",
            "expected": "Іван",
            "description": "mixed_diacritics - filter latin"
        },
        {
            "input": "Пётр Сергеев",
            "expected": "Пётр Сергеев",
            "description": "behavior_idempotent"
        },
        {
            "input": "иван ПЕТРОВ",
            "expected": "Иван Петров",
            "description": "behavior_case_policy - title case"
        }
    ]

    for case in test_cases:
        print(f"\nТест: {case['description']}")
        print(f"Входные данные: '{case['input']}'")

        result = service.normalize(case['input'], language='auto')

        print(f"Результат: '{result.normalized_text}'")
        print(f"Ожидалось: '{case['expected']}'")
        print(f"Токены: {result.tokens}")

        if result.normalized_text.strip() == case['expected']:
            print("✅ ПРОШЁЛ")
        else:
            print("❌ НЕ ПРОШЁЛ")

if __name__ == "__main__":
    test_basic_cases()
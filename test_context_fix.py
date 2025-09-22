#!/usr/bin/env python3
"""
Тест исправления контекстных слов
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from ai_service.layers.normalization.normalization_service import NormalizationService

def test_context_words():
    """Тест обработки контекстных слов"""
    service = NormalizationService()

    test_cases = [
        {
            "input": "получатель: гражданин РФ Петр Сергеев",
            "expected": "Пётр Сергеев",
            "description": "ru_context_words test case"
        },
        {
            "input": "паспорт номер Ab123456 Сергій Іванов",
            "expected": "Сергій Іванов",
            "description": "uk_passport test case"
        },
        {
            "input": "Україна Володимир Зеленський",
            "expected": "Володимир Зеленський",
            "description": "uk_ner_gate test case"
        }
    ]

    for case in test_cases:
        print(f"\nТест: {case['description']}")
        print(f"Входные данные: '{case['input']}'")

        result = service.normalize(case['input'], language='auto')

        print(f"Результат: '{result.normalized_text}'")
        print(f"Ожидалось: '{case['expected']}'")

        # Проверим токены
        print(f"Токены: {result.tokens}")

        if result.normalized_text.strip() == case['expected']:
            print("✅ ПРОШЁЛ")
        else:
            print("❌ НЕ ПРОШЁЛ")

if __name__ == "__main__":
    test_context_words()
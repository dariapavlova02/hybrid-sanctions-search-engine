#!/usr/bin/env python3
"""
Тест определения языка
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from ai_service.layers.language.language_detection_service import LanguageDetectionService

def test_language_detection():
    """Тест определения языка"""
    service = LanguageDetectionService()

    test_cases = [
        {
            "input": "Ивану Петрову",
            "expected_lang": "ru",
            "description": "Russian dative case"
        },
        {
            "input": "Оплата ТОВ \"ПРИВАТБАНК\" Ивану Петрову",
            "expected_lang": "uk",  # ТОВ - украинская форма
            "description": "Ukrainian context with Russian name"
        },
        {
            "input": "Івану",
            "expected_lang": "uk",
            "description": "Ukrainian with і"
        },
        {
            "input": "Mary Jane Watson",
            "expected_lang": "en",
            "description": "English names"
        }
    ]

    for case in test_cases:
        print(f"\nТест: {case['description']}")
        print(f"Входные данные: '{case['input']}'")

        result = service.detect_language(case['input'])

        language = result.get('language') if isinstance(result, dict) else result.language
        confidence = result.get('confidence', 0) if isinstance(result, dict) else result.confidence

        print(f"Результат: {language} (confidence: {confidence:.2f})")
        print(f"Ожидалось: {case['expected_lang']}")

        if language == case['expected_lang']:
            print("✅ ПРОШЁЛ")
        else:
            print("❌ НЕ ПРОШЁЛ")

if __name__ == "__main__":
    test_language_detection()
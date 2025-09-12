#!/usr/bin/env python3
"""
Debug test for language detection.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from ai_service.services.language_detection_service import LanguageDetectionService


def test_language_detection():
    """Test language detection for different texts."""
    service = LanguageDetectionService()
    
    test_cases = [
        ("Платеж в пользу Сергея Владимировича Петрова", "ru"),
        ("Переказ коштів на ім'я Петро Іванович Коваленко", "uk"),
        ("Payment to John Michael Smith for services", "en"),
    ]
    
    print("🔍 Language Detection Debug Test")
    print("=" * 50)
    
    for text, expected_lang in test_cases:
        result = service.detect_language(text)
        print(f"Text: '{text}'")
        print(f"Expected: {expected_lang}")
        print(f"Detected: {result.get('language', 'unknown')}")
        print(f"Confidence: {result.get('confidence', 0.0)}")
        print(f"Match: {'✅' if result.get('language') == expected_lang else '❌'}")
        print("-" * 30)
    
    print("Test completed!")


if __name__ == "__main__":
    test_language_detection()

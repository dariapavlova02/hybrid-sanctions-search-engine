#!/usr/bin/env python3
"""
Debug language detection for Ukrainian names.
"""

import sys
sys.path.append('src')

from ai_service.layers.language.language_detection_service import LanguageDetectionService

def debug_language_detection():
    """Debug language detection service."""
    print("🌍 LANGUAGE DETECTION SERVICE DEBUG")
    print("=" * 50)

    service = LanguageDetectionService()

    test_cases = [
        "Петра Порошенка",       # Ukrainian genitive name
        "Порошенко",             # Ukrainian surname
        "Петр Порошенко",        # Nominative form
        "Одін Марін Інкорпорейтед", # Ukrainian organization
        "Дарья Павлова",         # Russian name
    ]

    for test_text in test_cases:
        result = service.detect_language(test_text)
        if isinstance(result, dict):
            language = result.get('language', 'unknown')
            confidence = result.get('confidence', 0.0)
        else:
            language = getattr(result, 'language', 'unknown')
            confidence = getattr(result, 'confidence', 0.0)
        print(f"'{test_text}' -> language: {language}, confidence: {confidence:.3f}")

if __name__ == "__main__":
    debug_language_detection()
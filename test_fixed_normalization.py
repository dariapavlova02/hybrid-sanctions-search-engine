#!/usr/bin/env python3
"""
Test script for the fixed normalization service
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from ai_service.services.normalization_service import NormalizationService

def test_fixed_normalization():
    """Test the fixed normalization service"""
    service = NormalizationService()
    
    test_cases = [
        # Names (diminutives -> full forms)
        ("Петрик", "Петро"),
        ("Петруся", "Петро"),
        ("Вовчика", "Володимир"),
        ("Сашка", "Олександр"),
        ("Дашеньки", "Дарія"),
        ("Жені", "Євген"),
        ("Ліною", "Ліна"),
        
        # Surnames (inflected -> nominative)
        ("Іванова", "Іванов"),
        ("Порошенка", "Порошенко"),
        ("Квіткової", "Квіткова"),
        ("Положинського", "Положинський"),
        ("Зеленського", "Зеленський"),
        ("Скрипці", "Скрипка"),
        ("Петренка", "Петренко"),
        
        # Other words
        ("оплата", "оплата"),
        ("за", "за"),
        ("ремонт", "ремонт"),
        ("В.", "В."),
        ("О.", "О."),
    ]
    
    print("Testing Fixed Normalization Service:")
    print("=" * 50)
    
    for original, expected in test_cases:
        result = service.normalize(original, language="uk", enable_advanced_features=True)
        actual = result.tokens[0] if result.tokens else original
        status = "✓" if actual == expected else "✗"
        print(f"{status} {original:15} -> {actual:15} (expected: {expected})")
    
    print("\nTesting text normalization:")
    print("=" * 50)
    
    text_cases = [
        "Для Петруся Іванова, за ремонт",
        "Переказ від Вовчика Зеленського В. О.",
        "Подарунок для Дашеньки Квіткової",
        "Від Сашка Положинського за квитки",
        "Для Жені Галича з групи O.Torvald",
        "Зустріч з Ліною Костенко",
        "Переказ ОЛЕГУ СКРИПЦІ",
        "Для Іванова-Петренка С.В.",
    ]
    
    for text in text_cases:
        result = service.normalize(text, language="uk", enable_advanced_features=True)
        print(f"Original: {text}")
        print(f"Normalized: {' '.join(result.tokens)}")
        print()

if __name__ == "__main__":
    test_fixed_normalization()

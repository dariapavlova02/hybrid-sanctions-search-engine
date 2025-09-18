#!/usr/bin/env python3
"""
Test script for enhanced surname declension rules based on Petrovich patterns.
Tests the improved Russian and Ukrainian surname normalization.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ai_service.layers.normalization.morphology.gender_rules import (
    convert_surname_to_nominative_ru,
    convert_surname_to_nominative_uk,
    is_invariable_surname,
    SURNAME_EXCEPTIONS
)

def test_russian_surname_declension():
    """Test Russian surname declension with enhanced patterns."""
    print("Testing Russian surname declension...")
    
    test_cases = [
        # Basic patterns
        ("Иванову", "Иванов"),  # Dative
        ("Ивановым", "Иванов"),  # Instrumental
        ("Иванове", "Иванов"),  # Prepositional
        ("Иванева", "Иванев"),  # Genitive
        ("Иваневу", "Иванев"),  # Dative
        ("Иваневым", "Иванев"),  # Instrumental
        ("Иваневе", "Иванев"),  # Prepositional
        ("Петрина", "Петрин"),  # Genitive
        ("Петрину", "Петрин"),  # Dative
        ("Петриным", "Петрин"),  # Instrumental
        ("Петрине", "Петрин"),  # Prepositional
        
        # -ский patterns
        ("Петровского", "Петровский"),  # Genitive
        ("Петровскому", "Петровский"),  # Dative
        ("Петровским", "Петровский"),  # Instrumental
        ("Петровском", "Петровский"),  # Prepositional
        
        # -цкий patterns
        ("Петровцкого", "Петровцкий"),  # Genitive
        ("Петровцкому", "Петровцкий"),  # Dative
        ("Петровцким", "Петровцкий"),  # Instrumental
        ("Петровцком", "Петровцкий"),  # Prepositional
        
        # General masculine patterns
        ("Петрова", "Петров"),  # Genitive
        ("Петрову", "Петров"),  # Dative
        ("Петровом", "Петров"),  # Instrumental
        ("Петрове", "Петров"),  # Prepositional
        
        # Hyphenated surnames
        ("Петров-Сидорову", "Петров-Сидоров"),  # Dative
        ("Петров-Сидоровым", "Петров-Сидоров"),  # Instrumental
        
        # Feminine surnames
        ("Ивановой", "Иванова"),  # Genitive feminine
        ("Иванову", "Иванова"),  # Accusative feminine
        ("Ивановой", "Иванова"),  # Instrumental feminine
        ("Ивановой", "Иванова"),  # Prepositional feminine
        ("Петровой", "Петрова"),  # Genitive feminine
        ("Петрову", "Петрова"),  # Accusative feminine
        ("Петровой", "Петрова"),  # Instrumental feminine
        ("Петровой", "Петрова"),  # Prepositional feminine
        
        # Invariable surnames (should remain unchanged)
        ("Ткач", "Ткач"),  # Invariable
        ("Бондаренко", "Бондаренко"),  # Invariable
        ("Шевченко", "Шевченко"),  # Invariable
    ]
    
    passed = 0
    failed = 0
    
    for input_surname, expected in test_cases:
        result = convert_surname_to_nominative_ru(input_surname)
        if result == expected:
            print(f"✓ {input_surname} -> {result}")
            passed += 1
        else:
            print(f"✗ {input_surname} -> {result} (expected: {expected})")
            failed += 1
    
    print(f"Russian tests: {passed} passed, {failed} failed")
    return failed == 0

def test_ukrainian_surname_declension():
    """Test Ukrainian surname declension with enhanced patterns."""
    print("\nTesting Ukrainian surname declension...")
    
    test_cases = [
        # Basic patterns
        ("Іванову", "Іванов"),  # Dative
        ("Івановим", "Іванов"),  # Instrumental
        ("Іванові", "Іванов"),  # Prepositional
        ("Іванева", "Іванев"),  # Genitive
        ("Іваневу", "Іванев"),  # Dative
        ("Іваневим", "Іванев"),  # Instrumental
        ("Іваневі", "Іванев"),  # Prepositional
        
        # -енко patterns
        ("Петренку", "Петренко"),  # Dative
        ("Петренком", "Петренко"),  # Instrumental
        ("Петренкові", "Петренко"),  # Prepositional
        ("Петренка", "Петренко"),  # Genitive
        
        # -ук patterns
        ("Петруку", "Петрук"),  # Dative
        ("Петруком", "Петрук"),  # Instrumental
        ("Петрукові", "Петрук"),  # Prepositional
        ("Петрука", "Петрук"),  # Genitive
        
        # -юк patterns
        ("Петрюку", "Петрюк"),  # Dative
        ("Петрюком", "Петрюк"),  # Instrumental
        ("Петрюкові", "Петрюк"),  # Prepositional
        ("Петрюка", "Петрюк"),  # Genitive
        
        # -чук patterns
        ("Петручуку", "Петручук"),  # Dative
        ("Петручуком", "Петручук"),  # Instrumental
        ("Петручукові", "Петручук"),  # Prepositional
        ("Петручука", "Петручук"),  # Genitive
        
        # -ський patterns
        ("Петровського", "Петровський"),  # Genitive
        ("Петровському", "Петровський"),  # Dative
        ("Петровським", "Петровський"),  # Instrumental
        ("Петровськом", "Петровський"),  # Prepositional
        
        # -цький patterns
        ("Петровцького", "Петровцький"),  # Genitive
        ("Петровцькому", "Петровцький"),  # Dative
        ("Петровцьким", "Петровцький"),  # Instrumental
        ("Петровцьком", "Петровцький"),  # Prepositional
        
        # General masculine patterns
        ("Петрова", "Петров"),  # Genitive
        ("Петрову", "Петров"),  # Dative
        ("Петровом", "Петров"),  # Instrumental
        ("Петрові", "Петров"),  # Prepositional
        
        # Hyphenated surnames
        ("Петров-Сидорову", "Петров-Сидоров"),  # Dative
        ("Петров-Сидоровим", "Петров-Сидоров"),  # Instrumental
        
        # Feminine surnames
        ("Іванової", "Іванова"),  # Genitive feminine
        ("Іванову", "Іванова"),  # Accusative feminine
        ("Івановою", "Іванова"),  # Instrumental feminine
        ("Івановій", "Іванова"),  # Prepositional feminine
        ("Петрової", "Петрова"),  # Genitive feminine
        ("Петрову", "Петрова"),  # Accusative feminine
        ("Петровою", "Петрова"),  # Instrumental feminine
        ("Петровій", "Петрова"),  # Prepositional feminine
        ("Петренкової", "Петренко"),  # Genitive feminine
        ("Петренку", "Петренко"),  # Accusative feminine
        ("Петренкою", "Петренко"),  # Instrumental feminine
        ("Петренці", "Петренко"),  # Prepositional feminine
        
        # Invariable surnames (should remain unchanged)
        ("Ткач", "Ткач"),  # Invariable
        ("Бондаренко", "Бондаренко"),  # Invariable
        ("Шевченко", "Шевченко"),  # Invariable
        ("Петренко", "Петренко"),  # Invariable
    ]
    
    passed = 0
    failed = 0
    
    for input_surname, expected in test_cases:
        result = convert_surname_to_nominative_uk(input_surname)
        if result == expected:
            print(f"✓ {input_surname} -> {result}")
            passed += 1
        else:
            print(f"✗ {input_surname} -> {result} (expected: {expected})")
            failed += 1
    
    print(f"Ukrainian tests: {passed} passed, {failed} failed")
    return failed == 0

def test_invariable_surnames():
    """Test invariable surname detection."""
    print("\nTesting invariable surname detection...")
    
    invariable_cases = [
        "Ткач", "Бондаренко", "Шевченко", "Петренко", "Ко", "Дзе", "Швили"
    ]
    
    variable_cases = [
        "Иванов", "Петров", "Сидоров", "Козлов", "Морозов"
    ]
    
    passed = 0
    failed = 0
    
    for surname in invariable_cases:
        if is_invariable_surname(surname):
            print(f"✓ {surname} correctly identified as invariable")
            passed += 1
        else:
            print(f"✗ {surname} should be invariable but wasn't detected")
            failed += 1
    
    for surname in variable_cases:
        if not is_invariable_surname(surname):
            print(f"✓ {surname} correctly identified as variable")
            passed += 1
        else:
            print(f"✗ {surname} should be variable but was detected as invariable")
            failed += 1
    
    print(f"Invariable tests: {passed} passed, {failed} failed")
    return failed == 0

def test_exception_system():
    """Test the exception system for complex surnames."""
    print("\nTesting exception system...")
    
    # Test that exceptions are properly defined
    assert "ткач" in SURNAME_EXCEPTIONS["ru"]["male"]
    assert "ткач" in SURNAME_EXCEPTIONS["ru"]["female"]
    assert "бондаренко" in SURNAME_EXCEPTIONS["uk"]["male"]
    assert "бондаренко" in SURNAME_EXCEPTIONS["uk"]["female"]
    
    print("✓ Exception system properly configured")
    return True

def main():
    """Run all tests."""
    print("Testing Enhanced Surname Declension Rules")
    print("=" * 50)
    
    tests = [
        test_russian_surname_declension,
        test_ukrainian_surname_declension,
        test_invariable_surnames,
        test_exception_system
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed!")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

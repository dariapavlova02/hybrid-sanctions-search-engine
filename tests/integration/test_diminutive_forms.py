#!/usr/bin/env python3
"""
Тест для проверки нормализации уменьшительных форм.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from ai_service.layers.normalization.morphology.ukrainian_morphology import UkrainianMorphologyAnalyzer


def test_diminutive_forms():
    """Тест уменьшительных форм украинских имен."""
    analyzer = UkrainianMorphologyAnalyzer()
    
    test_cases = [
        ("Петрик", "Петро"),      # Петрик -> Петро
        ("Сашко", "Олександр"),   # Сашко -> Олександр  
        ("Вовчик", "Володимир"),  # Вовчик -> Володимир
        ("Женя", "Євген"),       # Женя -> Євген
        ("Дашенька", "Дарія"),   # Дашенька -> Дарія
    ]
    
    print("🔍 Testing Diminutive Forms")
    print("=" * 50)
    
    for input_name, expected_base in test_cases:
        print(f"\nInput: '{input_name}'")
        print(f"Expected base: '{expected_base}'")
        
        try:
            forms = analyzer.get_word_forms(input_name)
            print(f"Forms: {forms}")
            
            # Check if the expected base form is in the results
            forms_lower = [form.lower() for form in forms]
            expected_lower = expected_base.lower()
            
            if expected_lower in forms_lower:
                print(f"✅ Found expected base form: '{expected_base}'")
            else:
                print(f"❌ Expected base form '{expected_base}' NOT found")
                print(f"   Available forms: {forms}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("Test completed!")


if __name__ == "__main__":
    test_diminutive_forms()

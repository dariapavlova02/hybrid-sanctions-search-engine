#!/usr/bin/env python3
"""
Test script for gender rules functions
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.ai_service.layers.normalization.morphology.gender_rules import convert_given_name_to_nominative_ru

def test_gender_rules():
    """Test gender rules functions"""
    
    test_cases = [
        "Дашеньки",  # Should become "Дашенька" (diminutive in genitive)
        "Вики",      # Should become "Вика" (diminutive in genitive)
        "Анны",      # Should become "Анна" (regular genitive)
        "Марии",     # Should become "Мария" (regular genitive)
        "Ивану",     # Should become "Иван" (dative)
        "Сергеем",   # Should become "Сергей" (instrumental)
    ]
    
    print("Testing convert_given_name_to_nominative_ru:")
    for token in test_cases:
        result = convert_given_name_to_nominative_ru(token)
        print(f"  '{token}' -> '{result}'")

if __name__ == "__main__":
    test_gender_rules()

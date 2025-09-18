#!/usr/bin/env python3
"""
Debug script to test Вики normalization step by step
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.ai_service.layers.normalization.morphology.gender_rules import convert_given_name_to_nominative_ru

def test_viki_step_by_step():
    """Test Вики normalization step by step"""
    
    token = "Вики"
    print(f"Testing token: '{token}'")
    
    # Step 1: Check diminutives dictionary
    print("\nStep 1: Check diminutives dictionary")
    import json
    with open('data/diminutives_ru.json', 'r', encoding='utf-8') as f:
        diminutives = json.load(f)
    
    token_lower = token.lower()
    diminutive_result = diminutives.get(token_lower)
    print(f"  Token lower: '{token_lower}'")
    print(f"  Diminutive lookup: {diminutive_result}")
    
    # Step 2: Check morphological normalization
    print("\nStep 2: Check morphological normalization")
    morph_result = convert_given_name_to_nominative_ru(token)
    print(f"  Morphological result: '{morph_result}'")
    
    # Step 3: Check if Вика is in diminutives
    print("\nStep 3: Check if Вика is in diminutives")
    vika_result = diminutives.get("вика")
    print(f"  'вика' -> '{vika_result}'")
    
    # Step 4: Full pipeline simulation
    print("\nStep 4: Full pipeline simulation")
    normalized = token
    
    # First check diminutives
    full = diminutives.get(token_lower)
    if full:
        normalized = full.title()
        print(f"  After diminutive lookup: '{normalized}'")
    
    # Then morphological normalization
    converted = convert_given_name_to_nominative_ru(normalized)
    if converted != normalized:
        normalized = converted
        print(f"  After morphological normalization: '{normalized}'")
    
    # Check if result is in diminutives again
    if normalized.lower() in diminutives:
        final_result = diminutives[normalized.lower()].title()
        print(f"  Final result from diminutives: '{final_result}'")
    
    print(f"\nFinal result: '{normalized}'")

if __name__ == "__main__":
    test_viki_step_by_step()

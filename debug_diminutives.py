#!/usr/bin/env python3
"""
Debug script to test diminutives lookup
"""

import json
from pathlib import Path

def test_diminutives_lookup():
    """Test diminutives dictionary lookup"""
    
    # Load the dictionary
    ru_path = Path("data/diminutives_ru.json")
    with open(ru_path, 'r', encoding='utf-8') as f:
        diminutives_ru = json.load(f)
    
    print("Loaded diminutives dictionary:")
    print(f"Total entries: {len(diminutives_ru)}")
    print(f"Keys: {list(diminutives_ru.keys())}")
    
    # Test different variations of "Вики"
    test_tokens = ["Вики", "вики", "Вика", "вика", "ВИКА", "ВИКИ"]
    
    print("\nTesting token variations:")
    for token in test_tokens:
        token_lower = token.lower()
        canonical = diminutives_ru.get(token_lower)
        print(f"Token: '{token}' -> lower: '{token_lower}' -> canonical: '{canonical}'")
    
    # Check if "вика" exists
    print(f"\nDirect check for 'вика': {diminutives_ru.get('вика')}")
    print(f"Direct check for 'вики': {diminutives_ru.get('вики')}")

if __name__ == "__main__":
    test_diminutives_lookup()

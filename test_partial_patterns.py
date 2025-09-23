#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, 'src')

from ai_service.layers.patterns.high_recall_ac_generator import HighRecallACGenerator, NamePatternGenerator

def test_partial_patterns():
    """Test partial pattern generation for Poroshenko"""

    # Create sample person data like in sanctions list
    person_data = {
        'id': 'test_1',
        'name': 'Порошенко Петро Олексійович',  # Full name with patronymic
        'name_ru': 'Порошенко Петр Алексеевич',
        'name_en': 'Poroshenko Petro Oleksiyovych'
    }

    print("🧪 Testing partial pattern generation...")
    print(f"Original name: {person_data['name']}")

    # Test name generator directly
    name_generator = NamePatternGenerator()

    # Test tier 2 patterns (should include our partial patterns)
    patterns = name_generator.generate_tier_2_patterns(person_data['name'], 'uk')

    print(f"\n📋 Generated {len(patterns)} Tier 2 patterns:")
    for i, pattern in enumerate(patterns, 1):
        print(f"{i}. Pattern: '{pattern.pattern}'")
        print(f"   Type: {pattern.metadata.pattern_type}")
        print(f"   Confidence: {pattern.metadata.confidence}")
        print(f"   Hints: {pattern.metadata.hints}")
        print()

    # Check specifically for partial match
    partial_patterns = [p for p in patterns if p.metadata.pattern_type == 'partial_match']
    print(f"🎯 Found {len(partial_patterns)} partial match patterns:")
    for pattern in partial_patterns:
        print(f"   - '{pattern.pattern}'")

    # Test that we have the expected pattern
    expected_partial = "порошенко петро"
    found_partial = any(p.pattern == expected_partial for p in patterns)

    if found_partial:
        print(f"✅ SUCCESS: Found expected pattern '{expected_partial}'")
    else:
        print(f"❌ FAIL: Did not find expected pattern '{expected_partial}'")
        print("Available patterns:")
        for p in patterns:
            print(f"   - '{p.pattern}'")

if __name__ == "__main__":
    test_partial_patterns()
#!/usr/bin/env python3
"""
Test exclusion patterns against our problematic names
"""

import re
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ai_service.data.dicts.smart_filter_patterns import EXCLUSION_PATTERNS

def test_exclusion_patterns():
    """Test if our names match exclusion patterns"""

    test_names = [
        "Дарья Павлова",
        "Кухарук Вікторія",
        "John Smith",
        "Іван Петров",  # This one works
        "Прийом оплат",  # This should be excluded
    ]

    print("🔍 Testing exclusion patterns")
    print("=" * 60)

    for name in test_names:
        name_lower = name.lower().strip()
        excluded = False
        matching_pattern = None

        for pattern in EXCLUSION_PATTERNS:
            try:
                if re.match(pattern, name_lower, re.IGNORECASE):
                    excluded = True
                    matching_pattern = pattern
                    break
            except re.error as e:
                print(f"   ❌ Invalid regex pattern: {pattern} - {e}")
                continue

        status = "❌ EXCLUDED" if excluded else "✅ ALLOWED"
        print(f"{status}: '{name}'")
        if matching_pattern:
            print(f"   Matched pattern: {matching_pattern}")

    print("\n🧪 Patterns count:", len(EXCLUSION_PATTERNS))
    print("First few patterns:")
    for i, pattern in enumerate(EXCLUSION_PATTERNS[:5]):
        print(f"  {i+1}. {pattern}")

if __name__ == "__main__":
    test_exclusion_patterns()
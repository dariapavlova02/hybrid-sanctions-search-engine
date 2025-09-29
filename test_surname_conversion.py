#!/usr/bin/env python3
"""
Test Ukrainian surname conversion rules directly.
"""

import sys
sys.path.append('src')

from ai_service.layers.normalization.morphology.gender_rules import convert_surname_to_nominative_uk

def test_surname_conversion():
    """Test Ukrainian surname conversion rules."""
    print("🧪 TESTING UKRAINIAN SURNAME CONVERSION")
    print("=" * 50)

    test_cases = [
        "Порошенка",   # Target case
        "Шевченка",    # Common Ukrainian surname
        "Петренка",    # Another -енка case
        "Порошенко",   # Already nominative
        "Порошенку",   # Dative
        "Порошенком",  # Instrumental
    ]

    for surname in test_cases:
        result = convert_surname_to_nominative_uk(surname)
        print(f"'{surname}' -> '{result}'")

if __name__ == "__main__":
    test_surname_conversion()
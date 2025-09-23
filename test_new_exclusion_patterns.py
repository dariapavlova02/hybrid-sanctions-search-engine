#!/usr/bin/env python3
"""
Test new exclusion patterns against problematic codes
"""

import re
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ai_service.data.dicts.smart_filter_patterns import EXCLUSION_PATTERNS

def test_exclusion_patterns():
    """Test new patterns against problematic codes"""

    # Codes from the insurance payment example that should be excluded
    problematic_codes = [
        "68ccdc4cd19cabdee2eaa56c",  # Long hex code
        "TV0015628",   # TV code
        "GM293232",    # GM code
        "OKPO",        # Business abbreviation
        "30929821",    # Long number
        "7sichey",     # Number with letters
        "2515321244",  # Long number (INN)
        "іпн",         # Ukrainian INN abbreviation
        "д.р.",        # Date of birth marker
        "12.11.1968",  # Birth date
        "20.09.2025",  # Date
    ]

    # Valid names that should NOT be excluded
    valid_names = [
        "Holoborodko",
        "Liudmyla",
        "Дарья",
        "Павлова",
        "John",
        "Smith",
    ]

    print("🔍 Testing NEW exclusion patterns")
    print("=" * 70)

    print("\n🚨 CODES (should be EXCLUDED):")
    for code in problematic_codes:
        code_lower = code.lower().strip()
        excluded = False
        matching_pattern = None

        for pattern in EXCLUSION_PATTERNS:
            try:
                if re.match(pattern, code_lower, re.IGNORECASE):
                    excluded = True
                    matching_pattern = pattern
                    break
            except re.error as e:
                print(f"   ❌ Invalid regex pattern: {pattern} - {e}")
                continue

        status = "✅ EXCLUDED" if excluded else "❌ NOT excluded"
        print(f"  {status}: '{code}'")
        if matching_pattern:
            print(f"      Matched: {matching_pattern}")

    print("\n👤 NAMES (should NOT be excluded):")
    for name in valid_names:
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
                continue

        status = "❌ EXCLUDED" if excluded else "✅ NOT excluded"
        print(f"  {status}: '{name}'")
        if matching_pattern:
            print(f"      Matched: {matching_pattern}")

    print(f"\n📊 Total patterns: {len(EXCLUSION_PATTERNS)}")

if __name__ == "__main__":
    test_exclusion_patterns()
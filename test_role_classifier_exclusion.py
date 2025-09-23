#!/usr/bin/env python3
"""
Test role classifier exclusion patterns
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_role_classifier_exclusion():
    """Test that role classifier excludes garbage codes"""

    from ai_service.layers.normalization.processors.role_classifier import RoleClassifier

    print("🔍 Testing role classifier exclusion patterns")
    print("="*60)

    classifier = RoleClassifier()

    # Test garbage codes
    garbage_codes = [
        "68ccdc4cd19cabdee2eaa56c",  # hex code
        "TV0015628",    # system code
        "GM293232",     # system code
        "7sichey",      # mixed garbage
        "2515321244",   # could be IPN - should still be filtered as pure number
    ]

    # Test valid names
    valid_names = [
        "Holoborodko",
        "Liudmyla",
        "Дарья",
        "Павлова"
    ]

    print("🚨 GARBAGE CODES (should be 'unknown'):")
    for code in garbage_codes:
        role = classifier._classify_personal_role(code, "uk")
        status = "✅ FILTERED" if role == "unknown" else f"❌ WRONG: {role}"
        print(f"  {status}: '{code}' → role='{role}'")

    print("\n👤 VALID NAMES (should be 'given' or 'surname'):")
    for name in valid_names:
        role = classifier._classify_personal_role(name, "uk")
        status = "✅ VALID" if role in ["given", "surname"] else f"❌ WRONG: {role}"
        print(f"  {status}: '{name}' → role='{role}'")

    print(f"\n📊 Summary:")
    garbage_filtered = all(
        classifier._classify_personal_role(code, "uk") == "unknown"
        for code in garbage_codes
    )
    names_valid = all(
        classifier._classify_personal_role(name, "uk") in ["given", "surname"]
        for name in valid_names
    )

    print(f"  Garbage codes filtered: {'✅ YES' if garbage_filtered else '❌ NO'}")
    print(f"  Valid names preserved: {'✅ YES' if names_valid else '❌ NO'}")

    success = garbage_filtered and names_valid
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Role classifier exclusion {'works' if success else 'does not work'}")

if __name__ == "__main__":
    test_role_classifier_exclusion()
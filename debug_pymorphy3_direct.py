#!/usr/bin/env python3
"""
Direct pymorphy3 test
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def debug_pymorphy3_direct():
    """Test pymorphy3 Ukrainian directly"""
    print("🔍 PYMORPHY3 DIRECT TEST")
    print("="*30)

    try:
        import pymorphy3

        # Test Ukrainian analyzer
        morph_uk = pymorphy3.MorphAnalyzer(lang='uk')

        token = "Петр"
        print(f"Testing token: '{token}'")

        parses = morph_uk.parse(token)
        print(f"Found {len(parses)} parses:")

        for i, p in enumerate(parses):
            print(f"  {i+1}. word: '{p.word}' | normal_form: '{p.normal_form}' | tag: {p.tag}")
            if p.lexeme:
                print(f"     Lexeme forms:")
                for j, form in enumerate(p.lexeme[:5]):  # First 5 forms
                    print(f"       {j+1}. '{form.word}' - {form.tag}")

        # Check for nominative case specifically
        print("\nSearching for nominative forms:")
        for p in parses:
            if hasattr(p.tag, 'case') and str(p.tag.case) == 'nomn':
                print(f"  NOMINATIVE: '{p.word}' | normal: '{p.normal_form}'")

        # Try inflecting to nominative
        print("\nTrying to inflect to nominative:")
        for p in parses:
            try:
                nominative = p.inflect({'nomn'})
                if nominative:
                    print(f"  Inflected nominative: '{nominative.word}'")
            except:
                continue

        # Check if it's already nominative
        print("\nChecking if already nominative:")
        for p in parses:
            if hasattr(p.tag, 'case'):
                print(f"  Case: {p.tag.case} for form '{p.word}'")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_pymorphy3_direct()
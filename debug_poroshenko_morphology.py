#!/usr/bin/env python3
"""
Debug pymorphy3 processing of Poroshenko surname.
"""

import sys
sys.path.append('src')

try:
    import pymorphy3

    def debug_pymorphy():
        """Debug pymorphy3 handling of Poroshenko."""
        print("🔬 PYMORPHY3 POROSHENKO DEBUG")
        print("=" * 50)

        morph = pymorphy3.MorphAnalyzer(lang='ru')

        test_words = [
            "Порошенка",  # Genitive
            "Порошенко",  # Nominative
            "Петра",      # Given name genitive
            "Петр",       # Given name nominative
        ]

        for word in test_words:
            print(f"\n🔍 Analyzing: '{word}'")

            # Get all parses
            parses = morph.parse(word)
            print(f"   Parses found: {len(parses)}")

            for i, parse in enumerate(parses[:3]):  # Show top 3
                print(f"   {i+1}. {parse.word} -> {parse.normal_form}")
                print(f"      Tag: {parse.tag}")
                print(f"      Score: {parse.score:.3f}")

                # Try to get nominative form
                if 'gent' in str(parse.tag) or 'nomn' not in str(parse.tag):
                    try:
                        nominative = parse.inflect({'nomn'})
                        if nominative:
                            print(f"      Nominative: {nominative.word}")
                        else:
                            print(f"      Nominative: (failed)")
                    except Exception as e:
                        print(f"      Nominative: (error: {e})")

                print()

    debug_pymorphy()

except ImportError:
    print("❌ pymorphy3 not available")
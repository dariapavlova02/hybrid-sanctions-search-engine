#!/usr/bin/env python3
"""
Test exclusion patterns in normalization layer
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_exclusion_in_normalization():
    """Test that exclusion patterns work in normalization"""

    from ai_service.layers.normalization.processors.token_processor import TokenProcessor

    print("🔍 Testing exclusion patterns in normalization")
    print("="*60)

    processor = TokenProcessor()

    # Test text with garbage codes
    test_text = "Страх. платіж 68ccdc4cd19cabdee2eaa56c TV0015628 Holoborodko Liudmyla д.р. 12.11.1968 іпн 2515321244"

    print(f"📝 Input: '{test_text}'")

    tokens, traces, metadata = processor.strip_noise_and_tokenize(
        test_text,
        language="uk",
        remove_stop_words=True,
        preserve_names=True
    )

    print(f"🔍 Output tokens: {tokens}")
    print(f"📊 Token count: {len(tokens)}")

    print(f"\n📋 Processing traces:")
    for i, trace in enumerate(traces, 1):
        print(f"  {i}. {trace}")

    # Check if garbage codes were filtered
    garbage_codes = ["68ccdc4cd19cabdee2eaa56c", "TV0015628", "2515321244", "іпн", "д.р.", "12.11.1968"]
    filtered_codes = []
    remaining_codes = []

    for code in garbage_codes:
        if code not in tokens:
            filtered_codes.append(code)
        else:
            remaining_codes.append(code)

    print(f"\n✅ Filtered codes: {filtered_codes}")
    print(f"❌ Remaining codes: {remaining_codes}")

    # Expected clean result
    expected = ["Holoborodko", "Liudmyla"]
    actual_names = [token for token in tokens if token.isalpha() and len(token) > 2]

    print(f"\n🎯 Expected names: {expected}")
    print(f"✅ Actual names: {actual_names}")

    # Check success
    success = len(filtered_codes) >= 4 and "Holoborodko" in tokens and "Liudmyla" in tokens
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Exclusion patterns {'work' if success else 'do not work'} in normalization")

if __name__ == "__main__":
    test_exclusion_in_normalization()
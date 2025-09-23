#!/usr/bin/env python3
"""
Test full exclusion chain: role classifier + result builder
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_full_exclusion_chain():
    """Test that exclusion works through the entire normalization chain"""

    print("🔍 Testing full exclusion chain")
    print("="*60)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService
        from ai_service.utils.feature_flags import FeatureFlags

        # Initialize normalization service
        service = NormalizationService()
        flags = FeatureFlags()

        # Test text with garbage
        test_text = "68ccdc4cd19cabdee2eaa56c TV0015628 Holoborodko Liudmyla GM293232 7sichey"

        print(f"📝 Input: '{test_text}'")

        # Run normalization
        result = service.normalize(
            text=test_text,
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"🔍 Normalized: '{result.normalized}'")
        print(f"📊 Tokens: {result.tokens}")

        # Check if garbage codes are filtered
        garbage_codes = ["68ccdc4cd19cabdee2eaa56c", "TV0015628", "GM293232", "7sichey"]
        filtered_codes = [code for code in garbage_codes if code not in result.normalized]
        remaining_codes = [code for code in garbage_codes if code in result.normalized]

        print(f"\n✅ Filtered from normalized: {filtered_codes}")
        print(f"❌ Still in normalized: {remaining_codes}")

        # Check traces
        print(f"\n📋 Token traces:")
        for trace in result.trace:
            print(f"  {trace.token} → role={trace.role}, output={trace.output}")

        # Expected clean result
        expected_clean = "Holoborodko Liudmyla"
        success = (
            "Holoborodko" in result.normalized and
            "Liudmyla" in result.normalized and
            len(filtered_codes) >= 3  # Most garbage filtered
        )

        print(f"\n🎯 Expected: '{expected_clean}'")
        print(f"✅ Actual: '{result.normalized}'")
        print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Full exclusion chain {'works' if success else 'does not work'}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_full_exclusion_chain()
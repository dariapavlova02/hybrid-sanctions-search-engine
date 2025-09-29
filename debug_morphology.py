#!/usr/bin/env python3
"""
Debug morphology processing in normalization factory.
"""

import sys
sys.path.append('src')

from ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory, NormalizationConfig
import asyncio

async def debug_morphology():
    """Debug morphology step by step."""
    print("🔬 MORPHOLOGY DEBUG")
    print("=" * 50)

    try:
        factory = NormalizationFactory(None, None)

        config = NormalizationConfig(
            language="ru",
            enable_advanced_features=True,  # Enable morphology
            enable_fsm_tuned_roles=True
        )

        test_text = "Павловой Дарьи"
        print(f"🔍 Processing: '{test_text}'")
        print(f"🔧 Config: language={config.language}, advanced={config.enable_advanced_features}")

        result = await factory.normalize_text(test_text, config)

        print(f"✅ Success: {result.success}")
        print(f"🌍 Language: {result.language}")
        print(f"📝 Normalized: '{result.normalized}'")

        print(f"\n🔍 Detailed trace:")
        for token in result.trace:
            print(f"  '{token.token}' -> role:{token.role}, lang:{token.morph_lang}, normal:{token.normal_form}, fallback:{token.fallback}")
            if hasattr(token, 'notes') and token.notes:
                print(f"    Notes: {token.notes[:100]}...")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_morphology())
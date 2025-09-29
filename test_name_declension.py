#!/usr/bin/env python3
"""
Test name declension to find why Pavlova Daria doesn't decline properly.
"""

import sys
sys.path.append('src')

from ai_service.core.orchestrator_factory import OrchestratorFactory
import asyncio

async def test_name_declension():
    """Test name declension issues."""
    print("🧪 NAME DECLENSION TEST")
    print("=" * 50)

    try:
        # Create orchestrator
        orchestrator = await OrchestratorFactory.create_orchestrator()

        test_cases = [
            "Павловой Дарьи",    # Should become "Дарья Павлова"
            "Дарья Павлова",     # Should stay the same
            "Иванов Петр",       # Should become "Петр Иванов"
        ]

        for test_text in test_cases:
            print(f"\n🔍 Testing: '{test_text}'")

            result = await orchestrator.process(test_text)

            print(f"✅ Success: {result.success}")
            print(f"🌍 Language: {result.language}")
            print(f"📝 Normalized: '{result.normalized_text}'")

            # Check trace details
            if hasattr(result, 'trace') and result.trace:
                print(f"🔍 Trace details:")
                for token in result.trace:
                    role = token.role if hasattr(token, 'role') else 'unknown'
                    morph_lang = token.morph_lang if hasattr(token, 'morph_lang') else 'none'
                    normal_form = token.normal_form if hasattr(token, 'normal_form') else 'none'
                    fallback = token.fallback if hasattr(token, 'fallback') else False

                    print(f"  '{token.token}' -> role:{role}, morph_lang:{morph_lang}, normal:{normal_form}, fallback:{fallback}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_name_declension())
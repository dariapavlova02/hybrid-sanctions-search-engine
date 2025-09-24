#!/usr/bin/env python3
"""
Debug full normalization path for 'Коваленко Олександра Сергіївна'
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

async def debug_full_normalization():
    """Debug full normalization path."""
    print("🔍 DEBUGGING FULL NORMALIZATION PATH")
    print("="*50)

    test_text = "Коваленко Олександра Сергіївна"

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService
        from ai_service.layers.normalization.processors.normalization_factory import NormalizationConfig

        # Create service
        service = NormalizationService()

        # Create config
        config = NormalizationConfig(
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True,
            preserve_feminine_suffix_uk=True
        )

        print(f"Input: '{test_text}'")
        print(f"Config: {config}")

        # Run normalization
        result = await service.normalize_async(
            test_text,
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True,
            preserve_feminine_suffix_uk=True
        )

        print(f"\n✅ RESULT:")
        print(f"  Normalized: '{result.normalized}'")
        print(f"  Tokens: {result.tokens}")
        print(f"  Language: {result.language}")
        print(f"  Success: {result.success}")

        print(f"\n📝 TRACE:")
        for i, trace in enumerate(result.trace):
            print(f"  {i+1}. {trace}")

        # Check if there are any morphological traces
        if hasattr(trace, 'morph_traces'):
            for morph_trace in trace.morph_traces:
                print(f"    Morph: {morph_trace}")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(debug_full_normalization())
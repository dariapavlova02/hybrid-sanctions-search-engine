#!/usr/bin/env python3

import sys
sys.path.append("src")

from ai_service.layers.normalization.normalization_service import NormalizationService

async def test_vladislav():
    service = NormalizationService()

    # Test just the problematic name
    test_text = "Владислав"

    print(f"Testing: '{test_text}'")

    result = await service.normalize_async(
        test_text,
        language="uk",
        remove_stop_words=True,
        preserve_names=True,
        enable_advanced_features=True
    )

    print(f"Result: {result}")
    print()
    print("Trace:")
    for i, trace in enumerate(result.trace):
        print(f"  {i}: {trace}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_vladislav())
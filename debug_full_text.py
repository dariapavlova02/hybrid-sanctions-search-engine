#!/usr/bin/env python3

import sys
sys.path.append("src")

from ai_service.layers.normalization.normalization_service import NormalizationService

async def test_full_text():
    service = NormalizationService()

    # Test the problematic full text
    test_text = "Страховий платіж за поліс ОСЦПВ EPcode 232483013 від 20.09.2025 Хамін Владислав Ігорович іпн 3731301153 Арсенал AG*232483013 33908322"

    print(f"Testing: '{test_text}'")

    result = await service.normalize_async(
        test_text,
        language="uk",
        remove_stop_words=True,
        preserve_names=True,
        enable_advanced_features=True
    )

    print(f"Result: {result.normalized}")
    print(f"Tokens: {result.tokens}")
    print()
    print("Trace:")
    for i, trace in enumerate(result.trace):
        print(f"  {i}: {trace}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_full_text())
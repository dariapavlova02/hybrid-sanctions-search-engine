#!/usr/bin/env python3

import sys
sys.path.append("src")

from ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory

async def test_simple_factory():
    # Test the full problematic text
    test_text = "Страховий платіж за поліс ОСЦПВ EPcode 232483013 від 20.09.2025 Хамін Владислав Ігорович іпн 3731301153 Арсенал AG*232483013 33908322"

    print(f"Testing: '{test_text}'\n")

    # Test factory directly without complex flags
    print("=== NORMALIZATION FACTORY ===")

    factory = NormalizationFactory()

    # Create config
    from ai_service.layers.normalization.processors.normalization_factory import NormalizationConfig
    from ai_service.config import FEATURE_FLAGS

    config = NormalizationConfig(
        remove_stop_words=True,
        preserve_names=True,
        enable_advanced_features=True,
        language="uk"
    )

    factory_result = await factory.normalize_text(
        test_text,
        config,
        feature_flags=FEATURE_FLAGS
    )

    print(f"Factory result: '{factory_result.normalized}'")
    print(f"Factory tokens: {factory_result.tokens}")
    print()

    # Show detailed trace
    print("=== FACTORY TRACE ===")
    for i, trace in enumerate(factory_result.trace):
        print(f"  {i}: token='{trace.token}' role={trace.role} output='{trace.output}' notes='{trace.notes}'")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_simple_factory())
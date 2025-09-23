#!/usr/bin/env python3

import sys
sys.path.append("src")

from ai_service.layers.normalization.normalization_service import NormalizationService
from ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory

async def test_factory_vs_service():
    # Test full text
    test_text = "Страховий платіж за поліс ОСЦПВ EPcode 232483013 від 20.09.2025 Хамін Владислав Ігорович іпн 3731301153 Арсенал AG*232483013 33908322"

    print(f"Testing: '{test_text}'\n")

    # Test service
    print("=== NORMALIZATION SERVICE ===")
    service = NormalizationService()
    service_result = await service.normalize_async(
        test_text,
        language="uk",
        remove_stop_words=True,
        preserve_names=True,
        enable_advanced_features=True
    )
    print(f"Service result: '{service_result.normalized}'")
    print(f"Service tokens: {service_result.tokens}")
    print()

    # Test factory directly
    print("=== NORMALIZATION FACTORY ===")

    # Get the same dictionaries and settings as the service
    name_dictionaries = service._load_name_dictionaries()
    diminutive_maps = service._load_diminutive_maps()

    factory = NormalizationFactory(name_dictionaries, diminutive_maps)

    # Use factory with the same flags as API
    from ai_service.config import FEATURE_FLAGS
    feature_flags = FEATURE_FLAGS
    feature_flags._flags.normalization_implementation = "factory"
    feature_flags._flags.use_factory_normalizer = True
    feature_flags._flags.remove_stop_words = True
    feature_flags._flags.preserve_names = True
    feature_flags._flags.enable_advanced_features = True
    feature_flags._flags.strict_stopwords = True

    factory_result = await factory.normalize_async(
        test_text,
        language="uk",
        feature_flags=feature_flags
    )

    print(f"Factory result: '{factory_result.normalized}'")
    print(f"Factory tokens: {factory_result.tokens}")
    print()

    # Show token-level comparison
    print("=== TOKEN COMPARISON ===")
    print("Service trace (first 10):")
    for i, trace in enumerate(service_result.trace[:10]):
        print(f"  {i}: {trace.token} -> {trace.output} (role: {trace.role})")
    print()
    print("Factory trace (first 10):")
    for i, trace in enumerate(factory_result.trace[:10]):
        print(f"  {i}: {trace.token} -> {trace.output} (role: {trace.role})")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_factory_vs_service())
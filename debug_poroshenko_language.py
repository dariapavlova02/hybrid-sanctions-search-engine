#!/usr/bin/env python3
"""
Debug language detection for Poroshenko case.
"""

import sys
sys.path.append('src')

from ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory, NormalizationConfig
from ai_service.layers.normalization.processors.morphology_processor import MorphologyProcessor
from ai_service.layers.normalization.morphology.gender_rules import convert_surname_to_nominative
import asyncio

async def debug_language():
    """Debug language detection and processing."""
    print("🌍 LANGUAGE DETECTION DEBUG")
    print("=" * 50)

    # Test different language configurations
    test_cases = [
        ("Петра Порошенка", "ru"),
        ("Петра Порошенка", "uk"),
        ("Петра Порошенка", "auto"),
    ]

    factory = NormalizationFactory()

    for test_text, language in test_cases:
        print(f"\n🔍 Testing: '{test_text}' with language='{language}'")

        config = NormalizationConfig(
            language=language,
            enable_advanced_features=True,
            enable_fsm_tuned_roles=True
        )

        result = await factory.normalize_text(test_text, config)

        print(f"📝 Normalized: '{result.normalized}'")
        print(f"🌍 Detected Language: {result.language}")
        print(f"🔍 Tokens: {result.tokens}")

        # Check if surname is properly processed
        for token in result.trace:
            if token.token == "Порошенка":
                print(f"   Порошенка: role={token.role}, output='{token.output}'")
                print(f"   Notes: {token.notes[:150]}...")

    print(f"\n🧪 DIRECT CONVERSION TEST:")
    direct_ru = convert_surname_to_nominative("Порошенка", "ru")
    direct_uk = convert_surname_to_nominative("Порошенка", "uk")
    print(f"   Порошенка + ru -> {direct_ru}")
    print(f"   Порошенка + uk -> {direct_uk}")

if __name__ == "__main__":
    asyncio.run(debug_language())
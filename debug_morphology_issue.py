#!/usr/bin/env python3
"""
Debug script to investigate morphology issue.
"""

import sys
sys.path.append('src')

from ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory, NormalizationConfig
from ai_service.layers.normalization.lexicon_loader import get_lexicons
import asyncio
import json

async def debug_morphology_issue():
    """Debug the morphology issue where 'Дарьи Павловой' doesn't normalize properly."""
    print("🔍 DEBUGGING MORPHOLOGY ISSUE")
    print("=" * 50)

    try:
        # Create factory instance (with None values like production)
        factory = NormalizationFactory(
            name_dictionaries=None,
            diminutive_maps=None
        )

        # Test configuration with all morphology flags enabled
        config = NormalizationConfig(
            language="ru",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True,  # This should enable morphology
            enable_morphology=True,  # Explicitly enable morphology
            enable_cache=True
        )

        # Test text that should undergo morphological normalization
        test_text = "Дарьи Павловой"

        print(f"Testing text: '{test_text}'")
        print(f"Language: {config.language}")
        print(f"enable_advanced_features: {config.enable_advanced_features}")
        print(f"enable_morphology: {config.enable_morphology}")

        # Try normalization
        result = await factory.normalize_text(test_text, config)

        print(f"\n📊 RESULT:")
        print(f"Normalized: '{result.normalized}'")
        print(f"Tokens: {result.tokens}")

        print(f"\n🔍 TRACE ANALYSIS:")
        for i, trace in enumerate(result.trace):
            print(f"Token {i+1}: {trace.token} -> {trace.output}")
            print(f"  Role: {trace.role}")
            print(f"  Rule: {trace.rule}")
            print(f"  Morph Lang: {trace.morph_lang}")
            print(f"  Normal Form: {trace.normal_form}")
            print(f"  Notes: {trace.notes}")
            print()

        # Expected: "Дарья Павлова"
        expected = "Дарья Павлова"
        if result.normalized == expected:
            print(f"✅ SUCCESS: Got expected result '{expected}'")
        else:
            print(f"❌ FAILED: Expected '{expected}', got '{result.normalized}'")

            # Additional debugging - check if morphology was even attempted
            morph_applied = any(trace.morph_lang is not None for trace in result.trace)
            print(f"Morphology attempted: {morph_applied}")

    except Exception as e:
        print(f"❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_morphology_issue())
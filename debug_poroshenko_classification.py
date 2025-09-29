#!/usr/bin/env python3
"""
Debug Poroshenko name classification issue.
"""

import sys
sys.path.append('src')

from ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory, NormalizationConfig
import asyncio

async def debug_poroshenko():
    """Debug Poroshenko classification."""
    print("🔬 POROSHENKO CLASSIFICATION DEBUG")
    print("=" * 50)

    factory = NormalizationFactory()

    test_cases = [
        "Петра Порошенка",     # Current failing case
        "Порошенка Петра",     # Reversed order
        "Порошенко Петр",      # Target result
        "Петр Порошенко",      # Nominative
    ]

    for test_text in test_cases:
        print(f"\n🔍 Testing: '{test_text}'")

        config = NormalizationConfig(
            language="ru",
            enable_advanced_features=True,
            enable_fsm_tuned_roles=True
        )

        result = await factory.normalize_text(test_text, config)

        print(f"📝 Normalized: '{result.normalized}'")
        print(f"🔍 Tokens: {result.tokens}")

        print(f"📋 Trace:")
        for token in result.trace:
            role = token.role
            output = token.output
            notes = token.notes[:100] if token.notes else ""
            print(f"  '{token.token}' -> role:{role}, output:'{output}'")
            print(f"    Notes: {notes}...")

if __name__ == "__main__":
    asyncio.run(debug_poroshenko())
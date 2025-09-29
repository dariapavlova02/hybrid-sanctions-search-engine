#!/usr/bin/env python3
"""
Test the factory wrapper directly to verify morphological processing.
"""

import sys
sys.path.append('src')

from ai_service.layers.normalization.factory_wrapper import FactoryBasedNormalizationService
from ai_service.core.orchestrator_factory import OrchestratorFactory
import asyncio

async def test_factory_wrapper():
    """Test the factory wrapper for name declension."""
    print("🧪 TESTING FACTORY WRAPPER")
    print("=" * 50)

    # Test 1: Direct factory wrapper
    print("\n📋 Test 1: Direct factory wrapper")
    wrapper = FactoryBasedNormalizationService()

    test_text = "Павловой Дарьи"
    result = await wrapper.normalize_async(
        test_text,
        language="ru",
        enable_advanced_features=True
    )

    print(f"🔍 Input: '{test_text}'")
    print(f"📝 Normalized: '{result.normalized}'")
    print(f"✅ Success: {result.success}")
    print(f"🌍 Language: {result.language}")
    print(f"🔍 Tokens: {result.tokens}")

    # Test 2: Orchestrator with factory wrapper
    print("\n📋 Test 2: Orchestrator with factory wrapper")
    orchestrator = await OrchestratorFactory.create_testing_orchestrator(minimal=True)

    orchestrator_result = await orchestrator.process(test_text)

    print(f"🔍 Input: '{test_text}'")
    print(f"📝 Normalized: '{orchestrator_result.normalized_text}'")
    print(f"✅ Success: {orchestrator_result.success}")
    print(f"🌍 Language: {orchestrator_result.language}")

    # Check if fix worked
    if result.normalized == "Дарья Павлова":
        print("🎉 DECLENSION FIXED IN WRAPPER!")
    else:
        print(f"❌ Declension not working: '{test_text}' -> '{result.normalized}'")

    if orchestrator_result.normalized_text == "Дарья Павлова":
        print("🎉 DECLENSION FIXED IN ORCHESTRATOR!")
    else:
        print(f"❌ Orchestrator declension not working: '{test_text}' -> '{orchestrator_result.normalized_text}'")

if __name__ == "__main__":
    asyncio.run(test_factory_wrapper())
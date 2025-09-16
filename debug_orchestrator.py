#!/usr/bin/env python3
"""
Debug script to test orchestrator directly
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ai_service.core.orchestrator_factory import OrchestratorFactory

async def test_orchestrator():
    print("=== Testing Orchestrator Directly ===")
    
    # Create orchestrator
    orchestrator = await OrchestratorFactory.create_orchestrator(
        enable_smart_filter=True,
        enable_variants=False,
        enable_embeddings=False,
        enable_decision_engine=False
    )
    
    print(f"Orchestrator created: {orchestrator is not None}")
    
    # Test processing
    text = "Иван Петров"
    print(f"Processing text: '{text}'")
    
    result = await orchestrator.process(
        text=text,
        generate_variants=False,
        generate_embeddings=False,
        remove_stop_words=False,
        preserve_names=True,
        enable_advanced_features=True,
    )
    
    print(f"Result: {result}")
    print(f"Success: {result.success}")
    print(f"Tokens: {result.tokens}")
    print(f"Language: {result.language}")
    print(f"Normalized text: {result.normalized_text}")

if __name__ == "__main__":
    asyncio.run(test_orchestrator())

#!/usr/bin/env python3
"""
Test script for garbage terms filtering
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ai_service.core.unified_orchestrator import UnifiedOrchestrator

async def test_garbage_terms():
    """Test that garbage terms are properly filtered"""

    orchestrator = UnifiedOrchestrator()

    test_cases = [
        "Прийом оплат клієнтів додатку tахi838",
        "Перевезення",
        "Кухарук В. Р.",  # This should still be processed as a valid name
        "Іван Петров",     # This should definitely be processed
    ]

    for i, text in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test case {i}: '{text}'")
        print('='*60)

        try:
            result = await orchestrator.process_async(text)

            print(f"Original: {text}")
            print(f"Normalized: {result.normalized}")
            print(f"Success: {result.success}")
            print(f"Language: {result.language}")

            # Check smart filter result
            if hasattr(result, 'smartfilter') and result.smartfilter:
                print(f"Smart filter confidence: {result.smartfilter.confidence}")
                print(f"Smart filter should_process: {getattr(result.smartfilter, 'should_process', 'N/A')}")

            # Check normalization result
            if result.tokens:
                print(f"Tokens: {result.tokens}")

            # Check if any names were detected
            names_detected = len(result.tokens) > 0 and result.normalized.strip()
            print(f"Names detected: {names_detected}")

        except Exception as e:
            print(f"Error processing '{text}': {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_garbage_terms())
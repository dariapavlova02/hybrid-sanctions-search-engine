#!/usr/bin/env python3
"""
Test Signals Service directly
"""

import sys
import os
import asyncio

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from ai_service.layers.signals.signals_service import SignalsService

async def test_signals_service():
    print("=== Testing Signals Service ===")
    
    service = SignalsService()
    
    text = "Платіж від Івана Петренко для ТОВ Товари і послуги"
    print(f"Input text: '{text}'")
    
    # Test extraction
    result = await service.extract_async(text, language="uk")
    print(f"Result: {result}")
    print(f"Organizations: {result.get('organizations', [])}")
    print(f"Persons: {result.get('persons', [])}")

if __name__ == "__main__":
    asyncio.run(test_signals_service())

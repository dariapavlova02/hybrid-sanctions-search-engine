#!/usr/bin/env python3
"""Debug English ALL-CAPS normalization issue."""

import sys
import os
sys.path.insert(0, '/Users/dariapavlova/Desktop/ai-service/src')

from ai_service.layers.normalization.normalization_service import NormalizationService

def debug_english_caps():
    """Debug English ALL-CAPS normalization"""
    print("=== English ALL-CAPS Debug ===")

    service = NormalizationService()

    test_cases = [
        "Sent to ELON MUSK for X corp",
        "For BARACK H. OBAMA, invoice 123",
    ]

    for text in test_cases:
        print(f"\n--- Testing: {text} ---")
        result = service.normalize(text, language="en")
        print(f"Normalized: '{result.normalized}'")
        print(f"Tokens: {result.tokens}")
        print("Trace:")
        for trace in result.trace:
            print(f"  {trace.token} -> {trace.output} (role: {trace.role}, rule: {trace.rule})")

if __name__ == "__main__":
    debug_english_caps()
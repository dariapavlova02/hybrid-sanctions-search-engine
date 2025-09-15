#!/usr/bin/env python3
"""Debug morphology for Дар'ї"""

import sys
import os
sys.path.insert(0, '/Users/dariapavlova/Desktop/ai-service/src')

from ai_service.layers.normalization.normalization_service import NormalizationService

def debug_dari_morph():
    """Debug morphology issue with Дар'ї"""
    print("=== Дар'ї Morphology Debug ===")

    service = NormalizationService()

    token = "Дар'ї"
    print(f"Testing token: {token}")

    # Test morphology directly
    result = service._morph_nominal(token, "uk")
    print(f"_morph_nominal result: '{result}'")

    # Test the Ukrainian morphology service
    uk_morph = service._get_morph("uk")
    if uk_morph:
        print(f"Ukrainian morphology available: {uk_morph.morph_analyzer is not None}")
        if uk_morph.morph_analyzer:
            import pymorphy3
            analyzer = pymorphy3.MorphAnalyzer(lang="uk")
            parses = analyzer.parse(token)
            print(f"Direct pymorphy3 parses for '{token}':")
            for i, p in enumerate(parses):
                print(f"  {i}: {p.normal_form} | {p.tag} | score: {p.score}")
        else:
            print("Ukrainian morphology analyzer is None")
    else:
        print("No Ukrainian morphology service")

    # Test the full normalization pipeline
    print(f"\n--- Full normalization test ---")
    full_result = service.normalize(f"Тест {token}", language="uk")
    print(f"Full result: '{full_result.normalized}'")
    for trace in full_result.trace:
        if trace.token == token:
            print(f"Trace for {token}: {trace}")

if __name__ == "__main__":
    debug_dari_morph()
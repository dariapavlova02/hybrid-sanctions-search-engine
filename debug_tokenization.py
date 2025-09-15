#!/usr/bin/env python3
"""Debug tokenization issue with Дар'ї"""

import sys
import os
sys.path.insert(0, '/Users/dariapavlova/Desktop/ai-service/src')

from ai_service.layers.normalization.normalization_service import NormalizationService

def debug_tokenization():
    """Debug tokenization issue"""
    print("=== Tokenization Debug ===")

    service = NormalizationService()

    # Test different steps
    text = "Оплата від Павлової Дар'ї Юріївни"
    print(f"Original text: {text}")

    # Step 1: Strip noise and tokenize
    tokens = service._strip_noise_and_tokenize(text, language="uk")
    print(f"After tokenization: {tokens}")

    # Step 2: Tag roles
    tagged = service._tag_roles(tokens, language="uk")
    print(f"After role tagging: {tagged}")

    # Try normalizing just these tokens
    print(f"\n--- Manual token normalization ---")
    for token, role in tagged:
        print(f"{token} ({role})")
        result = service._morph_nominal(token, "uk")
        print(f"  -> morph result: {result}")

    # Check if diminutives working
    from ai_service.data.dicts.ukrainian_diminutives import UKRAINIAN_DIMINUTIVES
    print(f"\n--- Diminutive lookup ---")
    dari_key = "дар'ї"
    print(f"дар'ї in diminutives: {dari_key in UKRAINIAN_DIMINUTIVES}")
    if dari_key in UKRAINIAN_DIMINUTIVES:
        print(f"  -> {UKRAINIAN_DIMINUTIVES[dari_key]}")
    print(f"дарї in diminutives: {'дарї' in UKRAINIAN_DIMINUTIVES}")
    if 'дарї' in UKRAINIAN_DIMINUTIVES:
        print(f"  -> {UKRAINIAN_DIMINUTIVES['дарї']}")

if __name__ == "__main__":
    debug_tokenization()
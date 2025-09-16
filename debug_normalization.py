#!/usr/bin/env python3
"""
Debug script to test normalization step by step
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ai_service.layers.normalization.normalization_service import NormalizationService
from ai_service.layers.language.language_detection_service import LanguageDetectionService
from ai_service.layers.unicode.unicode_service import UnicodeService

def test_normalization():
    print("=== Testing Normalization Step by Step ===")
    
    # Initialize services
    normalization_service = NormalizationService()
    
    text = "Иван Петров"
    print(f"Input text: '{text}'")
    
    # Test tokenization
    print("\n=== Step 1: Tokenization ===")
    tokens = normalization_service._strip_noise_and_tokenize(
        text, language="ru", remove_stop_words=False, preserve_names=True
    )
    print(f"Tokens: {tokens}")
    
    if not tokens:
        print("ERROR: No tokens generated!")
        return
    
    # Test role tagging
    print("\n=== Step 2: Role Tagging ===")
    tagged_tokens = normalization_service._tag_roles(tokens, "ru")
    print(f"Tagged tokens: {tagged_tokens}")
    
    if not tagged_tokens:
        print("ERROR: No tagged tokens!")
        return
    
    # Test normalization
    print("\n=== Step 3: Normalization ===")
    normalized_tokens, traces = normalization_service._normalize_slavic_tokens(
        tagged_tokens, "ru", enable_advanced_features=True
    )
    print(f"Normalized tokens: {normalized_tokens}")
    print(f"Traces: {traces}")
    
    # Test full normalization
    print("\n=== Full Normalization ===")
    result = normalization_service._normalize_sync(
        text, language="ru", remove_stop_words=False, 
        preserve_names=True, enable_advanced_features=True
    )
    print(f"Result: {result}")
    print(f"Success: {result.success}")
    print(f"Tokens: {result.tokens}")
    print(f"Language: {result.language}")

if __name__ == "__main__":
    test_normalization()

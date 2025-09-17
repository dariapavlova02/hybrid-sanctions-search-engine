#!/usr/bin/env python3
"""
Test script for normalization with edge characters.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.ai_service.layers.normalization.normalization_service import NormalizationService

def test_normalization_edge_chars():
    """Test normalization with edge characters."""
    service = NormalizationService()
    
    # Test cases for edge characters
    test_cases = [
        "Иван 123 Петров",
        "Иван ª Петров", 
        "Иван 0 Петров",
        "ª Иван ª",
        "Иван º Петров",
        "0",  # Single digit
        "ª",  # Single special character
    ]
    
    flags = {
        "remove_stop_words": True,
        "preserve_names": True,
        "enable_advanced_features": True,
        "strict_stopwords": True,
        "preserve_feminine_suffix_uk": False,
        "enable_spacy_uk_ner": False
    }
    
    print("Testing normalization with edge characters:")
    print("=" * 50)
    
    for text in test_cases:
        print(f"\nInput: '{text}'")
        try:
            result = service.normalize(text, **flags)
            print(f"Success: {result.success}")
            print(f"Normalized: '{result.normalized}'")
            print(f"Tokens: {result.tokens}")
            print(f"Language: {result.language}")
            print(f"Errors: {result.errors}")
            
            # Test idempotence
            if result.success:
                result2 = service.normalize(result.normalized, **flags)
                if result2.success:
                    print(f"Idempotent: {result.normalized == result2.normalized}")
                    if result.normalized != result2.normalized:
                        print(f"  First: '{result.normalized}'")
                        print(f"  Second: '{result2.normalized}'")
                else:
                    print(f"Second normalization failed: {result2.errors}")
            
        except Exception as e:
            print(f"Exception: {e}")
            import traceback
            traceback.print_exc()
        
        print("-" * 30)

if __name__ == "__main__":
    test_normalization_edge_chars()

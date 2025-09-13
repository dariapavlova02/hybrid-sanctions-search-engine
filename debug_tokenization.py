#!/usr/bin/env python3
"""
Debug tokenization issues
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ai_service.services.normalization_service import NormalizationService

def debug_tokenization():
    """Debug tokenization step by step"""
    print("Debugging tokenization...")
    
    service = NormalizationService()
    
    test_texts = [
        "А.С. Пушкин",
        "П.І. Чайковський", 
        "John Smith",
        "Петро Іванович"
    ]
    
    for text in test_texts:
        print(f"\nText: '{text}'")
        
        # Test basic cleanup
        cleaned = service.basic_cleanup(text, preserve_names=True)
        print(f"Cleaned: '{cleaned}'")
        
        # Test unicode normalization
        unicode_cleaned = service.normalize_unicode(cleaned)
        print(f"Unicode cleaned: '{unicode_cleaned}'")
        
        # Test tokenization
        tokens = service.tokenize_text(unicode_cleaned, 'ru')
        print(f"Tokens: {tokens}")
        
        # Test initial detection
        for token in tokens:
            is_init = service._is_initial(token)
            print(f"  '{token}' is initial: {is_init}")

if __name__ == "__main__":
    debug_tokenization()

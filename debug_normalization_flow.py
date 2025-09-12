#!/usr/bin/env python3
"""
Отладка потока нормализации
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from ai_service.services.normalization_service import NormalizationService

def test_normalization_flow():
    service = NormalizationService()
    
    test_cases = [
        "Вовчика",
        "Сашка",
    ]
    
    for text in test_cases:
        print(f"\n=== Testing: {text} ===")
        
        # Test tokenization
        tokens = service.tokenize_text(text, "uk")
        print(f"Tokens: {tokens}")
        
        # Test Ukrainian forms
        ukrainian_forms = service._get_ukrainian_forms(tokens)
        print(f"Ukrainian forms: {ukrainian_forms}")
        
        # Test full normalization
        result = service.normalize(text, language="uk", enable_advanced_features=True)
        print(f"Full result: {result.tokens}")

if __name__ == "__main__":
    test_normalization_flow()

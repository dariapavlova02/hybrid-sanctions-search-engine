#!/usr/bin/env python3
"""
Test script for NormalizationService pipeline
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ai_service.services.normalization_service import NormalizationService

async def test_pipeline():
    """Test the full normalization pipeline"""
    print("Testing NormalizationService pipeline...")
    
    # Initialize service
    service = NormalizationService()
    
    # Test cases
    test_cases = [
        {
            "text": "Петро Іванович",
            "language": "uk",
            "description": "Ukrainian name"
        },
        {
            "text": "Иван Петрович",
            "language": "ru", 
            "description": "Russian name"
        },
        {
            "text": "John Smith",
            "language": "en",
            "description": "English name"
        },
        {
            "text": "А.С. Пушкин",
            "language": "ru",
            "description": "Russian name with initials"
        },
        {
            "text": "П.І. Чайковський",
            "language": "uk",
            "description": "Ukrainian name with initials"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_case['description']} ---")
        print(f"Input: '{test_case['text']}'")
        print(f"Language: {test_case['language']}")
        
        try:
            result = await service.normalize(
                text=test_case['text'],
                language=test_case['language'],
                remove_stop_words=False,
                apply_stemming=False,
                apply_lemmatization=True,
                clean_unicode=True,
                preserve_names=True,
                enable_advanced_features=True
            )
            
            print(f"Normalized: '{result.normalized}'")
            print(f"Tokens: {result.tokens}")
            print(f"Success: {result.success}")
            print(f"Processing time: {result.processing_time:.4f}s")
            
            if result.errors:
                print(f"Errors: {result.errors}")
                
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n--- Pipeline test completed ---")

if __name__ == "__main__":
    asyncio.run(test_pipeline())

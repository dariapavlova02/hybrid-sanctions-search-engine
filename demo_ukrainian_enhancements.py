#!/usr/bin/env python3
"""
Demo script for Ukrainian normalization enhancements.

Demonstrates the new Ukrainian-specific features:
1. strict_stopwords flag for preventing preposition/conjunction conflicts with initials
2. preserve_feminine_suffix_uk flag for preserving feminine surname suffixes
3. enable_spacy_uk_ner flag for NER-enhanced role tagging
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.ai_service.layers.normalization.normalization_service import NormalizationService


async def demo_ukrainian_enhancements():
    """Demonstrate Ukrainian normalization enhancements."""
    print("🇺🇦 Ukrainian Normalization Enhancements Demo")
    print("=" * 50)
    
    # Initialize service
    service = NormalizationService()
    
    # Test cases
    test_cases = [
        {
            "text": "Переказ з картки О. Петренко",
            "description": "Preposition 'з' should not be tagged as initial with strict_stopwords=True"
        },
        {
            "text": "Анна Ковальська",
            "description": "Feminine suffix -ська should be preserved with preserve_feminine_suffix_uk=True"
        },
        {
            "text": "Анна Ковальської",
            "description": "Feminine genitive -ської should become -ська with preserve_feminine_suffix_uk=True"
        },
        {
            "text": "ТОВ ПРИВАТБАНК",
            "description": "Organization should be detected with NER (if available)"
        },
        {
            "text": "Анна Ковальська працює в ТОВ ПРИВАТБАНК",
            "description": "Mixed person and organization with NER"
        }
    ]
    
    # Test without enhancements
    print("\n📝 Testing WITHOUT Ukrainian enhancements:")
    print("-" * 40)
    
    for case in test_cases:
        print(f"\nText: {case['text']}")
        print(f"Description: {case['description']}")
        
        result = await service.normalize_async(
            case['text'],
            language="uk",
            strict_stopwords=False,
            preserve_feminine_suffix_uk=False,
            enable_spacy_uk_ner=False
        )
        
        print(f"Normalized: {result.normalized}")
        print(f"Tokens: {result.tokens}")
        if result.trace:
            print(f"Trace: {result.trace[:3]}...")  # Show first 3 trace entries
    
    # Test with enhancements
    print("\n🚀 Testing WITH Ukrainian enhancements:")
    print("-" * 40)
    
    for case in test_cases:
        print(f"\nText: {case['text']}")
        print(f"Description: {case['description']}")
        
        result = await service.normalize_async(
            case['text'],
            language="uk",
            strict_stopwords=True,
            preserve_feminine_suffix_uk=True,
            enable_spacy_uk_ner=True
        )
        
        print(f"Normalized: {result.normalized}")
        print(f"Tokens: {result.tokens}")
        if result.trace:
            print(f"Trace: {result.trace[:3]}...")  # Show first 3 trace entries
    
    # Test specific functionality
    print("\n🔍 Detailed Functionality Tests:")
    print("-" * 40)
    
    # Test 1: Stopwords vs initials
    print("\n1. Stopwords vs Initials Test:")
    text1 = "Переказ з картки О. Петренко"
    
    result_no_strict = await service.normalize_async(text1, language="uk", strict_stopwords=False)
    result_strict = await service.normalize_async(text1, language="uk", strict_stopwords=True)
    
    print(f"Without strict_stopwords: {result_no_strict.tokens}")
    print(f"With strict_stopwords: {result_strict.tokens}")
    
    # Test 2: Feminine suffix preservation
    print("\n2. Feminine Suffix Preservation Test:")
    text2 = "Анна Ковальської"
    
    result_no_preserve = await service.normalize_async(text2, language="uk", preserve_feminine_suffix_uk=False)
    result_preserve = await service.normalize_async(text2, language="uk", preserve_feminine_suffix_uk=True)
    
    print(f"Without preserve_feminine_suffix_uk: {result_no_preserve.normalized}")
    print(f"With preserve_feminine_suffix_uk: {result_preserve.normalized}")
    
    # Test 3: NER functionality (if available)
    print("\n3. NER Functionality Test:")
    text3 = "Анна Ковальська працює в ТОВ ПРИВАТБАНК"
    
    result_no_ner = await service.normalize_async(text3, language="uk", enable_spacy_uk_ner=False)
    result_ner = await service.normalize_async(text3, language="uk", enable_spacy_uk_ner=True)
    
    print(f"Without NER: {result_no_ner.tokens}")
    print(f"With NER: {result_ner.tokens}")
    
    # Check if NER is available
    try:
        from src.ai_service.layers.normalization.ner_gateways import get_spacy_uk_ner
        ner = get_spacy_uk_ner()
        if ner.is_available():
            print("✅ spaCy Ukrainian NER is available")
        else:
            print("❌ spaCy Ukrainian NER is not available (install with: python -m spacy download uk_core_news_sm)")
    except ImportError:
        print("❌ spaCy not installed")
    
    print("\n🎉 Demo completed!")


if __name__ == "__main__":
    asyncio.run(demo_ukrainian_enhancements())

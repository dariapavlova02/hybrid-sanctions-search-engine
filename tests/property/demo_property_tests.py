#!/usr/bin/env python3
"""
Demo script for property-based tests of NormalizationService.

This script demonstrates the property-based testing approach and shows
how the tests validate critical properties of the normalization service.
"""

import sys
import os
from pathlib import Path

# Add src to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from src.ai_service.layers.normalization.normalization_service import NormalizationService


def demo_property_tests():
    """Demonstrate property-based testing concepts."""
    print("=== Property-Based Testing Demo ===\n")
    
    # Initialize service
    service = NormalizationService()
    flags = {
        "remove_stop_words": True,
        "preserve_names": True,
        "enable_advanced_features": True,
        "strict_stopwords": True,
        "preserve_feminine_suffix_uk": False,
        "enable_spacy_uk_ner": False
    }
    
    # Test cases for different properties
    test_cases = [
        "Александр Петров",
        "Мария Сидорова",
        "John Smith",
        "Олександр Петренко",
        "Анна Козлова",
        "William Johnson",
        "Петр-Сидоров",
        "Mary-Jane Wilson"
    ]
    
    print("1. Idempotence Test (norm(norm(x)) == norm(x))")
    print("-" * 50)
    for text in test_cases:
        result1 = service.normalize(text, **flags)
        if result1.success:
            result2 = service.normalize(result1.normalized, **flags)
            if result2.success:
                # Check if core letters are the same (allowing for morphological changes)
                letters1 = ''.join(c.lower() for c in result1.normalized if c.isalnum())
                letters2 = ''.join(c.lower() for c in result2.normalized if c.isalnum())
                is_idempotent = letters1 == letters2
                print(f"✓ '{text}' -> '{result1.normalized}' -> '{result2.normalized}' (idempotent: {is_idempotent})")
            else:
                print(f"✗ '{text}' -> '{result1.normalized}' -> FAILED (second normalization)")
        else:
            print(f"✗ '{text}' -> FAILED (first normalization)")
    
    print("\n2. Feminine Preservation Test")
    print("-" * 50)
    feminine_cases = [
        "Мария Петрова",
        "Анна Козлова",
        "Олена Сидоренко",
        "Elizabeth Johnson"
    ]
    
    for text in feminine_cases:
        result = service.normalize(text, **flags)
        if result.success:
            # Check for feminine suffixes
            feminine_suffixes = {'ова', 'ева', 'іна', 'ська', 'ская'}
            has_feminine = any(any(token.lower().endswith(suffix) for suffix in feminine_suffixes) 
                             for token in result.tokens)
            print(f"✓ '{text}' -> '{result.normalized}' (feminine preserved: {has_feminine})")
        else:
            print(f"✗ '{text}' -> FAILED")
    
    print("\n3. Character Set Test (output ⊆ input + allowed additions)")
    print("-" * 50)
    for text in test_cases:
        result = service.normalize(text, **flags)
        if result.success:
            input_chars = set(c.lower() for c in text if c.isalnum())
            output_chars = set(c.lower() for c in result.normalized if c.isalnum())
            allowed_additions = {'.', '-'}
            extra_chars = output_chars - input_chars - allowed_additions
            is_valid = len(extra_chars) == 0
            print(f"✓ '{text}' -> '{result.normalized}' (valid charset: {is_valid})")
            if extra_chars:
                print(f"  Extra chars: {extra_chars}")
        else:
            print(f"✗ '{text}' -> FAILED")
    
    print("\n4. Metamorphic Test (order independence)")
    print("-" * 50)
    order_test_cases = [
        ("Александр Петров", "Петров Александр"),
        ("Мария Сидорова", "Сидорова Мария"),
        ("John Smith", "Smith John")
    ]
    
    for original, reversed_order in order_test_cases:
        result1 = service.normalize(original, **flags)
        result2 = service.normalize(reversed_order, **flags)
        
        if result1.success and result2.success:
            # Check if token sets are the same (ignoring order)
            tokens1 = set(''.join(c.lower() for c in token if c.isalnum()) for token in result1.tokens)
            tokens2 = set(''.join(c.lower() for c in token if c.isalnum()) for token in result2.tokens)
            is_metamorphic = tokens1 == tokens2
            print(f"✓ '{original}' vs '{reversed_order}' (metamorphic: {is_metamorphic})")
            print(f"  Tokens1: {tokens1}")
            print(f"  Tokens2: {tokens2}")
        else:
            print(f"✗ '{original}' vs '{reversed_order}' -> FAILED")
    
    print("\n=== Demo Complete ===")
    print("\nProperty-based tests validate these critical properties:")
    print("1. Idempotence: Multiple normalizations should be stable")
    print("2. Feminine preservation: Gender information should be maintained")
    print("3. Character set constraints: Only allowed characters should be added")
    print("4. Metamorphic properties: Order changes should not affect core structure")
    print("\nThese tests use Hypothesis to generate thousands of test cases")
    print("automatically, providing comprehensive coverage of edge cases.")


if __name__ == "__main__":
    demo_property_tests()

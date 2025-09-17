#!/usr/bin/env python3
"""
Test script for edge character rules implementation.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.ai_service.layers.normalization.processors.token_processor import TokenProcessor

def test_edge_characters():
    """Test edge character rules."""
    processor = TokenProcessor()
    
    # Test cases for edge characters
    test_cases = [
        ("Иван 123 Петров", "Should preserve digits in trace"),
        ("Иван ª Петров", "Should remove special characters"),
        ("Иван 0 Петров", "Should handle single digits"),
        ("ª Иван ª", "Should handle multiple special characters"),
        ("Иван º Петров", "Should handle different special characters"),
    ]
    
    print("Testing edge character rules:")
    print("=" * 50)
    
    for text, description in test_cases:
        print(f"\nInput: '{text}'")
        print(f"Description: {description}")
        
        # Test with preserve_names=True
        tokens, traces, metadata = processor.strip_noise_and_tokenize(
            text, 
            language="uk", 
            preserve_names=True,
            remove_stop_words=False
        )
        
        print(f"Tokens: {tokens}")
        print(f"Traces: {traces}")
        print("-" * 30)
    
    print("\nTesting with remove_stop_words=True:")
    print("=" * 50)
    
    # Test with stop word filtering
    for text, description in test_cases:
        print(f"\nInput: '{text}'")
        print(f"Description: {description}")
        
        tokens, traces, metadata = processor.strip_noise_and_tokenize(
            text, 
            language="uk", 
            preserve_names=True,
            remove_stop_words=True
        )
        
        print(f"Tokens: {tokens}")
        print(f"Traces: {traces}")
        print("-" * 30)

if __name__ == "__main__":
    test_edge_characters()

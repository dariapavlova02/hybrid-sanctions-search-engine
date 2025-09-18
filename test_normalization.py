#!/usr/bin/env python3
"""
Test script for normalization API
"""

import requests
import json

def test_normalization(text, language="auto"):
    """Test normalization with given text and language"""
    url = "http://localhost:8000/normalize"
    data = {
        "text": text,
        "language": language,
        "apply_lemmatization": True,  # Enable morphological normalization
        "remove_stop_words": True,
        "preserve_names": True,
        "options": {
            "flags": {
                "enable_cache": False  # Disable cache to use MorphologyProcessor
            }
        }
    }
    
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

def main():
    """Test various normalization cases"""
    test_cases = [
        ("John Smith", "en"),
        ("Иван Петров", "ru"),
        ("Дашеньки Павловой", "ru"),
        ("Платеж от Дашеньки Павловой", "ru"),
        ("Платеж от Вики Кухарук", "ru"),
        ("Оплата комунальних послуг від Петра Порошенка", "uk")
    ]
    
    for text, lang in test_cases:
        print(f"\n=== Testing: '{text}' (language: {lang}) ===")
        result = test_normalization(text, lang)
        if result:
            print(f"Success: {result['success']}")
            print(f"Language: {result['language']}")
            print(f"Normalized: '{result['normalized_text']}'")
            print(f"Tokens: {result['tokens']}")
            if result.get('trace'):
                print("Trace details:")
                for i, trace in enumerate(result['trace']):
                    if isinstance(trace, str):
                        try:
                            trace_data = json.loads(trace)
                            print(f"  Token {i}: {trace_data}")
                        except:
                            print(f"  Token {i}: {trace}")
                    else:
                        print(f"  Token {i}: {trace}")
            if result['errors']:
                print(f"Errors: {result['errors']}")
        else:
            print("Failed to get response")

if __name__ == "__main__":
    main()

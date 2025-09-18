#!/usr/bin/env python3
"""
Test script for Вики normalization only
"""

import requests
import json

def test_viki_only():
    """Test Вики normalization only"""
    url = "http://localhost:8000/normalize"
    data = {
        "text": "Вики",
        "language": "ru",
        "apply_lemmatization": True,
        "remove_stop_words": True,
        "preserve_names": True
    }
    
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        result = response.json()
        
        print(f"Text: 'Вики'")
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
            
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_viki_only()

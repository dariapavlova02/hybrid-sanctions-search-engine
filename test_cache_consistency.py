#!/usr/bin/env python3
"""
Test script to verify cache ON/OFF consistency
"""

import requests
import json

def test_normalization_with_cache(text, language="ru", cache_enabled=True):
    """Test normalization with given cache setting"""
    url = "http://localhost:8000/normalize"
    data = {
        "text": text,
        "language": language,
        "apply_lemmatization": True,
        "remove_stop_words": True,
        "preserve_names": True,
        "options": {
            "flags": {
                "enable_cache": cache_enabled
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

def test_cache_consistency():
    """Test that cache ON and OFF give identical results"""
    test_cases = [
        "Вики Кухарук",
        "Дашеньки Павловой", 
        "Сашка Пушкин",
        "Вове Петрову",
        "Марии Сидоровой",
        "Олені Петренко"
    ]
    
    print("Testing cache consistency (ON vs OFF):")
    print("=" * 50)
    
    all_consistent = True
    
    for text in test_cases:
        print(f"\nTesting: '{text}'")
        
        # Test with cache ON
        result_cache_on = test_normalization_with_cache(text, cache_enabled=True)
        # Test with cache OFF  
        result_cache_off = test_normalization_with_cache(text, cache_enabled=False)
        
        if not result_cache_on or not result_cache_off:
            print(f"  ❌ Failed to get results")
            all_consistent = False
            continue
            
        # Compare results
        cache_on_normalized = result_cache_on.get('normalized_text', '')
        cache_off_normalized = result_cache_off.get('normalized_text', '')
        
        cache_on_tokens = result_cache_on.get('tokens', [])
        cache_off_tokens = result_cache_off.get('tokens', [])
        
        if cache_on_normalized == cache_off_normalized and cache_on_tokens == cache_off_tokens:
            print(f"  ✅ Consistent: '{cache_on_normalized}'")
        else:
            print(f"  ❌ INCONSISTENT!")
            print(f"    Cache ON:  '{cache_on_normalized}' {cache_on_tokens}")
            print(f"    Cache OFF: '{cache_off_normalized}' {cache_off_tokens}")
            all_consistent = False
    
    print("\n" + "=" * 50)
    if all_consistent:
        print("🎉 All tests passed! Cache ON and OFF are consistent.")
    else:
        print("❌ Some tests failed! Cache ON and OFF are inconsistent.")
    
    return all_consistent

if __name__ == "__main__":
    test_cache_consistency()

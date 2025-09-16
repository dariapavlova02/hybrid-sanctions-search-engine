#!/usr/bin/env python3
"""
Test API directly
"""

import requests
import json

def test_api():
    url = "http://localhost:8000/normalize"
    data = {"text": "Иван Петров"}
    
    print(f"Testing API: {url}")
    print(f"Data: {data}")
    
    try:
        response = requests.post(url, json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result.get('success')}")
            print(f"Tokens: {result.get('tokens')}")
            print(f"Language: {result.get('language')}")
            print(f"Normalized text: {result.get('normalized_text')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()

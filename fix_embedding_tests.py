#!/usr/bin/env python3
"""
Script to fix embedding service tests by updating API calls and attributes
"""

import re

def fix_embedding_tests():
    file_path = "tests/unit/embeddings/test_embedding_service_comprehensive.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace non-existent attributes with real ones
    replacements = [
        (r"service\.default_model", "service.config.model_name"),
        (r"service\.model_cache", "service.config"),
        (r"hasattr\(service, 'model_cache'\)", "hasattr(service, 'config')"),
        (r"hasattr\(service, 'default_model'\)", "hasattr(service, 'config')"),
        (r"isinstance\(service\.model_cache, dict\)", "isinstance(service.config, object)"),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    # Fix method calls that don't exist
    content = re.sub(r"service\._load_model\([^)]*\)", "service._load_model()", content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Fixed embedding service tests")

if __name__ == "__main__":
    fix_embedding_tests()

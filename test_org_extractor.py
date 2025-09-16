#!/usr/bin/env python3
"""
Test OrganizationExtractor directly
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from ai_service.layers.signals.extractors.organization_extractor import OrganizationExtractor

def test_org_extractor():
    print("=== Testing OrganizationExtractor ===")
    
    extractor = OrganizationExtractor()
    
    text = "Платіж від Івана Петренко для ТОВ Товари і послуги"
    print(f"Input text: '{text}'")
    
    # Test extraction
    organizations = extractor.extract(text, language="uk")
    print(f"Extracted organizations: {organizations}")
    
    # Test with different texts
    test_cases = [
        "ТОВ Рога і Копита",
        "ООО Газпром", 
        "LLC Microsoft",
        "ПАТ ПриватБанк",
        "ТОВ Товари і послуги",
    ]
    
    for test_text in test_cases:
        orgs = extractor.extract(test_text, language="uk")
        print(f"'{test_text}' -> {orgs}")

if __name__ == "__main__":
    test_org_extractor()

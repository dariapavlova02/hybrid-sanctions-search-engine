#!/usr/bin/env python3
"""
Simple test to verify legal forms detection works.
"""

import sys
sys.path.append('src')

from ai_service.data.patterns.legal_forms import is_legal_form, extract_legal_forms
from ai_service.layers.signals.extractors.organization_extractor import OrganizationExtractor

def test_simple_legal_form():
    """Simple test for legal forms."""
    print("🧪 SIMPLE LEGAL FORMS TEST")
    print("=" * 40)

    test_cases = [
        "Одін Марін Інкорпорейтед",
        "Компанія ТОВ",
        "Test Inc",
    ]

    for text in test_cases:
        print(f"\nTesting: '{text}'")

        # Test legal form detection
        detected = is_legal_form(text, "auto")
        forms = extract_legal_forms(text, "auto")

        print(f"  Legal form detected: {detected}")
        if forms:
            for form in forms:
                print(f"  Found: '{form['abbreviation']}' -> '{form['full_name']}'")

        # Test organization extraction
        try:
            org_extractor = OrganizationExtractor()
            # Create mock normalization result
            class MockNormResult:
                def __init__(self, text):
                    self.normalized = text
                    self.tokens = text.split()
                    self.organizations = {}

            mock_result = MockNormResult(text)

            # Try to extract organizations
            orgs = org_extractor.extract_organizations(text, mock_result, "auto")
            print(f"  Organizations found: {len(orgs)}")
            for org in orgs:
                print(f"    Core: {org.get('core', 'N/A')}")
                print(f"    Legal form: {org.get('legal_form', 'N/A')}")
                print(f"    Full: {org.get('full', 'N/A')}")

        except Exception as e:
            print(f"  Organization extraction error: {e}")

if __name__ == "__main__":
    test_simple_legal_form()
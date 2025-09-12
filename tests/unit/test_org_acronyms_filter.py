#!/usr/bin/env python3
"""
Unit tests for ORG_LEGAL_FORMS filter in normalization service.
"""

import pytest
from ai_service.services.normalization_service import NormalizationService, ORG_LEGAL_FORMS


class TestOrgAcronymsFilter:
    """Test that company legal acronyms are filtered out and never leak into person names."""
    
    @pytest.fixture
    def service(self):
        """Create normalization service instance."""
        return NormalizationService()
    
    def test_org_acronyms_are_tagged_as_unknown(self, service):
        """Test that ORG_LEGAL_FORMS are tagged as 'unknown' and excluded from positional fallbacks."""
        # Test with the specific input from the requirements
        text = "OOO 'Тест' переводит средства Ивану Петрову"
        
        # Check tokenization and role tagging before normalization
        tokens = service._strip_noise_and_tokenize(text, "ru", remove_stop_words=True, preserve_names=True)
        tagged_tokens = service._tag_roles(tokens, "ru")
        
        # Find the roles for OOO and Тест
        ooo_role = None
        test_role = None
        for token, role in tagged_tokens:
            if token.upper() == "OOO":
                ooo_role = role
            elif token == "__QUOTED__Тест":
                test_role = role
        
        # Both should be tagged as unknown
        assert ooo_role == "unknown", f"Expected OOO to be tagged as 'unknown', got '{ooo_role}'"
        assert test_role == "unknown", f"Expected Тест to be tagged as 'unknown', got '{test_role}'"
    
    def test_org_acronyms_not_in_normalized_output(self, service):
        """Test that ORG_LEGAL_FORMS do not appear in the final normalized string."""
        text = "OOO 'Тест' переводит средства Ивану Петрову"
        result = service._normalize_sync(text, language="ru")
        
        normalized_text = result.normalized.lower()
        
        # Check that OOO and Тест are not in the normalized output
        assert "ooo" not in normalized_text, f"Expected 'OOO' to be filtered out, but found in: {result.normalized}"
        assert "тест" not in normalized_text, f"Expected 'Тест' to be filtered out, but found in: {result.normalized}"
    
    def test_person_tokens_survive(self, service):
        """Test that person name tokens survive the filtering."""
        text = "OOO 'Тест' переводит средства Ивану Петрову"
        result = service._normalize_sync(text, language="ru")
        
        normalized_text = result.normalized.lower()
        
        # Person names should survive
        assert "иван" in normalized_text, f"Expected 'Иван' to survive, but not found in: {result.normalized}"
        assert "петров" in normalized_text, f"Expected 'Петров' to survive, but not found in: {result.normalized}"
    
    def test_various_org_acronyms_are_filtered(self, service):
        """Test that various ORG_LEGAL_FORMS are properly filtered."""
        test_cases = [
            ("LLC Company", "en"),
            ("GmbH Test", "en"), 
            ("ООО Компания", "ru"),
            ("ЗАО Предприятие", "ru"),
            ("S.A. Corporation", "en"),
            ("S.R.L. Business", "en"),
        ]
        
        for text, language in test_cases:
            result = service._normalize_sync(text, language=language)
            tagged_tokens = service._tag_roles(result.tokens, language)
            
            # Check that company acronyms are tagged as unknown
            for token, role in tagged_tokens:
                if token.casefold() in ORG_LEGAL_FORMS:
                    assert role == "unknown", f"Expected {token} to be tagged as 'unknown', got '{role}'"
    
    def test_org_acronyms_case_insensitive(self, service):
        """Test that ORG_LEGAL_FORMS filtering is case insensitive."""
        test_cases = [
            ("ooo", "ru"),
            ("LLC", "en"),
            ("GmbH", "en"),
            ("S.A.", "en"),
            ("ооо", "ru"),
        ]
        
        for text, language in test_cases:
            result = service._normalize_sync(text, language=language)
            tagged_tokens = service._tag_roles(result.tokens, language)
            
            # Check that the token is tagged as unknown
            for token, role in tagged_tokens:
                if token.casefold() in ORG_LEGAL_FORMS:
                    assert role == "unknown", f"Expected {token} to be tagged as 'unknown', got '{role}'"
    
    def test_org_acronyms_excluded_from_positional_fallbacks(self, service):
        """Test that ORG_LEGAL_FORMS are excluded from positional fallback rules."""
        # Test with OOO at the beginning (should not become 'given')
        text = "OOO переводит средства"
        result = service._normalize_sync(text, language="ru")
        tagged_tokens = service._tag_roles(result.tokens, "ru")
        
        # OOO should remain unknown, not become 'given' due to first position
        for token, role in tagged_tokens:
            if token.upper() == "OOO":
                assert role == "unknown", f"Expected OOO to remain 'unknown' despite first position, got '{role}'"
        
        # Test with LLC at the end (should not become 'surname')
        text = "переводит средства LLC"
        result = service._normalize_sync(text, language="en")
        tagged_tokens = service._tag_roles(result.tokens, "en")
        
        # LLC should remain unknown, not become 'surname' due to last position
        for token, role in tagged_tokens:
            if token.upper() == "LLC":
                assert role == "unknown", f"Expected LLC to remain 'unknown' despite last position, got '{role}'"
    
    def test_mixed_content_with_org_acronyms(self, service):
        """Test mixed content with both person names and company acronyms."""
        text = "Компания ООО 'Тест' переводит средства Ивану Петрову от LLC Business"
        result = service._normalize_sync(text, language="ru")
        
        # Check that person names survive
        normalized_text = result.normalized.lower()
        assert "иван" in normalized_text, f"Expected 'Иван' to survive, but not found in: {result.normalized}"
        assert "петров" in normalized_text, f"Expected 'Петров' to survive, but not found in: {result.normalized}"
        
        # Check that company acronyms are filtered out
        assert "ооо" not in normalized_text, f"Expected 'ООО' to be filtered out, but found in: {result.normalized}"
        assert "тест" not in normalized_text, f"Expected 'Тест' to be filtered out, but found in: {result.normalized}"
        assert "llc" not in normalized_text, f"Expected 'LLC' to be filtered out, but found in: {result.normalized}"
    
    def test_org_acronyms_constant_contains_expected_values(self, service):
        """Test that ORG_LEGAL_FORMS constant contains the expected values."""
        expected_acronyms = {
            "ооо", "зао", "оао", "пао", "ао", "ип", "чп", "фоп", "тов", "пп", "кс",
            "ooo", "llc", "ltd", "inc", "corp", "co", "gmbh", "srl", "s.a.", "s.r.l.", "s.p.a.", "bv", "nv", "oy", "ab", "as", "sa", "ag"
        }
        
        assert ORG_LEGAL_FORMS == expected_acronyms, f"ORG_LEGAL_FORMS constant does not match expected values"
        
        # Test that all expected acronyms are present
        for acronym in expected_acronyms:
            assert acronym in ORG_LEGAL_FORMS, f"Expected acronym '{acronym}' not found in ORG_LEGAL_FORMS"

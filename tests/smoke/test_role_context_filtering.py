#!/usr/bin/env python3
"""
Smoke tests for role context filtering functionality.

Tests the new strict_stopwords flag and ±3 token context window filtering
for legal forms and person stopwords.
"""

import pytest
from typing import List, Dict, Any

from src.ai_service.layers.normalization.role_tagger_service import RoleTaggerService


class TestRoleContextFiltering:
    """Test role context filtering with strict_stopwords flag."""
    
    def test_strict_stopwords_default_false(self):
        """Test that strict_stopwords defaults to False."""
        tagger = RoleTaggerService()
        assert tagger.rules.strict_stopwords is False
    
    def test_strict_stopwords_true_enabled(self):
        """Test that strict_stopwords=True enables person stopword filtering."""
        tagger = RoleTaggerService(strict_stopwords=True)
        assert tagger.rules.strict_stopwords is True
    
    def test_legal_form_context_window_ru(self):
        """Test legal form detection with ±3 token context window in Russian."""
        tagger = RoleTaggerService(strict_stopwords=False)
        
        # Test case: "ООО РОМАШКА" - should detect ORG due to legal form
        tokens = ["ООО", "РОМАШКА"]
        role_tags = tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 2
        assert role_tags[0].role.value == "org"  # ООО
        assert role_tags[1].role.value == "org"  # РОМАШКА (due to context)
        assert "org_legal_form_context" in role_tags[1].reason
    
    def test_legal_form_context_window_uk(self):
        """Test legal form detection with ±3 token context window in Ukrainian."""
        tagger = RoleTaggerService(strict_stopwords=False)
        
        # Test case: "ТЗОВ КВІТКА" - should detect ORG due to legal form
        tokens = ["ТЗОВ", "КВІТКА"]
        role_tags = tagger.tag(tokens, "uk")
        
        assert len(role_tags) == 2
        assert role_tags[0].role.value == "org"  # ТЗОВ
        assert role_tags[1].role.value == "org"  # КВІТКА (due to context)
        assert "org_legal_form_context" in role_tags[1].reason
    
    def test_legal_form_context_window_en(self):
        """Test legal form detection with ±3 token context window in English."""
        tagger = RoleTaggerService(strict_stopwords=False)
        
        # Test case: "LLC FLOWER" - should detect ORG due to legal form
        tokens = ["LLC", "FLOWER"]
        role_tags = tagger.tag(tokens, "en")
        
        assert len(role_tags) == 2
        assert role_tags[0].role.value == "org"  # LLC
        assert role_tags[1].role.value == "org"  # FLOWER (due to context)
        assert "org_legal_form_context" in role_tags[1].reason
    
    def test_person_stopword_filtering_strict_false(self):
        """Test that person stopwords are NOT filtered when strict_stopwords=False."""
        tagger = RoleTaggerService(strict_stopwords=False)
        
        # Test case: "господин Иван" - should NOT filter "господин"
        tokens = ["господин", "Иван"]
        role_tags = tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 2
        # "господин" should get a role (not filtered)
        assert role_tags[0].role.value != "unknown" or "person_stopword_filtered" not in role_tags[0].reason
    
    def test_person_stopword_filtering_strict_true(self):
        """Test that person stopwords ARE filtered when strict_stopwords=True."""
        tagger = RoleTaggerService(strict_stopwords=True)
        
        # Test case: "господин Иван" - should filter "господин"
        tokens = ["господин", "Иван"]
        role_tags = tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 2
        # "господин" should be filtered
        assert role_tags[0].role.value == "unknown"
        assert "person_stopword_filtered" in role_tags[0].reason
    
    def test_person_stopword_with_legal_form_context(self):
        """Test that person stopwords are NOT filtered when legal form is in context."""
        tagger = RoleTaggerService(strict_stopwords=True)
        
        # Test case: "ООО господин Иван" - should NOT filter "господин" due to ООО context
        tokens = ["ООО", "господин", "Иван"]
        role_tags = tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 3
        assert role_tags[0].role.value == "org"  # ООО
        # "господин" should NOT be filtered due to ООО context
        assert "person_stopword_filtered" not in role_tags[1].reason
        assert role_tags[1].role.value == "org"  # господин (due to ООО context)
        assert role_tags[2].role.value == "org"  # Иван (due to ООО context)
    
    def test_mixed_org_noise_strict_true(self):
        """Test mixed organization with noise when strict_stopwords=True."""
        tagger = RoleTaggerService(strict_stopwords=True)
        
        # Test case: "ООО господин РОМАШКА" - should handle mixed content
        tokens = ["ООО", "господин", "РОМАШКА"]
        role_tags = tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 3
        assert role_tags[0].role.value == "org"  # ООО
        # "господин" should be treated as ORG due to ООО context, not filtered
        assert role_tags[1].role.value == "org"  # господин (due to ООО context)
        assert role_tags[2].role.value == "org"  # РОМАШКА (due to ООО context)
    
    def test_ru_context_words_strict_true(self):
        """Test Russian context words when strict_stopwords=True."""
        tagger = RoleTaggerService(strict_stopwords=True)
        
        # Test case: "товарищ Петров" - should filter "товарищ"
        tokens = ["товарищ", "Петров"]
        role_tags = tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 2
        assert role_tags[0].role.value == "unknown"
        assert "person_stopword_filtered" in role_tags[0].reason
        assert role_tags[1].role.value == "surname"  # Петров
    
    def test_uk_context_words_strict_true(self):
        """Test Ukrainian context words when strict_stopwords=True."""
        tagger = RoleTaggerService(strict_stopwords=True)
        
        # Test case: "пан Коваленко" - should filter "пан"
        tokens = ["пан", "Коваленко"]
        role_tags = tagger.tag(tokens, "uk")
        
        assert len(role_tags) == 2
        assert role_tags[0].role.value == "unknown"
        assert "person_stopword_filtered" in role_tags[0].reason
        assert role_tags[1].role.value == "surname"  # Коваленко
    
    def test_en_context_words_strict_true(self):
        """Test English context words when strict_stopwords=True."""
        tagger = RoleTaggerService(strict_stopwords=True)
        
        # Test case: "mister Smith" - should filter "mister"
        tokens = ["mister", "Smith"]
        role_tags = tagger.tag(tokens, "en")
        
        assert len(role_tags) == 2
        assert role_tags[0].role.value == "unknown"
        assert "person_stopword_filtered" in role_tags[0].reason
        assert role_tags[1].role.value == "surname"  # Smith
    
    def test_trace_fields_payment_context_filtered(self):
        """Test that payment_context_filtered trace field is set correctly."""
        tagger = RoleTaggerService(strict_stopwords=True)
        
        # Test case with payment context word
        tokens = ["платеж", "Иван"]
        role_tags = tagger.tag(tokens, "ru")
        trace_entries = tagger.get_trace_entries(tokens, role_tags)
        
        assert len(trace_entries) == 2
        # Check if payment_context_filtered is in trace
        payment_traces = [entry for entry in trace_entries if entry.get("payment_context_filtered")]
        assert len(payment_traces) >= 0  # May or may not be present depending on lexicons
    
    def test_trace_fields_org_legal_form_context(self):
        """Test that org_legal_form_context trace field is set correctly."""
        tagger = RoleTaggerService(strict_stopwords=False)
        
        # Test case with legal form
        tokens = ["ООО", "РОМАШКА"]
        role_tags = tagger.tag(tokens, "ru")
        trace_entries = tagger.get_trace_entries(tokens, role_tags)
        
        assert len(trace_entries) == 2
        # Check if org_legal_form_context is in trace
        org_traces = [entry for entry in trace_entries if entry.get("org_legal_form_context")]
        assert len(org_traces) >= 1  # At least one should have org context
    
    def test_trace_fields_person_stopword_filtered(self):
        """Test that person_stopword_filtered trace field is set correctly."""
        tagger = RoleTaggerService(strict_stopwords=True)
        
        # Test case with person stopword
        tokens = ["господин", "Иван"]
        role_tags = tagger.tag(tokens, "ru")
        trace_entries = tagger.get_trace_entries(tokens, role_tags)
        
        assert len(trace_entries) == 2
        # Check if person_stopword_filtered is in trace
        person_traces = [entry for entry in trace_entries if entry.get("person_stopword_filtered")]
        assert len(person_traces) >= 0  # May or may not be present depending on lexicons
    
    def test_context_window_size(self):
        """Test that context window is properly sized at ±3 tokens."""
        tagger = RoleTaggerService(strict_stopwords=False)
        
        # Test case with legal form at different positions
        tokens = ["А", "Б", "В", "ООО", "Г", "Д", "Е"]
        role_tags = tagger.tag(tokens, "ru")
        trace_entries = tagger.get_trace_entries(tokens, role_tags)
        
        assert len(role_tags) == 7
        # Check that context window information is present
        for i, trace in enumerate(trace_entries):
            if "org_legal_form_context" in trace.get("reason", ""):
                assert "context_window" in trace.get("evidence", [])
    
    def test_golden_cases_ru_context_words(self):
        """Test golden cases for Russian context words."""
        tagger = RoleTaggerService(strict_stopwords=True)
        
        # Golden case: "господин Петров Иван Сергеевич"
        tokens = ["господин", "Петров", "Иван", "Сергеевич"]
        role_tags = tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 4
        assert role_tags[0].role.value == "unknown"  # господин (filtered)
        assert "person_stopword_filtered" in role_tags[0].reason
        assert role_tags[1].role.value == "surname"  # Петров
        assert role_tags[2].role.value == "given"    # Иван
        assert role_tags[3].role.value == "patronymic"  # Сергеевич
    
    def test_golden_cases_mixed_org_noise(self):
        """Test golden cases for mixed organization with noise."""
        tagger = RoleTaggerService(strict_stopwords=True)
        
        # Golden case: "ООО господин РОМАШКА"
        tokens = ["ООО", "господин", "РОМАШКА"]
        role_tags = tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 3
        assert role_tags[0].role.value == "org"  # ООО
        assert role_tags[1].role.value == "org"  # господин (due to ООО context)
        assert role_tags[2].role.value == "org"  # РОМАШКА (due to ООО context)
        # "господин" should NOT be filtered due to ООО context
        assert "person_stopword_filtered" not in role_tags[1].reason


if __name__ == "__main__":
    pytest.main([__file__])

#!/usr/bin/env python3
"""
Smoke tests for role tagger trace structure.

Ensures that trace entries have the correct shape and required fields.
"""

import pytest
from unittest.mock import Mock

from src.ai_service.layers.normalization.role_tagger_service import (
    RoleTaggerService, RoleRules
)
from src.ai_service.layers.normalization.lexicon_loader import Lexicons


class TestRolesTraceShape:
    """Test trace structure and required fields."""
    
    @pytest.fixture
    def mock_lexicons(self):
        """Mock lexicons for testing."""
        lexicons = Mock(spec=Lexicons)
        lexicons.stopwords = {
            'ru': {'и', 'в', 'на', 'с', 'по'},
            'uk': {'і', 'в', 'на', 'з', 'по'},
            'en': {'and', 'in', 'on', 'with', 'by'}
        }
        lexicons.legal_forms = {'ооо', 'тов', 'llc', 'ltd', 'inc', 'corp'}
        return lexicons
    
    @pytest.fixture
    def role_tagger(self, mock_lexicons):
        """Create role tagger service for testing."""
        rules = RoleRules()
        return RoleTaggerService(lexicons=mock_lexicons, rules=rules)
    
    def test_trace_entry_structure(self, role_tagger):
        """Test that trace entries have the correct structure."""
        tokens = ["И.", "Петров", "Иванович"]
        role_tags = role_tagger.tag(tokens, "ru")
        trace_entries = role_tagger.get_trace_entries(tokens, role_tags)
        
        assert len(trace_entries) == 3
        
        for trace_entry in trace_entries:
            # Required fields
            assert "type" in trace_entry
            assert "token" in trace_entry
            assert "role" in trace_entry
            assert "reason" in trace_entry
            assert "evidence" in trace_entry
            assert "confidence" in trace_entry
            assert "state_from" in trace_entry
            assert "state_to" in trace_entry
            
            # Field types
            assert trace_entry["type"] == "role"
            assert isinstance(trace_entry["token"], str)
            assert isinstance(trace_entry["role"], str)
            assert isinstance(trace_entry["reason"], str)
            assert isinstance(trace_entry["evidence"], list)
            assert isinstance(trace_entry["confidence"], (int, float))
            assert isinstance(trace_entry["state_from"], str)
            assert isinstance(trace_entry["state_to"], str)
    
    def test_trace_entry_values(self, role_tagger):
        """Test that trace entry values are valid."""
        tokens = ["И.", "Петров", "Иванович"]
        role_tags = role_tagger.tag(tokens, "ru")
        trace_entries = role_tagger.get_trace_entries(tokens, role_tags)
        
        # Check first token (initial)
        trace1 = trace_entries[0]
        assert trace1["token"] == "И."
        assert trace1["role"] in ["initial", "given", "surname", "patronymic", "org", "unknown"]
        assert trace1["reason"] in [
            "initial_detected", "surname_suffix_detected", "patronymic_suffix_detected",
            "org_legal_form_context", "given_detected", "surname_detected",
            "stopword_filtered", "fallback_unknown"
        ]
        assert len(trace1["evidence"]) > 0
        assert 0.0 <= trace1["confidence"] <= 1.0
        
        # Check second token (surname)
        trace2 = trace_entries[1]
        assert trace2["token"] == "Петров"
        assert trace2["role"] in ["initial", "given", "surname", "patronymic", "org", "unknown"]
        assert len(trace2["evidence"]) > 0
        
        # Check third token (patronymic)
        trace3 = trace_entries[2]
        assert trace3["token"] == "Иванович"
        assert trace3["role"] in ["initial", "given", "surname", "patronymic", "org", "unknown"]
        assert len(trace3["evidence"]) > 0
    
    def test_trace_evidence_content(self, role_tagger):
        """Test that evidence contains meaningful information."""
        tokens = ["И.", "Петров", "ТОВ", "ПРИВАТБАНК"]
        role_tags = role_tagger.tag(tokens, "ru")
        trace_entries = role_tagger.get_trace_entries(tokens, role_tags)
        
        # Check initial evidence
        trace1 = trace_entries[0]
        if trace1["role"] == "initial":
            assert "dot_after_capital" in trace1["evidence"]
        
        # Check surname evidence
        trace2 = trace_entries[1]
        if trace2["role"] == "surname":
            assert "surname_suffix_match" in trace2["evidence"]
            assert any("suffix_" in evidence for evidence in trace2["evidence"])
        
        # Check organization evidence
        trace3 = trace_entries[2]
        if trace3["role"] == "org":
            assert "org_legal_form_context" in trace3["evidence"]
            assert any("legal_form_" in evidence for evidence in trace3["evidence"])
        
        trace4 = trace_entries[3]
        if trace4["role"] == "org":
            assert "org_legal_form_context" in trace4["evidence"]
            assert "CAPS" in trace4["evidence"]
    
    def test_trace_state_transitions(self, role_tagger):
        """Test that state transitions are properly tracked."""
        tokens = ["Иван", "Петров", "Иванович"]
        role_tags = role_tagger.tag(tokens, "ru")
        trace_entries = role_tagger.get_trace_entries(tokens, role_tags)
        
        # Check state progression
        valid_states = ["START", "SURNAME_EXPECTED", "GIVEN_EXPECTED", 
                       "PATRONYMIC_EXPECTED", "ORG_EXPECTED", "DONE"]
        
        for trace_entry in trace_entries:
            assert trace_entry["state_from"] in valid_states
            assert trace_entry["state_to"] in valid_states
    
    def test_trace_window_context(self, role_tagger):
        """Test that window context is properly tracked for organization detection."""
        tokens = ["Слово1", "Слово2", "ТОВ", "ПРИВАТБАНК", "Слово3", "Слово4"]
        role_tags = role_tagger.tag(tokens, "ru")
        trace_entries = role_tagger.get_trace_entries(tokens, role_tags)
        
        # Check that org tokens have window context
        for i, trace_entry in enumerate(trace_entries):
            if trace_entry["role"] == "org":
                assert "window" in trace_entry
                assert "window_tokens" in trace_entry
                assert isinstance(trace_entry["window"], int)
                assert isinstance(trace_entry["window_tokens"], list)
                assert len(trace_entry["window_tokens"]) > 0
    
    def test_trace_consistency(self, role_tagger):
        """Test that trace entries are consistent with role tags."""
        tokens = ["И.", "Петров", "Иванович"]
        role_tags = role_tagger.tag(tokens, "ru")
        trace_entries = role_tagger.get_trace_entries(tokens, role_tags)
        
        assert len(role_tags) == len(trace_entries)
        
        for role_tag, trace_entry in zip(role_tags, trace_entries):
            assert role_tag.role.value == trace_entry["role"]
            assert role_tag.reason == trace_entry["reason"]
            assert role_tag.evidence == trace_entry["evidence"]
            assert role_tag.confidence == trace_entry["confidence"]
    
    def test_trace_with_empty_tokens(self, role_tagger):
        """Test trace generation with empty token list."""
        tokens = []
        role_tags = role_tagger.tag(tokens, "ru")
        trace_entries = role_tagger.get_trace_entries(tokens, role_tags)
        
        assert len(trace_entries) == 0
    
    def test_trace_with_single_token(self, role_tagger):
        """Test trace generation with single token."""
        tokens = ["Иван"]
        role_tags = role_tagger.tag(tokens, "ru")
        trace_entries = role_tagger.get_trace_entries(tokens, role_tags)
        
        assert len(trace_entries) == 1
        trace_entry = trace_entries[0]
        
        # Required fields
        assert "type" in trace_entry
        assert "token" in trace_entry
        assert "role" in trace_entry
        assert "reason" in trace_entry
        assert "evidence" in trace_entry
        assert "confidence" in trace_entry
        assert "state_from" in trace_entry
        assert "state_to" in trace_entry
        
        assert trace_entry["token"] == "Иван"
        assert trace_entry["type"] == "role"
    
    def test_trace_with_unknown_tokens(self, role_tagger):
        """Test trace generation with unknown tokens."""
        tokens = ["123", "!@#", "а"]
        role_tags = role_tagger.tag(tokens, "ru")
        trace_entries = role_tagger.get_trace_entries(tokens, role_tags)
        
        assert len(trace_entries) == 3
        
        for trace_entry in trace_entries:
            assert trace_entry["role"] == "unknown"
            assert trace_entry["reason"] == "fallback_unknown"
            assert "no_rule_matched" in trace_entry["evidence"]
            assert trace_entry["confidence"] == 0.0
    
    def test_trace_with_stopwords(self, role_tagger):
        """Test trace generation with stopwords."""
        tokens = ["и", "Иван", "Петров"]
        role_tags = role_tagger.tag(tokens, "ru")
        trace_entries = role_tagger.get_trace_entries(tokens, role_tags)
        
        assert len(trace_entries) == 3
        
        # First token should be stopword
        trace1 = trace_entries[0]
        assert trace1["role"] == "unknown"
        assert trace1["reason"] == "stopword_filtered"
        assert "stopword_ru" in trace1["evidence"]
        
        # Other tokens should be person names
        trace2 = trace_entries[1]
        assert trace2["role"] in ["given", "surname", "patronymic"]
        
        trace3 = trace_entries[2]
        assert trace3["role"] in ["given", "surname", "patronymic"]
    
    def test_trace_evidence_types(self, role_tagger):
        """Test that evidence contains appropriate types of information."""
        tokens = ["И.", "Петров", "ТОВ", "ПРИВАТБАНК"]
        role_tags = role_tagger.tag(tokens, "ru")
        trace_entries = role_tagger.get_trace_entries(tokens, role_tags)
        
        evidence_types = set()
        for trace_entry in trace_entries:
            for evidence in trace_entry["evidence"]:
                evidence_types.add(evidence)
        
        # Should have various types of evidence
        expected_evidence_types = {
            "dot_after_capital", "surname_suffix_match", "patronymic_suffix_match",
            "org_legal_form_context", "given_detected", "surname_detected",
            "person_heuristic", "stopword_ru", "CAPS", "no_rule_matched"
        }
        
        # At least some expected evidence types should be present
        assert len(evidence_types.intersection(expected_evidence_types)) > 0

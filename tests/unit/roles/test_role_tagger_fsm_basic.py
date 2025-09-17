#!/usr/bin/env python3
"""
Basic FSM tests for role tagger service.

Tests core FSM functionality and role assignment logic.
"""

import pytest
from unittest.mock import Mock, patch

from src.ai_service.layers.normalization.role_tagger_service import (
    RoleTaggerService, FSMState, TokenRole, RoleRules, Token
)
from src.ai_service.layers.normalization.lexicon_loader import Lexicons


class TestRoleTaggerFSMBasic:
    """Test basic FSM functionality."""
    
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
    
    def test_initial_detection(self, role_tagger):
        """Test detection of initials."""
        tokens = ["И.", "И.", "Петров"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 3
        assert role_tags[0].role == TokenRole.INITIAL
        assert role_tags[0].reason == "initial_detected"
        assert "dot_after_capital" in role_tags[0].evidence
        
        assert role_tags[1].role == TokenRole.INITIAL
        assert role_tags[1].reason == "initial_detected"
        
        assert role_tags[2].role == TokenRole.SURNAME
        assert role_tags[2].reason == "surname_suffix_detected"
    
    def test_surname_suffix_detection(self, role_tagger):
        """Test detection of surnames by suffix patterns."""
        tokens = ["Петров", "Иван", "Иванович"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 3
        assert role_tags[0].role == TokenRole.SURNAME
        assert role_tags[0].reason == "surname_suffix_detected"
        assert "surname_suffix_match" in role_tags[0].evidence
        
        assert role_tags[1].role == TokenRole.GIVEN
        assert role_tags[1].reason == "given_detected"
        
        assert role_tags[2].role == TokenRole.PATRONYMIC
        assert role_tags[2].reason == "patronymic_suffix_detected"
    
    def test_patronymic_suffix_detection(self, role_tagger):
        """Test detection of patronymics by suffix patterns."""
        tokens = ["Иван", "Петрович"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 2
        assert role_tags[0].role == TokenRole.GIVEN
        assert role_tags[0].reason == "given_detected"
        
        assert role_tags[1].role == TokenRole.PATRONYMIC
        assert role_tags[1].reason == "patronymic_suffix_detected"
        assert "patronymic_suffix_match" in role_tags[1].evidence
    
    def test_organization_context_detection(self, role_tagger):
        """Test detection of organization context."""
        tokens = ["ТОВ", "ПРИВАТБАНК", "Иван", "Петров"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 4
        assert role_tags[0].role == TokenRole.ORG
        assert role_tags[0].reason == "org_legal_form_context"
        assert "org_legal_form_context" in role_tags[0].evidence
        
        assert role_tags[1].role == TokenRole.ORG
        assert role_tags[1].reason == "org_legal_form_context"
        assert "CAPS" in role_tags[1].evidence
        
        # Person names in org context should be marked as org (correct FSM behavior)
        assert role_tags[2].role == TokenRole.ORG
        assert role_tags[2].reason == "org_legal_form_context"
        assert role_tags[3].role == TokenRole.ORG
        assert role_tags[3].reason == "org_legal_form_context"
    
    def test_stopword_filtering(self, role_tagger):
        """Test filtering of stopwords."""
        tokens = ["и", "Иван", "Петров"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 3
        assert role_tags[0].role == TokenRole.UNKNOWN
        assert role_tags[0].reason == "stopword_filtered"
        assert f"stopword_ru" in role_tags[0].evidence
        
        assert role_tags[1].role == TokenRole.GIVEN
        assert role_tags[2].role == TokenRole.SURNAME
    
    def test_fallback_unknown(self, role_tagger):
        """Test fallback to unknown role."""
        tokens = ["123", "!@#", "а"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 3
        for role_tag in role_tags:
            assert role_tag.role == TokenRole.UNKNOWN
            assert role_tag.reason == "fallback_unknown"
            assert "no_rule_matched" in role_tag.evidence
    
    def test_trace_generation(self, role_tagger):
        """Test trace entry generation."""
        tokens = ["И.", "Петров"]
        role_tags = role_tagger.tag(tokens, "ru")
        trace_entries = role_tagger.get_trace_entries(tokens, role_tags)
        
        assert len(trace_entries) == 2
        
        # Check first token trace
        trace1 = trace_entries[0]
        assert trace1["type"] == "role"
        assert trace1["token"] == "И."
        assert trace1["role"] == "initial"
        assert trace1["reason"] == "initial_detected"
        assert "dot_after_capital" in trace1["evidence"]
        assert "state_from" in trace1
        assert "state_to" in trace1
        
        # Check second token trace
        trace2 = trace_entries[1]
        assert trace2["type"] == "role"
        assert trace2["token"] == "Петров"
        assert trace2["role"] == "surname"
        assert trace2["reason"] == "surname_suffix_detected"
        assert "surname_suffix_match" in trace2["evidence"]
    
    def test_state_transitions(self, role_tagger):
        """Test FSM state transitions."""
        tokens = ["Иван", "Петров", "Иванович"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        # Check state progression
        assert role_tags[0].state_from == FSMState.START
        assert role_tags[0].state_to == FSMState.SURNAME_EXPECTED
        
        assert role_tags[1].state_from == FSMState.SURNAME_EXPECTED
        assert role_tags[1].state_to == FSMState.PATRONYMIC_EXPECTED
        
        assert role_tags[2].state_from == FSMState.PATRONYMIC_EXPECTED
        assert role_tags[2].state_to == FSMState.DONE
    
    def test_empty_tokens(self, role_tagger):
        """Test handling of empty token list."""
        role_tags = role_tagger.tag([], "ru")
        assert role_tags == []
    
    def test_single_token(self, role_tagger):
        """Test handling of single token."""
        tokens = ["Иван"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 1
        assert role_tags[0].role == TokenRole.GIVEN
        assert role_tags[0].reason == "given_detected"
    
    def test_confidence_scores(self, role_tagger):
        """Test confidence score assignment."""
        tokens = ["Иван", "Петров"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        # All rules should have confidence 1.0
        for role_tag in role_tags:
            assert role_tag.confidence == 1.0
        
        # Fallback should have confidence 0.0
        tokens_unknown = ["123"]
        role_tags_unknown = role_tagger.tag(tokens_unknown, "ru")
        assert role_tags_unknown[0].confidence == 0.0


class TestRoleTaggerFSMEdgeCases:
    """Test edge cases and complex scenarios."""
    
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
    
    def test_hyphenated_surname(self, role_tagger):
        """Test handling of hyphenated surnames."""
        tokens = ["Петрова-Сидорова", "Анна"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 2
        assert role_tags[0].role == TokenRole.SURNAME
        assert role_tags[0].reason == "surname_suffix_detected"
        assert "surname_suffix_match" in role_tags[0].evidence
        
        assert role_tags[1].role == TokenRole.GIVEN
        assert role_tags[1].reason == "given_detected"
    
    def test_mixed_case_organization(self, role_tagger):
        """Test handling of mixed case organization names."""
        tokens = ["ТОВ", "PrivatBank", "Иван", "Петров"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 4
        assert role_tags[0].role == TokenRole.ORG
        assert role_tags[0].reason == "org_legal_form_context"
        
        assert role_tags[1].role == TokenRole.ORG
        assert role_tags[1].reason == "org_legal_form_context"
        
        # Person names in org context should be marked as org
        assert role_tags[2].role == TokenRole.ORG
        assert role_tags[3].role == TokenRole.ORG
    
    def test_multiple_organizations(self, role_tagger):
        """Test handling of multiple organizations in text."""
        tokens = ["ТОВ", "БАНК1", "и", "ООО", "БАНК2"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 5
        assert role_tags[0].role == TokenRole.ORG
        assert role_tags[1].role == TokenRole.ORG
        assert role_tags[2].role == TokenRole.UNKNOWN  # stopword
        assert role_tags[3].role == TokenRole.ORG
        assert role_tags[4].role == TokenRole.ORG
    
    def test_quoted_organization_name(self, role_tagger):
        """Test handling of quoted organization names."""
        tokens = ["ТОВ", '"ПРИВАТБАНК"', "Иван", "Петров"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 4
        assert role_tags[0].role == TokenRole.ORG
        assert role_tags[1].role == TokenRole.ORG
        assert role_tags[1].reason == "org_legal_form_context"
        
        # Person names in org context should be marked as org
        assert role_tags[2].role == TokenRole.ORG
        assert role_tags[3].role == TokenRole.ORG
    
    def test_window_context_tracking(self, role_tagger):
        """Test window context tracking for organization detection."""
        tokens = ["Слово", "ТОВ", "ПРИВАТБАНК", "Слово", "Иван"]
        role_tags = role_tagger.tag(tokens, "ru")
        trace_entries = role_tagger.get_trace_entries(tokens, role_tags)
        
        # Check that window context is tracked
        for i, trace_entry in enumerate(trace_entries):
            if trace_entry["role"] == "org":
                assert "window" in trace_entry
                assert "window_tokens" in trace_entry
                assert len(trace_entry["window_tokens"]) > 0
    
    def test_ukrainian_patronymic_suffixes(self, role_tagger):
        """Test Ukrainian patronymic suffix detection."""
        tokens = ["Іван", "Петрович"]
        role_tags = role_tagger.tag(tokens, "uk")
        
        assert len(role_tags) == 2
        assert role_tags[0].role == TokenRole.GIVEN
        assert role_tags[1].role == TokenRole.PATRONYMIC
        assert role_tags[1].reason == "patronymic_suffix_detected"
        assert "suffix_ович" in role_tags[1].evidence
    
    def test_english_legal_forms(self, role_tagger):
        """Test English legal form detection."""
        tokens = ["LLC", "COMPANY", "John", "Doe"]
        role_tags = role_tagger.tag(tokens, "en")
        
        assert len(role_tags) == 4
        assert role_tags[0].role == TokenRole.ORG
        assert role_tags[0].reason == "org_legal_form_context"
        assert role_tags[1].role == TokenRole.ORG
        
        # Person names in org context should be marked as org
        assert role_tags[2].role == TokenRole.ORG
        assert role_tags[3].role == TokenRole.ORG

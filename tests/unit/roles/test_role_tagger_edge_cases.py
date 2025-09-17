#!/usr/bin/env python3
"""
Edge cases tests for role tagger FSM.

Tests complex scenarios, error handling, and boundary conditions.
"""

import pytest
from unittest.mock import Mock, patch

from src.ai_service.layers.normalization.role_tagger_service import (
    RoleTaggerService, FSMState, TokenRole, RoleRules, Token
)
from src.ai_service.layers.normalization.lexicon_loader import Lexicons


class TestRoleTaggerEdgeCases:
    """Test edge cases and complex scenarios."""
    
    @pytest.fixture
    def mock_lexicons(self):
        """Mock lexicons for testing."""
        lexicons = Mock(spec=Lexicons)
        lexicons.stopwords = {
            'ru': {'и', 'в', 'на', 'с', 'по', 'для', 'от', 'до', 'за', 'про'},
            'uk': {'і', 'в', 'на', 'з', 'по', 'для', 'від', 'до', 'за', 'про'},
            'en': {'and', 'in', 'on', 'with', 'by', 'for', 'from', 'to', 'at', 'about'}
        }
        lexicons.legal_forms = {
            'ооо', 'тов', 'пао', 'ао', 'ип', 'чп', 'фоп', 'пп',
            'llc', 'ltd', 'inc', 'corp', 'co', 'gmbh', 'srl', 'spa', 'bv', 'nv', 'oy', 'ab', 'as', 'sa', 'ag'
        }
        return lexicons
    
    @pytest.fixture
    def role_tagger(self, mock_lexicons):
        """Create role tagger service for testing."""
        rules = RoleRules()
        return RoleTaggerService(lexicons=mock_lexicons, rules=rules)
    
    def test_punctuation_only_tokens(self, role_tagger):
        """Test handling of punctuation-only tokens."""
        tokens = [".", ",", "!", "?", ";", ":"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        for role_tag in role_tags:
            assert role_tag.role == TokenRole.UNKNOWN
            assert role_tag.reason == "fallback_unknown"
    
    def test_numbers_and_symbols(self, role_tagger):
        """Test handling of numbers and symbols."""
        tokens = ["123", "45.67", "100%", "№1", "§2"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        for role_tag in role_tags:
            assert role_tag.role == TokenRole.UNKNOWN
            assert role_tag.reason == "fallback_unknown"
    
    def test_single_character_tokens(self, role_tagger):
        """Test handling of single character tokens."""
        tokens = ["а", "б", "в", "г", "д"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        for role_tag in role_tags:
            assert role_tag.role == TokenRole.UNKNOWN
            assert role_tag.reason == "fallback_unknown"
    
    def test_mixed_language_tokens(self, role_tagger):
        """Test handling of mixed language tokens."""
        tokens = ["John", "Петров", "Іван", "Smith"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 4
        assert role_tags[0].role == TokenRole.GIVEN
        assert role_tags[1].role == TokenRole.SURNAME
        assert role_tags[2].role == TokenRole.GIVEN
        assert role_tags[3].role == TokenRole.SURNAME
    
    def test_all_caps_person_names(self, role_tagger):
        """Test handling of all caps person names."""
        tokens = ["ИВАН", "ПЕТРОВ", "ИВАНОВИЧ"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        # All caps should still be detected as person names if they have surname suffixes
        assert len(role_tags) == 3
        assert role_tags[0].role == TokenRole.GIVEN
        assert role_tags[1].role == TokenRole.SURNAME
        assert role_tags[2].role == TokenRole.PATRONYMIC
    
    def test_very_long_tokens(self, role_tagger):
        """Test handling of very long tokens."""
        long_token = "А" * 100
        tokens = [long_token, "Петров"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 2
        assert role_tags[0].role == TokenRole.UNKNOWN  # Too long, no suffix match
        assert role_tags[1].role == TokenRole.SURNAME
    
    def test_unicode_edge_cases(self, role_tagger):
        """Test handling of Unicode edge cases."""
        tokens = ["Іван", "Їжак", "Євген", "Ґудзик", "Петров"]
        role_tags = role_tagger.tag(tokens, "uk")
        
        assert len(role_tags) == 5
        assert role_tags[0].role == TokenRole.GIVEN
        assert role_tags[1].role == TokenRole.GIVEN
        assert role_tags[2].role == TokenRole.GIVEN
        assert role_tags[3].role == TokenRole.GIVEN
        assert role_tags[4].role == TokenRole.SURNAME
    
    def test_whitespace_and_empty_tokens(self, role_tagger):
        """Test handling of whitespace and empty tokens."""
        tokens = ["", " ", "  ", "Иван", "Петров"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 5
        # Empty/whitespace tokens should be unknown
        for i in range(3):
            assert role_tags[i].role == TokenRole.UNKNOWN
            assert role_tags[i].reason == "fallback_unknown"
        
        assert role_tags[3].role == TokenRole.GIVEN
        assert role_tags[4].role == TokenRole.SURNAME
    
    def test_organization_with_person_context(self, role_tagger):
        """Test organization detection when person names are nearby."""
        tokens = ["Иван", "ТОВ", "ПРИВАТБАНК", "Петров", "Иванович"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 5
        assert role_tags[0].role == TokenRole.GIVEN
        assert role_tags[1].role == TokenRole.ORG
        assert role_tags[2].role == TokenRole.ORG
        assert role_tags[3].role == TokenRole.SURNAME
        assert role_tags[4].role == TokenRole.PATRONYMIC
    
    def test_multiple_legal_forms_in_context(self, role_tagger):
        """Test handling of multiple legal forms in context window."""
        tokens = ["ТОВ", "ООО", "ПРИВАТБАНК", "Иван", "Петров"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 5
        assert role_tags[0].role == TokenRole.ORG
        assert role_tags[1].role == TokenRole.ORG
        assert role_tags[2].role == TokenRole.ORG
        assert role_tags[3].role == TokenRole.GIVEN
        assert role_tags[4].role == TokenRole.SURNAME
    
    def test_stopwords_in_organization_context(self, role_tagger):
        """Test stopwords in organization context."""
        tokens = ["ТОВ", "и", "ПРИВАТБАНК", "Иван", "Петров"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 5
        assert role_tags[0].role == TokenRole.ORG
        assert role_tags[1].role == TokenRole.UNKNOWN  # stopword
        assert role_tags[2].role == TokenRole.ORG
        assert role_tags[3].role == TokenRole.GIVEN
        assert role_tags[4].role == TokenRole.SURNAME
    
    def test_conflicting_roles(self, role_tagger):
        """Test handling of conflicting role assignments."""
        # This test ensures that the first matching rule wins
        tokens = ["ТОВ", "Петров"]  # "Петров" could be surname or org name
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 2
        assert role_tags[0].role == TokenRole.ORG
        assert role_tags[1].role == TokenRole.ORG  # Should be org due to context
    
    def test_window_boundary_conditions(self, role_tagger):
        """Test organization detection at window boundaries."""
        # Test at the beginning
        tokens = ["ПРИВАТБАНК", "ТОВ", "Иван"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 3
        assert role_tags[0].role == TokenRole.ORG
        assert role_tags[1].role == TokenRole.ORG
        assert role_tags[2].role == TokenRole.GIVEN
        
        # Test at the end
        tokens = ["Иван", "ТОВ", "ПРИВАТБАНК"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 3
        assert role_tags[0].role == TokenRole.GIVEN
        assert role_tags[1].role == TokenRole.ORG
        assert role_tags[2].role == TokenRole.ORG
    
    def test_very_long_context_window(self, role_tagger):
        """Test with very long context that exceeds window size."""
        tokens = ["Слово1", "Слово2", "Слово3", "Слово4", "ТОВ", "ПРИВАТБАНК", "Слово5", "Слово6"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        # Only tokens within window should be affected
        assert len(role_tags) == 8
        assert role_tags[4].role == TokenRole.ORG
        assert role_tags[5].role == TokenRole.ORG
        # Other tokens should not be affected by org context
        for i in [0, 1, 2, 3, 6, 7]:
            assert role_tags[i].role == TokenRole.UNKNOWN
    
    def test_case_sensitivity(self, role_tagger):
        """Test case sensitivity in role detection."""
        tokens = ["иван", "петров", "ИВАН", "ПЕТРОВ"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 4
        # Only capitalized tokens should get person roles
        assert role_tags[0].role == TokenRole.UNKNOWN  # lowercase
        assert role_tags[1].role == TokenRole.UNKNOWN  # lowercase
        assert role_tags[2].role == TokenRole.GIVEN    # uppercase
        assert role_tags[3].role == TokenRole.SURNAME  # uppercase with suffix
    
    def test_special_characters_in_tokens(self, role_tagger):
        """Test handling of special characters in tokens."""
        tokens = ["О'Коннор", "Мак-Дональд", "ван-дер-Берг", "Петров"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 4
        # Tokens with special characters should still be detected if they have surname suffixes
        assert role_tags[0].role == TokenRole.UNKNOWN  # No suffix match
        assert role_tags[1].role == TokenRole.UNKNOWN  # No suffix match
        assert role_tags[2].role == TokenRole.UNKNOWN  # No suffix match
        assert role_tags[3].role == TokenRole.SURNAME  # Has suffix match
    
    def test_duplicate_tokens(self, role_tagger):
        """Test handling of duplicate tokens."""
        tokens = ["Иван", "Иван", "Петров", "Петров"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 4
        assert role_tags[0].role == TokenRole.GIVEN
        assert role_tags[1].role == TokenRole.GIVEN
        assert role_tags[2].role == TokenRole.SURNAME
        assert role_tags[3].role == TokenRole.SURNAME
    
    def test_very_short_tokens_with_suffixes(self, role_tagger):
        """Test very short tokens that might match suffixes."""
        tokens = ["ов", "ев", "ин", "ан"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        # Very short tokens should not match surname suffixes
        for role_tag in role_tags:
            assert role_tag.role == TokenRole.UNKNOWN
            assert role_tag.reason == "fallback_unknown"
    
    def test_organization_with_quotes_and_special_chars(self, role_tagger):
        """Test organization names with quotes and special characters."""
        tokens = ['ТОВ', '"ПРИВАТ-БАНК"', 'Иван', 'Петров']
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 4
        assert role_tags[0].role == TokenRole.ORG
        assert role_tags[1].role == TokenRole.ORG
        assert role_tags[2].role == TokenRole.GIVEN
        assert role_tags[3].role == TokenRole.SURNAME
    
    def test_mixed_script_tokens(self, role_tagger):
        """Test tokens with mixed scripts."""
        tokens = ["Иван", "Ivan", "Петров", "Petrov"]
        role_tags = role_tagger.tag(tokens, "ru")
        
        assert len(role_tags) == 4
        assert role_tags[0].role == TokenRole.GIVEN
        assert role_tags[1].role == TokenRole.GIVEN
        assert role_tags[2].role == TokenRole.SURNAME
        assert role_tags[3].role == TokenRole.SURNAME

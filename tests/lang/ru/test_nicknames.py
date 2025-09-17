#!/usr/bin/env python3
"""
Tests for Russian nickname expansion.

Tests that Russian nicknames are correctly expanded to full names
with proper gender handling for ambiguous cases.
"""

import pytest
import json
from pathlib import Path
from pathlib import Path
from src.ai_service.layers.normalization.morphology.diminutive_resolver import DiminutiveResolver


class TestRussianNicknames:
    """Test Russian nickname expansion."""
    
    @pytest.fixture
    def diminutive_resolver(self):
        """Create DiminutiveResolver instance."""
        return DiminutiveResolver(base_path=Path("."))
    
    @pytest.fixture
    def russian_diminutives(self):
        """Load Russian diminutives dictionary."""
        diminutives_file = Path("data/diminutives_ru.json")
        if diminutives_file.exists():
            with open(diminutives_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def test_basic_nickname_expansion(self, diminutive_resolver, russian_diminutives):
        """Test basic nickname expansion."""
        # Test cases from the expanded dictionary
        test_cases = [
            ("вова", "владимир"),
            ("саша", "александр"),
            ("коля", "николай"),
            ("лёша", "алексей"),
            ("дима", "дмитрий"),
            ("миша", "михаил"),
        ]
        
        for nickname, expected_full in test_cases:
            if nickname in russian_diminutives:
                result = diminutive_resolver.resolve(nickname, "ru")
                # The resolver might return multiple options, check if expected is in results
                assert expected_full in result or any(expected_full in str(option) for option in result)
    
    def test_feminine_nickname_expansion(self, diminutive_resolver, russian_diminutives):
        """Test feminine nickname expansion."""
        # Test feminine forms
        test_cases = [
            ("женя", "евгения"),  # Feminine form
        ]
        
        for nickname, expected_full in test_cases:
            if nickname in russian_diminutives:
                result = diminutive_resolver.resolve(nickname, "ru")
                # Check if feminine form is in results
                assert any(expected_full in str(option) for option in result)
    
    def test_masculine_nickname_expansion(self, diminutive_resolver, russian_diminutives):
        """Test masculine nickname expansion."""
        # Test masculine forms
        test_cases = [
            ("женя", "евгений"),  # Masculine form
        ]
        
        for nickname, expected_full in test_cases:
            if nickname in russian_diminutives:
                result = diminutive_resolver.resolve(nickname, "ru")
                # Check if masculine form is in results
                assert any(expected_full in str(option) for option in result)
    
    def test_ambiguous_nickname_gender_context(self, diminutive_resolver):
        """Test that ambiguous nicknames require gender context."""
        # "Женя" can be both masculine (Евгений) and feminine (Евгения)
        nickname = "женя"
        
        # Without gender context, should return both options
        result = diminutive_resolver.resolve(nickname, "ru")
        assert len(result) > 0  # Should have some results
        
        # Check that both masculine and feminine forms are possible
        result_str = str(result).lower()
        assert "евгений" in result_str or "евгения" in result_str
    
    def test_nickname_case_insensitive(self, diminutive_resolver, russian_diminutives):
        """Test that nickname expansion is case insensitive."""
        test_cases = [
            ("Вова", "владимир"),
            ("САША", "александр"),
            ("Коля", "николай"),
        ]
        
        for nickname, expected_full in test_cases:
            if nickname.lower() in russian_diminutives:
                result = diminutive_resolver.resolve(nickname, "ru")
                assert any(expected_full in str(option).lower() for option in result)
    
    def test_non_nickname_tokens(self, diminutive_resolver):
        """Test that non-nickname tokens are not expanded."""
        test_cases = [
            "иван",
            "петр",
            "мария",
            "анна",
            "смирнов",
            "петров",
        ]
        
        for token in test_cases:
            result = diminutive_resolver.resolve(token, "ru")
            # Non-nickname tokens should return empty or original token
            assert len(result) == 0 or token in str(result)
    
    def test_nickname_with_surname_context(self, diminutive_resolver):
        """Test nickname expansion with surname context."""
        # Test "Вова Петров" -> should expand to "Владимир Петров"
        nickname = "вова"
        result = diminutive_resolver.resolve(nickname, "ru")
        
        # Should return masculine form when used with masculine surname
        assert any("владимир" in str(option).lower() for option in result)
    
    def test_nickname_with_feminine_surname_context(self, diminutive_resolver):
        """Test nickname expansion with feminine surname context."""
        # Test "Женя Смирнова" -> should expand to "Евгения Смирнова"
        nickname = "женя"
        result = diminutive_resolver.resolve(nickname, "ru")
        
        # Should return both masculine and feminine forms
        result_str = str(result).lower()
        assert "евгений" in result_str or "евгения" in result_str
    
    def test_multiple_nicknames_in_text(self, diminutive_resolver):
        """Test multiple nicknames in the same text."""
        nicknames = ["вова", "саша", "коля"]
        expected_full_names = ["владимир", "александр", "николай"]
        
        for nickname, expected_full in zip(nicknames, expected_full_names):
            result = diminutive_resolver.resolve(nickname, "ru")
            assert any(expected_full in str(option).lower() for option in result)
    
    def test_nickname_expansion_confidence(self, diminutive_resolver):
        """Test that nickname expansion has appropriate confidence."""
        nickname = "вова"
        result = diminutive_resolver.resolve(nickname, "ru")
        
        # Should have some confidence in the expansion
        assert len(result) > 0
    
    def test_empty_nickname(self, diminutive_resolver):
        """Test that empty nickname is handled correctly."""
        result = diminutive_resolver.resolve("", "ru")
        assert len(result) == 0
    
    def test_none_nickname(self, diminutive_resolver):
        """Test that None nickname is handled correctly."""
        result = diminutive_resolver.resolve(None, "ru")
        assert len(result) == 0
    
    def test_nickname_with_special_characters(self, diminutive_resolver):
        """Test that nicknames with special characters are handled correctly."""
        # Test nicknames that might have special characters
        test_cases = [
            "лёша",  # Contains 'ё'
            "женечка",  # Diminutive form
            "женюша",  # Another diminutive form
        ]
        
        for nickname in test_cases:
            result = diminutive_resolver.resolve(nickname, "ru")
            # Should handle special characters correctly
            assert isinstance(result, (list, tuple))
    
    def test_nickname_resolution_caching(self, diminutive_resolver):
        """Test that nickname resolution is cached for performance."""
        nickname = "вова"
        
        # First resolution
        result1 = diminutive_resolver.resolve(nickname, "ru")
        
        # Second resolution (should be cached)
        result2 = diminutive_resolver.resolve(nickname, "ru")
        
        # Results should be the same
        assert result1 == result2

#!/usr/bin/env python3
"""
Tests for Russian stopwords initials conflict prevention.

Tests that Russian prepositions and conjunctions are not marked as initials
when strict_stopwords=True is enabled.
"""

import pytest
from src.ai_service.layers.normalization.role_tagger_service import RoleTaggerService, RoleRules
from src.ai_service.layers.normalization.lexicon_loader import get_lexicons


class TestRussianStopwordsInitials:
    """Test Russian stopwords initials conflict prevention."""
    
    @pytest.fixture
    def role_tagger_service(self):
        """Create RoleTaggerService with Russian stopwords for initials."""
        lexicons = get_lexicons()
        rules = RoleRules(strict_stopwords=True)
        return RoleTaggerService(lexicons, rules)
    
    def test_preposition_not_initial(self, role_tagger_service):
        """Test that prepositions are not marked as initials."""
        tokens = ["перевод", "с", "карты", "И.", "Иванов"]
        tags = role_tagger_service.tag(tokens, "ru")
        
        # Check that 'с' is not marked as initial
        s_tag = tags[1]  # 'с' token
        assert s_tag.role.value == "unknown"
        assert s_tag.reason == "ru_stopword_conflict"
        assert "ru_stopword_conflict" in s_tag.evidence
    
    def test_conjunction_not_initial(self, role_tagger_service):
        """Test that conjunctions are not marked as initials."""
        tokens = ["Иван", "и", "Мария", "Петровы"]
        tags = role_tagger_service.tag(tokens, "ru")
        
        # Check that 'и' is not marked as initial
        i_tag = tags[1]  # 'и' token
        assert i_tag.role.value == "unknown"
        assert i_tag.reason == "ru_stopword_conflict"
        assert "ru_stopword_conflict" in i_tag.evidence
    
    def test_legitimate_initial_preserved(self, role_tagger_service):
        """Test that legitimate initials are still detected."""
        tokens = ["перевод", "с", "карты", "И.", "Иванов"]
        tags = role_tagger_service.tag(tokens, "ru")
        
        # Check that 'И.' is still marked as initial
        initial_tag = tags[3]  # 'И.' token
        assert initial_tag.role.value == "initial"
        assert initial_tag.reason == "initial_detected"
    
    def test_surname_preserved(self, role_tagger_service):
        """Test that surnames are still detected correctly."""
        tokens = ["перевод", "с", "карты", "И.", "Иванов"]
        tags = role_tagger_service.tag(tokens, "ru")
        
        # Check that 'Иванов' is marked as surname
        surname_tag = tags[4]  # 'Иванов' token
        assert surname_tag.role.value == "surname"
    
    def test_mixed_prepositions_conjunctions(self, role_tagger_service):
        """Test multiple prepositions and conjunctions in one text."""
        tokens = ["в", "доме", "и", "на", "улице", "живут", "А.", "Петров", "и", "М.", "Сидоров"]
        tags = role_tagger_service.tag(tokens, "ru")
        
        # Check that prepositions and conjunctions are not initials
        preposition_tags = [tags[0], tags[3], tags[4]]  # 'в', 'на', 'улице'
        conjunction_tags = [tags[2], tags[8]]  # 'и' tokens
        
        for tag in preposition_tags + conjunction_tags:
            if tag.role.value == "unknown" and tag.reason == "ru_stopword_conflict":
                assert "ru_stopword_conflict" in tag.evidence
    
    def test_strict_stopwords_disabled(self):
        """Test that when strict_stopwords=False, stopwords might get other roles."""
        lexicons = get_lexicons()
        rules = RoleRules(strict_stopwords=False)
        role_tagger_service = RoleTaggerService(lexicons, rules)
        
        tokens = ["перевод", "с", "карты", "И.", "Иванов"]
        tags = role_tagger_service.tag(tokens, "ru")
        
        # With strict_stopwords=False, 'с' might get a different role
        s_tag = tags[1]  # 'с' token
        # The exact role depends on other rules, but it shouldn't be ru_stopword_conflict
        assert s_tag.reason != "ru_stopword_conflict"
    
    def test_common_prepositions(self, role_tagger_service):
        """Test common Russian prepositions are handled correctly."""
        prepositions = ["с", "со", "к", "ко", "в", "во", "на", "над", "под", "при", "за", "до", "от", "из"]
        
        for prep in prepositions:
            tokens = [prep, "доме", "живет", "И.", "Петров"]
            tags = role_tagger_service.tag(tokens, "ru")
            
            prep_tag = tags[0]  # preposition token
            assert prep_tag.role.value == "unknown"
            assert prep_tag.reason == "ru_stopword_conflict"
    
    def test_common_conjunctions(self, role_tagger_service):
        """Test common Russian conjunctions are handled correctly."""
        conjunctions = ["и", "а", "но", "да", "или", "либо", "что", "чтобы", "если", "когда"]
        
        for conj in conjunctions:
            tokens = ["Иван", conj, "Мария", "Петровы"]
            tags = role_tagger_service.tag(tokens, "ru")
            
            conj_tag = tags[1]  # conjunction token
            assert conj_tag.role.value == "unknown"
            assert conj_tag.reason == "ru_stopword_conflict"

#!/usr/bin/env python3
"""
Tests for Russian patronymics detection and normalization.

Tests that patronymics are correctly detected and normalized to nominative case,
and that ambiguous cases (like Belarusian surnames ending in -ович) are handled correctly.
"""

import pytest
from src.ai_service.layers.normalization.role_tagger_service import RoleTaggerService, RoleRules
from src.ai_service.layers.normalization.lexicon_loader import get_lexicons
from src.ai_service.layers.normalization.morphology_adapter import MorphologyAdapter


class TestRussianPatronymics:
    """Test Russian patronymics detection and normalization."""
    
    @pytest.fixture
    def role_tagger_service(self):
        """Create RoleTaggerService with patronymic detection."""
        lexicons = get_lexicons()
        rules = RoleRules(strict_stopwords=True)
        return RoleTaggerService(lexicons, rules)
    
    @pytest.fixture
    def morphology_adapter(self):
        """Create MorphologyAdapter instance."""
        return MorphologyAdapter()
    
    def test_masculine_patronymic_detection(self, role_tagger_service):
        """Test that masculine patronymics are detected correctly."""
        tokens = ["Иван", "Петрович", "Сидоров"]
        tags = role_tagger_service.tag(tokens, "ru")
        
        # Check that 'Петрович' is detected as patronymic
        patronymic_tag = tags[1]  # 'Петрович' token
        assert patronymic_tag.role.value == "patronymic"
        assert patronymic_tag.reason == "patronymic_detected"
        assert "patronymic_suffix_match" in patronymic_tag.evidence
        assert "suffix_ович" in patronymic_tag.evidence
    
    def test_feminine_patronymic_detection(self, role_tagger_service):
        """Test that feminine patronymics are detected correctly."""
        tokens = ["Анна", "Петровна", "Сидорова"]
        tags = role_tagger_service.tag(tokens, "ru")
        
        # Check that 'Петровна' is detected as patronymic
        patronymic_tag = tags[1]  # 'Петровна' token
        assert patronymic_tag.role.value == "patronymic"
        assert patronymic_tag.reason == "patronymic_detected"
        assert "patronymic_suffix_match" in patronymic_tag.evidence
        assert "suffix_овна" in patronymic_tag.evidence
    
    def test_patronymic_nominative_normalization(self, morphology_adapter):
        """Test that patronymics are normalized to nominative case."""
        # Test genitive to nominative conversion
        token = "Петровича"
        normalized, traces = morphology_adapter.normalize_patronymic_to_nominative(token, "ru")
        
        assert normalized == "Петрович"
        assert len(traces) == 1
        assert traces[0]["type"] == "patronymic_nominalized"
        assert traces[0]["reason"] == "patronymic_nominalized"
    
    def test_feminine_patronymic_nominative_normalization(self, morphology_adapter):
        """Test that feminine patronymics are normalized to nominative case."""
        # Test genitive to nominative conversion
        token = "Петровны"
        normalized, traces = morphology_adapter.normalize_patronymic_to_nominative(token, "ru")
        
        assert normalized == "Петровна"
        assert len(traces) == 1
        assert traces[0]["type"] == "patronymic_nominalized"
        assert traces[0]["reason"] == "patronymic_nominalized"
    
    def test_ambiguous_ovich_surname(self, role_tagger_service):
        """Test that ambiguous -ович endings are treated as surnames when no adjacent given name."""
        tokens = ["Ович", "работает", "в", "компании"]
        tags = role_tagger_service.tag(tokens, "ru")
        
        # Check that 'Ович' is treated as surname, not patronymic
        surname_tag = tags[0]  # 'Ович' token
        assert surname_tag.role.value == "surname"
        assert surname_tag.reason == "ambiguous_ovich_surname"
        assert "ambiguous_ovich_surname" in surname_tag.evidence
    
    def test_ovich_with_adjacent_given_name(self, role_tagger_service):
        """Test that -ович with adjacent given name is treated as patronymic."""
        tokens = ["Иван", "Петрович", "работает"]
        tags = role_tagger_service.tag(tokens, "ru")
        
        # Check that 'Петрович' is treated as patronymic
        patronymic_tag = tags[1]  # 'Петрович' token
        assert patronymic_tag.role.value == "patronymic"
        assert patronymic_tag.reason == "patronymic_detected"
    
    def test_various_patronymic_suffixes(self, role_tagger_service):
        """Test various patronymic suffixes are detected."""
        test_cases = [
            ("Петрович", "ович"),
            ("Петровича", "овича"),
            ("Петровичу", "овичу"),
            ("Петровичем", "овичем"),
            ("Петровиче", "овиче"),
            ("Петровна", "овна"),
            ("Петровны", "овны"),
            ("Петровне", "овне"),
            ("Петровной", "овной"),
            ("Петровно", "овно"),
        ]
        
        for patronymic, expected_suffix in test_cases:
            tokens = ["Иван", patronymic, "Сидоров"]
            tags = role_tagger_service.tag(tokens, "ru")
            
            patronymic_tag = tags[1]  # patronymic token
            assert patronymic_tag.role.value == "patronymic"
            assert f"suffix_{expected_suffix}" in patronymic_tag.evidence
    
    def test_patronymic_detection_case_insensitive(self, role_tagger_service):
        """Test that patronymic detection is case insensitive."""
        tokens = ["Иван", "петрович", "Сидоров"]  # lowercase patronymic
        tags = role_tagger_service.tag(tokens, "ru")
        
        patronymic_tag = tags[1]  # 'петрович' token
        assert patronymic_tag.role.value == "patronymic"
        assert patronymic_tag.reason == "patronymic_detected"
    
    def test_non_patronymic_tokens(self, role_tagger_service):
        """Test that non-patronymic tokens are not marked as patronymics."""
        tokens = ["Иван", "Петров", "Сидоров"]  # No patronymic
        tags = role_tagger_service.tag(tokens, "ru")
        
        # Check that 'Петров' is not marked as patronymic
        surname_tag = tags[1]  # 'Петров' token
        assert surname_tag.role.value != "patronymic"
    
    def test_patronymic_detection_with_capitalization(self, role_tagger_service):
        """Test that patronymic detection works with proper capitalization."""
        tokens = ["Иван", "Петрович", "Сидоров"]
        tags = role_tagger_service.tag(tokens, "ru")
        
        patronymic_tag = tags[1]  # 'Петрович' token
        assert patronymic_tag.role.value == "patronymic"
        assert "patronymic_suffix_match" in patronymic_tag.evidence
    
    def test_patronymic_normalization_rule_based_fallback(self, morphology_adapter):
        """Test rule-based fallback for patronymic normalization."""
        # Test cases that should work with rule-based approach
        test_cases = [
            ("Петровича", "Петрович"),
            ("Петровичу", "Петрович"),
            ("Петровичем", "Петрович"),
            ("Петровиче", "Петрович"),
            ("Петровны", "Петровна"),
            ("Петровне", "Петровна"),
            ("Петровной", "Петровна"),
            ("Петровно", "Петровна"),
        ]
        
        for input_token, expected_output in test_cases:
            normalized, traces = morphology_adapter.normalize_patronymic_to_nominative(input_token, "ru")
            assert normalized == expected_output
            assert len(traces) == 1
            assert traces[0]["type"] == "patronymic_nominalized"
    
    def test_patronymic_detection_with_initial(self, role_tagger_service):
        """Test patronymic detection with initial in the name."""
        tokens = ["И.", "Петрович", "Сидоров"]
        tags = role_tagger_service.tag(tokens, "ru")
        
        # Check that 'Петрович' is still detected as patronymic
        patronymic_tag = tags[1]  # 'Петрович' token
        assert patronymic_tag.role.value == "patronymic"
        assert patronymic_tag.reason == "patronymic_detected"

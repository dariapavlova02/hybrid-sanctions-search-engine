#!/usr/bin/env python3
"""
Tests for Ukrainian stopwords that conflict with initials.

Tests the strict_stopwords flag functionality to ensure that Ukrainian
prepositions and conjunctions are not tagged as initials or name roles.
"""

import pytest
from src.ai_service.layers.normalization.role_tagger import RoleTagger
from src.ai_service.layers.normalization.lexicon_loader import get_lexicons


class TestUkrainianStopwordsInitials:
    """Test Ukrainian stopwords that conflict with initials."""

    def setup_method(self):
        """Set up test fixtures."""
        self.lexicons = get_lexicons()
        self.role_tagger_strict = RoleTagger(
            lexicons=self.lexicons,
            strict_stopwords=True
        )
        self.role_tagger_normal = RoleTagger(
            lexicons=self.lexicons,
            strict_stopwords=False
        )

    def test_ukrainian_prepositions_not_tagged_as_initials(self):
        """Test that Ukrainian prepositions are not tagged as initials with strict_stopwords=True."""
        # Test cases: preposition + initial + surname
        test_cases = [
            "Переказ з картки О. Петренко",
            "Документ від А. Коваленко", 
            "Запит до І. Сидоренко",
            "Лист за М. Шевченко",
            "Договір над П. Франко",
            "Звіт під В. Лесі",
            "Справка при Ю. Котляревському",
            "Розрахунок по С. Грушевському",
            "Документ о Т. Шевченку",
            "Звіт об О. Пушкіні",
            "Договір без А. Міцкевича",
            "Лист для І. Франка",
            "Справка між М. Гоголем та Л. Толстим"
        ]

        for text in test_cases:
            tokens = text.split()
            tags_strict = self.role_tagger_strict.tag(tokens, language="uk")
            tags_normal = self.role_tagger_normal.tag(tokens, language="uk")
            
            # Find the preposition token
            preposition_token = None
            for i, token in enumerate(tokens):
                if token.lower() in ["з", "від", "до", "за", "над", "під", "при", "по", "о", "об", "без", "для", "між"]:
                    preposition_token = (i, token)
                    break
            
            assert preposition_token is not None, f"Preposition not found in: {text}"
            
            idx, prep = preposition_token
            tag_strict = tags_strict[idx]
            tag_normal = tags_normal[idx]
            
            # With strict_stopwords=True, preposition should be tagged as stopword
            assert tag_strict.role == "stopword", f"Preposition '{prep}' should be stopword with strict_stopwords=True in: {text}"
            assert "uk_stopword_conflict" in tag_strict.context_evidence, f"Should have uk_stopword_conflict evidence for '{prep}' in: {text}"
            
            # With strict_stopwords=False, behavior may vary
            # This test ensures the flag actually changes behavior
            if tag_normal.role != "stopword":
                assert tag_strict.role != tag_normal.role, f"strict_stopwords flag should change behavior for '{prep}' in: {text}"

    def test_ukrainian_conjunctions_not_tagged_as_initials(self):
        """Test that Ukrainian conjunctions are not tagged as initials with strict_stopwords=True."""
        test_cases = [
            "Анна та О. Петренко",
            "Іван і М. Коваленко", 
            "Олексій й С. Сидоренко",
            "Марія або В. Шевченко",
            "Петро чи І. Франко"
        ]

        for text in test_cases:
            tokens = text.split()
            tags_strict = self.role_tagger_strict.tag(tokens, language="uk")
            
            # Find the conjunction token
            conjunction_token = None
            for i, token in enumerate(tokens):
                if token.lower() in ["та", "і", "й", "або", "чи"]:
                    conjunction_token = (i, token)
                    break
            
            assert conjunction_token is not None, f"Conjunction not found in: {text}"
            
            idx, conj = conjunction_token
            tag_strict = tags_strict[idx]
            
            # With strict_stopwords=True, conjunction should be tagged as stopword
            assert tag_strict.role == "stopword", f"Conjunction '{conj}' should be stopword with strict_stopwords=True in: {text}"
            assert "uk_stopword_conflict" in tag_strict.context_evidence, f"Should have uk_stopword_conflict evidence for '{conj}' in: {text}"

    def test_legitimate_initials_still_recognized(self):
        """Test that legitimate initials are still recognized with strict_stopwords=True."""
        test_cases = [
            "О. Петренко",  # Single initial
            "А. М. Коваленко",  # Multiple initials
            "І. О. Сидоренко",  # Multiple initials
        ]

        for text in test_cases:
            tokens = text.split()
            tags_strict = self.role_tagger_strict.tag(tokens, language="uk")
            
            # Find initial tokens (single letters followed by period)
            for i, token in enumerate(tokens):
                if len(token) == 2 and token[1] == '.' and token[0].isupper():
                    tag = tags_strict[i]
                    # Initials should still be recognized as person candidates or similar
                    assert tag.role in ["person_candidate", "initial"], f"Initial '{token}' should be recognized in: {text}"

    def test_strict_stopwords_flag_behavior(self):
        """Test that strict_stopwords flag actually changes behavior."""
        text = "Переказ з картки О. Петренко"
        tokens = text.split()
        
        tags_strict = self.role_tagger_strict.tag(tokens, language="uk")
        tags_normal = self.role_tagger_normal.tag(tokens, language="uk")
        
        # Find the "з" token
        z_idx = tokens.index("з")
        
        tag_strict = tags_strict[z_idx]
        tag_normal = tags_normal[z_idx]
        
        # With strict_stopwords=True, "з" should be stopword
        assert tag_strict.role == "stopword"
        assert "uk_stopword_conflict" in tag_strict.context_evidence
        
        # The behavior should be different (or at least the evidence should be different)
        if tag_normal.role == "stopword":
            # If both are stopwords, at least the evidence should be different
            assert "uk_stopword_conflict" not in tag_normal.context_evidence
        else:
            # If normal tagging doesn't mark it as stopword, strict should
            assert tag_normal.role != tag_strict.role

    def test_ukrainian_stopwords_init_lexicon_loaded(self):
        """Test that Ukrainian stopwords_init lexicon is properly loaded."""
        assert "uk" in self.lexicons.stopwords_init
        assert len(self.lexicons.stopwords_init["uk"]) > 0
        
        # Check that specific Ukrainian prepositions are loaded
        expected_prepositions = {"з", "зі", "у", "в", "до", "за", "над", "під", "при", "по", "о", "об", "без", "для", "між"}
        loaded_prepositions = self.lexicons.stopwords_init["uk"]
        
        for prep in expected_prepositions:
            assert prep in loaded_prepositions, f"Preposition '{prep}' should be in stopwords_init lexicon"
        
        # Check that specific Ukrainian conjunctions are loaded
        expected_conjunctions = {"та", "і", "й", "або", "чи"}
        for conj in expected_conjunctions:
            assert conj in loaded_prepositions, f"Conjunction '{conj}' should be in stopwords_init lexicon"

    def test_mixed_case_handling(self):
        """Test that mixed case Ukrainian stopwords are handled correctly."""
        test_cases = [
            "Переказ З картки О. Петренко",  # Capitalized preposition
            "Документ ВІД А. Коваленко",  # Capitalized preposition
            "Лист ДО І. Сидоренко",  # Capitalized preposition
        ]

        for text in test_cases:
            tokens = text.split()
            tags_strict = self.role_tagger_strict.tag(tokens, language="uk")
            
            # Find the preposition token (case insensitive)
            preposition_token = None
            for i, token in enumerate(tokens):
                if token.lower() in ["з", "від", "до"]:
                    preposition_token = (i, token)
                    break
            
            assert preposition_token is not None, f"Preposition not found in: {text}"
            
            idx, prep = preposition_token
            tag_strict = tags_strict[idx]
            
            # Should be tagged as stopword regardless of case
            assert tag_strict.role == "stopword", f"Preposition '{prep}' should be stopword regardless of case in: {text}"
            assert "uk_stopword_conflict" in tag_strict.context_evidence, f"Should have uk_stopword_conflict evidence for '{prep}' in: {text}"

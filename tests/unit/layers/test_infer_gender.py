#!/usr/bin/env python3
"""
Unit tests for the infer_gender function in NormalizationService.

This module tests the gender inference logic based on various token patterns
and morphological metadata.
"""

import pytest
from typing import Any, Dict, List, Tuple

from src.ai_service.layers.normalization.normalization_service import NormalizationService


class TestInferGender:
    """Test cases for the infer_gender function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = NormalizationService()

    def test_patronymic_male_clear(self):
        """Test male patronymic endings give +3 score."""
        elems = [
            ("Петрович", "patronymic", {}),
            ("Сергеевич", "patronymic", {}),
            ("Андреевич", "patronymic", {}),
        ]
        
        gender, score_f, score_m = self.service.infer_gender(elems)
        
        assert gender == "masc"
        assert score_m >= 3
        assert score_f == 0

    def test_patronymic_female_clear(self):
        """Test female patronymic endings give +3 score."""
        elems = [
            ("Петрівна", "patronymic", {}),
            ("Сергіївна", "patronymic", {}),
            ("Андріївна", "patronymic", {}),
        ]
        
        gender, score_f, score_m = self.service.infer_gender(elems)
        
        assert gender == "femn"
        assert score_f >= 3
        assert score_m == 0

    def test_given_name_male_clear(self):
        """Test male given names give +3 score."""
        elems = [
            ("Владимир", "given", {}),
            ("Александр", "given", {}),
            ("Сергей", "given", {}),
        ]
        
        gender, score_f, score_m = self.service.infer_gender(elems)
        
        assert gender == "masc"
        assert score_m >= 3
        assert score_f == 0

    def test_given_name_female_clear(self):
        """Test female given names give +3 score."""
        elems = [
            ("Анна", "given", {}),
            ("Елена", "given", {}),
            ("Мария", "given", {}),
        ]
        
        gender, score_f, score_m = self.service.infer_gender(elems)
        
        assert gender == "femn"
        assert score_f >= 3
        assert score_m == 0

    def test_surname_male_ending(self):
        """Test male surname endings give +2 score."""
        elems = [
            ("Петров", "surname", {}),
            ("Сергеев", "surname", {}),
            ("Андреев", "surname", {}),
        ]
        
        gender, score_f, score_m = self.service.infer_gender(elems)
        
        assert gender == "masc"
        assert score_m >= 2
        assert score_f == 0

    def test_surname_female_ending(self):
        """Test female surname endings give +2 score."""
        elems = [
            ("Петрова", "surname", {}),
            ("Сергеева", "surname", {}),
            ("Андреева", "surname", {}),
        ]
        
        gender, score_f, score_m = self.service.infer_gender(elems)
        
        assert gender == "femn"  # 6 vs 0, difference = 6 >= 3
        assert score_f == 6  # 2+2+2
        assert score_m == 0

    def test_context_markers_female(self):
        """Test female context markers give +1 score."""
        elems = [
            ("пані", "unknown", {}),
            ("г-жа", "unknown", {}),
            ("mrs", "unknown", {}),
        ]
        
        gender, score_f, score_m = self.service.infer_gender(elems)
        
        assert gender == "femn"  # 3 vs 0, difference = 3 >= 3
        assert score_f == 3  # 1+1+1
        assert score_m == 0

    def test_context_markers_male(self):
        """Test male context markers give +1 score."""
        elems = [
            ("пан", "unknown", {}),
            ("г-н", "unknown", {}),
            ("mr", "unknown", {}),
        ]
        
        gender, score_f, score_m = self.service.infer_gender(elems)
        
        assert gender == "masc"  # 0 vs 3, difference = 3 >= 3
        assert score_f == 0
        assert score_m == 3  # 1+1+1

    def test_combined_indicators_strong_female(self):
        """Test combined indicators that clearly indicate female gender."""
        elems = [
            ("Анна", "given", {}),  # +3 female
            ("Петрівна", "patronymic", {}),  # +3 female
            ("Петрова", "surname", {}),  # +2 female
            ("пані", "unknown", {}),  # +1 female
        ]
        
        gender, score_f, score_m = self.service.infer_gender(elems)
        
        assert gender == "femn"
        assert score_f == 9  # 3+3+2+1
        assert score_m == 0

    def test_combined_indicators_strong_male(self):
        """Test combined indicators that clearly indicate male gender."""
        elems = [
            ("Владимир", "given", {}),  # +3 male
            ("Петрович", "patronymic", {}),  # +3 male
            ("Петров", "surname", {}),  # +2 male
            ("пан", "unknown", {}),  # +1 male
        ]
        
        gender, score_f, score_m = self.service.infer_gender(elems)
        
        assert gender == "masc"
        assert score_f == 0
        assert score_m == 9  # 3+3+2+1

    def test_uncertain_gender(self):
        """Test case where gender cannot be determined (score difference < 3)."""
        elems = [
            ("Петров", "surname", {}),  # +2 male
            ("пані", "unknown", {}),  # +1 female
        ]
        
        gender, score_f, score_m = self.service.infer_gender(elems)
        
        assert gender is None  # difference = 1 < 3
        assert score_f == 1
        assert score_m == 2

    def test_empty_input(self):
        """Test empty input returns None gender."""
        elems = []
        
        gender, score_f, score_m = self.service.infer_gender(elems)
        
        assert gender is None
        assert score_f == 0
        assert score_m == 0

    def test_mixed_indicators_female_wins(self):
        """Test case where female indicators outweigh male ones."""
        elems = [
            ("Анна", "given", {}),  # +3 female
            ("Петрівна", "patronymic", {}),  # +3 female
            ("Петров", "surname", {}),  # +2 male
            ("пан", "unknown", {}),  # +1 male
        ]
        
        gender, score_f, score_m = self.service.infer_gender(elems)
        
        assert gender == "femn"  # 6 > 3, difference = 3 >= 3
        assert score_f == 6  # 3+3
        assert score_m == 3  # 2+1

    def test_mixed_indicators_male_wins(self):
        """Test case where male indicators outweigh female ones."""
        elems = [
            ("Владимир", "given", {}),  # +3 male
            ("Петрович", "patronymic", {}),  # +3 male
            ("Петрова", "surname", {}),  # +2 female
            ("пані", "unknown", {}),  # +1 female
        ]
        
        gender, score_f, score_m = self.service.infer_gender(elems)
        
        assert gender == "masc"  # 6 > 3, difference = 3 >= 3
        assert score_f == 3  # 2+1
        assert score_m == 6  # 3+3

    def test_initial_tokens_ignored(self):
        """Test that initial tokens don't contribute to gender scoring."""
        elems = [
            ("А.", "initial", {}),
            ("П.", "initial", {}),
            ("С.", "initial", {}),
        ]
        
        gender, score_f, score_m = self.service.infer_gender(elems)
        
        assert gender is None
        assert score_f == 0
        assert score_m == 0

    def test_ukrainian_surname_endings(self):
        """Test Ukrainian-specific surname endings."""
        elems = [
            ("Петренко", "surname", {}),  # No gender indication
            ("Коваленко", "surname", {}),  # No gender indication
        ]
        
        gender, score_f, score_m = self.service.infer_gender(elems)
        
        assert gender is None
        assert score_f == 0
        assert score_m == 0

    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive."""
        elems = [
            ("АННА", "given", {}),  # Should match female name
            ("ПЕТРОВИЧ", "patronymic", {}),  # Should match male patronymic
        ]
        
        gender, score_f, score_m = self.service.infer_gender(elems)
        
        assert gender is None  # Both have same score, difference = 0 < 3
        assert score_f == 3  # ANNA
        assert score_m == 3  # ПЕТРОВИЧ

    def test_multiple_patronymics(self):
        """Test multiple patronymics are handled correctly."""
        elems = [
            ("Петрович", "patronymic", {}),  # +3 male
            ("Сергеевич", "patronymic", {}),  # +3 male
        ]
        
        gender, score_f, score_m = self.service.infer_gender(elems)
        
        assert gender == "masc"
        assert score_f == 0
        assert score_m == 6  # 3+3

    def test_multiple_given_names(self):
        """Test multiple given names are handled correctly."""
        elems = [
            ("Анна", "given", {}),  # +3 female
            ("Мария", "given", {}),  # +3 female
        ]
        
        gender, score_f, score_m = self.service.infer_gender(elems)
        
        assert gender == "femn"  # 6 > 0, difference = 6 >= 3
        assert score_f == 6  # 3+3
        assert score_m == 0

    def test_edge_case_exactly_3_difference(self):
        """Test edge case where score difference is exactly 3."""
        elems = [
            ("Анна", "given", {}),  # +3 female
            ("Петров", "surname", {}),  # +2 male
        ]
        
        gender, score_f, score_m = self.service.infer_gender(elems)
        
        assert gender is None  # 3 vs 2, difference = 1 < 3
        assert score_f == 3
        assert score_m == 2

    def test_unknown_role_tokens(self):
        """Test that tokens with unknown role don't contribute to gender scoring."""
        elems = [
            ("неизвестное", "unknown", {}),
            ("слово", "unknown", {}),
        ]
        
        gender, score_f, score_m = self.service.infer_gender(elems)
        
        assert gender is None
        assert score_f == 0
        assert score_m == 0

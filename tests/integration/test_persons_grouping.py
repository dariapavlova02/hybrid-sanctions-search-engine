#!/usr/bin/env python3
"""
Integration tests for person grouping functionality.

This module tests the full integration of person grouping with gender inference
and surname adjustment in the normalization pipeline.
"""

import pytest
from typing import List, Dict, Any

from ai_service.layers.normalization.normalization_service import NormalizationService


class TestPersonsGroupingIntegration:
    """Integration tests for person grouping functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = NormalizationService()

    def test_single_person_normalization(self):
        """Test normalization of a single person."""
        result = self.service.normalize_sync("Иван Петров")
        
        assert result.success
        assert result.normalized == "Иван Петров"
        assert len(result.persons) == 1
        
        person = result.persons[0]
        assert person["tokens"] == ["Иван", "Петров"]
        assert person["roles"] == ["given", "surname"]
        assert person["gender"] == "masc"  # Should be determined from name

    def test_multiple_persons_with_conjunction(self):
        """Test normalization of multiple persons with conjunction."""
        result = self.service.normalize_sync("Иван Петров и Анна Сергеева")
        
        assert result.success
        assert len(result.persons) == 2
        
        # First person
        person1 = result.persons[0]
        assert person1["tokens"] == ["Иван", "Петров"]
        assert person1["roles"] == ["given", "surname"]
        assert person1["gender"] == "masc"
        
        # Second person
        person2 = result.persons[1]
        assert person2["tokens"] == ["Анна", "Сергеева"]
        assert person2["roles"] == ["given", "surname"]
        assert person2["gender"] == "femn"  # Correctly inferred from given name "Анна"

    def test_persons_with_patronymics(self):
        """Test normalization of persons with patronymics."""
        result = self.service.normalize_sync("Александр Петрович Петров и Анна Сергеевна Сергеева")
        
        assert result.success
        assert len(result.persons) == 2
        
        # First person
        person1 = result.persons[0]
        assert person1["tokens"] == ["Александр", "Петрович", "Петров"]
        assert person1["roles"] == ["given", "patronymic", "surname"]
        assert person1["gender"] == "masc"
        
        # Second person
        person2 = result.persons[1]
        assert person2["tokens"] == ["Анна", "Сергеевна", "Сергеева"]
        assert person2["roles"] == ["given", "patronymic", "surname"]
        assert person2["gender"] == "femn"

    def test_persons_with_initials(self):
        """Test normalization of persons with initials."""
        result = self.service.normalize_sync("И. Петров и А. Сергеева")
        
        assert result.success
        assert len(result.persons) == 2
        
        # First person
        person1 = result.persons[0]
        assert person1["tokens"] == ["И.", "Петров"]
        assert person1["roles"] == ["initial", "surname"]
        
        # Second person
        person2 = result.persons[1]
        assert person2["tokens"] == ["А.", "Сергеева"]
        assert person2["roles"] == ["initial", "surname"]

    def test_persons_with_comma_separator(self):
        """Test normalization of persons separated by comma."""
        result = self.service.normalize_sync("Иван Петров, Анна Сергеева")
        
        assert result.success
        assert len(result.persons) == 2
        
        # First person
        person1 = result.persons[0]
        assert person1["tokens"] == ["Иван", "Петров"]
        assert person1["roles"] == ["given", "surname"]
        
        # Second person
        person2 = result.persons[1]
        assert person2["tokens"] == ["Анна", "Сергеева"]
        assert person2["roles"] == ["given", "surname"]

    def test_persons_with_mixed_separators(self):
        """Test normalization of persons with mixed separators."""
        result = self.service.normalize_sync("Иван Петров, Анна Сергеева и Александр Козлов")
        
        assert result.success
        assert len(result.persons) == 3
        
        # First person
        person1 = result.persons[0]
        assert person1["tokens"] == ["Иван", "Петров"]
        assert person1["roles"] == ["given", "surname"]
        
        # Second person
        person2 = result.persons[1]
        assert person2["tokens"] == ["Анна", "Сергеева"]
        assert person2["roles"] == ["given", "surname"]
        
        # Third person
        person3 = result.persons[2]
        assert person3["tokens"] == ["Александр", "Козлов"]
        assert person3["roles"] == ["given", "surname"]

    def test_persons_with_non_person_tokens(self):
        """Test normalization with non-person tokens."""
        result = self.service.normalize_sync("Иван Петров работает в компании и Анна Сергеева")
        
        assert result.success
        assert len(result.persons) == 2
        
        # First person
        person1 = result.persons[0]
        assert person1["tokens"] == ["Иван", "Петров"]
        assert person1["roles"] == ["given", "surname"]
        
        # Second person
        person2 = result.persons[1]
        assert person2["tokens"] == ["Анна", "Сергеева"]
        assert person2["roles"] == ["given", "surname"]

    def test_persons_data_structure(self):
        """Test the structure of persons data in result."""
        result = self.service.normalize_sync("Иван Петров")
        
        assert result.success
        assert len(result.persons) == 1
        
        person = result.persons[0]
        
        # Check required fields
        assert "tokens" in person
        assert "original_tokens" in person
        assert "roles" in person
        assert "gender" in person
        assert "confidence" in person
        
        # Check confidence structure
        confidence = person["confidence"]
        assert "score_female" in confidence
        assert "score_male" in confidence
        assert "gap" in confidence
        
        # Check data types
        assert isinstance(person["tokens"], list)
        assert isinstance(person["original_tokens"], list)
        assert isinstance(person["roles"], list)
        assert isinstance(person["gender"], (str, type(None)))
        assert isinstance(confidence["score_female"], int)
        assert isinstance(confidence["score_male"], int)
        assert isinstance(confidence["gap"], int)

    def test_empty_text(self):
        """Test handling of empty text."""
        result = self.service.normalize_sync("")
        
        assert result.success
        assert result.normalized == ""
        assert len(result.persons) == 0

    def test_text_without_persons(self):
        """Test handling of text without person names."""
        result = self.service.normalize_sync("Это обычный текст без имен")
        
        assert result.success
        assert len(result.persons) == 0

    def test_ukrainian_persons(self):
        """Test normalization of Ukrainian persons."""
        result = self.service.normalize_sync("Іван Петренко та Анна Сергієнко")
        
        assert result.success
        assert len(result.persons) == 2
        
        # First person
        person1 = result.persons[0]
        assert person1["tokens"] == ["Іван", "Петренко"]
        assert person1["roles"] == ["given", "surname"]
        
        # Second person
        person2 = result.persons[1]
        assert person2["tokens"] == ["Анна", "Сергієнко"]
        assert person2["roles"] == ["given", "surname"]

    def test_english_persons(self):
        """Test normalization of English persons."""
        result = self.service.normalize_sync("John Smith and Jane Doe")
        
        assert result.success
        assert len(result.persons) == 2
        
        # First person
        person1 = result.persons[0]
        assert person1["tokens"] == ["John", "Smith"]
        assert person1["roles"] == ["given", "surname"]
        
        # Second person
        person2 = result.persons[1]
        assert person2["tokens"] == ["Jane", "Doe"]
        assert person2["roles"] == ["given", "surname"]

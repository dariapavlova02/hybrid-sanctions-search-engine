#!/usr/bin/env python3
"""
Unit tests for the group_persons function in NormalizationService.

This module tests the person grouping logic that separates multiple persons
in text and applies gender inference and surname adjustment to each person.
"""

import pytest
from typing import List, Dict, Any

from src.ai_service.layers.normalization.normalization_service import NormalizationService


class TestGroupPersons:
    """Test cases for the group_persons function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = NormalizationService()

    def test_single_person(self):
        """Test grouping a single person."""
        tokens = [
            ("Иван", "given"),
            ("Петров", "surname")
        ]
        
        persons = self.service.group_persons(tokens)
        
        assert len(persons) == 1
        person = persons[0]
        assert person["tokens"] == ["Иван", "Петров"]
        assert person["original_tokens"] == ["Иван", "Петров"]
        assert person["roles"] == ["given", "surname"]
        assert "gender" in person
        assert "confidence" in person

    def test_multiple_persons_with_conjunction(self):
        """Test grouping multiple persons separated by conjunction."""
        tokens = [
            ("Иван", "given"),
            ("Петров", "surname"),
            ("и", "conjunction"),
            ("Анна", "given"),
            ("Сергеева", "surname")
        ]
        
        persons = self.service.group_persons(tokens)
        
        assert len(persons) == 2
        
        # First person
        person1 = persons[0]
        assert person1["tokens"] == ["Иван", "Петров"]
        assert person1["roles"] == ["given", "surname"]
        
        # Second person
        person2 = persons[1]
        assert person2["tokens"] == ["Анна", "Сергеева"]
        assert person2["roles"] == ["given", "surname"]

    def test_multiple_persons_with_comma(self):
        """Test grouping multiple persons separated by comma."""
        tokens = [
            ("Иван", "given"),
            ("Петров", "surname"),
            (",", "punctuation"),
            ("Анна", "given"),
            ("Сергеева", "surname")
        ]
        
        persons = self.service.group_persons(tokens)
        
        assert len(persons) == 2
        
        # First person
        person1 = persons[0]
        assert person1["tokens"] == ["Иван", "Петров"]
        assert person1["roles"] == ["given", "surname"]
        
        # Second person
        person2 = persons[1]
        assert person2["tokens"] == ["Анна", "Сергеева"]
        assert person2["roles"] == ["given", "surname"]

    def test_person_with_patronymic(self):
        """Test grouping person with patronymic."""
        tokens = [
            ("Иван", "given"),
            ("Петрович", "patronymic"),
            ("Петров", "surname")
        ]
        
        persons = self.service.group_persons(tokens)
        
        assert len(persons) == 1
        person = persons[0]
        assert person["tokens"] == ["Иван", "Петрович", "Петров"]
        assert person["roles"] == ["given", "patronymic", "surname"]

    def test_person_with_initial(self):
        """Test grouping person with initial."""
        tokens = [
            ("И.", "initial"),
            ("Петров", "surname")
        ]
        
        persons = self.service.group_persons(tokens)
        
        assert len(persons) == 1
        person = persons[0]
        assert person["tokens"] == ["И.", "Петров"]
        assert person["roles"] == ["initial", "surname"]

    def test_skip_non_person_tokens(self):
        """Test that non-person tokens are skipped."""
        tokens = [
            ("Иван", "given"),
            ("Петров", "surname"),
            ("работает", "unknown"),
            ("в", "unknown"),
            ("компании", "unknown"),
            ("и", "conjunction"),
            ("Анна", "given"),
            ("Сергеева", "surname")
        ]
        
        persons = self.service.group_persons(tokens)
        
        assert len(persons) == 2
        
        # First person
        person1 = persons[0]
        assert person1["tokens"] == ["Иван", "Петров"]
        assert person1["roles"] == ["given", "surname"]
        
        # Second person
        person2 = persons[1]
        assert person2["tokens"] == ["Анна", "Сергеева"]
        assert person2["roles"] == ["given", "surname"]

    def test_empty_tokens(self):
        """Test handling of empty tokens."""
        tokens = [
            ("", "given"),
            ("Иван", "given"),
            ("", "surname"),
            ("Петров", "surname")
        ]
        
        persons = self.service.group_persons(tokens)
        
        assert len(persons) == 1
        person = persons[0]
        assert person["tokens"] == ["Иван", "Петров"]
        assert person["roles"] == ["given", "surname"]

    def test_no_person_tokens(self):
        """Test handling when no person tokens are present."""
        tokens = [
            ("работает", "unknown"),
            ("в", "unknown"),
            ("компании", "unknown")
        ]
        
        persons = self.service.group_persons(tokens)
        
        assert len(persons) == 0

    def test_multiple_separators(self):
        """Test handling of multiple consecutive separators."""
        tokens = [
            ("Иван", "given"),
            ("Петров", "surname"),
            ("и", "conjunction"),
            (",", "punctuation"),
            ("Анна", "given"),
            ("Сергеева", "surname")
        ]
        
        persons = self.service.group_persons(tokens)
        
        assert len(persons) == 2
        
        # First person
        person1 = persons[0]
        assert person1["tokens"] == ["Иван", "Петров"]
        assert person1["roles"] == ["given", "surname"]
        
        # Second person
        person2 = persons[1]
        assert person2["tokens"] == ["Анна", "Сергеева"]
        assert person2["roles"] == ["given", "surname"]

    def test_ukrainian_separators(self):
        """Test handling of Ukrainian separators."""
        tokens = [
            ("Іван", "given"),
            ("Петренко", "surname"),
            ("та", "conjunction"),
            ("Анна", "given"),
            ("Сергієнко", "surname")
        ]
        
        persons = self.service.group_persons(tokens)
        
        assert len(persons) == 2
        
        # First person
        person1 = persons[0]
        assert person1["tokens"] == ["Іван", "Петренко"]
        assert person1["roles"] == ["given", "surname"]
        
        # Second person
        person2 = persons[1]
        assert person2["tokens"] == ["Анна", "Сергієнко"]
        assert person2["roles"] == ["given", "surname"]

    def test_english_separators(self):
        """Test handling of English separators."""
        tokens = [
            ("John", "given"),
            ("Smith", "surname"),
            ("and", "conjunction"),
            ("Jane", "given"),
            ("Doe", "surname")
        ]
        
        persons = self.service.group_persons(tokens)
        
        assert len(persons) == 2
        
        # First person
        person1 = persons[0]
        assert person1["tokens"] == ["John", "Smith"]
        assert person1["roles"] == ["given", "surname"]
        
        # Second person
        person2 = persons[1]
        assert person2["tokens"] == ["Jane", "Doe"]
        assert person2["roles"] == ["given", "surname"]

    def test_person_data_structure(self):
        """Test the structure of person data."""
        tokens = [
            ("Анна", "given"),
            ("Петрова", "surname")
        ]
        
        persons = self.service.group_persons(tokens)
        
        assert len(persons) == 1
        person = persons[0]
        
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

    def test_surname_adjustment_integration(self):
        """Test that surname adjustment is applied in person data."""
        tokens = [
            ("Анна", "given"),
            ("Петров", "surname")  # Should be adjusted to Петрова
        ]
        
        persons = self.service.group_persons(tokens)
        
        assert len(persons) == 1
        person = persons[0]
        
        # Check that surname was NOT adjusted (gender is not determined due to low confidence gap)
        assert person["tokens"] == ["Анна", "Петров"]  # No adjustment due to low confidence
        assert person["original_tokens"] == ["Анна", "Петров"]
        assert person["roles"] == ["given", "surname"]
        assert person["gender"] is None  # Gender not determined due to low confidence gap

    def test_surname_adjustment_with_high_confidence(self):
        """Test surname adjustment when gender is determined with high confidence."""
        tokens = [
            ("Александр", "given"),
            ("Петрович", "patronymic"),  # Male patronymic for high confidence
            ("Петров", "surname")
        ]
        
        persons = self.service.group_persons(tokens)
        
        assert len(persons) == 1
        person = persons[0]
        
        # Check that surname was adjusted (gender is determined with high confidence)
        assert person["tokens"] == ["Александр", "Петрович", "Петров"]  # No adjustment for male gender
        assert person["original_tokens"] == ["Александр", "Петрович", "Петров"]
        assert person["roles"] == ["given", "patronymic", "surname"]
        assert person["gender"] == "masc"  # Gender determined due to patronymic

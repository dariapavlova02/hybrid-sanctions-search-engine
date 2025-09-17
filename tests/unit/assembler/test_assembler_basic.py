#!/usr/bin/env python3
"""
Unit tests for NameAssembler basic functionality.
"""

import pytest
from src.ai_service.layers.normalization.name_assembler import (
    NameAssembler, TokenWithRole, AssembledPerson, PersonRole
)
from src.ai_service.layers.normalization.role_tagger_service import TokenRole


class TestNameAssemblerBasic:
    """Test cases for NameAssembler basic functionality."""
    
    def test_assemble_single_person(self):
        """Test assembling a single person from tokens."""
        assembler = NameAssembler()
        
        # Create tagged tokens for a single person
        tagged_tokens = [
            TokenWithRole(
                text="Иван",
                normalized="Иван",
                role=TokenRole.GIVEN,
                confidence=0.9,
                reason="given_name_detected",
                evidence=["capitalized", "not_stopword"]
            ),
            TokenWithRole(
                text="Петров",
                normalized="Петров",
                role=TokenRole.SURNAME,
                confidence=0.95,
                reason="surname_suffix_detected",
                evidence=["suffix_ов", "capitalized"]
            )
        ]
        
        result = assembler.assemble(tagged_tokens, "ru")
        
        # Check result structure
        assert len(result.persons) == 1
        assert result.person_tokens == 2
        assert result.excluded_tokens == 0
        assert result.total_tokens == 2
        
        # Check assembled person
        person = result.persons[0]
        assert person.given == "Иван"
        assert person.surname == "Петров"
        assert person.patronymic is None
        assert person.initials == []
        assert person.full_name == "Иван Петров"
        assert person.confidence > 0.9
        assert person.tokens_used == ["Иван", "Петров"]
    
    def test_assemble_person_with_patronymic(self):
        """Test assembling a person with patronymic."""
        assembler = NameAssembler()
        
        tagged_tokens = [
            TokenWithRole(text="Иван", normalized="Иван", role=TokenRole.GIVEN, confidence=0.9, reason="given", evidence=[]),
            TokenWithRole(text="Петрович", normalized="Петрович", role=TokenRole.PATRONYMIC, confidence=0.9, reason="patronymic", evidence=[]),
            TokenWithRole(text="Сидоров", normalized="Сидоров", role=TokenRole.SURNAME, confidence=0.95, reason="surname", evidence=[])
        ]
        
        result = assembler.assemble(tagged_tokens, "ru")
        
        person = result.persons[0]
        assert person.given == "Иван"
        assert person.patronymic == "Петрович"
        assert person.surname == "Сидоров"
        assert person.full_name == "Иван Петрович Сидоров"
    
    def test_assemble_person_with_initials(self):
        """Test assembling a person with initials."""
        assembler = NameAssembler()
        
        tagged_tokens = [
            TokenWithRole(text="И", normalized="И", role=TokenRole.INITIAL, confidence=0.8, reason="initial", evidence=[]),
            TokenWithRole(text="П", normalized="П", role=TokenRole.INITIAL, confidence=0.8, reason="initial", evidence=[]),
            TokenWithRole(text="Сидоров", normalized="Сидоров", role=TokenRole.SURNAME, confidence=0.95, reason="surname", evidence=[])
        ]
        
        result = assembler.assemble(tagged_tokens, "ru")
        
        person = result.persons[0]
        assert person.given is None
        assert person.surname == "Сидоров"
        assert person.initials == ["И", "П"]
        assert person.full_name == "И.П. Сидоров"
    
    def test_assemble_multiple_persons(self):
        """Test assembling multiple persons with separator."""
        assembler = NameAssembler()
        
        tagged_tokens = [
            # First person
            TokenWithRole(text="Анна", normalized="Анна", role=TokenRole.GIVEN, confidence=0.9, reason="given", evidence=[]),
            TokenWithRole(text="Петрова", normalized="Петрова", role=TokenRole.SURNAME, confidence=0.95, reason="surname", evidence=[]),
            # Second person
            TokenWithRole(text="Иван", normalized="Иван", role=TokenRole.GIVEN, confidence=0.9, reason="given", evidence=[]),
            TokenWithRole(text="Сидоров", normalized="Сидоров", role=TokenRole.SURNAME, confidence=0.95, reason="surname", evidence=[])
        ]
        
        result = assembler.assemble(tagged_tokens, "ru")
        
        # Check multiple persons
        assert len(result.persons) == 2
        assert result.persons[0].full_name == "Анна Петрова"
        assert result.persons[1].full_name == "Иван Сидоров"
        
        # Check that traces include person emission
        person_emit_traces = [t for t in result.traces if t.get("action") == "emit_person"]
        assert len(person_emit_traces) == 2
    
    def test_exclude_organization_tokens(self):
        """Test that organization tokens are excluded from assembly."""
        assembler = NameAssembler()
        
        tagged_tokens = [
            TokenWithRole(text="ТОВ", normalized="ТОВ", role=TokenRole.ORG, confidence=0.9, reason="org", evidence=[]),
            TokenWithRole(text="ПРИВАТБАНК", normalized="ПРИВАТБАНК", role=TokenRole.ORG, confidence=0.9, reason="org", evidence=[]),
            TokenWithRole(text="Иван", normalized="Иван", role=TokenRole.GIVEN, confidence=0.9, reason="given", evidence=[]),
            TokenWithRole(text="Петров", normalized="Петров", role=TokenRole.SURNAME, confidence=0.95, reason="surname", evidence=[])
        ]
        
        result = assembler.assemble(tagged_tokens, "ru")
        
        # Check that only person tokens are included
        assert result.person_tokens == 2
        assert result.excluded_tokens == 2
        assert len(result.persons) == 1
        assert result.persons[0].full_name == "Иван Петров"
        
        # Check exclusion traces
        exclude_traces = [t for t in result.traces if t.get("action") == "exclude_token"]
        assert len(exclude_traces) == 2
        assert all(t["role"] == "org" for t in exclude_traces)
    
    def test_exclude_unknown_tokens(self):
        """Test that unknown tokens are excluded from assembly."""
        assembler = NameAssembler()
        
        tagged_tokens = [
            TokenWithRole(text="и", normalized="и", role=TokenRole.UNKNOWN, confidence=0.5, reason="unknown", evidence=[]),
            TokenWithRole(text="Иван", normalized="Иван", role=TokenRole.GIVEN, confidence=0.9, reason="given", evidence=[]),
            TokenWithRole(text="Петров", normalized="Петров", role=TokenRole.SURNAME, confidence=0.95, reason="surname", evidence=[])
        ]
        
        result = assembler.assemble(tagged_tokens, "ru")
        
        # Check that only person tokens are included
        assert result.person_tokens == 2
        assert result.excluded_tokens == 1
        assert len(result.persons) == 1
        assert result.persons[0].full_name == "Иван Петров"
    
    def test_preserve_hyphenated_names(self):
        """Test that hyphenated names are preserved with proper typography."""
        assembler = NameAssembler()
        
        tagged_tokens = [
            TokenWithRole(text="Анна-Мария", normalized="Анна-Мария", role=TokenRole.GIVEN, confidence=0.9, reason="given", evidence=[]),
            TokenWithRole(text="Петрова-Сидорова", normalized="Петрова-Сидорова", role=TokenRole.SURNAME, confidence=0.95, reason="surname", evidence=[])
        ]
        
        result = assembler.assemble(tagged_tokens, "ru")
        
        person = result.persons[0]
        assert person.given == "Анна-Мария"
        assert person.surname == "Петрова-Сидорова"
        assert person.full_name == "Анна-Мария Петрова-Сидорова"
    
    def test_empty_tokens_list(self):
        """Test handling of empty tokens list."""
        assembler = NameAssembler()
        
        result = assembler.assemble([], "ru")
        
        assert len(result.persons) == 0
        assert result.person_tokens == 0
        assert result.excluded_tokens == 0
        assert result.total_tokens == 0
        assert result.traces == []
    
    def test_only_excluded_tokens(self):
        """Test handling when all tokens are excluded."""
        assembler = NameAssembler()
        
        tagged_tokens = [
            TokenWithRole(text="ТОВ", normalized="ТОВ", role=TokenRole.ORG, confidence=0.9, reason="org", evidence=[]),
            TokenWithRole(text="и", normalized="и", role=TokenRole.UNKNOWN, confidence=0.5, reason="unknown", evidence=[])
        ]
        
        result = assembler.assemble(tagged_tokens, "ru")
        
        assert len(result.persons) == 0
        assert result.person_tokens == 0
        assert result.excluded_tokens == 2
        assert result.total_tokens == 2
    
    def test_confidence_calculation(self):
        """Test confidence calculation for assembled persons."""
        assembler = NameAssembler()
        
        tagged_tokens = [
            TokenWithRole(text="Иван", normalized="Иван", role=TokenRole.GIVEN, confidence=0.8, reason="given", evidence=[]),
            TokenWithRole(text="Петров", normalized="Петров", role=TokenRole.SURNAME, confidence=0.9, reason="surname", evidence=[])
        ]
        
        result = assembler.assemble(tagged_tokens, "ru")
        
        person = result.persons[0]
        # Confidence should be average of token confidences
        expected_confidence = (0.8 + 0.9) / 2
        assert abs(person.confidence - expected_confidence) < 0.01
    
    def test_assembly_traces(self):
        """Test that assembly traces are generated correctly."""
        assembler = NameAssembler()
        
        tagged_tokens = [
            TokenWithRole(text="Иван", normalized="Иван", role=TokenRole.GIVEN, confidence=0.9, reason="given", evidence=[]),
            TokenWithRole(text="Петров", normalized="Петров", role=TokenRole.SURNAME, confidence=0.95, reason="surname", evidence=[])
        ]
        
        result = assembler.assemble(tagged_tokens, "ru")
        
        # Check that assembly traces are present
        assert len(result.persons[0].assembly_traces) == 2
        assert "assigned_given" in result.persons[0].assembly_traces[0]
        assert "assigned_surname" in result.persons[0].assembly_traces[1]
    
    def test_person_separator_property(self):
        """Test that person separator is accessible."""
        assembler = NameAssembler()
        assert assembler.person_separator == " | "
    
    def test_stats_tracking(self):
        """Test that statistics are tracked correctly."""
        assembler = NameAssembler()
        
        # Initial stats
        stats = assembler.get_stats()
        assert stats['total_requests'] == 0
        assert stats['total_persons_assembled'] == 0
        
        # Process some tokens
        tagged_tokens = [
            TokenWithRole(text="Иван", normalized="Иван", role=TokenRole.GIVEN, confidence=0.9, reason="given", evidence=[]),
            TokenWithRole(text="Петров", normalized="Петров", role=TokenRole.SURNAME, confidence=0.95, reason="surname", evidence=[])
        ]
        
        assembler.assemble(tagged_tokens, "ru")
        
        # Check updated stats
        stats = assembler.get_stats()
        assert stats['total_requests'] == 1
        assert stats['total_persons_assembled'] == 1
        assert stats['total_tokens_processed'] == 2

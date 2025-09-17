"""
Tests for English apostrophe and hyphen handling.

Tests the proper handling of apostrophes and hyphens in English names
to ensure they are preserved during normalization.
"""

import pytest
from src.ai_service.layers.normalization.nameparser_adapter import NameparserAdapter
from pathlib import Path


@pytest.fixture
def nameparser_adapter():
    """Create a nameparser adapter for testing."""
    lexicons_path = Path(__file__).resolve().parents[3] / "data" / "lexicons"
    return NameparserAdapter(lexicons_path)


def test_apostrophe_preservation(nameparser_adapter):
    """Test that apostrophes are preserved in names."""
    test_cases = [
        "O'Connor",
        "D'Angelo", 
        "O'Brien",
        "D'Artagnan",
        "O'Malley",
        "D'Souza",
    ]
    
    for name in test_cases:
        parsed = nameparser_adapter.parse_en_name(name)
        # The apostrophe should be preserved in the parsed name
        assert "'" in parsed.full_name, f"Apostrophe not preserved in '{name}'"
        assert parsed.confidence >= 0.3


def test_hyphen_preservation(nameparser_adapter):
    """Test that hyphens are preserved in names."""
    test_cases = [
        "Anne-Marie",
        "Jean-Pierre",
        "Mary-Jane",
        "Jean-Claude",
        "Marie-Louise",
        "Pierre-Paul",
    ]
    
    for name in test_cases:
        parsed = nameparser_adapter.parse_en_name(name)
        # The hyphen should be preserved in the parsed name
        assert "-" in parsed.full_name, f"Hyphen not preserved in '{name}'"
        assert parsed.confidence >= 0.3


def test_apostrophe_and_hyphen_combined(nameparser_adapter):
    """Test names with both apostrophes and hyphens."""
    test_cases = [
        "Anne-Marie O'Connor",
        "Jean-Pierre D'Angelo",
        "Mary-Jane O'Brien",
    ]
    
    for name in test_cases:
        parsed = nameparser_adapter.parse_en_name(name)
        # Both apostrophe and hyphen should be preserved
        assert "'" in parsed.full_name, f"Apostrophe not preserved in '{name}'"
        assert "-" in parsed.full_name, f"Hyphen not preserved in '{name}'"
        assert parsed.confidence >= 0.3


def test_title_case_with_apostrophes(nameparser_adapter):
    """Test that title case is applied correctly with apostrophes."""
    # Test the internal title case function from NormalizationFactory
    from src.ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory
    factory = NormalizationFactory()
    
    test_cases = [
        ("o'connor", "O'Connor"),
        ("d'angelo", "D'Angelo"),
        ("o'brien", "O'Brien"),
        ("d'artagnan", "D'Artagnan"),
    ]
    
    for input_name, expected in test_cases:
        result = factory._title_case_with_punctuation(input_name)
        assert result == expected, f"Expected '{expected}', got '{result}' for '{input_name}'"


def test_title_case_with_hyphens(nameparser_adapter):
    """Test that title case is applied correctly with hyphens."""
    from src.ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory
    factory = NormalizationFactory()
    
    test_cases = [
        ("anne-marie", "Anne-Marie"),
        ("jean-pierre", "Jean-Pierre"),
        ("mary-jane", "Mary-Jane"),
        ("jean-claude", "Jean-Claude"),
    ]
    
    for input_name, expected in test_cases:
        result = factory._title_case_with_punctuation(input_name)
        assert result == expected, f"Expected '{expected}', got '{result}' for '{input_name}'"


def test_title_case_with_apostrophes_and_hyphens(nameparser_adapter):
    """Test title case with both apostrophes and hyphens."""
    from src.ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory
    factory = NormalizationFactory()
    
    test_cases = [
        ("anne-marie o'connor", "Anne-Marie O'Connor"),
        ("jean-pierre d'angelo", "Jean-Pierre D'Angelo"),
        ("mary-jane o'brien", "Mary-Jane O'Brien"),
    ]
    
    for input_name, expected in test_cases:
        result = factory._title_case_with_punctuation(input_name)
        assert result == expected, f"Expected '{expected}', got '{result}' for '{input_name}'"


def test_normalize_english_name_token(nameparser_adapter):
    """Test the normalize_english_name_token method."""
    from src.ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory, NormalizationConfig
    
    factory = NormalizationFactory()
    config = NormalizationConfig()
    
    test_cases = [
        ("o'connor", "given", "O'Connor"),
        ("anne-marie", "given", "Anne-Marie"),
        ("smith", "surname", "Smith"),
        ("o'brien", "surname", "O'Brien"),
        ("jean-pierre", "given", "Jean-Pierre"),
    ]
    
    for input_token, role, expected in test_cases:
        result = factory._normalize_english_name_token(input_token, role, config)
        assert result == expected, f"Expected '{expected}', got '{result}' for '{input_token}' as {role}"


def test_punctuation_preservation_in_full_names(nameparser_adapter):
    """Test that punctuation is preserved in full name reconstruction."""
    test_cases = [
        "Dr. Anne-Marie O'Connor Jr.",
        "Prof. Jean-Pierre D'Angelo",
        "Mr. Mary-Jane O'Brien Sr.",
    ]
    
    for name in test_cases:
        parsed = nameparser_adapter.parse_en_name(name)
        reconstructed = nameparser_adapter.reconstruct_name(parsed)
        
        # Check that apostrophes and hyphens are preserved
        if "'" in name:
            assert "'" in reconstructed, f"Apostrophe not preserved in reconstruction of '{name}'"
        if "-" in name:
            assert "-" in reconstructed, f"Hyphen not preserved in reconstruction of '{name}'"


def test_edge_cases_punctuation(nameparser_adapter):
    """Test edge cases with punctuation."""
    # Multiple apostrophes
    parsed = nameparser_adapter.parse_en_name("O'Connor-Smith")
    assert "'" in parsed.full_name
    assert "-" in parsed.full_name
    
    # Multiple hyphens
    parsed = nameparser_adapter.parse_en_name("Anne-Marie-Louise")
    assert parsed.full_name.count("-") >= 2
    
    # Apostrophe at beginning
    parsed = nameparser_adapter.parse_en_name("'Connor")
    assert "'" in parsed.full_name
    
    # Hyphen at beginning
    parsed = nameparser_adapter.parse_en_name("-Smith")
    assert "-" in parsed.full_name


def test_punctuation_with_particles(nameparser_adapter):
    """Test punctuation handling with surname particles."""
    test_cases = [
        "John de la O'Connor",
        "Mary van der Berg-Smith",
        "Peter von O'Brien",
    ]
    
    for name in test_cases:
        parsed = nameparser_adapter.parse_en_name(name)
        # Punctuation should be preserved
        if "'" in name:
            assert "'" in parsed.full_name
        if "-" in name:
            assert "-" in parsed.full_name

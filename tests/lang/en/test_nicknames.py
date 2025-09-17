"""
Tests for English nickname expansion functionality.

Tests the nickname expansion feature that converts common English
nicknames to their full forms (e.g., Bill -> William).
"""

import pytest
from src.ai_service.layers.normalization.nameparser_adapter import NameparserAdapter
from pathlib import Path


@pytest.fixture
def nameparser_adapter():
    """Create a nameparser adapter for testing."""
    lexicons_path = Path(__file__).resolve().parents[3] / "data" / "lexicons"
    return NameparserAdapter(lexicons_path)


def test_nickname_expansion_basic(nameparser_adapter):
    """Test basic nickname expansion."""
    test_cases = [
        ("Bill", "william"),
        ("Bob", "robert"),
        ("Jim", "james"),
        ("Mike", "michael"),
        ("Dave", "david"),
        ("Tom", "thomas"),
        ("Rick", "richard"),
        ("Harry", "henry"),
        ("Jack", "john"),
        ("Sam", "samuel"),
    ]
    
    for nickname, expected_full in test_cases:
        expanded, was_expanded = nameparser_adapter.expand_nickname(nickname)
        assert was_expanded, f"Failed to expand nickname '{nickname}'"
        assert expanded == expected_full, f"Expected '{expected_full}', got '{expanded}' for '{nickname}'"


def test_nickname_expansion_case_insensitive(nameparser_adapter):
    """Test that nickname expansion is case insensitive."""
    test_cases = [
        ("bill", "william"),
        ("BILL", "william"),
        ("Bill", "william"),
        ("bOb", "robert"),
    ]
    
    for nickname, expected_full in test_cases:
        expanded, was_expanded = nameparser_adapter.expand_nickname(nickname)
        assert was_expanded, f"Failed to expand nickname '{nickname}'"
        assert expanded == expected_full, f"Expected '{expected_full}', got '{expanded}' for '{nickname}'"


def test_nickname_expansion_female_names(nameparser_adapter):
    """Test nickname expansion for female names."""
    test_cases = [
        ("Beth", "elizabeth"),
        ("Liz", "elizabeth"),
        ("Katie", "katherine"),
        ("Kathy", "katherine"),
        ("Sue", "susan"),
        ("Annie", "anne"),
        ("Maggie", "margaret"),
    ]
    
    for nickname, expected_full in test_cases:
        expanded, was_expanded = nameparser_adapter.expand_nickname(nickname)
        assert was_expanded, f"Failed to expand nickname '{nickname}'"
        assert expanded == expected_full, f"Expected '{expected_full}', got '{expanded}' for '{nickname}'"


def test_nickname_expansion_not_nickname(nameparser_adapter):
    """Test that non-nicknames are not expanded."""
    test_cases = [
        "William",  # Already full name
        "Robert",   # Already full name
        "Smith",    # Surname
        "Johnson",  # Surname
        "Unknown",  # Not in dictionary
        "X",        # Too short
        "",         # Empty
    ]
    
    for name in test_cases:
        expanded, was_expanded = nameparser_adapter.expand_nickname(name)
        assert not was_expanded, f"Should not expand '{name}' as nickname"
        assert expanded == name, f"Expected '{name}' unchanged, got '{expanded}'"


def test_nickname_in_parsed_name(nameparser_adapter):
    """Test that nicknames are properly expanded in parsed names."""
    # Test with a known nickname
    parsed = nameparser_adapter.parse_en_name("Bill Smith")
    
    # The first name should be expanded from Bill to William
    assert parsed.first == "William"  # Title case applied
    assert parsed.nickname == "Bill"  # Original nickname should be stored
    assert parsed.last == "Smith"
    assert parsed.full_name == "Bill Smith"


def test_nickname_with_middle_name(nameparser_adapter):
    """Test nickname expansion with middle names."""
    parsed = nameparser_adapter.parse_en_name("Bill Michael Smith")
    
    assert parsed.first == "William"  # Expanded from Bill
    assert parsed.middles == ["Michael"]
    assert parsed.last == "Smith"
    assert parsed.nickname == "Bill"


def test_nickname_with_title_and_suffix(nameparser_adapter):
    """Test nickname expansion with title and suffix."""
    parsed = nameparser_adapter.parse_en_name("Dr. Bill Smith Jr.")
    
    assert parsed.first == "William"  # Expanded from Bill
    assert parsed.last == "Smith"
    assert parsed.suffix == "Jr."
    assert parsed.nickname == "Bill"


def test_multiple_nicknames_in_name(nameparser_adapter):
    """Test names with multiple potential nicknames."""
    # Test case where first name is nickname but middle is not
    parsed = nameparser_adapter.parse_en_name("Bill Robert Smith")
    
    assert parsed.first == "William"  # Bill -> William
    assert parsed.middles == ["Robert"]  # Robert stays as is (not a nickname in our dict)
    assert parsed.last == "Smith"


def test_nickname_expansion_confidence(nameparser_adapter):
    """Test that nickname expansion affects parsing confidence."""
    # Name with nickname should have good confidence
    parsed_with_nickname = nameparser_adapter.parse_en_name("Bill Smith")
    assert parsed_with_nickname.confidence > 0.5
    
    # Name without nickname should also have good confidence
    parsed_without_nickname = nameparser_adapter.parse_en_name("William Smith")
    assert parsed_without_nickname.confidence > 0.5


def test_nickname_expansion_edge_cases(nameparser_adapter):
    """Test edge cases for nickname expansion."""
    # Empty string
    expanded, was_expanded = nameparser_adapter.expand_nickname("")
    assert not was_expanded
    assert expanded == ""
    
    # None (should handle gracefully)
    expanded, was_expanded = nameparser_adapter.expand_nickname(None)
    assert not was_expanded
    assert expanded is None
    
    # Very long string
    long_name = "A" * 100
    expanded, was_expanded = nameparser_adapter.expand_nickname(long_name)
    assert not was_expanded
    assert expanded == long_name

"""
Tests for English nameparser integration.

Tests the basic functionality of nameparser for parsing English names
with titles, particles, and suffixes.
"""

import pytest
from src.ai_service.layers.normalization.nameparser_adapter import (
    NameparserAdapter, 
    ParsedName,
    get_nameparser_adapter
)
from pathlib import Path


@pytest.fixture
def nameparser_adapter():
    """Create a nameparser adapter for testing."""
    # Use the actual lexicons path
    lexicons_path = Path(__file__).resolve().parents[3] / "data" / "lexicons"
    return NameparserAdapter(lexicons_path)


def test_parse_basic_name(nameparser_adapter):
    """Test parsing a basic English name."""
    parsed = nameparser_adapter.parse_en_name("John Smith")
    
    assert parsed.first == "John"
    assert parsed.last == "Smith"
    assert parsed.middles == []
    assert parsed.suffix == ""
    # Note: "John" is in our nickname dictionary, so it will be detected as nickname
    assert parsed.nickname == "John"
    assert parsed.particles == []
    assert parsed.full_name == "John Smith"
    assert parsed.confidence > 0.5


def test_parse_name_with_title(nameparser_adapter):
    """Test parsing a name with title."""
    parsed = nameparser_adapter.parse_en_name("Dr. John Smith")
    
    assert parsed.first == "John"
    assert parsed.last == "Smith"
    assert parsed.suffix == ""
    assert parsed.full_name == "Dr. John Smith"
    assert parsed.confidence > 0.5


def test_parse_name_with_suffix(nameparser_adapter):
    """Test parsing a name with suffix."""
    parsed = nameparser_adapter.parse_en_name("John Smith Jr.")
    
    assert parsed.first == "John"
    assert parsed.last == "Smith"
    assert parsed.suffix == "Jr."
    assert parsed.full_name == "John Smith Jr."
    assert parsed.confidence > 0.5


def test_parse_name_with_middle(nameparser_adapter):
    """Test parsing a name with middle name."""
    parsed = nameparser_adapter.parse_en_name("John Michael Smith")
    
    assert parsed.first == "John"
    assert parsed.middles == ["Michael"]
    assert parsed.last == "Smith"
    assert parsed.full_name == "John Michael Smith"
    assert parsed.confidence > 0.5


def test_parse_name_with_particles(nameparser_adapter):
    """Test parsing a name with surname particles."""
    parsed = nameparser_adapter.parse_en_name("John de la Cruz")
    
    assert parsed.first == "John"
    assert parsed.last == "De La Cruz"  # Title case applied
    assert "de" in parsed.particles
    assert "la" in parsed.particles
    assert parsed.full_name == "John de la Cruz"
    assert parsed.confidence > 0.5


def test_parse_complex_name(nameparser_adapter):
    """Test parsing a complex name with all components."""
    parsed = nameparser_adapter.parse_en_name("Dr. John Michael de la Cruz Jr.")
    
    assert parsed.first == "John"
    assert parsed.middles == ["Michael"]
    assert parsed.last == "De La Cruz"  # Title case applied
    assert parsed.suffix == "Jr."
    assert "de" in parsed.particles
    assert "la" in parsed.particles
    assert parsed.full_name == "Dr. John Michael de la Cruz Jr."
    assert parsed.confidence > 0.5


def test_parse_nickname_expansion(nameparser_adapter):
    """Test nickname expansion functionality."""
    # Test nickname expansion (case insensitive)
    expanded, was_expanded = nameparser_adapter.expand_nickname("Bill")
    assert was_expanded
    assert expanded == "william"
    
    # Test non-nickname (use a name not in our dictionary)
    expanded, was_expanded = nameparser_adapter.expand_nickname("Smith")
    assert not was_expanded
    assert expanded == "Smith"


def test_is_surname_particle(nameparser_adapter):
    """Test surname particle detection."""
    assert nameparser_adapter.is_surname_particle("van")
    assert nameparser_adapter.is_surname_particle("de")
    assert nameparser_adapter.is_surname_particle("von")
    assert not nameparser_adapter.is_surname_particle("smith")
    assert not nameparser_adapter.is_surname_particle("john")


def test_reconstruct_name(nameparser_adapter):
    """Test name reconstruction."""
    parsed = ParsedName(
        first="John",
        middles=["Michael"],
        last="Smith",
        suffix="Jr.",
        nickname="",
        particles=[],
        full_name="John Michael Smith Jr."
    )
    
    reconstructed = nameparser_adapter.reconstruct_name(parsed)
    assert reconstructed == "John Michael Smith Jr."
    
    # Test with particles
    parsed_with_particles = ParsedName(
        first="John",
        middles=[],
        last="Cruz",
        suffix="",
        nickname="",
        particles=["de", "la"],
        full_name="John de la Cruz"
    )
    
    reconstructed = nameparser_adapter.reconstruct_name(parsed_with_particles)
    assert reconstructed == "John de la Cruz"


def test_parse_empty_name(nameparser_adapter):
    """Test parsing empty or invalid names."""
    parsed = nameparser_adapter.parse_en_name("")
    assert parsed.first == ""
    assert parsed.last == ""
    assert parsed.confidence == 0.0
    
    parsed = nameparser_adapter.parse_en_name("   ")
    assert parsed.first == ""
    assert parsed.last == ""
    assert parsed.confidence == 0.0


def test_parse_single_name(nameparser_adapter):
    """Test parsing single name (no last name)."""
    parsed = nameparser_adapter.parse_en_name("John")
    
    assert parsed.first == "John"
    assert parsed.last == ""
    assert parsed.confidence < 0.6  # Lower confidence for incomplete names


def test_singleton_adapter():
    """Test singleton adapter functionality."""
    adapter1 = get_nameparser_adapter()
    adapter2 = get_nameparser_adapter()
    
    assert adapter1 is adapter2

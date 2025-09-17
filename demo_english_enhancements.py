#!/usr/bin/env python3
"""
Demo script for English normalization enhancements.

This script demonstrates the new English normalization features:
- nameparser integration for structured name parsing
- nickname expansion (Bill -> William)
- surname particle handling (van der, de la, etc.)
- apostrophe and hyphen preservation
- optional spaCy NER integration
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.ai_service.layers.normalization.normalization_service import NormalizationService
from src.ai_service.layers.normalization.nameparser_adapter import NameparserAdapter


async def demo_nameparser():
    """Demonstrate nameparser functionality."""
    print("=== Nameparser Demo ===")
    
    # Use the correct path to lexicons
    lexicons_path = Path(__file__).parent / "data" / "lexicons"
    nameparser = NameparserAdapter(lexicons_path)
    
    test_names = [
        "Dr. Bill J. de la Cruz Jr.",
        "Anne-Marie O'Connor",
        "John Michael Smith",
        "Prof. Mary-Jane O'Brien",
        "Robert van der Berg",
    ]
    
    for name in test_names:
        print(f"\nParsing: '{name}'")
        parsed = nameparser.parse_en_name(name)
        
        print(f"  First: {parsed.first}")
        print(f"  Middles: {parsed.middles}")
        print(f"  Last: {parsed.last}")
        print(f"  Suffix: {parsed.suffix}")
        print(f"  Nickname: {parsed.nickname}")
        print(f"  Particles: {parsed.particles}")
        print(f"  Confidence: {parsed.confidence:.2f}")
        
        # Test nickname expansion
        if parsed.nickname:
            expanded, was_expanded = nameparser.expand_nickname(parsed.nickname)
            print(f"  Nickname expansion: '{parsed.nickname}' -> '{expanded}'")


async def demo_normalization_service():
    """Demonstrate the normalization service with English features."""
    print("\n=== Normalization Service Demo ===")
    
    service = NormalizationService()
    
    test_cases = [
        {
            "text": "Dr. Bill J. de la Cruz Jr.",
            "description": "Complex name with title, nickname, particles, and suffix"
        },
        {
            "text": "Anne-Marie O'Connor",
            "description": "Name with hyphen and apostrophe"
        },
        {
            "text": "Bob Smith",
            "description": "Simple name with nickname"
        },
        {
            "text": "Microsoft Corporation CEO Tim Cook",
            "description": "Mixed person and organization (with NER if available)"
        },
    ]
    
    for case in test_cases:
        print(f"\n--- {case['description']} ---")
        print(f"Input: '{case['text']}'")
        
        # Test with nameparser enabled
        result = await service.normalize_async(
            case['text'],
            language='en',
            en_use_nameparser=True,
            enable_en_nickname_expansion=True,
            enable_spacy_en_ner=False  # Set to True if spaCy is available
        )
        
        print(f"Normalized: '{result.normalized}'")
        print(f"Tokens: {result.tokens}")
        print(f"Success: {result.success}")
        print(f"Processing time: {result.processing_time:.3f}s")
        
        if result.trace:
            print("Trace:")
            for trace in result.trace[:5]:  # Show first 5 traces
                print(f"  {trace.role}: '{trace.token}' -> '{trace.output}'")
                if trace.notes:
                    print(f"    Notes: {trace.notes}")


async def demo_nickname_expansion():
    """Demonstrate nickname expansion functionality."""
    print("\n=== Nickname Expansion Demo ===")
    
    # Use the correct path to lexicons
    lexicons_path = Path(__file__).parent / "data" / "lexicons"
    nameparser = NameparserAdapter(lexicons_path)
    
    nicknames = [
        "Bill", "Bob", "Jim", "Mike", "Dave", "Tom", "Dick", "Harry", "Jack", "Sam",
        "Beth", "Liz", "Katie", "Kathy", "Sue", "Annie", "Maggie"
    ]
    
    print("Nickname expansions:")
    for nickname in nicknames:
        expanded, was_expanded = nameparser.expand_nickname(nickname)
        if was_expanded:
            print(f"  {nickname} -> {expanded}")
        else:
            print(f"  {nickname} -> (not expanded)")


async def demo_punctuation_handling():
    """Demonstrate punctuation preservation."""
    print("\n=== Punctuation Handling Demo ===")
    
    # Use the correct path to lexicons
    lexicons_path = Path(__file__).parent / "data" / "lexicons"
    nameparser = NameparserAdapter(lexicons_path)
    
    test_cases = [
        "O'Connor",
        "D'Angelo",
        "Anne-Marie",
        "Jean-Pierre",
        "Mary-Jane O'Brien",
        "Jean-Claude van der Berg",
    ]
    
    for name in test_cases:
        print(f"\nTesting: '{name}'")
        
        # Test title case with punctuation
        from src.ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory
        factory = NormalizationFactory()
        result = factory._title_case_with_punctuation(name.lower())
        print(f"  Title case: '{name.lower()}' -> '{result}'")
        
        # Test parsing
        parsed = nameparser.parse_en_name(name)
        print(f"  Parsed: {parsed.first} {parsed.last}")
        print(f"  Confidence: {parsed.confidence:.2f}")


async def demo_surname_particles():
    """Demonstrate surname particle handling."""
    print("\n=== Surname Particles Demo ===")
    
    # Use the correct path to lexicons
    lexicons_path = Path(__file__).parent / "data" / "lexicons"
    nameparser = NameparserAdapter(lexicons_path)
    
    test_cases = [
        "John van der Berg",
        "Mary de la Cruz",
        "Peter von Habsburg",
        "Anna di Marco",
        "Jean du Pont",
    ]
    
    for name in test_cases:
        print(f"\nTesting: '{name}'")
        parsed = nameparser.parse_en_name(name)
        
        print(f"  First: {parsed.first}")
        print(f"  Last: {parsed.last}")
        print(f"  Particles: {parsed.particles}")
        
        # Test particle detection
        words = name.split()
        for word in words:
            is_particle = nameparser.is_surname_particle(word)
            print(f"    '{word}' is particle: {is_particle}")


async def main():
    """Run all demos."""
    print("English Normalization Enhancements Demo")
    print("=" * 50)
    
    try:
        await demo_nameparser()
        await demo_nickname_expansion()
        await demo_punctuation_handling()
        await demo_surname_particles()
        await demo_normalization_service()
        
        print("\n" + "=" * 50)
        print("Demo completed successfully!")
        
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

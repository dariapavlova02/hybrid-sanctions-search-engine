#!/usr/bin/env python3
"""Debug partial name variant generation"""

import sys
import os
sys.path.append('/Users/dariapavlova/Desktop/ai-service/src')

from ai_service.layers.patterns.high_recall_ac_generator import HighRecallACGenerator

def debug_partial_name_generation():
    """Debug why Liudmyla Ulianova pattern is not generated"""

    print("🔍 DEBUGGING PARTIAL NAME GENERATION")
    print("=" * 60)

    generator = HighRecallACGenerator()

    # Test with the exact name from our data
    name = "Ulianova Liudmyla Oleksandrivna"
    language = "en"

    print(f"📋 Input: '{name}' ({language})")

    # Split into words like the generator does
    words = name.split()
    print(f"📝 Words: {words}")
    print(f"📊 Word count: {len(words)}")

    # Call the partial name variant generation method
    partial_patterns = generator._generate_partial_name_variants(words, language)

    print(f"\n🎯 Generated partial patterns: {len(partial_patterns)}")
    for i, pattern in enumerate(partial_patterns, 1):
        print(f"   {i}. '{pattern.pattern}' (tier={pattern.metadata.tier.value}, type={pattern.metadata.pattern_type.value})")
        print(f"      hints: {pattern.metadata.hints}")

    # Now test tier 2 generation which calls this method
    print(f"\n🔄 Testing full Tier 2 generation...")
    tier2_patterns = generator.generate_tier_2_patterns(name, language)

    print(f"📊 Total Tier 2 patterns: {len(tier2_patterns)}")

    # Filter for partial matches
    partial_matches = [p for p in tier2_patterns if p.metadata.pattern_type.value == 'partial_match']
    print(f"🎯 Partial match patterns: {len(partial_matches)}")
    for pattern in partial_matches:
        print(f"   ✅ '{pattern.pattern}' (hints: {pattern.metadata.hints})")

    # Look for our specific pattern
    target_pattern = "Liudmyla Ulianova"
    found = [p for p in tier2_patterns if p.pattern == target_pattern]

    if found:
        print(f"\n✅ FOUND target pattern: '{target_pattern}'")
        for pattern in found:
            print(f"   Tier: {pattern.metadata.tier.value}")
            print(f"   Type: {pattern.metadata.pattern_type.value}")
            print(f"   Hints: {pattern.metadata.hints}")
    else:
        print(f"\n❌ TARGET PATTERN NOT FOUND: '{target_pattern}'")
        print("📋 All generated patterns:")
        for pattern in tier2_patterns:
            print(f"   - '{pattern.pattern}'")

def main():
    debug_partial_name_generation()

if __name__ == "__main__":
    main()
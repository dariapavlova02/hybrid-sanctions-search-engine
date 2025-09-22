#!/usr/bin/env python3
"""
High-Recall AC Patterns Export Script

Exports comprehensive AC patterns from sanctions data for production use.
Generates patterns across 4 tiers with configurable limits and filtering.

Usage:
    python scripts/export_high_recall_ac_patterns.py --output patterns.json
    python scripts/export_high_recall_ac_patterns.py --tier-limits 0:5,1:10,2:15,3:50
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from ai_service.layers.patterns.high_recall_ac_generator import HighRecallACGenerator, PatternTier


def parse_tier_limits(tier_limits_str: str) -> dict:
    """Parse tier limits from string format like '0:5,1:10,2:15,3:50'"""
    if not tier_limits_str:
        return {}

    limits = {}
    for pair in tier_limits_str.split(','):
        tier_str, limit_str = pair.split(':')
        tier = PatternTier(int(tier_str))
        limits[tier] = int(limit_str)

    return limits


def main():
    parser = argparse.ArgumentParser(
        description="Export High-Recall AC patterns from sanctions data"
    )

    parser.add_argument(
        "--output", "-o",
        default="high_recall_ac_patterns.json",
        help="Output file path (default: high_recall_ac_patterns.json)"
    )

    parser.add_argument(
        "--persons-file",
        default="src/ai_service/data/sanctioned_persons.json",
        help="Path to sanctioned persons JSON file"
    )

    parser.add_argument(
        "--companies-file",
        default="src/ai_service/data/sanctioned_companies.json",
        help="Path to sanctioned companies JSON file"
    )

    parser.add_argument(
        "--tier-limits",
        help="Custom tier limits in format '0:5,1:10,2:15,3:50'"
    )

    parser.add_argument(
        "--max-patterns-per-entity",
        type=int,
        default=50,
        help="Maximum patterns per entity (default: 50)"
    )

    parser.add_argument(
        "--filter-tiers",
        help="Include only specific tiers, e.g., '0,1,2' (default: all tiers)"
    )

    parser.add_argument(
        "--sample-size",
        type=int,
        help="Generate patterns for only first N entities (for testing)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Initialize generator
    if args.verbose:
        print("Initializing High-Recall AC Pattern Generator...")

    generator = HighRecallACGenerator()

    # Apply custom tier limits if provided
    if args.tier_limits:
        custom_limits = parse_tier_limits(args.tier_limits)
        generator.tier_limits.update(custom_limits)
        if args.verbose:
            print(f"Applied custom tier limits: {custom_limits}")

    # Check input files
    if not os.path.exists(args.persons_file):
        print(f"Warning: Persons file not found: {args.persons_file}")
        args.persons_file = None

    if not os.path.exists(args.companies_file):
        print(f"Warning: Companies file not found: {args.companies_file}")
        args.companies_file = None

    if not args.persons_file and not args.companies_file:
        print("Error: No valid input files found")
        return 1

    # Generate corpus
    if args.verbose:
        print("Generating pattern corpus...")

    start_time = time.time()

    if args.sample_size:
        # For testing - modify data loading to limit size
        print(f"Generating sample with {args.sample_size} entities...")

        # Load and limit data
        limited_persons = None
        limited_companies = None

        if args.persons_file:
            with open(args.persons_file, 'r', encoding='utf-8') as f:
                persons_data = json.load(f)
                limited_persons = persons_data[:args.sample_size]

            # Write temporary file
            temp_persons_file = "temp_persons_sample.json"
            with open(temp_persons_file, 'w', encoding='utf-8') as f:
                json.dump(limited_persons, f, ensure_ascii=False)
            args.persons_file = temp_persons_file

        if args.companies_file:
            with open(args.companies_file, 'r', encoding='utf-8') as f:
                companies_data = json.load(f)
                limited_companies = companies_data[:args.sample_size]

            # Write temporary file
            temp_companies_file = "temp_companies_sample.json"
            with open(temp_companies_file, 'w', encoding='utf-8') as f:
                json.dump(limited_companies, f, ensure_ascii=False)
            args.companies_file = temp_companies_file

    # Generate full corpus
    corpus = generator.generate_full_corpus(
        persons_file=args.persons_file,
        companies_file=args.companies_file
    )

    generation_time = time.time() - start_time

    # Filter by tiers if requested
    if args.filter_tiers:
        allowed_tiers = set(int(t) for t in args.filter_tiers.split(','))
        original_count = len(corpus['patterns'])
        corpus['patterns'] = [
            p for p in corpus['patterns']
            if p['tier'] in allowed_tiers
        ]
        if args.verbose:
            print(f"Filtered to tiers {allowed_tiers}: {original_count} -> {len(corpus['patterns'])} patterns")

    # Limit patterns per entity if requested
    if args.max_patterns_per_entity:
        entity_counts = {}
        filtered_patterns = []

        for pattern in corpus['patterns']:
            entity_key = f"{pattern['entity_type']}:{pattern['entity_id']}"
            current_count = entity_counts.get(entity_key, 0)

            if current_count < args.max_patterns_per_entity:
                filtered_patterns.append(pattern)
                entity_counts[entity_key] = current_count + 1

        original_count = len(corpus['patterns'])
        corpus['patterns'] = filtered_patterns

        if args.verbose:
            print(f"Limited patterns per entity to {args.max_patterns_per_entity}: {original_count} -> {len(corpus['patterns'])} patterns")

    # Update statistics
    corpus['statistics']['patterns_generated'] = len(corpus['patterns'])
    corpus['statistics']['generation_time'] = generation_time
    corpus['statistics']['filtering_applied'] = {
        'tier_filter': args.filter_tiers,
        'max_per_entity': args.max_patterns_per_entity,
        'sample_size': args.sample_size
    }

    # Add tier distribution for final patterns
    final_tier_dist = {}
    for pattern in corpus['patterns']:
        tier = pattern['tier']
        final_tier_dist[tier] = final_tier_dist.get(tier, 0) + 1

    corpus['statistics']['final_tier_distribution'] = final_tier_dist

    # Print statistics
    stats = corpus['statistics']
    print(f"\n=== GENERATION STATISTICS ===")
    print(f"Persons processed: {stats['persons_processed']}")
    print(f"Companies processed: {stats['companies_processed']}")
    print(f"Total patterns generated: {stats['patterns_generated']}")
    print(f"Generation time: {stats['processing_time']:.2f}s")

    print(f"\nTier distribution:")
    for tier in sorted(final_tier_dist.keys()):
        print(f"  Tier {tier}: {final_tier_dist[tier]:,} patterns")

    # Export to file
    print(f"\nExporting to {args.output}...")

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    # Generate statistics summary
    summary_file = args.output.replace('.json', '_summary.txt')
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("HIGH-RECALL AC PATTERNS GENERATION SUMMARY\n")
        f.write("=" * 50 + "\n\n")

        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Generator version: {corpus['generator_version']}\n\n")

        f.write("INPUT DATA:\n")
        f.write(f"  Persons file: {args.persons_file}\n")
        f.write(f"  Companies file: {args.companies_file}\n")
        f.write(f"  Sample size: {args.sample_size or 'Full dataset'}\n\n")

        f.write("PROCESSING:\n")
        f.write(f"  Persons processed: {stats['persons_processed']:,}\n")
        f.write(f"  Companies processed: {stats['companies_processed']:,}\n")
        f.write(f"  Total patterns: {stats['patterns_generated']:,}\n")
        f.write(f"  Processing time: {stats['processing_time']:.2f}s\n")
        f.write(f"  Patterns per second: {stats['patterns_generated'] / stats['processing_time']:.0f}\n\n")

        f.write("TIER DISTRIBUTION:\n")
        for tier in sorted(final_tier_dist.keys()):
            percentage = (final_tier_dist[tier] / stats['patterns_generated']) * 100
            f.write(f"  Tier {tier}: {final_tier_dist[tier]:,} patterns ({percentage:.1f}%)\n")

        f.write(f"\nTIER DESCRIPTIONS:\n")
        f.write(f"  Tier 0: Exact documents/IDs (100% precision)\n")
        f.write(f"  Tier 1: High-precision names/companies\n")
        f.write(f"  Tier 2: Morphological and structured variants\n")
        f.write(f"  Tier 3: Broad recall patterns (requires post-filtering)\n\n")

        f.write(f"OUTPUT FILES:\n")
        f.write(f"  Patterns: {args.output}\n")
        f.write(f"  Summary: {summary_file}\n")

    print(f"Summary written to {summary_file}")

    # Sample patterns for verification
    if args.verbose and corpus['patterns']:
        print(f"\nSample patterns:")
        for i, pattern in enumerate(corpus['patterns'][:10]):
            print(f"  {i+1}. Tier {pattern['tier']}: '{pattern['pattern']}' ({pattern['type']})")

    # Cleanup temp files
    if args.sample_size:
        for temp_file in ["temp_persons_sample.json", "temp_companies_sample.json"]:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    print(f"\n✓ Export completed successfully!")
    print(f"Generated {stats['patterns_generated']:,} patterns in {stats['processing_time']:.2f}s")

    return 0


if __name__ == "__main__":
    sys.exit(main())
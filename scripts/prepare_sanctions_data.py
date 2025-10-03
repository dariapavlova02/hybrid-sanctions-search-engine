#!/usr/bin/env python3
"""
Prepare Sanctions Data Pipeline
===============================

One-click script to prepare all sanctions data for Elasticsearch deployment.

Features:
- Generate AC patterns (high-recall, 4 tiers)
- Generate vector embeddings (384-dim)
- Export templates
- Validation and statistics

Usage:
    # Default (all steps)
    python scripts/prepare_sanctions_data.py

    # Custom output directory
    python scripts/prepare_sanctions_data.py --output-dir ./output

    # Skip vectors (faster)
    python scripts/prepare_sanctions_data.py --skip-vectors

    # Only AC patterns
    python scripts/prepare_sanctions_data.py --patterns-only
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from ai_service.layers.patterns.high_recall_ac_generator import HighRecallACGenerator
from ai_service.layers.variants.template_builder import TemplateBuilder


def print_header(text: str):
    """Print formatted header"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_step(step_num: int, text: str):
    """Print step indicator"""
    print(f"\n🔹 Step {step_num}: {text}")
    print("-" * 50)


def validate_input_files(data_dir: Path) -> Dict[str, Path]:
    """Validate that all required input files exist"""
    print_step(1, "Validating input files")

    files = {
        "persons": data_dir / "sanctioned_persons.json",
        "companies": data_dir / "sanctioned_companies.json",
        "terrorism": data_dir / "terrorism_black_list.json"
    }

    for name, filepath in files.items():
        if not filepath.exists():
            print(f"❌ Missing required file: {filepath}")
            sys.exit(1)

        # Check file size
        size_mb = filepath.stat().st_size / (1024 * 1024)
        print(f"✅ {name:12} {filepath.name:40} ({size_mb:.1f} MB)")

    return files




def generate_ac_patterns(
    files: Dict[str, Path],
    output_dir: Path,
    tier_limits: Optional[str] = None,
    max_patterns: int = 50,
    filter_tiers: Optional[str] = None
) -> Path:
    """Generate AC patterns from sanctions data using generate_full_corpus"""
    print_step(2, "Generating AC patterns")

    # Initialize generator
    print("🔧 Initializing AC pattern generator...")
    generator = HighRecallACGenerator()

    # Apply custom tier limits if provided
    if tier_limits:
        custom_limits = parse_tier_limits(tier_limits)
        generator.tier_limits.update(custom_limits)
        print(f"   Applied custom tier limits: {custom_limits}")

    # Generate full corpus using proper method
    print("⚙️  Generating patterns (this may take a few minutes)...")
    start_time = time.time()

    corpus = generator.generate_full_corpus(
        persons_file=str(files["persons"]),
        companies_file=str(files["companies"]),
        terrorism_file=str(files["terrorism"])
    )

    generation_time = time.time() - start_time

    # Filter by tiers if requested
    if filter_tiers:
        allowed_tiers = set(int(t) for t in filter_tiers.split(','))
        original_count = len(corpus['patterns'])
        corpus['patterns'] = [
            p for p in corpus['patterns']
            if p['tier'] in allowed_tiers
        ]
        print(f"   Filtered to tiers {allowed_tiers}: {original_count} -> {len(corpus['patterns'])} patterns")

    # Limit patterns per entity if requested
    if max_patterns:
        entity_counts = {}
        filtered_patterns = []

        for pattern in corpus['patterns']:
            entity_key = f"{pattern['entity_type']}:{pattern['entity_id']}"
            current_count = entity_counts.get(entity_key, 0)

            if current_count < max_patterns:
                filtered_patterns.append(pattern)
                entity_counts[entity_key] = current_count + 1

        original_count = len(corpus['patterns'])
        corpus['patterns'] = filtered_patterns
        print(f"   Limited patterns per entity to {max_patterns}: {original_count} -> {len(corpus['patterns'])} patterns")

    # Update statistics with final counts
    corpus['statistics']['patterns_generated'] = len(corpus['patterns'])
    corpus['statistics']['generation_time'] = generation_time

    # Calculate final tier distribution
    final_tier_dist = {}
    for pattern in corpus['patterns']:
        tier = pattern['tier']
        final_tier_dist[tier] = final_tier_dist.get(tier, 0) + 1

    corpus['statistics']['final_tier_distribution'] = final_tier_dist

    # Print statistics
    stats = corpus['statistics']
    print(f"\n✅ Generated {len(corpus['patterns']):,} patterns in {stats['processing_time']:.1f}s")
    print(f"   Persons processed:   {stats['persons_processed']:,}")
    print(f"   Companies processed: {stats['companies_processed']:,}")
    print(f"   Terrorism processed: {stats['terrorism_processed']:,}")
    print(f"\n   Tier distribution:")
    for tier in sorted(final_tier_dist.keys()):
        count = final_tier_dist[tier]
        pct = (count / len(corpus['patterns']) * 100) if corpus['patterns'] else 0
        print(f"      Tier {tier}: {count:,} ({pct:.1f}%)")

    # Save patterns with proper structure
    output_file = output_dir / f"ac_patterns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    output_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "generator_version": corpus.get('generator_version', '1.0.0'),
            "total_patterns": len(corpus['patterns']),
            "sources": {
                "persons": stats['persons_processed'],
                "companies": stats['companies_processed'],
                "terrorism": stats['terrorism_processed']
            },
            "tier_distribution": final_tier_dist,
            "generation_time_seconds": stats['processing_time'],
            "filtering_applied": {
                "tier_filter": filter_tiers,
                "max_per_entity": max_patterns
            }
        },
        "patterns": corpus['patterns']
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Saved to: {output_file}")

    return output_file


def parse_tier_limits(tier_limits_str: str) -> dict:
    """Parse tier limits from string format like '0:5,1:10,2:15,3:50'"""
    from ai_service.layers.patterns.high_recall_ac_generator import PatternTier

    if not tier_limits_str:
        return {}

    limits = {}
    for pair in tier_limits_str.split(','):
        tier_str, limit_str = pair.split(':')
        tier = PatternTier(int(tier_str))
        limits[tier] = int(limit_str)

    return limits


def generate_vectors(patterns_file: Path, output_dir: Path) -> Path:
    """Generate vector embeddings from AC patterns"""
    print_step(3, "Generating vector embeddings")

    print("ℹ️  Vector generation requires sentence-transformers")
    print(f"   Input: {patterns_file.name}")
    print("   Running generate_vectors.py script...")

    import subprocess

    # Output file with correct JSON format
    output_file = output_dir / f"vectors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    print(f"\n📊 Generating vectors from AC patterns...")

    try:
        result = subprocess.run([
            sys.executable,
            str(project_root / "scripts" / "generate_vectors.py"),
            "--input", str(patterns_file),  # AC patterns file, not sanctions
            "--output", str(output_file),
            "--max-patterns", "10000"
        ], capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            print(f"✅ Generated: {output_file.name}")
            return output_file
        else:
            print(f"❌ Failed: {result.stderr}")
            return None

    except subprocess.TimeoutExpired:
        print(f"⏱️  Timeout generating vectors")
        return None
    except FileNotFoundError:
        print("⚠️  generate_vectors.py not found, skipping vector generation")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def generate_templates(files: Dict[str, Path], output_dir: Path):
    """Generate templates for additional processing"""
    print_step(4, "Generating templates")

    print("🏗️  Building templates...")

    template_builder = TemplateBuilder()
    templates_dir = output_dir / "templates"
    templates_dir.mkdir(exist_ok=True)

    for entity_type, filepath in files.items():
        print(f"\n   Processing {entity_type}...")

        # Load JSON data inline
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        templates = template_builder.create_batch_templates(data, entity_type=entity_type)

        output_file = templates_dir / f"{entity_type}_templates.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(templates, f, ensure_ascii=False, indent=2)

        print(f"   ✅ {len(templates):,} templates → {output_file.name}")

    print(f"\n💾 Templates saved to: {templates_dir}")


def create_deployment_manifest(
    output_dir: Path,
    patterns_file: Path,
    vector_file: Optional[Path],
    input_files: Dict[str, Path]
):
    """Create deployment manifest with all file paths"""
    print_step(5, "Creating deployment manifest")

    manifest = {
        "created_at": datetime.now().isoformat(),
        "version": "1.0",
        "input_files": {
            name: str(filepath.relative_to(project_root))
            for name, filepath in input_files.items()
        },
        "generated_files": {
            "ac_patterns": str(patterns_file.relative_to(project_root)),
            "vectors": str(vector_file.relative_to(project_root)) if vector_file else None
        },
        "elasticsearch_config": {
            "index_prefix": "sanctions",
            "suggested_indices": [
                "sanctions_ac_patterns",
                "sanctions_vectors"
            ]
        },
        "next_steps": [
            "Review generated files in output directory",
            "Run deploy_to_elasticsearch.py to load data",
            "Verify indices in Elasticsearch",
            "Run warmup queries"
        ]
    }

    manifest_file = output_dir / "deployment_manifest.json"
    with open(manifest_file, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"📋 Deployment manifest: {manifest_file}")

    return manifest_file


def main():
    parser = argparse.ArgumentParser(
        description="Prepare sanctions data for Elasticsearch deployment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--data-dir",
        type=Path,
        default=project_root / "src" / "ai_service" / "data",
        help="Directory containing sanctions JSON files"
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "output" / "sanctions",
        help="Output directory for generated files"
    )

    parser.add_argument(
        "--max-patterns",
        type=int,
        default=50,
        help="Maximum patterns per entity (default: 50)"
    )

    parser.add_argument(
        "--tier-limits",
        help="Custom tier limits in format '0:5,1:10,2:15,3:50'"
    )

    parser.add_argument(
        "--filter-tiers",
        help="Include only specific tiers, e.g., '0,1,2' (default: all tiers)"
    )

    parser.add_argument(
        "--skip-vectors",
        action="store_true",
        help="Skip vector generation (faster)"
    )

    parser.add_argument(
        "--skip-templates",
        action="store_true",
        help="Skip template generation"
    )

    parser.add_argument(
        "--patterns-only",
        action="store_true",
        help="Only generate AC patterns (skip vectors and templates)"
    )

    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print_header("🚀 SANCTIONS DATA PREPARATION PIPELINE")
    print(f"📁 Data directory: {args.data_dir}")
    print(f"📦 Output directory: {args.output_dir}")

    # Step 1: Validate inputs
    input_files = validate_input_files(args.data_dir)

    # Step 2: Generate AC patterns
    patterns_file = generate_ac_patterns(
        input_files,
        args.output_dir,
        tier_limits=args.tier_limits,
        max_patterns=args.max_patterns,
        filter_tiers=args.filter_tiers
    )

    # Step 3: Generate vectors
    vector_file = None
    if not args.skip_vectors and not args.patterns_only:
        vector_file = generate_vectors(patterns_file, args.output_dir)
    else:
        print("\nℹ️  Skipping vector generation")

    # Step 4: Generate templates
    if not args.skip_templates and not args.patterns_only:
        generate_templates(input_files, args.output_dir)
    else:
        print("\nℹ️  Skipping template generation")

    # Step 5: Create deployment manifest
    manifest_file = create_deployment_manifest(
        args.output_dir,
        patterns_file,
        vector_file,
        input_files
    )

    # Summary
    print_header("✅ PREPARATION COMPLETE")
    print(f"📦 Output directory: {args.output_dir}")
    print(f"📋 Deployment manifest: {manifest_file.name}")
    print(f"\n📝 Next steps:")
    print(f"   1. Review generated files in: {args.output_dir}")
    print(f"   2. Load to Elasticsearch:")
    print(f"      python scripts/deploy_to_elasticsearch.py \\")
    print(f"        --manifest {manifest_file}")
    print(f"\n💡 Quick deploy:")
    print(f"   python scripts/deploy_to_elasticsearch.py --es-host localhost:9200")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

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


def load_json_data(filepath: Path) -> List[Dict]:
    """Load and validate JSON data"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            print(f"❌ {filepath.name} must contain a JSON array")
            sys.exit(1)

        if len(data) == 0:
            print(f"⚠️  {filepath.name} is empty")

        return data

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {filepath.name}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading {filepath.name}: {e}")
        sys.exit(1)


def generate_ac_patterns(
    files: Dict[str, Path],
    output_dir: Path,
    tier_limits: Optional[Dict] = None,
    max_patterns: int = 50
) -> Path:
    """Generate AC patterns from sanctions data"""
    print_step(2, "Generating AC patterns")

    # Load data
    print("📂 Loading data...")
    persons = load_json_data(files["persons"])
    companies = load_json_data(files["companies"])
    terrorism = load_json_data(files["terrorism"])

    print(f"   Persons:   {len(persons):,}")
    print(f"   Companies: {len(companies):,}")
    print(f"   Terrorism: {len(terrorism):,}")

    # Initialize generator
    print("\n🔧 Initializing AC pattern generator...")
    generator = HighRecallACGenerator()

    # Generate patterns
    print("⚙️  Generating patterns (this may take a few minutes)...")
    start_time = time.time()

    all_patterns = []

    # Process persons
    print("   👥 Processing persons...")
    for person in persons:
        try:
            patterns = generator.generate_patterns(
                person,
                entity_type="person",
                max_patterns_per_entity=max_patterns
            )
            all_patterns.extend(patterns)
        except Exception as e:
            print(f"   ⚠️  Error processing person {person.get('id')}: {e}")

    # Process companies
    print("   🏢 Processing companies...")
    for company in companies:
        try:
            patterns = generator.generate_patterns(
                company,
                entity_type="company",
                max_patterns_per_entity=max_patterns
            )
            all_patterns.extend(patterns)
        except Exception as e:
            print(f"   ⚠️  Error processing company {company.get('id')}: {e}")

    # Process terrorism
    print("   ⚠️  Processing terrorism list...")
    for entry in terrorism:
        try:
            patterns = generator.generate_patterns(
                entry,
                entity_type="terrorism",
                max_patterns_per_entity=max_patterns
            )
            all_patterns.extend(patterns)
        except Exception as e:
            print(f"   ⚠️  Error processing terrorism entry {entry.get('id')}: {e}")

    elapsed = time.time() - start_time

    # Statistics
    tier_counts = {}
    for pattern in all_patterns:
        tier = pattern.get("tier", -1)
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    print(f"\n✅ Generated {len(all_patterns):,} patterns in {elapsed:.1f}s")
    print(f"   Tier distribution:")
    for tier in sorted(tier_counts.keys()):
        count = tier_counts[tier]
        pct = (count / len(all_patterns) * 100) if all_patterns else 0
        print(f"      Tier {tier}: {count:,} ({pct:.1f}%)")

    # Save patterns
    output_file = output_dir / f"ac_patterns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    output_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_patterns": len(all_patterns),
            "sources": {
                "persons": len(persons),
                "companies": len(companies),
                "terrorism": len(terrorism)
            },
            "tier_distribution": tier_counts,
            "generation_time_seconds": elapsed
        },
        "patterns": all_patterns
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Saved to: {output_file}")

    return output_file


def generate_vectors(files: Dict[str, Path], output_dir: Path) -> Dict[str, Path]:
    """Generate vector embeddings (placeholder - calls external script)"""
    print_step(3, "Generating vector embeddings")

    print("ℹ️  Vector generation requires sentence-transformers")
    print("   Running generate_vectors.py script...")

    import subprocess

    vector_files = {}

    for entity_type, filepath in files.items():
        output_file = output_dir / f"vectors_{entity_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.npy"

        print(f"\n📊 Generating vectors for {entity_type}...")

        try:
            result = subprocess.run([
                sys.executable,
                str(project_root / "scripts" / "generate_vectors.py"),
                "--input", str(filepath),
                "--output", str(output_file)
            ], capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                print(f"✅ Generated: {output_file.name}")
                vector_files[entity_type] = output_file
            else:
                print(f"❌ Failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            print(f"⏱️  Timeout generating vectors for {entity_type}")
        except FileNotFoundError:
            print("⚠️  generate_vectors.py not found, skipping vector generation")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

    return vector_files


def generate_templates(files: Dict[str, Path], output_dir: Path):
    """Generate templates for additional processing"""
    print_step(4, "Generating templates")

    print("🏗️  Building templates...")

    template_builder = TemplateBuilder()
    templates_dir = output_dir / "templates"
    templates_dir.mkdir(exist_ok=True)

    for entity_type, filepath in files.items():
        print(f"\n   Processing {entity_type}...")

        data = load_json_data(filepath)
        templates = template_builder.create_batch_templates(data, entity_type=entity_type)

        output_file = templates_dir / f"{entity_type}_templates.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(templates, f, ensure_ascii=False, indent=2)

        print(f"   ✅ {len(templates):,} templates → {output_file.name}")

    print(f"\n💾 Templates saved to: {templates_dir}")


def create_deployment_manifest(
    output_dir: Path,
    patterns_file: Path,
    vector_files: Dict[str, Path],
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
            "vectors": {
                name: str(filepath.relative_to(project_root))
                for name, filepath in vector_files.items()
            }
        },
        "elasticsearch_config": {
            "index_prefix": "sanctions",
            "suggested_indices": [
                "sanctions_ac_patterns",
                "sanctions_vectors_persons",
                "sanctions_vectors_companies",
                "sanctions_vectors_terrorism"
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
        max_patterns=args.max_patterns
    )

    # Step 3: Generate vectors
    vector_files = {}
    if not args.skip_vectors and not args.patterns_only:
        vector_files = generate_vectors(input_files, args.output_dir)
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
        vector_files,
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

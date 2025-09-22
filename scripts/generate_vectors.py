#!/usr/bin/env python3
"""
Generate vectors from AC patterns for semantic search.
"""

import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("⚠️ sentence-transformers not available, using dummy vectors")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorGenerator:
    """Generate vectors from text patterns."""

    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"):
        self.model_name = model_name
        self.model = None

        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                logger.info(f"Loading model: {model_name}")
                self.model = SentenceTransformer(model_name)
                logger.info("✅ Model loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load model: {e}")
                self.model = None
        else:
            logger.warning("sentence-transformers not available")

    def generate_vector(self, text: str) -> List[float]:
        """Generate vector for a single text."""
        if self.model:
            try:
                embedding = self.model.encode([text])
                return embedding[0].tolist()
            except Exception as e:
                logger.error(f"Failed to generate vector for '{text}': {e}")
                return [0.0] * 384  # Fallback dummy vector

        # Dummy vector for testing
        return [0.1] * 384

    def generate_vectors_from_patterns(self, patterns_file: Path, output_file: Path,
                                     max_patterns: int = 10000, sample_tiers: List[str] = None) -> int:
        """Generate vectors from AC patterns file."""
        if sample_tiers is None:
            sample_tiers = ["tier_0_exact", "tier_1_high", "tier_2_medium"]

        logger.info(f"Generating vectors from {patterns_file}")

        # Load patterns
        with open(patterns_file, 'r', encoding='utf-8') as f:
            patterns_data = json.load(f)

        vectors = []
        pattern_count = 0

        # Process each tier
        for tier_name, patterns in patterns_data.items():
            if tier_name not in sample_tiers:
                continue

            if not isinstance(patterns, list):
                continue

            logger.info(f"Processing tier {tier_name}: {len(patterns)} patterns")

            for pattern_data in patterns:
                if pattern_count >= max_patterns:
                    break

                pattern = pattern_data.get('pattern', '')
                if not pattern or len(pattern) < 2:
                    continue

                # Generate vector
                vector = self.generate_vector(pattern)

                # Create vector entry
                vector_entry = {
                    "name": pattern,
                    "vector": vector,
                    "metadata": {
                        "tier": tier_name,
                        "pattern_type": pattern_data.get('pattern_type', 'unknown'),
                        "source_list": pattern_data.get('source_list', 'unknown'),
                        "original_data": pattern_data
                    }
                }

                vectors.append(vector_entry)
                pattern_count += 1

                if pattern_count % 1000 == 0:
                    logger.info(f"Generated {pattern_count} vectors...")

            if pattern_count >= max_patterns:
                break

        # Save vectors
        logger.info(f"Saving {len(vectors)} vectors to {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(vectors, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ Generated {len(vectors)} vectors")
        return len(vectors)

    def generate_sample_vectors(self, output_file: Path, count: int = 1000) -> int:
        """Generate sample vectors for testing."""
        logger.info(f"Generating {count} sample vectors")

        # Sample names for different categories
        sample_names = {
            "russian_surnames": [
                "иванов", "петров", "сидоров", "козлов", "новиков", "морозов", "попов", "волков",
                "соколов", "лебедев", "семенов", "егоров", "павлов", "кузнецов", "белов"
            ],
            "russian_given": [
                "александр", "михаил", "максим", "артем", "даниил", "дмитрий", "иван", "егор",
                "анна", "мария", "елена", "наталья", "ольга", "татьяна", "ирина", "екатерина"
            ],
            "ukrainian_surnames": [
                "коваленко", "шевченко", "бондаренко", "ткаченко", "кравченко", "полищук",
                "савченко", "мельник", "клименко", "марченко"
            ],
            "companies": [
                "газпром", "сбербанк", "роснефть", "лукойл", "магнит", "мтс", "вебэр",
                "нафтогаз", "укрнафта", "приватбанк", "метінвест"
            ]
        }

        vectors = []

        for category, names in sample_names.items():
            for name in names:
                # Generate variations
                variations = [name, name.upper(), name.title()]

                for variation in variations:
                    if len(vectors) >= count:
                        break

                    vector = self.generate_vector(variation)

                    vector_entry = {
                        "name": variation,
                        "vector": vector,
                        "metadata": {
                            "category": category,
                            "original_form": name,
                            "is_variation": variation != name
                        }
                    }

                    vectors.append(vector_entry)

                if len(vectors) >= count:
                    break

            if len(vectors) >= count:
                break

        # Trim to exact count
        vectors = vectors[:count]

        # Save vectors
        logger.info(f"Saving {len(vectors)} sample vectors to {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(vectors, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ Generated {len(vectors)} sample vectors")
        return len(vectors)

async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate vectors from AC patterns")
    parser.add_argument("--input", type=Path, help="Input AC patterns file")
    parser.add_argument("--output", type=Path, help="Output vectors file")
    parser.add_argument("--max-patterns", type=int, default=10000, help="Maximum patterns to process")
    parser.add_argument("--sample", action="store_true", help="Generate sample vectors instead")
    parser.add_argument("--model", default="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
                       help="Model name for embeddings")

    args = parser.parse_args()

    generator = VectorGenerator(args.model)

    if args.sample:
        # Generate sample vectors
        output_file = args.output or Path("data/templates/sample_vectors.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        count = generator.generate_sample_vectors(output_file, args.max_patterns)
        print(f"✅ Generated {count} sample vectors in {output_file}")

    elif args.input and args.output:
        # Generate vectors from patterns file
        args.output.parent.mkdir(parents=True, exist_ok=True)
        count = generator.generate_vectors_from_patterns(args.input, args.output, args.max_patterns)
        print(f"✅ Generated {count} vectors from {args.input} → {args.output}")

    else:
        # Generate vectors for all available pattern files
        data_dir = Path("data/templates")

        pattern_files = [
            ("person_ac_export.json", "person_vectors.json"),
            ("company_ac_export.json", "company_vectors.json"),
            ("terrorism_ac_export.json", "terrorism_vectors.json")
        ]

        for input_filename, output_filename in pattern_files:
            input_file = data_dir / input_filename
            output_file = data_dir / output_filename

            if input_file.exists():
                count = generator.generate_vectors_from_patterns(input_file, output_file, args.max_patterns)
                print(f"✅ Generated {count} vectors: {input_filename} → {output_filename}")
            else:
                print(f"⚠️ Input file not found: {input_file}")

        # Also generate sample vectors
        sample_output = data_dir / "sample_vectors.json"
        count = generator.generate_sample_vectors(sample_output, 1000)
        print(f"✅ Generated {count} sample vectors in {sample_output}")

if __name__ == "__main__":
    asyncio.run(main())
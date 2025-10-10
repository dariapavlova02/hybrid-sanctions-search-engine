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
    print("[WARN] sentence-transformers not available, using dummy vectors")

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
                logger.info("[OK] Model loaded successfully")
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

    def generate_vectors_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate vectors for multiple texts in batches (faster)."""
        if not self.model:
            return [[0.1] * 384 for _ in texts]

        try:
            embeddings = self.model.encode(texts, batch_size=batch_size, show_progress_bar=True)
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            logger.error(f"Failed to generate batch vectors: {e}")
            return [[0.0] * 384 for _ in texts]

    def generate_vectors_from_patterns(self, patterns_file: Path, output_file: Path,
                                     max_patterns: int = 10000, sample_tiers: List[int] = None) -> int:
        """Generate vectors from AC patterns file (new format with metadata)."""
        if sample_tiers is None:
            sample_tiers = [0, 1, 2]  # Tier 0, 1, 2 only (skip tier 3 for vectors)

        logger.info(f"Generating vectors from {patterns_file}")

        # Load patterns (new format: {"metadata": {...}, "patterns": [...]})
        with open(patterns_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract patterns array
        patterns_list = data.get('patterns', [])
        logger.info(f"Loaded {len(patterns_list)} total patterns")

        # Collect patterns for batch processing
        patterns_to_process = []
        tier_counts = {tier: 0 for tier in sample_tiers}

        for pattern_data in patterns_list:
            if len(patterns_to_process) >= max_patterns:
                break

            tier = pattern_data.get('tier')
            if tier not in sample_tiers:
                continue

            pattern = pattern_data.get('pattern', '')
            if not pattern or len(pattern) < 2:
                continue

            patterns_to_process.append({
                'text': pattern,
                'metadata': {
                    "tier": tier,
                    "pattern_type": pattern_data.get('type', 'unknown'),
                    "entity_id": pattern_data.get('entity_id', ''),
                    "entity_type": pattern_data.get('entity_type', 'unknown'),
                    "confidence": pattern_data.get('confidence', 0.0),
                    "canonical": pattern_data.get('canonical', pattern)
                }
            })
            tier_counts[tier] += 1

        logger.info(f"Collected {len(patterns_to_process)} patterns for vectorization")
        logger.info(f"Tier distribution: {tier_counts}")

        # Generate vectors in batches (much faster!)
        texts = [p['text'] for p in patterns_to_process]
        logger.info(f"Generating vectors in batches...")

        embeddings = self.generate_vectors_batch(texts, batch_size=64)

        # Create vector entries
        vectors = []
        for pattern_info, embedding in zip(patterns_to_process, embeddings):
            vector_entry = {
                "name": pattern_info['text'],
                "vector": embedding,
                "metadata": pattern_info['metadata']
            }
            vectors.append(vector_entry)

        # Save vectors
        logger.info(f"Saving {len(vectors)} vectors to {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(vectors, f, ensure_ascii=False, indent=2)

        logger.info(f"[OK] Generated {len(vectors)} vectors")
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

        logger.info(f"[OK] Generated {len(vectors)} sample vectors")
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
        print(f"[OK] Generated {count} sample vectors in {output_file}")

    elif args.input and args.output:
        # Generate vectors from patterns file
        args.output.parent.mkdir(parents=True, exist_ok=True)
        count = generator.generate_vectors_from_patterns(args.input, args.output, args.max_patterns)
        print(f"[OK] Generated {count} vectors from {args.input} → {args.output}")

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
                print(f"[OK] Generated {count} vectors: {input_filename} → {output_filename}")
            else:
                print(f"[WARN] Input file not found: {input_file}")

        # Also generate sample vectors
        sample_output = data_dir / "sample_vectors.json"
        count = generator.generate_sample_vectors(sample_output, 1000)
        print(f"[OK] Generated {count} sample vectors in {sample_output}")

if __name__ == "__main__":
    asyncio.run(main())
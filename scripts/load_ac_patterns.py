#!/usr/bin/env python3
"""
Script to load AC patterns into Elasticsearch for high-performance search.
"""

import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Any
import sys
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_service.layers.search.elasticsearch_client import ElasticsearchClient
from ai_service.config.settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ACPatternLoader:
    """Loads AC patterns into Elasticsearch for fast search."""

    def __init__(self, es_client: ElasticsearchClient):
        self.es_client = es_client
        self.patterns_dir = Path(__file__).parent.parent / "data" / "templates"

    async def create_patterns_index(self, index_name: str) -> bool:
        """Create optimized index for AC patterns."""

        index_config = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "pattern_analyzer": {
                            "type": "custom",
                            "tokenizer": "keyword",
                            "filter": ["lowercase"]
                        },
                        "pattern_search": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "asciifolding"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "pattern": {
                        "type": "text",
                        "analyzer": "pattern_analyzer",
                        "search_analyzer": "pattern_search",
                        "fields": {
                            "exact": {
                                "type": "keyword"
                            },
                            "prefix": {
                                "type": "text",
                                "analyzer": "pattern_analyzer",
                                "search_analyzer": "pattern_search"
                            }
                        }
                    },
                    "pattern_type": {
                        "type": "keyword"
                    },
                    "tier": {
                        "type": "keyword"
                    },
                    "category": {
                        "type": "keyword"
                    },
                    "source_list": {
                        "type": "keyword"
                    },
                    "confidence": {
                        "type": "float"
                    },
                    "metadata": {
                        "type": "object",
                        "enabled": false
                    }
                }
            }
        }

        try:
            # Delete index if exists
            if await self.es_client.client.indices.exists(index=index_name):
                await self.es_client.client.indices.delete(index=index_name)
                logger.info(f"Deleted existing index: {index_name}")

            # Create new index
            await self.es_client.client.indices.create(
                index=index_name,
                body=index_config
            )
            logger.info(f"Created index: {index_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {e}")
            return False

    async def load_pattern_file(self, file_path: Path, category: str, index_name: str) -> int:
        """Load patterns from a single file."""

        logger.info(f"Loading patterns from {file_path.name} into {index_name}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            total_loaded = 0

            # Process each tier
            for tier_name, patterns in data.items():
                if not isinstance(patterns, list):
                    continue

                logger.info(f"Processing tier {tier_name}: {len(patterns)} patterns")

                # Prepare bulk documents
                docs = []
                for pattern_data in patterns:
                    if not isinstance(pattern_data, dict):
                        continue

                    pattern = pattern_data.get('pattern', '')
                    if not pattern:
                        continue

                    doc = {
                        "pattern": pattern,
                        "pattern_type": pattern_data.get('pattern_type', 'unknown'),
                        "tier": tier_name,
                        "category": category,
                        "source_list": pattern_data.get('source_list', 'unknown'),
                        "confidence": self._tier_to_confidence(tier_name),
                        "metadata": {
                            k: v for k, v in pattern_data.items()
                            if k not in ['pattern', 'pattern_type', 'source_list']
                        }
                    }
                    docs.append(doc)

                # Bulk index in chunks
                chunk_size = 1000
                for i in range(0, len(docs), chunk_size):
                    chunk = docs[i:i + chunk_size]

                    # Prepare bulk request
                    bulk_body = []
                    for doc in chunk:
                        bulk_body.append({"index": {"_index": index_name}})
                        bulk_body.append(doc)

                    # Execute bulk request
                    try:
                        response = await self.es_client.client.bulk(body=bulk_body)

                        # Check for errors
                        if response.get('errors'):
                            errors = [item for item in response['items'] if 'error' in item.get('index', {})]
                            logger.warning(f"Bulk indexing errors: {len(errors)}")
                            for error in errors[:5]:  # Show first 5 errors
                                logger.warning(f"Error: {error}")

                        total_loaded += len(chunk)
                        logger.info(f"Indexed {total_loaded}/{len(docs)} patterns from {tier_name}")

                    except Exception as e:
                        logger.error(f"Bulk indexing failed for chunk {i//chunk_size}: {e}")

            logger.info(f"Successfully loaded {total_loaded} patterns from {file_path.name}")
            return total_loaded

        except Exception as e:
            logger.error(f"Failed to load patterns from {file_path}: {e}")
            return 0

    def _tier_to_confidence(self, tier_name: str) -> float:
        """Convert tier name to confidence score."""
        tier_mapping = {
            'tier_0_exact': 1.0,
            'tier_1_high': 0.9,
            'tier_2_medium': 0.7,
            'tier_3_low': 0.5,
            'tier_4_experimental': 0.3
        }
        return tier_mapping.get(tier_name, 0.5)

    async def load_all_patterns(self) -> Dict[str, int]:
        """Load all AC pattern files into Elasticsearch."""

        pattern_files = [
            ("person_ac_export.json", "person", "ac_patterns_person"),
            ("company_ac_export.json", "company", "ac_patterns_company"),
            ("terrorism_ac_export.json", "terrorism", "ac_patterns_terrorism")
        ]

        results = {}

        for filename, category, index_name in pattern_files:
            file_path = self.patterns_dir / filename

            if not file_path.exists():
                logger.warning(f"Pattern file not found: {file_path}")
                results[category] = 0
                continue

            # Create index
            if not await self.create_patterns_index(index_name):
                results[category] = 0
                continue

            # Load patterns
            count = await self.load_pattern_file(file_path, category, index_name)
            results[category] = count

            # Refresh index to make documents searchable
            try:
                await self.es_client.client.indices.refresh(index=index_name)
                logger.info(f"Refreshed index: {index_name}")
            except Exception as e:
                logger.warning(f"Failed to refresh index {index_name}: {e}")

        return results

    async def verify_patterns(self) -> Dict[str, Any]:
        """Verify that patterns were loaded correctly."""

        indices = ["ac_patterns_person", "ac_patterns_company", "ac_patterns_terrorism"]
        results = {}

        for index_name in indices:
            try:
                # Get index stats
                stats = await self.es_client.client.cat.count(index=index_name, format="json")
                count = int(stats[0]['count']) if stats else 0

                # Sample some patterns
                search_result = await self.es_client.client.search(
                    index=index_name,
                    body={
                        "size": 3,
                        "query": {"match_all": {}},
                        "sort": [{"confidence": {"order": "desc"}}]
                    }
                )

                samples = [hit['_source'] for hit in search_result['hits']['hits']]

                results[index_name] = {
                    "count": count,
                    "samples": samples
                }

                logger.info(f"Index {index_name}: {count} patterns")

            except Exception as e:
                logger.error(f"Failed to verify index {index_name}: {e}")
                results[index_name] = {"count": 0, "error": str(e)}

        return results

async def main():
    """Main function to load AC patterns."""

    logger.info("🚀 Starting AC patterns loading into Elasticsearch")

    try:
        # Initialize settings and ES client
        settings = get_settings()
        es_client = ElasticsearchClient()

        # Test connection
        logger.info("Testing Elasticsearch connection...")
        if not await es_client.health_check():
            logger.error("❌ Elasticsearch connection failed")
            return 1

        logger.info("✅ Elasticsearch connection successful")

        # Initialize loader
        loader = ACPatternLoader(es_client)

        # Load all patterns
        logger.info("📥 Loading AC patterns...")
        results = await loader.load_all_patterns()

        # Print results
        total_patterns = sum(results.values())
        logger.info(f"📊 Loading completed: {total_patterns} total patterns")
        for category, count in results.items():
            logger.info(f"  - {category}: {count:,} patterns")

        # Verify loading
        logger.info("🔍 Verifying pattern loading...")
        verification = await loader.verify_patterns()

        for index_name, info in verification.items():
            if 'error' in info:
                logger.error(f"❌ {index_name}: {info['error']}")
            else:
                logger.info(f"✅ {index_name}: {info['count']:,} patterns verified")
                if info['samples']:
                    logger.info(f"   Sample patterns: {[s['pattern'] for s in info['samples'][:3]]}")

        logger.info("🎉 AC patterns loading completed successfully!")
        return 0

    except Exception as e:
        logger.error(f"❌ Failed to load AC patterns: {e}")
        return 1

    finally:
        if 'es_client' in locals():
            await es_client.close()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
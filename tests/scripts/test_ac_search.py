#!/usr/bin/env python3
"""
Test script for AC pattern search in Elasticsearch.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_service.layers.search.elasticsearch_client import ElasticsearchClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ACSearchTester:
    """Test AC pattern search functionality."""

    def __init__(self, es_client: ElasticsearchClient):
        self.es_client = es_client

    async def search_patterns(self, query: str, index_name: str, min_confidence: float = 0.5) -> List[Dict[str, Any]]:
        """Search for patterns matching the query."""

        search_body = {
            "size": 10,
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["pattern^2", "pattern.prefix"],
                                "type": "best_fields",
                                "fuzziness": "AUTO"
                            }
                        }
                    ],
                    "filter": [
                        {
                            "range": {
                                "confidence": {
                                    "gte": min_confidence
                                }
                            }
                        }
                    ]
                }
            },
            "sort": [
                {"confidence": {"order": "desc"}},
                {"_score": {"order": "desc"}}
            ],
            "highlight": {
                "fields": {
                    "pattern": {}
                }
            }
        }

        try:
            result = await self.es_client.client.search(
                index=index_name,
                body=search_body
            )

            hits = []
            for hit in result['hits']['hits']:
                source = hit['_source']
                source['_score'] = hit['_score']
                source['_highlight'] = hit.get('highlight', {})
                hits.append(source)

            return hits

        except Exception as e:
            logger.error(f"Search failed for '{query}' in {index_name}: {e}")
            return []

    async def test_search_scenarios(self):
        """Test various search scenarios."""

        test_cases = [
            # Person searches
            ("person", "ac_patterns_person", [
                "ivanov", "иванов", "petrov", "петров", "smith", "garcia"
            ]),
            # Company searches
            ("company", "ac_patterns_company", [
                "gazprom", "газпром", "sberbank", "сбербанк", "microsoft", "apple"
            ]),
            # Terrorism searches
            ("terrorism", "ac_patterns_terrorism", [
                "taliban", "талибан", "hamas", "хамас"
            ])
        ]

        for category, index_name, queries in test_cases:
            logger.info(f"\n[CHECK] Testing {category} patterns in {index_name}")

            for query in queries:
                logger.info(f"\n  Query: '{query}'")

                # Test with different confidence levels
                for min_conf in [0.9, 0.7, 0.5]:
                    results = await self.search_patterns(query, index_name, min_conf)

                    if results:
                        logger.info(f"    Confidence ≥ {min_conf}: {len(results)} matches")
                        # Show top 3 results
                        for i, result in enumerate(results[:3]):
                            pattern = result['pattern']
                            confidence = result['confidence']
                            tier = result['tier']
                            score = result['_score']

                            logger.info(f"      {i+1}. '{pattern}' (tier={tier}, conf={confidence:.2f}, score={score:.2f})")

                        break  # Found results, no need to try lower confidence
                    else:
                        if min_conf == 0.5:
                            logger.info(f"    No matches found")

    async def get_index_stats(self):
        """Get statistics for all AC pattern indices."""

        indices = ["ac_patterns_person", "ac_patterns_company", "ac_patterns_terrorism"]

        logger.info("\n[STATS] Index Statistics:")

        for index_name in indices:
            try:
                # Get count
                stats = await self.es_client.client.cat.count(index=index_name, format="json")
                count = int(stats[0]['count']) if stats else 0

                # Get tier distribution
                agg_result = await self.es_client.client.search(
                    index=index_name,
                    body={
                        "size": 0,
                        "aggs": {
                            "tiers": {
                                "terms": {
                                    "field": "tier",
                                    "size": 10
                                }
                            },
                            "confidence_stats": {
                                "stats": {
                                    "field": "confidence"
                                }
                            }
                        }
                    }
                )

                tier_distribution = {
                    bucket['key']: bucket['doc_count']
                    for bucket in agg_result['aggregations']['tiers']['buckets']
                }

                conf_stats = agg_result['aggregations']['confidence_stats']

                logger.info(f"\n  📋 {index_name}:")
                logger.info(f"    Total patterns: {count:,}")
                logger.info(f"    Tier distribution:")
                for tier, tier_count in tier_distribution.items():
                    logger.info(f"      {tier}: {tier_count:,}")
                logger.info(f"    Confidence: avg={conf_stats['avg']:.2f}, min={conf_stats['min']:.2f}, max={conf_stats['max']:.2f}")

            except Exception as e:
                logger.error(f"Failed to get stats for {index_name}: {e}")

async def main():
    """Main test function."""

    logger.info("🧪 Starting AC pattern search tests")

    try:
        # Initialize ES client
        es_client = ElasticsearchClient()

        # Test connection
        if not await es_client.health_check():
            logger.error("[ERROR] Elasticsearch connection failed")
            return 1

        logger.info("[OK] Elasticsearch connection successful")

        # Initialize tester
        tester = ACSearchTester(es_client)

        # Get index statistics
        await tester.get_index_stats()

        # Test search scenarios
        await tester.test_search_scenarios()

        logger.info("\n🎉 AC pattern search tests completed!")
        return 0

    except Exception as e:
        logger.error(f"[ERROR] Test failed: {e}")
        return 1

    finally:
        if 'es_client' in locals():
            await es_client.close()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
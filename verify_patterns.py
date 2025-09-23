#!/usr/bin/env python3
"""
Verify AC patterns deployment in Elasticsearch
"""

import json
import requests
from typing import Dict

def check_patterns_deployment(es_url="http://95.217.84.234:9200"):
    """Check deployment status and statistics"""

    print("🔍 Verifying AC patterns deployment...")
    print("=" * 50)

    # 1. Check total count
    resp = requests.get(f"{es_url}/ac_patterns/_count")
    total_count = resp.json()["count"]
    expected_count = 957978

    print(f"📊 Total patterns: {total_count:,}")
    print(f"📋 Expected: {expected_count:,}")
    print(f"📈 Progress: {(total_count/expected_count)*100:.1f}%")
    print()

    # 2. Check tier distribution
    tier_query = {
        "size": 0,
        "aggs": {
            "tiers": {
                "terms": {
                    "field": "tier",
                    "size": 10
                }
            }
        }
    }

    resp = requests.post(f"{es_url}/ac_patterns/_search", json=tier_query)
    buckets = resp.json()["aggregations"]["tiers"]["buckets"]

    print("🏷️  Tier distribution:")
    for bucket in sorted(buckets, key=lambda x: int(x["key"])):
        tier = bucket["key"]
        count = bucket["doc_count"]
        print(f"  Tier {tier}: {count:,} patterns")
    print()

    # 3. Check pattern types
    type_query = {
        "size": 0,
        "aggs": {
            "types": {
                "terms": {
                    "field": "pattern_type",
                    "size": 15
                }
            }
        }
    }

    resp = requests.post(f"{es_url}/ac_patterns/_search", json=type_query)
    type_buckets = resp.json()["aggregations"]["types"]["buckets"]

    print("🔧 Pattern types:")
    for bucket in sorted(type_buckets, key=lambda x: x["doc_count"], reverse=True)[:10]:
        pattern_type = bucket["key"]
        count = bucket["doc_count"]
        print(f"  {pattern_type}: {count:,}")
    print()

    # 4. Check languages
    lang_query = {
        "size": 0,
        "aggs": {
            "languages": {
                "terms": {
                    "field": "language",
                    "size": 10
                }
            }
        }
    }

    resp = requests.post(f"{es_url}/ac_patterns/_search", json=lang_query)
    result = resp.json()
    lang_buckets = result.get("aggregations", {}).get("languages", {}).get("buckets", [])

    print("🌐 Language distribution:")
    for bucket in sorted(lang_buckets, key=lambda x: x["doc_count"], reverse=True):
        language = bucket["key"]
        count = bucket["doc_count"]
        print(f"  {language}: {count:,}")
    print()

    # 5. Sample patterns by tier
    print("🔍 Sample patterns by tier:")
    for tier in [0, 1, 2, 3]:
        sample_query = {
            "size": 2,
            "query": {"term": {"tier": tier}},
            "_source": ["pattern", "pattern_type", "language"]
        }

        resp = requests.post(f"{es_url}/ac_patterns/_search", json=sample_query)
        hits = resp.json()["hits"]["hits"]

        print(f"  Tier {tier} samples:")
        for hit in hits:
            source = hit["_source"]
            pattern = source["pattern"][:50] + ("..." if len(source["pattern"]) > 50 else "")
            print(f"    '{pattern}' ({source['pattern_type']}, {source['language']})")
    print()

    # 6. Final status
    if total_count >= expected_count * 0.95:
        print("✅ Deployment SUCCESS!")
        print(f"📊 {total_count:,} patterns uploaded successfully")
        return True
    else:
        print("⚠️  Deployment INCOMPLETE")
        print(f"📊 Only {total_count:,}/{expected_count:,} patterns uploaded")
        return False

if __name__ == "__main__":
    check_patterns_deployment()
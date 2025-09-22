#!/usr/bin/env python3
"""
Load AC patterns from person_ac_export.json into Elasticsearch

Usage:
    python load_ac_patterns.py
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
import requests


class ACPatternLoader:
    """Load AC patterns into Elasticsearch"""

    def __init__(self):
        self.es_url = "http://localhost:9200"
        self.index_name = "watchlist_persons_current"
        self.patterns_file = Path("data/templates/person_ac_export.json")

    def load_patterns(self):
        """Load all patterns from the JSON file into Elasticsearch"""
        print(f"Loading patterns from {self.patterns_file}")

        if not self.patterns_file.exists():
            print(f"Error: Pattern file not found: {self.patterns_file}")
            return False

        # Load patterns
        with open(self.patterns_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Process each tier
        total_loaded = 0
        for tier_name, patterns in data.items():
            if not patterns:
                continue

            print(f"Loading {len(patterns)} patterns from {tier_name}")
            success_count = self._load_tier_patterns(tier_name, patterns)
            total_loaded += success_count
            print(f"Successfully loaded {success_count}/{len(patterns)} patterns from {tier_name}")

        print(f"Total patterns loaded: {total_loaded}")
        return True

    def _load_tier_patterns(self, tier_name: str, patterns: List[Dict[str, Any]]) -> int:
        """Load patterns from a specific tier using bulk API with batching"""
        batch_size = 1000  # Process in smaller batches
        total_success = 0

        for batch_start in range(0, len(patterns), batch_size):
            batch_end = min(batch_start + batch_size, len(patterns))
            batch_patterns = patterns[batch_start:batch_end]

            print(f"  Processing batch {batch_start//batch_size + 1}/{(len(patterns) + batch_size - 1)//batch_size}")

            bulk_actions = []
            for i, pattern_data in enumerate(batch_patterns):
                doc_id = f"{tier_name}_{batch_start + i}"

                # Create index action
                action = {
                    "index": {
                        "_index": self.index_name,
                        "_id": doc_id
                    }
                }

                # Create document
                doc = {
                    "entity_id": doc_id,
                    "entity_type": "person",
                    "normalized_name": pattern_data["pattern"],
                    "name_text": pattern_data["pattern"],
                    "name_ngrams": pattern_data["pattern"],
                    "pattern_type": pattern_data["pattern_type"],
                    "recall_tier": pattern_data["recall_tier"],
                    "tier_name": tier_name,
                    "meta": {
                        "loaded_at": "2025-09-22",
                        "source": "person_ac_export.json"
                    }
                }

                bulk_actions.append(json.dumps(action))
                bulk_actions.append(json.dumps(doc))

            # Send bulk request for this batch
            if not bulk_actions:
                continue

            bulk_body = "\n".join(bulk_actions) + "\n"

            try:
                response = requests.post(
                    f"{self.es_url}/_bulk",
                    data=bulk_body,
                    headers={"Content-Type": "application/x-ndjson"},
                    timeout=60
                )

                if response.status_code == 200:
                    result = response.json()
                    errors = []
                    batch_success = 0

                    for item in result.get("items", []):
                        if "index" in item:
                            if item["index"].get("status") in [200, 201]:
                                batch_success += 1
                            else:
                                errors.append(item["index"].get("error", "Unknown error"))

                    if errors:
                        print(f"    Batch errors: {len(errors)} errors")

                    total_success += batch_success
                    print(f"    Batch loaded: {batch_success}/{len(batch_patterns)}")
                else:
                    print(f"    Batch failed: {response.status_code} - {response.text[:200]}")

            except Exception as e:
                print(f"    Error during batch load: {e}")

        return total_success

    def verify_load(self):
        """Verify that patterns were loaded correctly"""
        try:
            response = requests.get(f"{self.es_url}/{self.index_name}/_count")
            if response.status_code == 200:
                count = response.json()["count"]
                print(f"Index {self.index_name} contains {count} documents")

                # Sample search
                search_response = requests.post(
                    f"{self.es_url}/{self.index_name}/_search",
                    json={
                        "size": 3,
                        "query": {"match_all": {}},
                        "sort": [{"_id": "asc"}]
                    }
                )

                if search_response.status_code == 200:
                    hits = search_response.json()["hits"]["hits"]
                    print(f"Sample documents:")
                    for hit in hits:
                        source = hit["_source"]
                        print(f"  - {source['normalized_name']} ({source['pattern_type']})")

                return True
            else:
                print(f"Failed to verify load: {response.status_code}")
                return False

        except Exception as e:
            print(f"Error during verification: {e}")
            return False

def main():
    """Main function"""
    loader = ACPatternLoader()

    success = loader.load_patterns()
    if success:
        loader.verify_load()
        print("AC patterns loaded successfully!")
    else:
        print("Failed to load AC patterns")
        sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Check AC index mapping and field structure
"""

import requests
import json

def check_ac_index_mapping():
    """Check the mapping and sample documents in AC indices"""

    print("🔍 CHECKING AC INDEX MAPPING")
    print("=" * 60)

    es_host = "http://95.217.84.234:9200"
    indices = ["ac_patterns", "ai_service_ac_patterns"]

    for index_name in indices:
        print(f"\n📋 INDEX: {index_name}")

        try:
            # Get index mapping
            mapping_response = requests.get(f"{es_host}/{index_name}/_mapping", timeout=10)

            if mapping_response.status_code == 200:
                mapping = mapping_response.json()
                print(f"   ✅ Mapping retrieved")

                # Show field structure
                index_mapping = mapping.get(index_name, {}).get('mappings', {}).get('properties', {})
                print(f"   📝 Fields:")
                for field, props in index_mapping.items():
                    field_type = props.get('type', 'unknown')
                    print(f"      - {field}: {field_type}")
                    if 'fields' in props:
                        for subfield, subprops in props['fields'].items():
                            subtype = subprops.get('type', 'unknown')
                            print(f"        - {field}.{subfield}: {subtype}")

            # Get a sample document to see structure
            sample_response = requests.post(
                f"{es_host}/{index_name}/_search",
                json={
                    "query": {"match_all": {}},
                    "size": 1
                },
                timeout=10
            )

            if sample_response.status_code == 200:
                sample_result = sample_response.json()
                hits = sample_result.get('hits', {}).get('hits', [])

                if hits:
                    sample_doc = hits[0].get('_source', {})
                    print(f"   📄 Sample document structure:")
                    for key, value in sample_doc.items():
                        if isinstance(value, str) and len(value) > 50:
                            value = value[:50] + "..."
                        print(f"      - {key}: {value}")

            # Test specific Ulianova search
            ulianova_search = requests.post(
                f"{es_host}/{index_name}/_search",
                json={
                    "query": {
                        "bool": {
                            "should": [
                                {"match": {"pattern": "Ulianova Liudmyla"}},
                                {"match": {"text": "Ulianova Liudmyla"}},
                                {"match": {"content": "Ulianova Liudmyla"}},
                                {"match_all": {}}
                            ]
                        }
                    },
                    "query_string": {
                        "query": "*Ulianova*",
                        "fields": ["*"]
                    },
                    "size": 5
                },
                timeout=10
            )

            if ulianova_search.status_code == 200:
                search_result = ulianova_search.json()
                hits = search_result.get('hits', {}).get('hits', [])
                print(f"   🎯 Ulianova search results: {len(hits)}")

                for hit in hits:
                    source = hit.get('_source', {})
                    score = hit.get('_score', 0)
                    print(f"      Score {score}: {source}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

def main():
    check_ac_index_mapping()

    print(f"\n🎯 NEXT STEP:")
    print("   Check if field name mismatch is causing search issues")

if __name__ == "__main__":
    main()
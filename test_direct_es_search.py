#!/usr/bin/env python3

import json
import subprocess

def test_direct_elasticsearch_search():
    """Test search functionality directly against Elasticsearch"""

    print("🔍 Testing search functionality directly against Elasticsearch")
    print("This bypasses the AI service completely to test if patterns work")

    # Elasticsearch connection details
    ES_HOST = "95.217.84.234"
    ES_PORT = 9200
    ES_USER = "elastic"
    ES_PASSWORD = "AiServiceElastic2024!"
    ES_INDEX = "ai_service_ac_patterns"

    # Test queries to search for
    test_queries = [
        ("порошенко петро", "Poroshenko partial pattern (lowercase)"),
        ("Порошенко Петро", "Poroshenko partial pattern (capitalized)"),
        ("петро порошенко", "Poroshenko reversed order"),
        ("ПОРОШЕНКО ПЕТРО", "Poroshenko uppercase"),
        ("порошенко", "Poroshenko surname only"),
        ("петро", "Petro firstname only"),
        ("Poroshenko Petro", "Poroshenko Latin"),
        ("John Smith", "English test name")
    ]

    print(f"\n📊 Testing {len(test_queries)} search queries...")

    for query, description in test_queries:
        print(f"\n🔍 Testing: '{query}' ({description})")

        # Create Elasticsearch search query
        es_query = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "match": {
                                "pattern": {
                                    "query": query,
                                    "fuzziness": "AUTO"
                                }
                            }
                        },
                        {
                            "wildcard": {
                                "pattern": {
                                    "value": f"*{query.lower()}*",
                                    "case_insensitive": True
                                }
                            }
                        },
                        {
                            "term": {
                                "pattern": query.lower()
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            },
            "size": 5,
            "sort": [
                {"confidence": {"order": "desc"}},
                "_score"
            ]
        }

        # Write query to temp file
        with open('es_search_query.json', 'w', encoding='utf-8') as f:
            json.dump(es_query, f, ensure_ascii=False, indent=2)

        # Execute search via curl
        curl_cmd = [
            'curl', '-s', '-X', 'GET',
            f'{ES_HOST}:{ES_PORT}/{ES_INDEX}/_search',
            '-u', f'{ES_USER}:{ES_PASSWORD}',
            '-H', 'Content-Type: application/json',
            '--data-binary', '@es_search_query.json'
        ]

        try:
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                try:
                    response = json.loads(result.stdout)

                    if 'error' in response:
                        print(f"  ❌ Elasticsearch error: {response['error']}")
                        continue

                    hits = response.get('hits', {})
                    total_hits = hits.get('total', {}).get('value', 0)
                    search_hits = hits.get('hits', [])

                    print(f"  📊 Total hits: {total_hits}")

                    if total_hits > 0:
                        print(f"  🎯 Top results:")
                        for i, hit in enumerate(search_hits):
                            source = hit.get('_source', {})
                            pattern = source.get('pattern', 'N/A')
                            pattern_type = source.get('pattern_type', 'unknown')
                            confidence = source.get('confidence', 'N/A')
                            tier = source.get('tier', 'N/A')
                            canonical = source.get('canonical', 'N/A')
                            score = hit.get('_score', 'N/A')

                            print(f"    {i+1}. '{pattern}' -> '{canonical}'")
                            print(f"       Type: {pattern_type}, Tier: {tier}, Confidence: {confidence}, Score: {score}")

                        # Check for partial match patterns specifically
                        partial_matches = [h for h in search_hits if h.get('_source', {}).get('pattern_type') == 'partial_match']
                        if partial_matches:
                            print(f"  ✅ Found {len(partial_matches)} partial match patterns!")
                        else:
                            print(f"  ⚠️ No partial match patterns found")

                    else:
                        print(f"  ⚠️ No results found")

                except json.JSONDecodeError as e:
                    print(f"  ❌ Error parsing response: {e}")
                    print(f"  Raw response: {result.stdout[:200]}...")
                except Exception as e:
                    print(f"  ❌ Error processing response: {e}")
            else:
                print(f"  ❌ curl failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            print(f"  ❌ Request timed out")
        except Exception as e:
            print(f"  ❌ Error executing search: {e}")

    # Clean up temp file
    try:
        import os
        if os.path.exists('es_search_query.json'):
            os.remove('es_search_query.json')
    except:
        pass

    print("\n📈 Index Statistics:")
    # Get index statistics
    stats_cmd = [
        'curl', '-s', '-X', 'GET',
        f'{ES_HOST}:{ES_PORT}/{ES_INDEX}/_count',
        '-u', f'{ES_USER}:{ES_PASSWORD}'
    ]

    try:
        result = subprocess.run(stats_cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            response = json.loads(result.stdout)
            total_docs = response.get('count', 'unknown')
            print(f"  📊 Total patterns in index: {total_docs}")
        else:
            print(f"  ❌ Could not get index stats")
    except Exception as e:
        print(f"  ❌ Error getting stats: {e}")

    print("\n💡 Summary:")
    print("✅ Direct Elasticsearch testing completed")
    print("🔧 This verifies if our uploaded patterns are working")
    print("📋 If patterns are found here but not in AI service, the issue is the Python import problem")

if __name__ == "__main__":
    test_direct_elasticsearch_search()
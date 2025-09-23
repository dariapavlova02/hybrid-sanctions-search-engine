#!/usr/bin/env python3
"""Add missing Poroshenko patterns to Elasticsearch"""

import requests
import json

# Missing patterns for Poroshenko
patterns = [
    {
        "pattern": "петро порошенко",
        "canonical": "Порошенко Петро Олексійович",
        "tier": 2,
        "pattern_type": "partial_match",
        "language": "uk",
        "confidence": 0.75,
        "source_field": "name",
        "entity_id": "2965",
        "entity_type": "person",
        "hints": {"partial": "firstname_surname"}
    },
    {
        "pattern": "порошенко петро",
        "canonical": "Порошенко Петро Олексійович",
        "tier": 2,
        "pattern_type": "partial_match",
        "language": "uk",
        "confidence": 0.75,
        "source_field": "name",
        "entity_id": "2965",
        "entity_type": "person",
        "hints": {"partial": "surname_firstname"}
    }
]

es_url = "http://95.217.84.234:9200/ai_service_ac_patterns/_doc"

for pattern in patterns:
    try:
        response = requests.post(es_url, json=pattern, headers={"Content-Type": "application/json"})
        if response.status_code in [200, 201]:
            print(f"✅ Added pattern: '{pattern['pattern']}'")
        else:
            print(f"❌ Failed to add pattern: '{pattern['pattern']}' - {response.status_code}")
    except Exception as e:
        print(f"❌ Error adding pattern: '{pattern['pattern']}' - {e}")

print("\n🔄 Refreshing index...")
try:
    refresh_response = requests.post("http://95.217.84.234:9200/ai_service_ac_patterns/_refresh")
    if refresh_response.status_code == 200:
        print("✅ Index refreshed")
    else:
        print(f"❌ Failed to refresh index: {refresh_response.status_code}")
except Exception as e:
    print(f"❌ Error refreshing index: {e}")
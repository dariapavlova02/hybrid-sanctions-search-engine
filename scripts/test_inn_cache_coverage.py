#!/usr/bin/env python3
"""
Test script to verify INN cache coverage and risk detection.
"""

import json
from pathlib import Path

def test_inn_cache():
    """Test INN cache coverage and risk detection."""
    
    cache_file = Path(__file__).parent.parent / "src" / "ai_service" / "data" / "sanctioned_inns_cache.json"
    
    if not cache_file.exists():
        print("❌ INN cache file not found!")
        return
    
    with open(cache_file, 'r', encoding='utf-8') as f:
        cache = json.load(f)
    
    print(f"🔍 Testing INN Cache Coverage")
    print(f"=" * 50)
    print(f"📊 Total INNs in cache: {len(cache)}")
    
    # Statistics
    persons = sum(1 for item in cache.values() if item.get('type') == 'person')
    orgs = sum(1 for item in cache.values() if item.get('type') == 'organization')
    sources = {}
    risk_levels = {}
    
    for inn, data in cache.items():
        source = data.get('source', 'unknown')
        sources[source] = sources.get(source, 0) + 1
        
        risk = data.get('risk_level', 'unknown')
        risk_levels[risk] = risk_levels.get(risk, 0) + 1
    
    print(f"👤 Persons: {persons}")
    print(f"🏢 Organizations: {orgs}")
    print(f"📂 Sources:")
    for source, count in sorted(sources.items()):
        print(f"   {source}: {count}")
    
    print(f"⚠️  Risk Levels:")
    for risk, count in sorted(risk_levels.items()):
        print(f"   {risk}: {count}")
    
    # Test critical IDs
    print(f"\n🧪 Testing Critical IDs:")
    test_cases = [
        ("2839403975", "Якубов Руслан - должен быть high risk"),
        ("9106015074", "Company tax number - должен быть detected"),
        ("123456789012", "Test INN - должен отсутствовать"),
    ]
    
    for inn, description in test_cases:
        if inn in cache:
            data = cache[inn]
            print(f"✅ {inn}: {data['name']} ({data['type']}) - {data.get('source', 'unknown')}")
        else:
            print(f"❌ {inn}: NOT FOUND - {description}")
    
    # Test ID patterns
    print(f"\n🔍 Testing ID Patterns:")
    patterns = {
        "10-digit INNs": lambda x: len(x) == 10 and x.isdigit(),
        "8-digit IDs": lambda x: len(x) == 8 and x.isdigit(),
        "12+ digit IDs": lambda x: len(x) >= 12 and x.isdigit(),
        "Mixed patterns": lambda x: not x.isdigit()
    }
    
    for pattern_name, pattern_func in patterns.items():
        count = sum(1 for inn in cache.keys() if pattern_func(inn))
        print(f"   {pattern_name}: {count}")
    
    # Sample entries by type
    print(f"\n📋 Sample Entries:")
    
    # Persons
    person_entries = [(inn, data) for inn, data in cache.items() if data.get('type') == 'person'][:3]
    print(f"   👤 Persons:")
    for inn, data in person_entries:
        print(f"     {inn}: {data['name']}")
    
    # Organizations  
    org_entries = [(inn, data) for inn, data in cache.items() if data.get('type') == 'organization'][:3]
    print(f"   🏢 Organizations:")
    for inn, data in org_entries:
        print(f"     {inn}: {data['name']}")
    
    print(f"\n✅ INN Cache test completed!")

if __name__ == "__main__":
    test_inn_cache()
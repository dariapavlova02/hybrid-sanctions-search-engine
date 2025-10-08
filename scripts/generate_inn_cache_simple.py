#!/usr/bin/env python3
"""
Simple script to generate sanctioned INN cache from JSON data files.
"""

import json
import time
from pathlib import Path


def main():
    """Generate INN cache."""
    data_dir = Path(__file__).parent.parent / "src" / "ai_service" / "data"
    
    cache = {}
    
    # Load persons
    persons_file = data_dir / "sanctioned_persons.json"
    if persons_file.exists():
        print(f"Loading persons from {persons_file}")
        with open(persons_file, 'r', encoding='utf-8') as f:
            persons = json.load(f)
            for person in persons:
                inn = person.get('itn') or person.get('itn_import')
                if inn:
                    cache[inn.strip()] = {
                        "inn": inn.strip(),
                        "name": person.get('name', ''),
                        "name_en": person.get('name_en', ''),
                        "type": "person",
                        "source": "sanctioned_persons",
                        "person_id": person.get('person_id'),
                        "birthdate": person.get('birthdate'),
                        "aliases": person.get('aliases', [])
                    }
    
    # Load organizations  
    orgs_file = data_dir / "sanctioned_companies.json"
    if orgs_file.exists():
        print(f"Loading organizations from {orgs_file}")
        with open(orgs_file, 'r', encoding='utf-8') as f:
            orgs = json.load(f)
            for org in orgs:
                tax_number = org.get('tax_number')
                if tax_number:
                    cache[tax_number.strip()] = {
                        "inn": tax_number.strip(),
                        "name": org.get('name', ''),
                        "name_en": org.get('name_en', ''),
                        "type": "organization", 
                        "source": "sanctioned_companies",
                        "person_id": org.get('person_id'),
                        "reg_number": org.get('reg_number'),
                        "aliases": org.get('aliases', [])
                    }
    
    # Save cache
    output_file = data_dir / "sanctioned_inns_cache.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    
    # Statistics
    persons_count = sum(1 for item in cache.values() if item.get('type') == 'person')
    orgs_count = sum(1 for item in cache.values() if item.get('type') == 'organization')
    
    print(f"✅ Cache generated!")
    print(f"   Total INNs: {len(cache)}")
    print(f"   Persons: {persons_count}")
    print(f"   Organizations: {orgs_count}")
    print(f"   File: {output_file}")
    
    # Test lookup
    import os
    test_inn = os.getenv("TEST_INN", "2839403975")
    if test_inn in cache:
        print(f"✅ Test INN {test_inn} found: {cache[test_inn].get('name')}")
    else:
        print(f"❌ Test INN {test_inn} not found in cache")


if __name__ == "__main__":
    main()
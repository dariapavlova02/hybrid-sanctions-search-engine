#!/usr/bin/env python3
"""
Generate sanctioned INN cache from JSON data files.

This script should be run during deployment to create the fast lookup cache
for sanctioned INNs that powers the FAST PATH optimization.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List

# Add src to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))

try:
    from ai_service.utils.logging_config import get_logger
except ImportError:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger(__name__)


def load_sanctioned_data() -> List[Dict[str, Any]]:
    """Load sanctioned persons and organizations from JSON files."""
    data_dir = Path(__file__).parent.parent / "src" / "ai_service" / "data"
    
    sanctioned_data = []
    
    # Load persons
    persons_file = data_dir / "sanctioned_persons.json"
    if persons_file.exists():
        logger.info(f"Loading persons from {persons_file}")
        with open(persons_file, 'r', encoding='utf-8') as f:
            persons = json.load(f)
            for person in persons:
                # Convert person to cache format
                if person.get('itn') or person.get('itn_import'):
                    inn = person.get('itn') or person.get('itn_import')
                    if inn:
                        sanctioned_data.append({
                            "inn": inn,
                            "name": person.get('name', ''),
                            "name_en": person.get('name_en', ''),
                            "type": "person",
                            "source": "sanctioned_persons",
                            "person_id": person.get('person_id'),
                            "birthdate": person.get('birthdate'),
                            "aliases": person.get('aliases', [])
                        })
    else:
        logger.warning(f"Persons file not found: {persons_file}")
    
    # Load organizations  
    orgs_file = data_dir / "sanctioned_companies.json"
    if orgs_file.exists():
        logger.info(f"Loading organizations from {orgs_file}")
        with open(orgs_file, 'r', encoding='utf-8') as f:
            orgs = json.load(f)
            for org in orgs:
                # Convert organization to cache format
                if org.get('tax_number'):
                    sanctioned_data.append({
                        "inn": org['tax_number'],
                        "name": org.get('name', ''),
                        "name_en": org.get('name_en', ''),
                        "type": "organization", 
                        "source": "sanctioned_companies",
                        "person_id": org.get('person_id'),
                        "reg_number": org.get('reg_number'),
                        "aliases": org.get('aliases', [])
                    })
    else:
        logger.warning(f"Organizations file not found: {orgs_file}")
    
    return sanctioned_data


def generate_cache(sanctioned_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Generate INN cache dictionary from sanctioned data."""
    cache = {}
    
    for item in sanctioned_data:
        inn = item['inn']
        if inn and inn.strip():
            cache[inn.strip()] = item
    
    logger.info(f"Generated cache with {len(cache)} unique INNs")
    return cache


def save_cache(cache: Dict[str, Dict[str, Any]], output_file: Path):
    """Save cache to JSON file."""
    # Create directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Save cache
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Cache saved to {output_file}")


def main():
    """Main function to generate INN cache."""
    logger.info("Starting INN cache generation...")
    
    try:
        # Load sanctioned data
        sanctioned_data = load_sanctioned_data()
        logger.info(f"Loaded {len(sanctioned_data)} sanctioned entities")
        
        # Generate cache
        cache = generate_cache(sanctioned_data)
        
        # Save cache
        output_file = Path(__file__).parent.parent / "src" / "ai_service" / "data" / "sanctioned_inns_cache.json"
        save_cache(cache, output_file)
        
        # Print statistics
        persons_count = sum(1 for item in cache.values() if item.get('type') == 'person')
        orgs_count = sum(1 for item in cache.values() if item.get('type') == 'organization')
        
        logger.info(f"✅ Cache generation completed!")
        logger.info(f"   Total INNs: {len(cache)}")
        logger.info(f"   Persons: {persons_count}")
        logger.info(f"   Organizations: {orgs_count}")
        logger.info(f"   File: {output_file}")
        
        # Test lookup for the problematic INN
        test_inn = os.getenv("TEST_INN", "2839403975")
        if test_inn in cache:
            logger.info(f"✅ Test INN {test_inn} found: {cache[test_inn].get('name')}")
        else:
            logger.warning(f"❌ Test INN {test_inn} not found in cache")
        
    except Exception as e:
        logger.error(f"❌ Failed to generate INN cache: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Generate complete INN cache from all sanctions sources including terrorism data
"""

import json
import sys
import os
from datetime import datetime

def extract_inn_data(data, source_name, entity_type):
    """Extract INN/tax numbers from entity data."""
    inn_cache = {}
    processed_count = 0

    for entity in data:
        processed_count += 1

        # Extract various ID fields that could be INN/tax numbers
        id_fields = []

        # Direct INN fields
        if 'inn' in entity:
            id_fields.append(entity['inn'])

        # ITN (Individual Taxpayer Number) - used in persons data
        if 'itn' in entity:
            id_fields.append(entity['itn'])

        # Tax numbers
        if 'tax_number' in entity:
            id_fields.append(entity['tax_number'])

        # EDRPOU (Ukrainian company identifier)
        if 'edrpou' in entity:
            id_fields.append(entity['edrpou'])

        # Other ID fields from different sources
        if 'identifiers' in entity:
            identifiers = entity['identifiers']
            if isinstance(identifiers, dict):
                for id_type, id_value in identifiers.items():
                    if id_type.lower() in ['inn', 'tax_number', 'edrpou', 'ogrn', 'kpp']:
                        id_fields.append(id_value)
            elif isinstance(identifiers, list):
                for identifier in identifiers:
                    if isinstance(identifier, dict):
                        if 'number' in identifier:
                            id_fields.append(identifier['number'])
                        elif 'value' in identifier:
                            id_fields.append(identifier['value'])

        # Add any numeric ID fields that look like tax numbers
        for key in ['id', 'identifier', 'registration_number', 'company_id']:
            if key in entity and entity[key]:
                value = str(entity[key])
                # Only include if it looks like a tax number (digits, reasonable length)
                if value.isdigit() and 8 <= len(value) <= 15:
                    id_fields.append(value)

        # Process found ID fields
        for id_field in id_fields:
            if id_field and str(id_field).strip():
                clean_id = str(id_field).strip()

                # Only include numeric IDs of reasonable length
                if clean_id.isdigit() and 8 <= len(clean_id) <= 15:
                    inn_cache[clean_id] = {
                        "type": entity_type,
                        "name": entity.get('name', entity.get('full_name', 'Unknown')),
                        "name_en": entity.get('name_en', entity.get('name_eng', '')),
                        "birthdate": entity.get('birthdate', entity.get('date_of_birth', '')),
                        "entity_id": entity.get('id', entity.get('person_id', entity.get('company_id', 0))),
                        "source": source_name,
                        "status": entity.get('status', 1)
                    }

    return inn_cache, processed_count

def main():
    data_dir = "src/ai_service/data"

    print("🔍 GENERATING COMPLETE INN CACHE FROM ALL SANCTIONS SOURCES")
    print("=" * 70)

    all_inn_cache = {}
    total_entities = 0

    # 1. Process persons
    persons_file = os.path.join(data_dir, "sanctioned_persons.json")
    if os.path.exists(persons_file):
        print(f"📋 Loading persons from {persons_file}")
        with open(persons_file, 'r', encoding='utf-8') as f:
            persons_data = json.load(f)

        inn_cache, count = extract_inn_data(persons_data, "ukrainian_sanctions_persons", "person")
        all_inn_cache.update(inn_cache)
        total_entities += count
        print(f"   ✅ Processed {count:,} persons, found {len(inn_cache):,} with INN")
    else:
        print(f"   ❌ File not found: {persons_file}")

    # 2. Process companies
    companies_file = os.path.join(data_dir, "sanctioned_companies.json")
    if os.path.exists(companies_file):
        print(f"📋 Loading companies from {companies_file}")
        with open(companies_file, 'r', encoding='utf-8') as f:
            companies_data = json.load(f)

        inn_cache, count = extract_inn_data(companies_data, "ukrainian_sanctions_companies", "organization")
        all_inn_cache.update(inn_cache)
        total_entities += count
        print(f"   ✅ Processed {count:,} companies, found {len(inn_cache):,} with INN")
    else:
        print(f"   ❌ File not found: {companies_file}")

    # 3. Process terrorism data
    terrorism_file = os.path.join(data_dir, "terrorism_black_list.json")
    if os.path.exists(terrorism_file):
        print(f"📋 Loading terrorism data from {terrorism_file}")
        with open(terrorism_file, 'r', encoding='utf-8') as f:
            terrorism_data = json.load(f)

        # Terrorism data might have mixed person/org types, let's detect
        terrorism_inn_cache = {}
        processed_terrorism = 0

        for entity in terrorism_data:
            processed_terrorism += 1

            # Detect entity type based on available fields
            entity_type = "person"  # Default
            if any(field in entity for field in ['company_name', 'organization', 'legal_form', 'edrpou']):
                entity_type = "organization"

            # Extract INN/tax data
            inn_cache, _ = extract_inn_data([entity], "terrorism_blacklist", entity_type)
            terrorism_inn_cache.update(inn_cache)

        all_inn_cache.update(terrorism_inn_cache)
        total_entities += processed_terrorism
        print(f"   ✅ Processed {processed_terrorism:,} terrorism entries, found {len(terrorism_inn_cache):,} with INN")
    else:
        print(f"   ❌ File not found: {terrorism_file}")

    # Generate output
    output_file = os.path.join(data_dir, "sanctioned_inns_cache.json")

    print(f"\n📊 CACHE GENERATION SUMMARY:")
    print(f"   Total entities processed: {total_entities:,}")
    print(f"   Total INN entries: {len(all_inn_cache):,}")
    print(f"   Output file: {output_file}")

    # Write cache file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_inn_cache, f, ensure_ascii=False, indent=2)

    print(f"\n✅ INN cache generated successfully!")

    # Show source breakdown
    print(f"\n📋 SOURCE BREAKDOWN:")
    sources = {}
    for inn, data in all_inn_cache.items():
        source = data['source']
        sources[source] = sources.get(source, 0) + 1

    for source, count in sources.items():
        print(f"   {source}: {count:,} entries")

if __name__ == "__main__":
    main()
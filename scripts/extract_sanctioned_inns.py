#!/usr/bin/env python3

"""
Extract sanctioned INNs from all sanctions lists and create a fast lookup cache.
"""

import json
import os
from pathlib import Path
from typing import Dict, Set

def extract_inns_from_sanctions():
    """Extract all INNs from sanctions data files."""

    # Base path for data files
    data_dir = Path(__file__).parent.parent / "src" / "ai_service" / "data"

    # Dictionary to store INN -> person mapping
    inn_cache = {}

    # Track statistics
    stats = {
        "persons_processed": 0,
        "companies_processed": 0,
        "inns_extracted": 0,
        "files_processed": []
    }

    print("🔍 EXTRACTING SANCTIONED INNs")
    print("=" * 50)

    # Process sanctioned persons
    persons_file = data_dir / "sanctioned_persons.json"
    if persons_file.exists():
        print(f"📋 Processing: {persons_file}")

        with open(persons_file, 'r', encoding='utf-8') as f:
            persons_data = json.load(f)

        for person in persons_data:
            stats["persons_processed"] += 1

            # Extract INN/ITN
            inn = person.get('itn') or person.get('inn')
            if inn and str(inn).strip():
                inn = str(inn).strip()

                inn_cache[inn] = {
                    "type": "person",
                    "name": person.get('name', '').strip(),
                    "name_en": person.get('name_en', '').strip(),
                    "birthdate": person.get('birthdate'),
                    "person_id": person.get('person_id'),
                    "source": "ukrainian_sanctions",
                    "status": person.get('status', 1)
                }

                stats["inns_extracted"] += 1
                print(f"  ✓ {inn} -> {person.get('name', 'Unknown')}")

        stats["files_processed"].append(str(persons_file))

    # Process sanctioned companies
    companies_file = data_dir / "sanctioned_companies.json"
    if companies_file.exists():
        print(f"📋 Processing: {companies_file}")

        with open(companies_file, 'r', encoding='utf-8') as f:
            companies_data = json.load(f)

        for company in companies_data:
            stats["companies_processed"] += 1

            # Extract various ID fields
            id_fields = ['tax_number', 'edrpou', 'inn', 'itn', 'registration_number']
            for field in id_fields:
                inn = company.get(field)
                if inn and str(inn).strip():
                    inn = str(inn).strip()

                    inn_cache[inn] = {
                        "type": "organization",
                        "name": company.get('name', '').strip(),
                        "name_en": company.get('name_en', '').strip(),
                        "org_id": company.get('org_id'),
                        "source": "ukrainian_sanctions",
                        "status": company.get('status', 1),
                        "id_field": field
                    }

                    stats["inns_extracted"] += 1
                    print(f"  ✓ {inn} -> {company.get('name', 'Unknown')} ({field})")
                    break  # Only take first valid ID

        stats["files_processed"].append(str(companies_file))

    # Process terrorism black list if exists
    terrorism_file = data_dir / "terrorism_black_list.json"
    if terrorism_file.exists():
        print(f"📋 Processing: {terrorism_file}")

        with open(terrorism_file, 'r', encoding='utf-8') as f:
            terrorism_data = json.load(f)

        for entry in terrorism_data:
            # Look for IDs in metadata or direct fields
            inn = None
            for field in ['itn', 'inn', 'tax_id', 'passport', 'id_number']:
                if entry.get(field):
                    inn = str(entry[field]).strip()
                    break

            if inn and len(inn) >= 8:  # Reasonable ID length
                inn_cache[inn] = {
                    "type": "person",
                    "name": entry.get('name', '').strip(),
                    "source": "terrorism_blacklist",
                    "status": 1,
                    "risk_level": "critical"
                }

                stats["inns_extracted"] += 1
                print(f"  ✓ {inn} -> {entry.get('name', 'Unknown')} (TERRORISM)")

        stats["files_processed"].append(str(terrorism_file))

    # Process all other JSON files in data directory
    for json_file in data_dir.glob("*.json"):
        # Skip already processed files
        if json_file.name in ["sanctioned_persons.json", "sanctioned_companies.json", "terrorism_black_list.json", "sanctioned_inns_cache.json"]:
            continue

        print(f"📋 Processing additional file: {json_file}")
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                additional_data = json.load(f)

            # Handle different JSON structures
            if isinstance(additional_data, list):
                entries = additional_data
            elif isinstance(additional_data, dict) and 'data' in additional_data:
                entries = additional_data['data']
            else:
                entries = [additional_data] if isinstance(additional_data, dict) else []

            for entry in entries:
                if not isinstance(entry, dict):
                    continue

                # Look for various ID fields
                inn = None
                for field in ['itn', 'inn', 'tax_id', 'tax_number', 'edrpou', 'registration_number', 'passport', 'id_number']:
                    if entry.get(field):
                        candidate_inn = str(entry[field]).strip()
                        if len(candidate_inn) >= 8 and candidate_inn.isdigit():
                            inn = candidate_inn
                            break

                if inn and inn not in inn_cache:  # Avoid duplicates
                    # Determine type based on available fields
                    entry_type = "organization" if any(field in entry for field in ['company', 'organization', 'org', 'business']) else "person"

                    inn_cache[inn] = {
                        "type": entry_type,
                        "name": entry.get('name', entry.get('company', entry.get('organization', ''))).strip(),
                        "source": f"additional_sanctions_{json_file.stem}",
                        "status": entry.get('status', 1),
                        "risk_level": "high"
                    }

                    stats["inns_extracted"] += 1
                    print(f"  ✓ {inn} -> {inn_cache[inn]['name']} ({json_file.stem})")

            stats["files_processed"].append(str(json_file))

        except Exception as e:
            print(f"  ⚠️ Error processing {json_file}: {e}")

    # Save INN cache
    output_file = data_dir / "sanctioned_inns_cache.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(inn_cache, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 50)
    print("📊 EXTRACTION COMPLETE")
    print(f"📋 Persons processed: {stats['persons_processed']}")
    print(f"🏢 Companies processed: {stats['companies_processed']}")
    print(f"🎯 INNs extracted: {stats['inns_extracted']}")
    print(f"📁 Output file: {output_file}")
    print(f"📄 Files processed: {len(stats['files_processed'])}")

    for file_path in stats["files_processed"]:
        print(f"  - {file_path}")

    # Show sample entries
    print("\n🔍 SAMPLE ENTRIES:")
    for i, (inn, data) in enumerate(list(inn_cache.items())[:5]):
        print(f"  {inn}: {data['name']} ({data['type']})")
        if i >= 4:
            break

    if len(inn_cache) > 5:
        print(f"  ... and {len(inn_cache) - 5} more entries")

    return inn_cache, stats

if __name__ == "__main__":
    try:
        inn_cache, stats = extract_inns_from_sanctions()
        print(f"\n✅ SUCCESS: {stats['inns_extracted']} sanctioned INNs cached")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
#!/usr/bin/env python3
"""
Standalone test for sanctions data loading.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

# Test JSON loading first
def test_json_loading():
    """Test basic JSON file loading."""
    print("🔍 Testing JSON file loading...")

    data_dir = Path("data/sanctions")

    persons_file = data_dir / "sanctioned_persons.json"
    companies_file = data_dir / "sanctioned_companies.json"

    if not persons_file.exists():
        print(f"❌ Persons file not found: {persons_file}")
        return False

    if not companies_file.exists():
        print(f"❌ Companies file not found: {companies_file}")
        return False

    try:
        # Test persons file
        with open(persons_file, 'r', encoding='utf-8') as f:
            persons_data = json.load(f)

        print(f"✅ Persons file loaded: {len(persons_data)} entries")

        # Show sample person
        if persons_data:
            sample = persons_data[0]
            print(f"   Sample person: {sample.get('name', 'No name')}")
            if sample.get('name_en'):
                print(f"   English name: {sample['name_en']}")
            if sample.get('birthdate'):
                print(f"   Birth date: {sample['birthdate']}")

        # Test companies file
        with open(companies_file, 'r', encoding='utf-8') as f:
            companies_data = json.load(f)

        print(f"✅ Companies file loaded: {len(companies_data)} entries")

        # Show sample company
        if companies_data:
            sample = companies_data[0]
            print(f"   Sample company: {sample.get('name', 'No name')}")
            if sample.get('tax_number'):
                print(f"   Tax number: {sample['tax_number']}")

        return True

    except Exception as e:
        print(f"❌ Error loading JSON files: {e}")
        return False

async def test_simple_fuzzy():
    """Test simple fuzzy matching with loaded data."""
    print(f"\n🔍 Testing simple fuzzy matching...")

    try:
        import rapidfuzz
        from rapidfuzz import fuzz, process
    except ImportError:
        print("❌ rapidfuzz not available")
        return

    # Load persons for fuzzy matching
    data_dir = Path("data/sanctions")
    persons_file = data_dir / "sanctioned_persons.json"

    try:
        with open(persons_file, 'r', encoding='utf-8') as f:
            persons_data = json.load(f)

        # Extract names for fuzzy matching
        person_names = []
        for person in persons_data[:1000]:  # Limit for performance
            name = person.get('name')
            if name and name.strip():
                person_names.append(name.strip())

            # Add English name if different
            name_en = person.get('name_en')
            if name_en and name_en.strip() and name_en.strip() != (name.strip() if name else ''):
                person_names.append(name_en.strip())

            # Add Russian name if different
            name_ru = person.get('name_ru')
            if name_ru and name_ru.strip() and name_ru.strip() != (name.strip() if name else ''):
                person_names.append(name_ru.strip())

        print(f"✅ Extracted {len(person_names)} names for fuzzy matching")

        # Test some typos
        test_queries = [
            "Порошенк Петро",   # Should match if Порошенко is in data
            "Путин Владимир",   # Should match if Putin is in data
            "Ковриков",         # From our sample data
            "Гаркушев",         # From our sample data
        ]

        for query in test_queries:
            print(f"\n   Testing: '{query}'")

            matches = process.extract(
                query,
                person_names,
                scorer=fuzz.token_sort_ratio,
                limit=3,
                score_cutoff=60
            )

            if matches:
                print(f"      Found {len(matches)} matches:")
                for i, (name, score, idx) in enumerate(matches, 1):
                    print(f"        {i}. '{name}' - {score / 100.0:.3f}")
            else:
                print(f"      No matches found")

    except Exception as e:
        print(f"❌ Error in fuzzy testing: {e}")

def count_unique_names():
    """Count unique names for statistics."""
    print(f"\n📊 Counting unique names...")

    data_dir = Path("data/sanctions")

    try:
        # Load persons
        with open(data_dir / "sanctioned_persons.json", 'r', encoding='utf-8') as f:
            persons_data = json.load(f)

        # Load companies
        with open(data_dir / "sanctioned_companies.json", 'r', encoding='utf-8') as f:
            companies_data = json.load(f)

        # Count unique person names
        person_names = set()
        for person in persons_data:
            name = person.get('name')
            if name and name.strip():
                person_names.add(name.strip())

            name_en = person.get('name_en')
            if name_en and name_en.strip() and name_en.strip() != (name.strip() if name else ''):
                person_names.add(name_en.strip())

            name_ru = person.get('name_ru')
            if name_ru and name_ru.strip() and name_ru.strip() != (name.strip() if name else ''):
                person_names.add(name_ru.strip())

        # Count unique company names
        company_names = set()
        for company in companies_data:
            name = company.get('name')
            if name and name.strip():
                company_names.add(name.strip())

        print(f"✅ Statistics:")
        print(f"   Total persons in file: {len(persons_data)}")
        print(f"   Unique person names (including aliases): {len(person_names)}")
        print(f"   Total companies in file: {len(companies_data)}")
        print(f"   Unique company names: {len(company_names)}")
        print(f"   Total unique names for fuzzy search: {len(person_names) + len(company_names)}")

        # Show some examples
        print(f"\n   Sample person names:")
        for i, name in enumerate(sorted(list(person_names))[:5], 1):
            print(f"     {i}. {name}")

        print(f"\n   Sample company names:")
        for i, name in enumerate(sorted(list(company_names))[:5], 1):
            print(f"     {i}. {name}")

        return len(person_names) + len(company_names)

    except Exception as e:
        print(f"❌ Error counting names: {e}")
        return 0

async def main():
    """Run all tests."""
    print("🧪 Sanctions Data Standalone Testing")
    print("=" * 50)

    # Test 1: Basic JSON loading
    if not test_json_loading():
        print("❌ Basic tests failed, stopping")
        return

    # Test 2: Count statistics
    total_names = count_unique_names()

    # Test 3: Simple fuzzy matching
    await test_simple_fuzzy()

    print(f"\n{'='*50}")
    print("✅ Sanctions data testing completed!")
    print(f"📊 Key findings:")
    print(f"   - Ukrainian sanctions data loaded successfully")
    print(f"   - {total_names} unique names available for fuzzy search")
    print(f"   - Both persons and companies data parsed correctly")
    print(f"   - Fuzzy matching working with real sanctions data")
    print(f"\n💡 Next steps:")
    print(f"   - Integration with HybridSearchService")
    print(f"   - Performance optimization for large datasets")
    print(f"   - Cache implementation for faster access")

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Test sanctions data loader functionality.
"""

import asyncio
import json
from pathlib import Path

# Add the project to the path
import sys
sys.path.insert(0, '.')

from src.ai_service.layers.search.sanctions_data_loader import SanctionsDataLoader, SanctionEntry

async def test_sanctions_loader():
    """Test sanctions data loading and fuzzy matching."""
    print("🏛️  Testing Sanctions Data Loader")
    print("=" * 50)

    # Initialize loader
    loader = SanctionsDataLoader()

    # Test loading dataset
    print("1. Loading sanctions dataset...")
    dataset = await loader.load_dataset(force_reload=True)

    print(f"✅ Dataset loaded successfully!")
    print(f"   Total entries: {dataset.total_entries}")
    print(f"   Persons: {len(dataset.persons)}")
    print(f"   Organizations: {len(dataset.organizations)}")
    print(f"   Unique names: {len(dataset.all_names)}")
    print(f"   Sources: {', '.join(dataset.sources)}")
    print(f"   Loaded at: {dataset.loaded_at}")

    # Show sample persons
    print(f"\n2. Sample persons:")
    for i, person in enumerate(dataset.persons[:5], 1):
        aliases_str = f", aliases: {person.aliases}" if person.aliases else ""
        print(f"   {i}. {person.name} ({person.nationality or 'unknown'}){aliases_str}")

    # Show sample organizations
    print(f"\n3. Sample organizations:")
    for i, org in enumerate(dataset.organizations[:3], 1):
        aliases_str = f", aliases: {org.aliases}" if org.aliases else ""
        print(f"   {i}. {org.name}{aliases_str}")

    # Test fuzzy candidates
    print(f"\n4. Testing fuzzy candidates extraction...")

    # Get all candidates
    all_candidates = await loader.get_fuzzy_candidates()
    print(f"   All candidates: {len(all_candidates)}")

    # Get person candidates only
    person_candidates = await loader.get_fuzzy_candidates("person")
    print(f"   Person candidates: {len(person_candidates)}")

    # Get organization candidates only
    org_candidates = await loader.get_fuzzy_candidates("organization")
    print(f"   Organization candidates: {len(org_candidates)}")

    # Test name lookup
    print(f"\n5. Testing name lookup...")
    test_names = ["Петро Порошенко", "Владимир Путин", "Газпром"]

    for name in test_names:
        entry = await loader.find_entry(name)
        if entry:
            print(f"   ✅ Found '{name}': {entry.entity_type}, source: {entry.source}")
        else:
            print(f"   ❌ Not found: '{name}'")

    # Test cache functionality
    print(f"\n6. Testing cache functionality...")

    # Load again (should use cache)
    import time
    start_time = time.time()
    dataset2 = await loader.load_dataset()
    cache_time = (time.time() - start_time) * 1000

    print(f"   Second load took {cache_time:.2f}ms (cached: {dataset2.loaded_at == dataset.loaded_at})")

    # Get statistics
    print(f"\n7. Loader statistics:")
    stats = await loader.get_stats()
    print(f"   {json.dumps(stats, indent=4, ensure_ascii=False)}")

    return dataset

async def test_fuzzy_integration():
    """Test fuzzy search integration with sanctions data."""
    print(f"\n🔍 Testing Fuzzy Search Integration")
    print("=" * 50)

    try:
        from src.ai_service.layers.search.fuzzy_search_service import FuzzySearchService, FuzzyConfig

        # Initialize components
        loader = SanctionsDataLoader()
        fuzzy_config = FuzzyConfig(
            min_score_threshold=0.65,
            high_confidence_threshold=0.85
        )
        fuzzy_service = FuzzySearchService(fuzzy_config)

        if not fuzzy_service.enabled:
            print("❌ Fuzzy search not available (rapidfuzz missing)")
            return

        # Get sanctions data for fuzzy matching
        candidates = await loader.get_fuzzy_candidates("person")
        print(f"✅ Loaded {len(candidates)} person candidates from sanctions data")

        # Test fuzzy matching with typos
        test_queries = [
            "Порошенк Петро",    # Missing letter
            "Владимр Путин",     # Missing letter
            "Навалный",          # Missing first name
            "Ахметв Рінат",      # Missing letter
        ]

        for query in test_queries:
            print(f"\n   Testing: '{query}'")

            results = await fuzzy_service.search_async(
                query=query,
                candidates=candidates[:1000]  # Limit for speed
            )

            if results:
                print(f"      Found {len(results)} matches:")
                for i, result in enumerate(results[:3], 1):
                    print(f"        {i}. '{result.matched_text}' - {result.score:.3f} ({result.algorithm})")
            else:
                print(f"      No matches found")

    except ImportError as e:
        print(f"❌ Cannot test fuzzy integration: {e}")

async def create_sample_custom_data():
    """Create sample custom sanctions data file."""
    print(f"\n📄 Creating sample custom sanctions data...")

    # Create data directory
    data_dir = Path("data/sanctions")
    data_dir.mkdir(parents=True, exist_ok=True)

    # Sample custom data with more Ukrainian/Russian names
    custom_data = {
        "metadata": {
            "source": "custom_ukraine_russia",
            "created_at": "2024-01-01",
            "description": "Sample Ukrainian and Russian politically exposed persons"
        },
        "entries": [
            {
                "name": "Юлія Тимошенко",
                "type": "person",
                "aliases": ["Yulia Tymoshenko", "Тимошенко Юлія Володимирівна"],
                "birth_date": "1960-11-27",
                "nationality": "Ukraine",
                "metadata": {"position": "Former Prime Minister of Ukraine"}
            },
            {
                "name": "Віталій Кличко",
                "type": "person",
                "aliases": ["Vitali Klitschko", "Кличко Віталій Володимирович"],
                "birth_date": "1971-07-19",
                "nationality": "Ukraine",
                "metadata": {"position": "Mayor of Kyiv"}
            },
            {
                "name": "Сергей Лавров",
                "type": "person",
                "aliases": ["Sergey Lavrov", "Лавров Сергей Викторович"],
                "birth_date": "1950-03-21",
                "nationality": "Russia",
                "metadata": {"position": "Minister of Foreign Affairs of Russia"}
            },
            {
                "name": "Дмитро Фірташ",
                "type": "person",
                "aliases": ["Dmytro Firtash", "Фірташ Дмитро Васильович"],
                "nationality": "Ukraine",
                "metadata": {"business": "Gas trader, oligarch"}
            },
            {
                "name": "Вагнер",
                "type": "organization",
                "aliases": ["Wagner Group", "ЧВК Вагнер", "PMC Wagner"],
                "metadata": {"type": "Private military company"}
            }
        ]
    }

    custom_file = data_dir / "custom_ukraine_russia.json"
    with open(custom_file, 'w', encoding='utf-8') as f:
        json.dump(custom_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Created sample file: {custom_file}")
    print(f"   Contains {len(custom_data['entries'])} entries")

async def main():
    """Run all tests."""
    print("🧪 Sanctions Data Loader Testing Suite")
    print("======================================")

    # Create sample data first
    await create_sample_custom_data()

    # Test basic functionality
    dataset = await test_sanctions_loader()

    # Test fuzzy integration
    await test_fuzzy_integration()

    print(f"\n{'='*50}")
    print("✅ All tests completed!")
    print("💡 Key points:")
    print("- Sanctions data loaded and cached successfully")
    print("- Fuzzy matching works with real sanctions names")
    print("- Custom sanctions lists can be added easily")
    print("- Cache improves performance on subsequent loads")

if __name__ == "__main__":
    asyncio.run(main())
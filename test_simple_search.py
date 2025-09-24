#!/usr/bin/env python3
"""
Simple test for AC search without full orchestrator
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')
import json

def simple_ac_search():
    """Simple AC search test."""
    print("🔍 SIMPLE AC SEARCH TEST")
    print("="*40)

    # Load sanctions data directly
    sanctions_file = "/Users/dariapavlova/Desktop/ai-service/data/sanctions/sanctioned_persons.json"

    try:
        with open(sanctions_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"📊 Loaded {len(data)} sanctions records")

        # Test searches
        test_queries = [
            "Людмила Ульянова",
            "Ульянова Людмила",
            "Liudмуlа Uliаnоvа",  # Homoglyph
            "Шевченко Анатолійович",
            "Анатолійович",
            "Коваленко Олександра Сергіївна"
        ]

        for query in test_queries:
            print(f"\n🔍 Search: '{query}'")

            # Simple substring search
            matches = []
            for record in data:
                name = record.get('name', '')
                name_en = record.get('name_en', '') or ''
                name_ru = record.get('name_ru', '') or ''

                # Check all name variants
                if (query.lower() in name.lower() or
                    query.lower() in name_en.lower() or
                    query.lower() in name_ru.lower()):
                    matches.append({
                        'name': name,
                        'name_en': name_en,
                        'name_ru': name_ru,
                        'birthdate': record.get('birthdate')
                    })

            if matches:
                print(f"  ✅ Found {len(matches)} matches:")
                for match in matches[:3]:  # Show first 3
                    print(f"    - {match['name']}")
                    if match['name_en']:
                        print(f"      EN: {match['name_en']}")
                    if match['birthdate']:
                        print(f"      DOB: {match['birthdate']}")
            else:
                print(f"  ❌ No matches found")

        # Test homoglyph normalization
        print(f"\n🔤 HOMOGLYPH NORMALIZATION TEST")
        homoglyph_name = "Liudмуlа Uliаnоvа"

        # Simple Cyrillic->Latin mapping
        cyrillic_to_latin = {
            'а': 'a', 'е': 'e', 'і': 'i', 'о': 'o', 'у': 'u',
            'х': 'x', 'р': 'p', 'с': 'c', 'м': 'm', 'н': 'h',
            'к': 'k', 'т': 't', 'в': 'b', 'л': 'l'
        }

        # Try to normalize
        normalized = ""
        for char in homoglyph_name.lower():
            if char in cyrillic_to_latin:
                normalized += cyrillic_to_latin[char]
            else:
                normalized += char

        # Also try reverse - Latin->Cyrillic
        latin_to_cyrillic = {v: k for k, v in cyrillic_to_latin.items()}
        cyrillic_version = ""
        for char in homoglyph_name.lower():
            if char in latin_to_cyrillic:
                cyrillic_version += latin_to_cyrillic[char]
            else:
                cyrillic_version += char

        print(f"  Original: '{homoglyph_name}'")
        print(f"  To Latin: '{normalized.title()}'")
        print(f"  To Cyrillic: '{cyrillic_version.title()}'")

        # Search with normalized versions
        for norm_name in [normalized.title(), cyrillic_version.title()]:
            matches = []
            for record in data:
                name = record.get('name', '')
                if norm_name.lower() in name.lower():
                    matches.append(name)

            if matches:
                print(f"  🎯 '{norm_name}' found {len(matches)} matches:")
                for match in matches[:2]:
                    print(f"    - {match}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simple_ac_search()
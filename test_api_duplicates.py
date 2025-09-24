#!/usr/bin/env python3
"""
Test duplicates through API endpoint
"""

import sys
import json
import asyncio
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

async def test_via_api():
    """Test via API endpoint."""
    print("🔍 TESTING VIA API ENDPOINT")
    print("="*50)

    try:
        from ai_service.api.endpoints import create_app
        from fastapi.testclient import TestClient

        app = create_app()
        client = TestClient(app)

        # Test case
        test_input = "ШЕВЧЕНКО АНДРІЙ АНАТОЛІЙОВИЧ"
        print(f"Input: '{test_input}'")

        response = client.post(
            "/process",
            json={"text": test_input}
        )

        if response.status_code != 200:
            print(f"❌ API returned {response.status_code}: {response.text}")
            return

        result = response.json()

        print(f"\n📊 РЕЗУЛЬТАТЫ:")
        print(f"  normalized_text: '{result.get('normalized_text', '')}'")
        print(f"  tokens: {result.get('tokens', [])}")

        # Check trace for duplicates
        trace = result.get('trace', [])
        print(f"\n📝 TRACE ANALYSIS:")
        print(f"  Total trace entries: {len(trace)}")

        # Count token occurrences
        token_counts = {}
        for entry in trace:
            token = entry.get('token', '')
            token_counts[token] = token_counts.get(token, 0) + 1

        duplicates = {k: v for k, v in token_counts.items() if v > 1}
        if duplicates:
            print(f"  ⚠️ Tokens appearing multiple times in trace:")
            for token, count in duplicates.items():
                print(f"    '{token}': {count} times")

        # Check signals
        signals = result.get('signals', {})
        persons = signals.get('persons', [])

        if persons:
            print(f"\n📊 SIGNALS ANALYSIS:")
            for i, person in enumerate(persons):
                core = person.get('core', [])
                print(f"  Person {i+1} core: {core}")

                # Check for duplicates
                seen = set()
                dups = []
                for token in core:
                    if token.lower() in seen:
                        dups.append(token)
                    seen.add(token.lower())

                if dups:
                    print(f"    ⚠️ DUPLICATES FOUND: {dups}")

        # Check АНДРІЙ presence
        print(f"\n✅ АНДРІЙ CHECK:")
        normalized = result.get('normalized_text', '')
        if 'Андрій' in normalized or 'андрій' in normalized.lower():
            print(f"  ✅ АНДРІЙ found in normalized_text!")
        else:
            print(f"  ❌ АНДРІЙ NOT found in normalized_text!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_via_api())
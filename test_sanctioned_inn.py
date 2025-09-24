#!/usr/bin/env python3

"""
Test sanctioned INN detection logic.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_sanctioned_inn():
    """Test sanctioned INN detection through full pipeline."""
    print("🚨 SANCTIONED INN TEST")
    print("=" * 60)

    try:
        from ai_service.core.unified_orchestrator import UnifiedOrchestrator
        from ai_service.layers.search.mock_search_service import MockSearchService

        # Create orchestrator with mock search service
        from ai_service.layers.validation.validation_service import ValidationService
        from ai_service.layers.language.language_service import LanguageService
        from ai_service.layers.unicode.unicode_service import UnicodeService
        from ai_service.layers.normalization.normalization_service import NormalizationService
        from ai_service.layers.signals.signals_service import SignalsService

        validation_service = ValidationService()
        language_service = LanguageService()
        unicode_service = UnicodeService()
        normalization_service = NormalizationService()
        signals_service = SignalsService()

        # Create mock search service
        search_service = MockSearchService()

        orchestrator = UnifiedOrchestrator(
            validation_service=validation_service,
            language_service=language_service,
            unicode_service=unicode_service,
            normalization_service=normalization_service,
            signals_service=signals_service,
        )

        # Set search service
        orchestrator.search_service = search_service

        test_cases = [
            {
                "name": "Clean person without INN",
                "text": "Иван Петров",
                "expected_risk": "low",
                "expected_matches": 0
            },
            {
                "name": "Person with non-sanctioned INN",
                "text": "Иван Петров ИНН 123456789012",
                "expected_risk": "medium",  # Should be medium due to ID bonus
                "expected_matches": 0
            },
            {
                "name": "Person with sanctioned INN",
                "text": "Дарья Инн Павлова ИНН 782611846337",
                "expected_risk": "high",  # Should be HIGH due to sanctioned INN
                "expected_matches": 1
            }
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}. TEST: {test_case['name']}")
            print(f"   Text: '{test_case['text']}'")
            print(f"   Expected risk: {test_case['expected_risk']}")
            print(f"   Expected matches: {test_case['expected_matches']}")

            try:
                # Process through orchestrator
                result = await orchestrator.process_async(
                    test_case['text'],
                    hints={"language": None},
                    generate_variants=False,
                    generate_embeddings=False,
                    enable_search=True
                )

                # Check results
                risk_level = result.decision.risk_level if result.decision else "unknown"
                total_matches = result.search_results.get('total_hits', 0) if result.search_results else 0

                print(f"   🎯 Risk level: {risk_level}")
                print(f"   🔍 Total matches: {total_matches}")

                # Check IDs in signals
                if result.signals and result.signals.persons:
                    for person in result.signals.persons:
                        if person.get('ids'):
                            print(f"   📋 Extracted IDs: {len(person['ids'])}")
                            for id_info in person['ids']:
                                print(f"      -> {id_info.get('type')}: {id_info.get('value')}")

                # Check search candidates if available
                if hasattr(result, 'search_candidates'):
                    print(f"   👥 Search candidates: {len(result.search_candidates)}")
                    for candidate in result.search_candidates:
                        print(f"      -> {candidate.get('text', 'N/A')} (mode: {candidate.get('search_mode', 'N/A')})")

                # Check if it matches expectations
                risk_match = risk_level.lower() == test_case['expected_risk']
                matches_match = total_matches == test_case['expected_matches']

                if risk_match and matches_match:
                    print(f"   ✅ PASS")
                else:
                    print(f"   ❌ FAIL - Expected risk: {test_case['expected_risk']}, got: {risk_level}")
                    print(f"           Expected matches: {test_case['expected_matches']}, got: {total_matches}")

            except Exception as e:
                print(f"   ❌ ERROR: {e}")
                import traceback
                traceback.print_exc()

    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("SANCTIONED INN TEST COMPLETE")


if __name__ == "__main__":
    asyncio.run(test_sanctioned_inn())
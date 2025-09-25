#!/usr/bin/env python3

"""
Test full pipeline with metrics integration to verify fast path INN cache performance tracking.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_full_pipeline_metrics():
    """Test full processing pipeline with metrics."""
    print("🔍 TESTING FULL PIPELINE WITH METRICS")
    print("=" * 70)

    try:
        from ai_service.core.unified_orchestrator import UnifiedOrchestrator
        from ai_service.monitoring.prometheus_exporter import get_exporter

        print("✅ Successfully imported orchestrator and metrics")

        # Initialize orchestrator
        orchestrator = UnifiedOrchestrator()
        metrics = get_exporter()

        # Test cases with different scenarios
        test_cases = [
            {
                "name": "Sanctioned INN - should trigger fast path",
                "text": "Порошенко Петро Олексійович ІПН 123456789012",
                "expected_fast_path": True
            },
            {
                "name": "Regular person name - no fast path",
                "text": "Іванов Іван Іванович дата народження 15.05.1980",
                "expected_fast_path": False
            },
            {
                "name": "Organization with ЄДРПОУ",
                "text": "ТОВ \"Бест Компані\" ЄДРПОУ 12345678",
                "expected_fast_path": False
            }
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}. TEST: {test_case['name']}")
            print(f"   Text: '{test_case['text']}'")

            try:
                # Process the text
                import time
                start_time = time.time()

                result = await orchestrator.process(
                    test_case['text'],
                    remove_stop_words=True,
                    preserve_names=True,
                    enable_advanced_features=True
                )

                processing_time = (time.time() - start_time) * 1000  # Convert to ms

                print(f"   📋 Processing Results:")
                print(f"     Success: {result.success}")
                print(f"     Language: {result.language}")
                print(f"     Normalized: '{result.normalized_text}'")
                print(f"     Processing time: {processing_time:.1f}ms")

                # Check signals results
                if result.signals:
                    print(f"     Persons found: {len(result.signals.persons)}")
                    print(f"     Organizations found: {len(result.signals.organizations)}")
                    print(f"     Signals confidence: {result.signals.confidence:.3f}")

                    # Check for fast path sanctions
                    fast_path_detected = False
                    if hasattr(result.signals, 'fast_path_sanctions'):
                        fast_path_detected = result.signals.fast_path_sanctions.get('cache_hit', False)
                        print(f"     Fast path cache hit: {fast_path_detected}")

                    # Check for sanctioned IDs in persons
                    for person in result.signals.persons:
                        if hasattr(person, 'ids') and person.ids:
                            sanctioned_ids = [id_info for id_info in person.ids
                                           if isinstance(id_info, dict) and id_info.get('sanctioned', False)]
                            if sanctioned_ids:
                                print(f"     Sanctioned IDs found: {len(sanctioned_ids)}")
                                fast_path_detected = True

                # Validation
                if test_case['expected_fast_path'] == fast_path_detected:
                    print(f"   ✅ Fast path detection correct: {fast_path_detected}")
                else:
                    print(f"   ❌ Fast path detection wrong: expected {test_case['expected_fast_path']}, got {fast_path_detected}")

            except Exception as test_e:
                print(f"   ❌ TEST ERROR: {test_e}")
                import traceback
                traceback.print_exc()

        print("\n" + "=" * 50)
        print("FINAL METRICS REPORT")
        print("=" * 50)

        # Get final metrics
        final_metrics = metrics.get_metrics()
        print(final_metrics.decode('utf-8'))

    except Exception as e:
        print(f"❌ Setup error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("FULL PIPELINE METRICS TEST COMPLETE")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_full_pipeline_metrics())
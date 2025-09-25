#!/usr/bin/env python3

"""
Test search trace functionality.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_search_trace():
    """Test search trace with orchestrator."""
    print("🔍 TESTING SEARCH TRACE")
    print("=" * 60)

    try:
        from ai_service.core.unified_orchestrator import UnifiedOrchestrator
        from ai_service.core.orchestrator_factory import OrchestratorFactory

        # Create orchestrator with all components
        orchestrator = OrchestratorFactory.create()

        print(f"✅ Successfully created orchestrator")
        print(f"📊 Search enabled: {orchestrator.enable_search}")
        print(f"📊 Search service: {type(orchestrator.search_service).__name__ if orchestrator.search_service else None}")

        # Test cases
        test_cases = [
            {
                "name": "Exact match (no escalation expected)",
                "text": "Ковриков Роман Валерійович",
                "expected_escalation": False
            },
            {
                "name": "Fuzzy match (escalation expected)",
                "text": "Коврико Роман",
                "expected_escalation": True
            },
            {
                "name": "INN detection",
                "text": "ІПН 782611846337",
                "expected_escalation": True
            }
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}. TEST: {test_case['name']}")
            print(f"   Text: '{test_case['text']}'")
            print(f"   Expected escalation: {test_case['expected_escalation']}")

            try:
                # Process with search trace enabled (default now)
                result = await orchestrator.process_async(
                    test_case['text'],
                    hints={"language": None},
                    generate_variants=False,
                    generate_embeddings=False,
                    search_trace_enabled=True  # Explicitly enable
                )

                # Check search results
                if result.search_results:
                    print(f"   🎯 Search results: {result.search_results.get('total_hits', 0)} hits")
                    print(f"   ⏱️ Processing time: {result.search_results.get('processing_time_ms', 0):.2f}ms")

                    # Check if trace exists
                    if 'trace' in result.search_results:
                        trace = result.search_results['trace']
                        print(f"   🔍 TRACE AVAILABLE:")
                        print(f"     - Steps: {len(trace.get('steps', []))}")
                        print(f"     - Total time: {trace.get('total_time_ms', 0):.2f}ms")
                        print(f"     - Notes: {len(trace.get('notes', []))}")

                        # Show steps details
                        for step_idx, step in enumerate(trace.get('steps', []), 1):
                            stage = step.get('stage', 'unknown')
                            took_ms = step.get('took_ms', 0)
                            hits_count = step.get('hits_count', 0)
                            best_score = step.get('best_score', 0)
                            print(f"     Step {step_idx}: {stage} - {hits_count} hits, best_score={best_score:.3f}, {took_ms:.1f}ms")

                            # Check for escalation indicators
                            meta = step.get('meta', {})
                            if meta.get('escalation_triggered'):
                                print(f"       ✅ Escalation triggered!")
                    else:
                        print(f"   ❌ NO TRACE in search_results")
                else:
                    print(f"   ❌ NO search_results")

                # Check decision
                if result.decision:
                    risk_level = result.decision.get('risk_level', 'unknown')
                    print(f"   📊 Risk level: {risk_level}")

            except Exception as test_e:
                print(f"   ❌ TEST ERROR: {test_e}")
                import traceback
                traceback.print_exc()

    except Exception as e:
        print(f"❌ Setup error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("SEARCH TRACE TEST COMPLETE")

if __name__ == "__main__":
    asyncio.run(test_search_trace())
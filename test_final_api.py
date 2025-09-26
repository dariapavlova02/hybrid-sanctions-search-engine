#!/usr/bin/env python3
"""
Final test to verify the complete pipeline works for organization classification.
"""

import sys
sys.path.append('src')

from ai_service.core.orchestrator_factory import OrchestratorFactory
import asyncio
import json

async def test_final_api():
    """Test the unified orchestrator (simulates full API)."""
    print("🧪 FINAL API TEST - UNIFIED ORCHESTRATOR")
    print("=" * 50)

    try:
        # Create unified orchestrator using factory (this is what API uses)
        orchestrator = await OrchestratorFactory.create_orchestrator()

        test_cases = [
            "Одін Марін Інкорпорейтед",  # Should be organization
            "Дарья Павлова",  # Should be person
            "ООО Тест",  # Should be organization
        ]

        for test_text in test_cases:
            print(f"\n🔍 Testing: '{test_text}'")

            # Process through full pipeline
            result = await orchestrator.process(test_text)

            print(f"Success: {result.success}")
            print(f"Normalized: '{result.normalized_text}'")

            # Check signals
            if hasattr(result, 'signals'):
                print(f"Persons: {len(result.signals.persons)}")
                for person in result.signals.persons:
                    print(f"  Person: {person.full_name}")

                print(f"Organizations: {len(result.signals.organizations)}")
                for org in result.signals.organizations:
                    print(f"  Org: '{org.core}' + '{org.legal_form}' = '{org.full}'")

            # Check decision
            if hasattr(result, 'decision') and result.decision is not None:
                print(f"Risk Level: {result.decision.risk_level}")
                print(f"Risk Score: {result.decision.risk_score:.3f}")
            else:
                print("Decision engine not enabled")

            # Expected results
            if "Інкорпорейтед" in test_text or "ООО" in test_text:
                if len(result.signals.organizations) > 0:
                    print(f"✅ Correctly identified as organization")
                else:
                    print(f"❌ Failed: Should be organization")
            else:
                if len(result.signals.persons) > 0 and len(result.signals.organizations) == 0:
                    print(f"✅ Correctly identified as person")
                else:
                    print(f"❌ Failed: Should be person")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_final_api())
#!/usr/bin/env python3
"""
Test sanctions scoring for Ukrainian organizations.
"""

import sys
sys.path.append('src')

from ai_service.core.orchestrator_factory import OrchestratorFactory
import asyncio

async def test_sanctions_scoring():
    """Test that Ukrainian organizations get proper high risk scoring."""
    print("🎯 SANCTIONS SCORING TEST")
    print("=" * 50)

    try:
        # Create orchestrator with decision engine enabled
        orchestrator = await OrchestratorFactory.create_orchestrator(
            enable_decision_engine=True,
            enable_search=True  # Need search for sanctions matching
        )

        test_cases = [
            "Одін Марін Інкорпорейтед",  # Target organization
            "Невинна Компанія ТОВ",      # Non-sanctioned organization
        ]

        for test_text in test_cases:
            print(f"\n🔍 Testing: '{test_text}'")

            # Process through full pipeline with decision engine
            result = await orchestrator.process(test_text)

            print(f"Success: {result.success}")
            print(f"Normalized: '{result.normalized_text}'")

            # Check organizations detected
            if hasattr(result, 'signals'):
                print(f"Organizations: {len(result.signals.organizations)}")
                for org in result.signals.organizations:
                    print(f"  Org: '{org.core}' + '{org.legal_form}' = '{org.full}'")

            # Check decision and risk scoring
            if hasattr(result, 'decision') and result.decision is not None:
                print(f"Risk Level: {result.decision.risk}")
                print(f"Risk Score: {result.decision.score:.3f}")
                print(f"Reasons: {result.decision.reasons}")

                # Check if high risk for sanctioned entity
                if "Одін Марін" in test_text:
                    if result.decision.risk.value == "HIGH":
                        print("✅ Correctly scored as HIGH risk (sanctioned)")
                    else:
                        print(f"❌ Expected HIGH risk, got {result.decision.risk.value}")
                else:
                    if result.decision.risk.value in ["LOW", "MEDIUM"]:
                        print("✅ Correctly scored as non-sanctioned")
                    else:
                        print(f"❌ Expected LOW/MEDIUM risk, got {result.decision.risk.value}")
            else:
                print("❌ Decision engine not working")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_sanctions_scoring())
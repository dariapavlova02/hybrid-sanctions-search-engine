#!/usr/bin/env python3
"""
Test Decision Engine directly with mock data
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_decision_engine_direct():
    """Test Decision Engine directly with sanctions search results"""

    print("🔍 Testing Decision Engine directly")
    print("=" * 60)

    try:
        from ai_service.core.decision_engine import DecisionEngine
        from ai_service.config.settings import DecisionConfig, DECISION_CONFIG

        # Initialize decision engine with default config
        config = DECISION_CONFIG
        decision_engine = DecisionEngine(config)

        print(f"📊 Decision Engine Configuration:")
        print(f"  Search exact weight: {config.w_search_exact}")
        print(f"  Exact match bonus: {config.bonus_exact_match}")
        print(f"  Medium threshold: {config.thr_medium}")
        print(f"  High threshold: {config.thr_high}")

        # Test case 1: IPN with sanctions match
        print(f"\n🧪 Test Case 1: IPN with sanctions match")

        # Import decision contracts
        from ai_service.contracts.decision_contracts import (
            DecisionInput, SmartFilterInfo, SignalsInfo, SimilarityInfo
        )
        from ai_service.contracts.search_contracts import SearchInfo

        # Create decision input with sanctions match
        decision_input = DecisionInput(
            text="ІПН 782611846337",
            language="uk",
            smartfilter=SmartFilterInfo(
                should_process=True,
                confidence=0.7
            ),
            signals=SignalsInfo(
                person_confidence=0.0,  # No person detected
                org_confidence=0.1     # Some org signals
            ),
            similarity=SimilarityInfo(
                cos_top=None,
                cos_p95=None
            ),
            search=SearchInfo(
                has_exact_matches=True,
                exact_confidence=0.98,
                total_matches=1,
                high_confidence_matches=1
            )
        )

        # Calculate decision
        decision = decision_engine.decide(decision_input)

        print(f"  Risk level: {decision.risk}")
        print(f"  Final score: {decision.score}")
        print(f"  Review required: {decision.review_required}")
        print(f"  Reasons: {decision.reasons}")
        if decision.details:
            print(f"  Details: {decision.details}")

        # Check if sanctions were properly factored in
        expected_high_risk = decision.score >= config.thr_high
        print(f"  Expected high risk due to sanctions: {'✅ YES' if expected_high_risk else '❌ NO'}")

        # Test case 2: No sanctions match
        print(f"\n🧪 Test Case 2: No sanctions match")

        decision_input_no_sanctions = DecisionInput(
            text="Дарья Павлова",
            language="uk",
            smartfilter=SmartFilterInfo(
                should_process=True,
                confidence=0.7
            ),
            signals=SignalsInfo(
                person_confidence=0.8,  # Strong person signals
                org_confidence=0.0     # No org signals
            ),
            similarity=SimilarityInfo(
                cos_top=None,
                cos_p95=None
            ),
            search=SearchInfo(
                has_exact_matches=False,
                exact_confidence=0.0,
                total_matches=0,
                high_confidence_matches=0
            )
        )

        decision_no_sanctions = decision_engine.decide(decision_input_no_sanctions)

        print(f"  Risk level: {decision_no_sanctions.risk}")
        print(f"  Final score: {decision_no_sanctions.score}")
        print(f"  Review required: {decision_no_sanctions.review_required}")

        # Compare scores
        score_difference = decision.score - decision_no_sanctions.score
        print(f"\n📊 Impact Analysis:")
        print(f"  Score with sanctions: {decision.score:.3f}")
        print(f"  Score without sanctions: {decision_no_sanctions.score:.3f}")
        print(f"  Sanctions impact: +{score_difference:.3f}")
        print(f"  Impact significant: {'✅ YES' if score_difference >= 0.2 else '❌ NO'}")

        # Test case 3: Edge case - borderline sanctions match
        print(f"\n🧪 Test Case 3: Borderline sanctions match")

        decision_input_borderline = DecisionInput(
            text="ІПН 782611846337",
            language="uk",
            smartfilter=SmartFilterInfo(
                should_process=True,
                confidence=0.7
            ),
            signals=SignalsInfo(
                person_confidence=0.0,
                org_confidence=0.1
            ),
            similarity=SimilarityInfo(
                cos_top=None,
                cos_p95=None
            ),
            search=SearchInfo(
                has_exact_matches=True,
                exact_confidence=0.75,  # Lower confidence
                total_matches=1,
                high_confidence_matches=0  # Not high confidence
            )
        )

        decision_borderline = decision_engine.decide(decision_input_borderline)

        print(f"  Risk level: {decision_borderline.risk}")
        print(f"  Final score: {decision_borderline.score}")
        print(f"  Review required: {decision_borderline.review_required}")

        print(f"\n✅ Decision Engine integration test completed")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_decision_engine_direct()
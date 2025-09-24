#!/usr/bin/env python3
"""
Test end-to-end sanctions detection workflow
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_end_to_end_sanctions():
    """Test complete pipeline: normalization → signals → sanctions search → decision"""

    print("🔍 Testing end-to-end sanctions detection workflow")
    print("=" * 70)

    try:
        # Test the normalization → signals → decision flow
        from ai_service.layers.normalization.normalization_service import NormalizationService
        from ai_service.core.decision_engine import DecisionEngine
        from ai_service.config.settings import DECISION_CONFIG
        from ai_service.contracts.decision_contracts import (
            DecisionInput, SmartFilterInfo, SignalsInfo, SimilarityInfo
        )
        from ai_service.contracts.search_contracts import SearchInfo

        # Initialize services
        normalization_service = NormalizationService()
        decision_engine = DecisionEngine(DECISION_CONFIG)

        print("📊 Testing IPN detection pipeline")

        # Step 1: Normalization with IPN
        test_text = "ІПН 782611846337"
        print(f"📝 Input: '{test_text}'")

        normalization_result = normalization_service.normalize(
            text=test_text,
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"\n🔧 Normalization Results:")
        print(f"  Normalized: '{normalization_result.normalized}'")
        print(f"  Tokens: {normalization_result.tokens}")

        # Check business signals
        business_signals = []
        for trace in normalization_result.trace:
            if hasattr(trace, 'role') and trace.role in ['document', 'business_id']:
                business_signals.append((trace.token, trace.role))

        print(f"  Business signals: {business_signals}")

        # Step 2: Mock Signals Service (would extract IPN for sanctions search)
        ipn_detected = "782611846337" in normalization_result.tokens
        document_marker_detected = "ІПН" in normalization_result.tokens

        print(f"\n💼 Signals Service Analysis:")
        print(f"  IPN number detected: {'✅ YES' if ipn_detected else '❌ NO'}")
        print(f"  Document marker detected: {'✅ YES' if document_marker_detected else '❌ NO'}")

        # Step 3: Mock Sanctions Search (would check IPN against sanctions lists)
        # In real implementation, this would query elasticsearch or sanctions database
        sanctions_match_found = ipn_detected  # Simulate finding IPN in sanctions
        sanctions_confidence = 0.95 if sanctions_match_found else 0.0

        print(f"\n🔍 Sanctions Search (Mock):")
        print(f"  Sanctions match found: {'✅ YES' if sanctions_match_found else '❌ NO'}")
        print(f"  Confidence: {sanctions_confidence}")

        # Step 4: Decision Engine Integration
        decision_input = DecisionInput(
            text=test_text,
            language="uk",
            smartfilter=SmartFilterInfo(
                should_process=True,
                confidence=0.6  # Moderate confidence from smart filter
            ),
            signals=SignalsInfo(
                person_confidence=0.0,  # No person detected
                org_confidence=0.2 if document_marker_detected else 0.0  # IPN marker gives some org signal
            ),
            similarity=SimilarityInfo(
                cos_top=None,
                cos_p95=None
            ),
            search=SearchInfo(
                has_exact_matches=sanctions_match_found,
                exact_confidence=sanctions_confidence,
                total_matches=1 if sanctions_match_found else 0,
                high_confidence_matches=1 if sanctions_confidence >= 0.8 else 0
            ) if sanctions_match_found else SearchInfo()
        )

        decision = decision_engine.decide(decision_input)

        print(f"\n⚖️  Decision Engine Results:")
        print(f"  Risk level: {decision.risk}")
        print(f"  Final score: {decision.score:.3f}")
        print(f"  Review required: {decision.review_required}")

        # Step 5: Expected Business Logic
        expected_high_risk = sanctions_match_found and sanctions_confidence >= 0.9
        expected_block = decision.score >= DECISION_CONFIG.thr_high

        print(f"\n📋 Business Logic Validation:")
        print(f"  Should block transaction: {'✅ YES' if expected_block else '❌ NO'}")
        print(f"  Risk escalation working: {'✅ YES' if decision.score > 0.5 else '❌ NO'}")

        # Success criteria
        success_criteria = [
            ("IPN detected", ipn_detected),
            ("Business signals preserved", len(business_signals) >= 2),
            ("Sanctions impact", decision.score >= 0.7),
            ("Risk escalation", decision.risk.value in ['medium', 'high'])
        ]

        print(f"\n✅ Success Criteria:")
        all_passed = True
        for criterion, passed in success_criteria:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {criterion}: {status}")
            if not passed:
                all_passed = False

        print(f"\n{'🎉 SUCCESS' if all_passed else '❌ ISSUES'}: End-to-end sanctions detection {'works' if all_passed else 'has problems'}")

        # Additional test: Compare with non-sanctions case
        print(f"\n🆚 Comparison Test: Normal name vs IPN")

        normal_name_result = normalization_service.normalize(
            text="Дарья Павлова",
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        normal_decision_input = DecisionInput(
            text="Дарья Павлова",
            language="uk",
            smartfilter=SmartFilterInfo(
                should_process=True,
                confidence=0.8  # Higher confidence for clear name
            ),
            signals=SignalsInfo(
                person_confidence=0.9,  # Strong person signals
                org_confidence=0.0     # No org signals
            ),
            similarity=SimilarityInfo(
                cos_top=None,
                cos_p95=None
            ),
            search=SearchInfo()  # No search results
        )

        normal_decision = decision_engine.decide(normal_decision_input)

        print(f"  Normal name score: {normal_decision.score:.3f} ({normal_decision.risk.value})")
        print(f"  IPN case score: {decision.score:.3f} ({decision.risk.value})")
        print(f"  Risk escalation: +{decision.score - normal_decision.score:.3f}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_end_to_end_sanctions()
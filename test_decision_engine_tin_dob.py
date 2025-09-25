#!/usr/bin/env python3

"""
Test DecisionEngine TIN+DOB logic improvements.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_decision_engine_tin_dob():
    """Test DecisionEngine TIN+DOB matching logic."""
    print("🔍 TESTING DECISION ENGINE TIN+DOB LOGIC")
    print("=" * 60)

    try:
        from ai_service.core.decision_engine import DecisionEngine
        from ai_service.contracts.decision_contracts import (
            DecisionInput, SmartFilterInfo, SignalsInfo, SimilarityInfo, RiskLevel
        )
        from ai_service.contracts.search_contracts import SearchInfo, Candidate, SearchType

        print("✅ Successfully imported DecisionEngine components")

        # Create decision engine
        decision_engine = DecisionEngine()

        # Test cases
        test_cases = [
            {
                "name": "ID match confirmed - should be HIGH risk",
                "signals": SignalsInfo(
                    person_confidence=0.9,
                    org_confidence=0.1,
                    id_match=True,  # This should trigger HIGH risk immediately
                    date_match=False
                ),
                "expected_risk": RiskLevel.HIGH,
                "expected_review_required": False,  # No additional fields needed
                "expected_reasons_contain": ["🚨 SANCTIONED ID MATCH CONFIRMED"]
            },
            {
                "name": "TIN+DOB candidate match - should be HIGH risk",
                "signals": SignalsInfo(
                    person_confidence=0.85,
                    org_confidence=0.1,
                    id_match=False,
                    date_match=False
                ),
                "search": SearchInfo(
                    has_exact_matches=False,
                    total_matches=1,
                    fusion_candidates=[
                        Candidate(
                            entity_id="SANCTION_001",
                            entity_type="person",
                            normalized_name="Петров Иван Васильевич",
                            aliases=["Ivan Petrov"],
                            country="UA",
                            dob="1985-03-15",  # DOB present
                            meta={"inn": "782611846337"},  # TIN present
                            final_score=0.85,  # High score
                            ac_score=0.8,
                            vector_score=0.9,
                            features={},
                            search_type=SearchType.FUSION
                        )
                    ]
                ),
                "expected_risk": RiskLevel.HIGH,
                "expected_review_required": False,  # No additional fields needed
                "expected_reasons_contain": ["🚨 TIN+DOB SANCTIONS MATCH"]
            },
            {
                "name": "High confidence match without TIN+DOB - should be HIGH risk",
                "signals": SignalsInfo(
                    person_confidence=0.85,
                    org_confidence=0.1,
                    id_match=False,
                    date_match=False
                ),
                "search": SearchInfo(
                    has_exact_matches=False,
                    total_matches=1,
                    high_confidence_matches=1,
                    fusion_candidates=[
                        Candidate(
                            entity_id="SANCTION_002",
                            entity_type="person",
                            normalized_name="Иванов Петр Николаевич",
                            aliases=["Petr Ivanov"],
                            country="RU",
                            dob=None,  # No DOB
                            meta={},  # No TIN
                            final_score=0.92,  # Very high score
                            ac_score=0.9,
                            vector_score=0.94,
                            features={},
                            search_type=SearchType.FUSION
                        )
                    ]
                ),
                "expected_risk": RiskLevel.HIGH,
                "expected_review_required": True,  # Should request additional fields
                "expected_reasons_contain": ["🚨 HIGH CONFIDENCE SANCTIONS MATCH"]
            },
            {
                "name": "Strong name match but low search score - should request fields",
                "signals": SignalsInfo(
                    person_confidence=0.85,
                    org_confidence=0.1,
                    id_match=False,
                    date_match=False
                ),
                "search": SearchInfo(
                    has_exact_matches=False,
                    total_matches=1,
                    fusion_candidates=[
                        Candidate(
                            entity_id="SANCTION_003",
                            entity_type="person",
                            normalized_name="Сидоров Сергей Александрович",
                            aliases=["Sergey Sidorov"],
                            country="UA",
                            dob=None,
                            meta={},
                            final_score=0.75,  # Moderate score
                            ac_score=0.7,
                            vector_score=0.8,
                            features={},
                            search_type=SearchType.FUSION
                        )
                    ]
                ),
                "expected_risk": RiskLevel.HIGH,  # Score should put it in HIGH
                "expected_review_required": True,  # Should request additional fields
                "expected_reasons_contain": ["Overall risk score"]
            }
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}. TEST: {test_case['name']}")

            try:
                # Create decision input
                decision_input = DecisionInput(
                    text="Test text",
                    language="uk",
                    smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
                    signals=test_case['signals'],
                    similarity=SimilarityInfo(cos_top=0.7),
                    search=test_case.get('search')
                )

                # Make decision
                result = decision_engine.decide(decision_input)

                print(f"   📋 Decision Result:")
                print(f"     Risk Level: {result.risk.value}")
                print(f"     Score: {result.score:.3f}")
                print(f"     Review Required: {result.review_required}")
                print(f"     Required Fields: {result.required_additional_fields}")
                print(f"     Reasons: {result.reasons}")

                # Check expected risk level
                if result.risk == test_case['expected_risk']:
                    print(f"   ✅ Risk level correct: {result.risk.value}")
                else:
                    print(f"   ❌ Risk level WRONG: expected {test_case['expected_risk'].value}, got {result.risk.value}")

                # Check review required
                if result.review_required == test_case['expected_review_required']:
                    print(f"   ✅ Review requirement correct: {result.review_required}")
                else:
                    print(f"   ❌ Review requirement WRONG: expected {test_case['expected_review_required']}, got {result.review_required}")

                # Check reasons contain expected strings
                reasons_text = " ".join(result.reasons)
                reasons_match = all(
                    expected_reason in reasons_text
                    for expected_reason in test_case.get('expected_reasons_contain', [])
                )

                if reasons_match:
                    print(f"   ✅ Reasons contain expected content")
                else:
                    print(f"   ❌ Reasons MISSING expected content: {test_case.get('expected_reasons_contain', [])}")

            except Exception as test_e:
                print(f"   ❌ TEST ERROR: {test_e}")
                import traceback
                traceback.print_exc()

    except Exception as e:
        print(f"❌ Setup error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("DECISION ENGINE TIN+DOB TEST COMPLETE")

if __name__ == "__main__":
    test_decision_engine_tin_dob()
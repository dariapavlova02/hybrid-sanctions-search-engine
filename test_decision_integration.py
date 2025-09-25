#!/usr/bin/env python3

"""
Test DecisionEngine integration with signals and search.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_decision_integration():
    """Test DecisionEngine integration with realistic signals."""
    print("🔍 TESTING DECISION ENGINE INTEGRATION")
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

        # Realistic test cases that should happen in production
        test_cases = [
            {
                "name": "Poroshenko case - INN match",
                "text": "Порошенко Петро Олексійович ІПН 123456789012",
                "signals": SignalsInfo(
                    person_confidence=0.95,
                    org_confidence=0.0,
                    id_match=True,  # INN found in sanctions
                    date_match=False,
                    evidence={
                        "extracted_ids": ["123456789012"],
                        "extracted_dates": []
                    }
                ),
                "search": SearchInfo(
                    has_exact_matches=True,
                    exact_confidence=0.98,
                    total_matches=1,
                    high_confidence_matches=1,
                    fusion_candidates=[
                        Candidate(
                            entity_id="UA_SANCTION_001",
                            entity_type="person",
                            normalized_name="Порошенко Петро Олексійович",
                            aliases=["Petro Poroshenko", "П.О. Порошенко"],
                            country="UA",
                            dob="1965-09-26",
                            meta={"inn": "123456789012", "position": "Former President"},
                            final_score=0.98,
                            ac_score=0.95,
                            vector_score=0.92,
                            features={"name_match": True, "id_match": True},
                            search_type=SearchType.EXACT
                        )
                    ]
                ),
                "expected_risk": RiskLevel.HIGH,
                "expected_review_required": False,
                "expected_reasons_should_contain": ["🚨 SANCTIONED ID MATCH CONFIRMED"]
            },
            {
                "name": "Oligarch case - Name + DOB + EDRPOU match",
                "text": "Коломойський Ігор Валерійович дата народження 13.02.1963 ЄДРПОУ 87654321",
                "signals": SignalsInfo(
                    person_confidence=0.90,
                    org_confidence=0.0,
                    id_match=False,  # EDRPOU not directly matched as person ID
                    date_match=True,  # DOB matches
                    evidence={
                        "extracted_ids": ["87654321"],
                        "extracted_dates": ["1963-02-13"]
                    }
                ),
                "search": SearchInfo(
                    has_exact_matches=True,
                    exact_confidence=0.94,
                    total_matches=1,
                    high_confidence_matches=1,
                    fusion_candidates=[
                        Candidate(
                            entity_id="UA_SANCTION_002",
                            entity_type="person",
                            normalized_name="Коломойський Ігор Валерійович",
                            aliases=["Igor Kolomoisky", "Ihor Kolomoyskyy"],
                            country="UA",
                            dob="1963-02-13",  # DOB matches
                            meta={"edrpou": "87654321", "position": "Businessman"},  # EDRPOU matches
                            final_score=0.94,
                            ac_score=0.92,
                            vector_score=0.96,
                            features={"name_match": True, "dob_match": True, "edrpou_match": True},
                            search_type=SearchType.EXACT
                        )
                    ]
                ),
                "expected_risk": RiskLevel.HIGH,
                "expected_review_required": False,
                "expected_reasons_should_contain": ["🚨 TIN+DOB SANCTIONS MATCH"]
            },
            {
                "name": "Close name match but no identifiers - should request TIN/DOB",
                "text": "Петров Иван Васильевич",
                "signals": SignalsInfo(
                    person_confidence=0.88,
                    org_confidence=0.0,
                    id_match=False,
                    date_match=False,
                    evidence={
                        "extracted_ids": [],
                        "extracted_dates": []
                    }
                ),
                "search": SearchInfo(
                    has_exact_matches=False,
                    total_matches=1,
                    high_confidence_matches=0,
                    fusion_candidates=[
                        Candidate(
                            entity_id="RU_SANCTION_001",
                            entity_type="person",
                            normalized_name="Петров Иван Васильевич",
                            aliases=["Ivan Petrov"],
                            country="RU",
                            dob="1975-05-12",  # Has DOB in sanctions
                            meta={"inn": "987654321098"},  # Has INN in sanctions
                            final_score=0.82,  # High but not extreme
                            ac_score=0.85,
                            vector_score=0.79,
                            features={"name_match": True},
                            search_type=SearchType.PHRASE
                        )
                    ]
                ),
                "expected_risk": RiskLevel.HIGH,  # Strong score should make it HIGH
                "expected_review_required": True,  # Should request TIN+DOB
                "expected_reasons_should_contain": ["Overall risk score"]
            }
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}. TEST: {test_case['name']}")
            print(f"   Text: '{test_case['text']}'")

            try:
                # Create decision input
                decision_input = DecisionInput(
                    text=test_case['text'],
                    language="uk",
                    smartfilter=SmartFilterInfo(should_process=True, confidence=0.9),
                    signals=test_case['signals'],
                    similarity=SimilarityInfo(cos_top=0.8),
                    search=test_case['search']
                )

                # Make decision
                result = decision_engine.decide(decision_input)

                print(f"   📋 Decision Result:")
                print(f"     Risk Level: {result.risk.value}")
                print(f"     Score: {result.score:.3f}")
                print(f"     Review Required: {result.review_required}")
                print(f"     Required Fields: {result.required_additional_fields}")

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

                # Check reasons
                reasons_text = " ".join(result.reasons)
                for expected_reason in test_case.get('expected_reasons_should_contain', []):
                    if expected_reason in reasons_text:
                        print(f"   ✅ Contains expected reason: {expected_reason}")
                    else:
                        print(f"   ❌ Missing expected reason: {expected_reason}")

                print(f"   📝 Full reasons: {result.reasons}")

            except Exception as test_e:
                print(f"   ❌ TEST ERROR: {test_e}")
                import traceback
                traceback.print_exc()

    except Exception as e:
        print(f"❌ Setup error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("DECISION ENGINE INTEGRATION TEST COMPLETE")

if __name__ == "__main__":
    test_decision_integration()
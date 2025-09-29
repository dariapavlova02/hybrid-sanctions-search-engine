#!/usr/bin/env python3
"""
Debug risk calculation for Ulianova case.
"""

def analyze_risk_calculation():
    """Analyze why risk is MEDIUM despite high search score."""
    print("🔍 RISK CALCULATION ANALYSIS")
    print("=" * 50)

    # Data from the response
    search_vector_confidence = 0.90271816
    risk_score = 0.6424245838364445
    risk_level = "medium"

    print(f"📊 Search Results:")
    print(f"   Vector confidence: {search_vector_confidence:.3f} (HIGH!)")
    print(f"   Total matches: 2")
    print(f"   Match type: vector (not exact)")

    print(f"\n⚖️ Risk Assessment:")
    print(f"   Final risk score: {risk_score:.3f}")
    print(f"   Risk level: {risk_level.upper()}")
    print(f"   Threshold for HIGH: 0.7")

    print(f"\n📈 Score Breakdown:")
    score_breakdown = {
        "smartfilter_contribution": 0.056745043836444437,
        "person_contribution": 0.21,
        "org_contribution": 0,
        "similarity_contribution": 0,
        "search_contribution": 0.37567954,
    }

    for component, value in score_breakdown.items():
        print(f"   {component}: {value:.3f}")

    print(f"\n🔍 Key Observations:")
    print(f"1. Search type is 'vector', not 'exact'")
    print(f"   - Vector matches have weight: 0.25")
    print(f"   - Exact matches would have weight: 0.25 (but different threshold)")

    print(f"\n2. Search contribution calculation:")
    print(f"   search_contribution = 0.376")
    print(f"   This seems LOW for 0.9 confidence!")

    print(f"\n3. Thresholds:")
    print(f"   - Vector threshold (thr_search_vector): 0.9")
    print(f"   - Exact threshold (thr_search_exact): 0.8")
    print(f"   - High risk threshold (thr_high): 0.7")

    print(f"\n❌ PROBLEM IDENTIFIED:")
    print(f"   Vector confidence 0.903 > threshold 0.9")
    print(f"   But contribution is only 0.376 (should be higher!)")

    print(f"\n💡 LIKELY ISSUE:")
    print(f"   The search contribution might be scaled down")
    print(f"   OR vector matches are not weighted properly")

    # Calculate what the contribution should be
    w_search_vector = 0.25
    expected_contribution = search_vector_confidence * w_search_vector * 4  # 4 search types
    print(f"\n📐 Expected search contribution:")
    print(f"   {search_vector_confidence:.3f} * {w_search_vector} * 4 = {expected_contribution:.3f}")
    print(f"   But actual is: 0.376")

    # Check if it's a scaling issue
    print(f"\n🔧 Possible fixes:")
    print(f"   1. Increase vector match weight")
    print(f"   2. Lower vector threshold from 0.9 to 0.8")
    print(f"   3. Add bonus for high-confidence vector matches")
    print(f"   4. Check if vector contribution is being calculated correctly")

if __name__ == "__main__":
    analyze_risk_calculation()
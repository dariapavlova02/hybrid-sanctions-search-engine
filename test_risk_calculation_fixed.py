#!/usr/bin/env python3
"""
Test new risk calculation with updated vector weights.
"""

def calculate_new_risk():
    """Calculate risk with new vector weight."""
    print("🔧 NEW RISK CALCULATION TEST")
    print("=" * 50)

    # Original data
    vector_confidence = 0.90271816
    smartfilter_contrib = 0.056745043836444437
    person_contrib = 0.21

    # OLD weights
    old_w_vector = 0.25  # From API response
    old_thr_vector = 0.9

    # NEW weights
    new_w_vector = 0.4
    new_thr_vector = 0.8

    # Bonuses
    bonus_multiple = 0.1  # 2 matches > 1
    bonus_high_conf = 0.05  # high confidence matches > 0

    print(f"📊 Input Data:")
    print(f"   Vector confidence: {vector_confidence:.3f}")
    print(f"   SmartFilter contribution: {smartfilter_contrib:.3f}")
    print(f"   Person contribution: {person_contrib:.3f}")

    print(f"\n⚖️ OLD Configuration:")
    print(f"   w_search_vector: {old_w_vector}")
    print(f"   thr_search_vector: {old_thr_vector}")

    # OLD calculation
    old_passes_threshold = vector_confidence >= old_thr_vector
    old_search_contrib = 0
    if old_passes_threshold:
        old_search_contrib = old_w_vector * vector_confidence + bonus_multiple + bonus_high_conf

    old_total = smartfilter_contrib + person_contrib + old_search_contrib

    print(f"   Passes threshold: {old_passes_threshold}")
    print(f"   Search contribution: {old_search_contrib:.3f}")
    print(f"   Total risk score: {old_total:.3f}")
    print(f"   Risk level: {'HIGH' if old_total >= 0.7 else 'MEDIUM'}")

    print(f"\n🔧 NEW Configuration:")
    print(f"   w_search_vector: {new_w_vector}")
    print(f"   thr_search_vector: {new_thr_vector}")

    # NEW calculation
    new_passes_threshold = vector_confidence >= new_thr_vector
    new_search_contrib = 0
    if new_passes_threshold:
        new_search_contrib = new_w_vector * vector_confidence + bonus_multiple + bonus_high_conf

    new_total = smartfilter_contrib + person_contrib + new_search_contrib

    print(f"   Passes threshold: {new_passes_threshold}")
    print(f"   Search contribution: {new_search_contrib:.3f}")
    print(f"   Total risk score: {new_total:.3f}")
    print(f"   Risk level: {'HIGH' if new_total >= 0.7 else 'MEDIUM'}")

    print(f"\n📈 IMPROVEMENT:")
    improvement = new_total - old_total
    print(f"   Score improvement: +{improvement:.3f}")

    if new_total >= 0.7 and old_total < 0.7:
        print(f"   🎉 Risk level upgraded: MEDIUM → HIGH!")
    elif new_total >= 0.7:
        print(f"   ✅ Risk level remains HIGH")
    else:
        print(f"   ⚠️ Risk level still MEDIUM (need {0.7 - new_total:.3f} more)")

if __name__ == "__main__":
    calculate_new_risk()
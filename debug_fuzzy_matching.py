#!/usr/bin/env python3

"""
Debug fuzzy matching logic.
"""

def debug_fuzzy_matching():
    """Debug the fuzzy matching logic from MockSearchService."""
    print("🔍 DEBUG FUZZY MATCHING")
    print("=" * 50)

    # Test data
    query = "Коврико Роман"
    person_text = "Ковриков Роман Валерійович"

    query_lower = query.lower()
    person_lower = person_text.lower()

    print(f"Query: '{query}' -> '{query_lower}'")
    print(f"Person: '{person_text}' -> '{person_lower}'")

    query_tokens = query_lower.split()
    person_tokens = person_lower.split()

    print(f"Query tokens: {query_tokens}")
    print(f"Person tokens: {person_tokens}")

    print("\n🔍 Token matching:")

    # Check if query tokens are partial matches or have similar prefixes
    matching_tokens = 0
    for i, q_token in enumerate(query_tokens):
        print(f"\n  Query token [{i}]: '{q_token}' (len={len(q_token)})")

        found_match = False
        for j, p_token in enumerate(person_tokens):
            print(f"    vs Person token [{j}]: '{p_token}' (len={len(p_token)})")

            # Prefix matching (e.g., "коврико" matches "ковриков")
            if len(q_token) >= 3 and (p_token.startswith(q_token) or q_token.startswith(p_token)):
                print(f"      ✅ PREFIX MATCH: '{q_token}' <-> '{p_token}'")
                matching_tokens += 1
                found_match = True
                break
            # Exact token match
            elif q_token == p_token:
                print(f"      ✅ EXACT MATCH: '{q_token}' == '{p_token}'")
                matching_tokens += 1
                found_match = True
                break
            else:
                print(f"      ❌ No match: '{q_token}' vs '{p_token}'")

        if not found_match:
            print(f"    ❌ No match found for '{q_token}'")

    print(f"\n📊 Results:")
    print(f"  Total matching tokens: {matching_tokens}")
    print(f"  Query tokens: {len(query_tokens)}")
    print(f"  Person tokens: {len(person_tokens)}")

    # Calculate fuzzy match score
    if matching_tokens > 0:
        match_ratio = matching_tokens / max(len(query_tokens), len(person_tokens))
        print(f"  Match ratio: {matching_tokens} / {max(len(query_tokens), len(person_tokens))} = {match_ratio:.3f}")

        if match_ratio >= 0.5:  # At least 50% tokens match
            base_score = 0.95  # person.score from MockSearchService
            final_score = base_score * match_ratio * 1.05  # 105% of original score for fuzzy
            print(f"  ✅ MATCH! Final score: {base_score} * {match_ratio:.3f} * 1.05 = {final_score:.3f}")

            # Check against threshold
            threshold = 0.7
            if final_score >= threshold:
                print(f"  ✅ PASSES THRESHOLD: {final_score:.3f} >= {threshold}")
            else:
                print(f"  ❌ FAILS THRESHOLD: {final_score:.3f} < {threshold}")
        else:
            print(f"  ❌ INSUFFICIENT MATCH RATIO: {match_ratio:.3f} < 0.5")
    else:
        print(f"  ❌ NO MATCHING TOKENS")

if __name__ == "__main__":
    debug_fuzzy_matching()
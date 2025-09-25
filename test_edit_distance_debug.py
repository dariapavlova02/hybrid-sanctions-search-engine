#!/usr/bin/env python3

"""
Отладка edit distance для случая "Коврико Роман" vs "Ковриков Роман".
"""

def edit_distance(s1, s2):
    s1, s2 = s1.lower(), s2.lower()
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2 + 1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]

def analyze_fuzzy_match(query, result):
    """Анализ fuzzy match с той же логикой что в коде."""
    print(f"🔍 Анализ: '{query}' vs '{result}'")

    # Edit distance
    edit_dist = edit_distance(query, result)
    max_len = max(len(query), len(result))
    edit_ratio = 1.0 - (edit_dist / max_len) if max_len > 0 else 0

    print(f"   Edit distance: {edit_dist}")
    print(f"   Edit ratio: {edit_ratio:.3f}")

    # Max allowed edits check
    if len(query) < 15:
        max_allowed_edits = 3
    else:
        max_allowed_edits = max(3, len(query) // 5)

    print(f"   Max allowed edits: {max_allowed_edits}")
    print(f"   Passes edit filter: {edit_dist <= max_allowed_edits}")

    # Word similarity
    query_parts = set(query.lower().split())
    result_parts = set(result.lower().split())
    if query_parts and result_parts:
        overlap = len(query_parts.intersection(result_parts))
        total_unique = len(query_parts.union(result_parts))
        word_similarity = overlap / total_unique if total_unique > 0 else 0
    else:
        word_similarity = 0

    print(f"   Query words: {query_parts}")
    print(f"   Result words: {result_parts}")
    print(f"   Word overlap: {overlap if 'overlap' in locals() else 0}/{total_unique if 'total_unique' in locals() else 0}")
    print(f"   Word similarity: {word_similarity:.3f}")

    # Combined score (simulating ES score of ~20)
    es_score = 20.0
    es_normalized = min(es_score / 50.0, 1.0)
    normalized_score = (es_normalized * 0.2) + (edit_ratio * 0.5) + (word_similarity * 0.3)

    # Penalty for low edit ratio
    if edit_ratio < 0.6:
        normalized_score *= 0.7
        print(f"   Applied edit ratio penalty")

    print(f"   ES score: {es_score}")
    print(f"   ES normalized: {es_normalized:.3f}")
    print(f"   Combined score: {normalized_score:.3f}")

    # Threshold check
    min_threshold = 0.4 if edit_ratio > 0.8 else 0.5
    print(f"   Min threshold: {min_threshold}")
    print(f"   Passes threshold: {normalized_score >= min_threshold}")

    return normalized_score >= min_threshold and edit_dist <= max_allowed_edits

def main():
    print("🧪 EDIT DISTANCE DEBUG TEST")
    print("=" * 50)

    # Реальные паттерны из ES индекса
    test_cases = [
        ("Коврико Роман", "Ковриков Роман"),  # Точный pattern
        ("Коврико Роман", "Ковриков Роман Валерійович"),  # Полное имя
        ("Дарья Павлова Юрьевна", "Волочков П. Павлович"),  # Аббревиатура pattern
        ("Дарья Павлова Юрьевна", "Волочков Павло Павлович"),  # Полное имя
        ("Роман Ковриков Анатольевич", "Ковриков Роман"),  # Короткий pattern
    ]

    for i, (query, result) in enumerate(test_cases, 1):
        print(f"\n--- Тест {i} ---")
        should_pass = analyze_fuzzy_match(query, result)
        print(f"   РЕЗУЛЬТАТ: {'✅ PASS' if should_pass else '❌ FAIL'}")

if __name__ == "__main__":
    main()
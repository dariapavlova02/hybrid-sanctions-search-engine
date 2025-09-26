#!/usr/bin/env python3
"""
Тест fuzzy поиска для гомоглиф-случая
"""

from fuzzywuzzy import fuzz
import sys

def test_fuzzy_search():
    """Тестируем fuzzy поиск вручную"""

    query = "Liudmyla Ulianova"
    target = "Ulianova Liudmyla Oleksandrivna"

    print("🔍 ТЕСТ FUZZY ПОИСКА")
    print("=" * 50)
    print(f"Query: '{query}'")
    print(f"Target: '{target}'")
    print()

    # Тестируем разные алгоритмы fuzzy
    scores = {
        "ratio": fuzz.ratio(query, target),
        "partial_ratio": fuzz.partial_ratio(query, target),
        "token_sort_ratio": fuzz.token_sort_ratio(query, target),
        "token_set_ratio": fuzz.token_set_ratio(query, target),
    }

    print("📊 РЕЗУЛЬТАТЫ:")
    for algo, score in scores.items():
        print(f"  {algo:18}: {score:3d} ({score/100:.3f})")

    print()
    best_algo = max(scores, key=scores.get)
    best_score = scores[best_algo]

    print(f"🏆 ЛУЧШИЙ: {best_algo} = {best_score} ({best_score/100:.3f})")
    print(f"✅ Порог 65%: {'PASS' if best_score >= 65 else 'FAIL'}")
    print(f"✅ Порог 80%: {'PASS' if best_score >= 80 else 'FAIL'}")

    return best_score / 100

def test_other_candidates():
    """Тестируем другие похожие кандидаты"""

    query = "Liudmyla Ulianova"

    # Примеры других кандидатов из логов
    other_candidates = [
        "Kerimova Hulnara Suleimanivna",
        "Mukhin Oleksii Oleksiiovych",
        "Кавджарадзе Максим Геннадійович",
        "Трушанов Валерій Валерійович",
        "Sulimov",  # Из первого теста
    ]

    print(f"\n🔍 СРАВНЕНИЕ С ДРУГИМИ КАНДИДАТАМИ:")
    print("=" * 50)

    for candidate in other_candidates:
        score = fuzz.partial_ratio(query, candidate)
        print(f"{candidate:35}: {score:3d} ({score/100:.3f})")

    # А теперь правильный кандидат
    correct_target = "Ulianova Liudmyla Oleksandrivna"
    correct_score = fuzz.partial_ratio(query, correct_target)
    print(f"{'='*50}")
    print(f"{'ПРАВИЛЬНЫЙ КАНДИДАТ':35}: {correct_score:3d} ({correct_score/100:.3f})")

    return correct_score / 100

def main():
    best_score = test_fuzzy_search()
    correct_score = test_other_candidates()

    print(f"\n🎯 ВЫВОД:")
    print(f"   • Правильный кандидат должен скорить: {correct_score:.3f}")
    print(f"   • Если fuzzy находит 'Kerimova' вместо 'Ulianova' - это баг в данных или алгоритме")
    print(f"   • Нужно проверить содержимое санкционного списка")

if __name__ == "__main__":
    main()
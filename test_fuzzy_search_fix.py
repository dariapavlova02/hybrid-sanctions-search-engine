#!/usr/bin/env python3

"""
Тест исправления fuzzy search в MockSearchService для AC режима.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_mock_search_fuzzy():
    """Тест fuzzy поиска в MockSearchService."""
    print("🔍 ТЕСТ FUZZY ПОИСКА В MOCKSEARCHSERVICE")
    print("=" * 60)

    try:
        from ai_service.layers.search.mock_search_service import MockSearchService
        from ai_service.layers.search.contracts import SearchMode, SearchOpts

        print("✅ MockSearchService и SearchMode импортированы")

        # Создаем mock search service
        search_service = MockSearchService()
        # Ограничим количество персон для тестирования
        search_service._test_persons = search_service._test_persons[:5]  # Только первые 5
        search_service.initialize()

        print("✅ MockSearchService инициализирован")

        # Создаем mock NormalizationResult
        class MockNormResult:
            def __init__(self, normalized, tokens):
                self.normalized = normalized
                self.tokens = tokens
                self.trace = []
                self.language = "uk"
                self.confidence = 0.8
                self.original_length = len(normalized)
                self.normalized_length = len(normalized)
                self.token_count = len(tokens)
                self.processing_time = 0.1
                self.success = True

        # Тестируем fuzzy поиск
        test_cases = [
            ("Коврико Роман", "Ковриков Роман", SearchMode.AC),
            ("Коврико Роман", "Ковриков Роман", SearchMode.HYBRID),
            ("Коврико Роман", "Ковриков Роман", SearchMode.VECTOR),
        ]

        for query, expected, mode in test_cases:
            print(f"\n🧪 Тест: '{query}' → '{expected}' (режим: {mode.value})")

            norm_result = MockNormResult(query, query.split())
            search_opts = SearchOpts(
                top_k=10,
                threshold=0.5,  # Немного снизим порог для fuzzy matches
                search_mode=mode
            )
            print(f"   search_opts.search_mode = {search_opts.search_mode} (type: {type(search_opts.search_mode)})")

            try:
                candidates = await search_service.find_candidates(norm_result, query, search_opts)

                print(f"   Найдено кандидатов: {len(candidates)}")

                found_match = False
                for candidate in candidates:
                    print(f"   - {candidate.text} (score: {candidate.score:.3f}, confidence: {candidate.confidence:.3f})")
                    if "ковриков" in candidate.text.lower():
                        found_match = True
                        print(f"     ✅ FUZZY MATCH НАЙДЕН!")

                if not found_match:
                    print(f"     ❌ Fuzzy match НЕ найден для режима {mode.value}")
                    return False
                else:
                    print(f"     🎉 Fuzzy search работает для режима {mode.value}!")

            except Exception as e:
                print(f"     ❌ Ошибка поиска: {e}")
                return False

        print("\n🎉 ВСЕ ТЕСТЫ FUZZY ПОИСКА ПРОШЛИ!")
        return True

    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Главная функция."""
    print("🎯 ТЕСТ ИСПРАВЛЕНИЯ FUZZY SEARCH")
    print("=" * 50)

    success = await test_mock_search_fuzzy()

    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: Fuzzy search в MockSearchService исправлен!")
        print("   Теперь поиск 'Коврико Роман' найдет 'Ковриков Роман'")
    else:
        print("❌ FAILURE: Fuzzy search все еще не работает.")

    return success

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
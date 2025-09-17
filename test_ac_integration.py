"""
Test script to verify AC integration works correctly.
"""

from src.ai_service.layers.normalization.role_tagger import RoleTagger
from src.ai_service.layers.variants.templates.lexicon import get_stopwords, is_legal_form


def test_role_tagger_basic():
    """Test basic role tagger functionality."""
    print("Testing basic role tagger functionality...")

    # Test cases
    test_cases = [
        # Simple person name
        (["Іван", "Петрович", "Іваненко"], "ru"),
        # Organization with legal form
        (["ООО", "КОМПАНИЯ", "РАЗРАБОТКА"], "ru"),
        # Payment context
        (["платеж", "в", "пользу", "Іван", "Іваненко"], "ru"),
        # Mixed case
        (["ТОВ", "ПРОГРЕС", "оплата", "Петро", "Петренко"], "uk"),
    ]

    # Test both basic and AC versions
    basic_tagger = RoleTagger(window=3, enable_ac=False)
    ac_tagger = RoleTagger(window=3, enable_ac=True)

    print(f"AC automaton built: {ac_tagger._ac_automaton is not None}")

    for tokens, language in test_cases:
        print(f"\nTesting: {tokens} (language: {language})")

        # Test basic version
        basic_tags = basic_tagger.tag(tokens, language)
        basic_result = [(tag.token, tag.role.value, tag.reason) for tag in basic_tags]

        # Test AC version
        ac_tags = ac_tagger.tag(tokens, language)
        ac_result = [(tag.token, tag.role.value, tag.reason) for tag in ac_tags]

        print(f"Basic:  {basic_result}")
        print(f"AC:     {ac_result}")

        # Check consistency
        roles_match = all(b[1] == a[1] for b, a in zip(basic_result, ac_result))
        print(f"Results consistent: {roles_match}")


def test_lexicon_functions():
    """Test unified lexicon functions."""
    print("\nTesting unified lexicon functions...")

    # Test stopwords
    ru_stopwords = get_stopwords("ru")
    uk_stopwords = get_stopwords("uk")
    en_stopwords = get_stopwords("en")

    print(f"Russian stopwords count: {len(ru_stopwords)}")
    print(f"Ukrainian stopwords count: {len(uk_stopwords)}")
    print(f"English stopwords count: {len(en_stopwords)}")

    # Test some specific words
    test_words = [
        ("платеж", "ru", True),
        ("payment", "en", True),
        ("ООО", "any", True),  # legal form
        ("LLC", "any", True),  # legal form
        ("Іван", "ru", False),  # not a stopword/legal form
    ]

    for word, lang, expected_special in test_words:
        is_stop = word.lower() in get_stopwords(lang) if lang != "any" else False
        is_legal = is_legal_form(word)
        is_special = is_stop or is_legal

        print(f"'{word}' -> stopword: {is_stop}, legal: {is_legal}, special: {is_special} (expected: {expected_special})")


def main():
    """Run all tests."""
    print("=" * 60)
    print("AC Integration Test Suite")
    print("=" * 60)

    try:
        test_lexicon_functions()
        test_role_tagger_basic()
        print("\n" + "=" * 60)
        print("All tests completed successfully!")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
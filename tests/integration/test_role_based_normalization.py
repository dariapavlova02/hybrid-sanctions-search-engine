import pytest
from src.ai_service.layers.normalization.normalization_service import NormalizationService
from tests.integration.test_full_normalization_suite import assert_normalized_name

@pytest.fixture
def normalization_service():
    """Creates an instance of the normalization service for testing."""
    return NormalizationService()

# Test cases provided by the user to target specific failure modes.
role_based_test_cases = [
    # Genitive/dative to nominative
    ("Аллы Борисовны Пугачевой", "Алла Борисовна Пугачева", "ru"),
    ("Петру Чайковскому", "Петр Чайковский", "ru"),
    ("Сергієві Жадану", "Сергій Жадан", "uk"),
    ("Оксані Забужко", "Оксана Забужко", "uk"),

    # Gender flip on surname (mixed language input)
    ("Петра Иванова", "Петро Иванов", "uk"),

    # Patronymics with case
    ("от Александра Александровича", "Александр Александрович", "ru"),
    ("для Іванівни", "Іванівна", "uk"), # Assuming 'Іванівна' is a valid standalone name part for testing

    # Hyphenated names
    ("Для Іванова-Петренка С.В.", "Іванов-Петренко С.В.", "uk"),

    # Noise words to be removed
    ("Payment from JOHN DOE", "John Doe", "en"),
    ("Оплата від Петра Порошенка", "Петро Порошенко", "uk"),

    # Initials spacing/case
    ("Есенин с. а.", "Есенин С. А.", "ru"),
    ("пушкин а с", "Пушкин А. С.", "ru"),
]

@pytest.mark.parametrize("input_text, expected_name, lang", role_based_test_cases)
def test_role_based_slavic_normalization(normalization_service, input_text, expected_name, lang):
    """
    Tests the new role-based normalization logic with specific cases.
    """
    result = normalization_service.normalize(input_text, language=lang)
    assert_normalized_name(result, expected_name)

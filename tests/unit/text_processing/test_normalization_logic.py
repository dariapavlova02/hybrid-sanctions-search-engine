
import pytest
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from src.ai_service.layers.normalization.normalization_service import NormalizationService
from src.ai_service.contracts.base_contracts import NormalizationResult

# Helper function for clear assertions
def assert_normalized_name(result: NormalizationResult, expected_name: str):
    """
    Asserts that the normalized result string equals the expected name.
    This is a strict assertion.
    """
    assert result.normalized == expected_name, f"Expected '{expected_name}', but got '{result.normalized}'"

@pytest.fixture(scope="module")
def normalization_service():
    """Fixture to provide a NormalizationService instance."""
    return NormalizationService()

# --- Test Cases provided by the user ---

# Категория 1: УКРАИНСКИЕ ИМЕНА (полная нормализация)
ukrainian_test_cases = [
    ("Оплата за послуги, платник Петрик П.", "Петро П."),
    ("Для Петруся Іванова, за ремонт", "Петро Іванов"),
    ("Переказ від Вовчика Зеленського В. О.", "Володимир Зеленський В. О."),
    ("Подарунок для Дашеньки Квіткової", "Дарія Квіткова"),
    ("Від Сашка Положинського за квитки", "Олександр Положинський"),
    ("Для Жені Галича з групи O.Torvald", "Євген Галич"),
    ("Дякуємо Сергієві Жадану за творчість", "Сергій Жадан"),
    ("Зустріч з Ліною Костенко", "Ліна Костенко"),
    ("Подарунок для Оксани Забужко", "Оксана Забужко"),
    ("Розмовляв з Валерієм Залужним", "Валерій Залужний"),
    ("Плтіж від В'ячеслава вакарчука (океан ельзи)", "В'ячеслав Вакарчук"),
    ("Переказ ОЛЕГУ СКРИПЦІ", "Олег Скрипка"),
    ("Для Іванова-Петренка С.В.", "Іванов-Петренко С.В."),
]

@pytest.mark.parametrize("input_text, expected_name", ukrainian_test_cases)
def test_ukrainian_full_normalization(normalization_service, input_text, expected_name):
    """Проверяет полную нормализацию украинских имен."""
    result = normalization_service.normalize(input_text, language="uk")
    assert_normalized_name(result, expected_name)

# Категория 2: РУССКИЕ ИМЕНА (полная нормализация)
russian_test_cases = [
    ("Перевод от Саши Пушкина Александровича", "Александр Пушкин Александрович"),
    ("Оплата для Володи Высоцкого", "Владимир Высоцкий"),
    ("Платёж от Димы Медведева", "Дмитрий Медведев"),
    ("Для Аллы Борисовны Пугачевой", "Алла Борисовна Пугачева"),
    ("Благодарность Петру Чайковскому", "Петр Чайковский"),
    ("Встреча с Анной Ахматовой", "Анна Ахматова"),
    ("Перевод средств Ивану Бунину", "Иван Бунин"),
    ("Отправлено для Есенина С. А.", "Есенин С. А."),
    ("Зачисление от Лермонтова М.Ю.", "Лермонтов М.Ю."),
]

@pytest.mark.parametrize("input_text, expected_name", russian_test_cases)
def test_russian_full_normalization(normalization_service, input_text, expected_name):
    """Проверяет полную нормализацию русских имен."""
    result = normalization_service.normalize(input_text, language="ru")

    # Debug output for failing cases
    if "Высоцкого" in input_text:
        print(f"\nDEBUG - Input: '{input_text}'")
        print(f"DEBUG - Expected: '{expected_name}'")
        print(f"DEBUG - Actual: '{result.normalized}'")

        # Force create a fresh service to bypass any caching issues
        from ai_service.layers.normalization.normalization_service import NormalizationService
        fresh_service = NormalizationService()

        # Test with fresh service
        fresh_result = fresh_service.normalize(input_text, language="ru")
        print(f"DEBUG - Fresh service result: '{fresh_result.normalized}'")

        # Test morphology with fresh service
        fresh_morph_test = fresh_service._morph_nominal('Высоцкого', 'ru')
        print(f"DEBUG - Fresh _morph_nominal('Высоцкого', 'ru') = '{fresh_morph_test}'")

        fresh_ru_morph = fresh_service._get_morph('ru')
        if fresh_ru_morph:
            print(f"DEBUG - Fresh ru_morph available: {fresh_ru_morph.morph_analyzer is not None}")
            if fresh_ru_morph.morph_analyzer:
                print(f"DEBUG - Fresh ru_morph type: {type(fresh_ru_morph.morph_analyzer)}")
            else:
                # Test direct pymorphy3 initialization in test environment
                print("DEBUG - Testing direct pymorphy3 in test env:")
                import sys
                print(f"DEBUG - Python executable: {sys.executable}")
                print(f"DEBUG - Python path length: {len(sys.path)}")
                try:
                    import pymorphy3
                    test_analyzer = pymorphy3.MorphAnalyzer(lang="ru")
                    test_parses = test_analyzer.parse('Высоцкого')
                    print(f"DEBUG - Direct pymorphy3 works: {len(test_parses)} parses")
                    print(f"DEBUG - Direct result: {test_parses[0].normal_form if test_parses else 'No parses'}")
                except Exception as e:
                    print(f"DEBUG - Direct pymorphy3 error: {e}")
                    print(f"DEBUG - Type of error: {type(e)}")
                    import traceback
                    print(f"DEBUG - Traceback: {traceback.format_exc()}")
        else:
            print("DEBUG - Fresh ru_morph is None!")

    assert_normalized_name(result, expected_name)

# Категория 3: АНГЛИЙСКИЕ ИМЕНА (полная нормализация)
english_test_cases = [
    ("Payment from John Fitzgerald Kennedy", "John Fitzgerald Kennedy"),
    ("Transfer to Stephen E. King for services", "Stephen E. King"),
    ("For Mr. Sherlock Holmes, Baker st. 221b", "Sherlock Holmes"),
    ("Refund to Ms. Joanna Rowling", "Joanna Rowling"),
    ("From Bill Gates for charity", "William Gates"),
    ("For Liz Truss, former PM", "Elizabeth Truss"),
    ("Payment from Mike Johnson", "Michael Johnson"),
    ("Sent to ELON MUSK for X corp", "Elon Musk"),
    ("For BARACK H. OBAMA, invoice 123", "Barack H. Obama"),
]

@pytest.mark.parametrize("input_text, expected_name", english_test_cases)
def test_english_full_normalization(normalization_service, input_text, expected_name):
    """Проверяет полную нормализацию английских имен."""
    result = normalization_service.normalize(input_text, language="en")
    assert_normalized_name(result, expected_name)

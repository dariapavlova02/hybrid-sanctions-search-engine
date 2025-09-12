#!/usr/bin/env python3
"""
Комплексный набор тестов для полной нормализации имен.
Проверяет морфологическую нормализацию с сохранением структуры имени.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from ai_service.services.normalization_service import NormalizationService


# --- Фикстура для инициализации сервиса ---
@pytest.fixture
def normalization_service():
    """Создает экземпляр сервиса нормализации для тестов."""
    return NormalizationService()


# --- Хелпер для сравнения результатов ---
def assert_normalized_name(result, expected_name):
    """
    Сравнивает нормализованный результат с ожидаемым именем.
    Игнорирует регистр, лишние пробелы и порядок слов.
    Требует точного совпадения наборов токенов.
    """
    # Приводим ожидаемый результат к набору слов в нижнем регистре
    expected_parts = set(expected_name.lower().split())
    
    # Получаем реальные токены из результата
    actual_tokens = {token.lower() for token in result.tokens if token.strip()}
    
    # Проверяем, что наборы токенов в точности совпадают
    assert expected_parts == actual_tokens, \
        f"Ожидалось: {expected_parts}, получено: {actual_tokens}"


# ======================================================================================
# Категория 1: УКРАИНСКИЕ ИМЕНА (полная нормализация)
# ======================================================================================
ukrainian_test_cases = [
    # --- Уменьшительные формы с сохранением фамилий и инициалов ---
    ("Оплата за послуги, платник Петрик П.", "Петро П."),
    ("Для Петруся Іванова, за ремонт", "Петро Іванов"),
    ("Переказ від Вовчика Зеленського В. О.", "Володимир Зеленський В. О."),
    ("Подарунок для Дашеньки Квіткової", "Дарія Квіткова"),
    ("Від Сашка Положинського за квитки", "Олександр Положинський"),
    ("Для Жені Галича з групи O.Torvald", "Євген Галич"),

    # --- Разные падежи и склонения ---
    ("Дякуємо Сергієві Жадану за творчість", "Сергій Жадан"),
    ("Зустріч з Ліною Костенко", "Ліна Костенко"),
    ("Подарунок для Оксани Забужко", "Оксана Забужко"),
    ("Розмовляв з Валерієм Залужним", "Валерій Залужний"),

    # --- Сложные случаи и опечатки ---
    ("Плтіж від В'ячеслава вакарчука (океан ельзи)", "В'ячеслав Вакарчук"),
    ("Переказ ОЛЕГУ СКРИПЦІ", "Олег Скрипка"),
    ("Для Іванова-Петренка С.В.", "Іванов-Петренко С.В."),
]

@pytest.mark.parametrize("input_text, expected_name", ukrainian_test_cases)
def test_ukrainian_full_normalization(normalization_service, input_text, expected_name):
    """Проверяет полную нормализацию украинских имен."""
    result = normalization_service.normalize(input_text, language="uk")
    assert_normalized_name(result, expected_name)


# ======================================================================================
# Категория 2: РУССКИЕ ИМЕНА (полная нормализация)
# ======================================================================================
russian_test_cases = [
    # --- Уменьшительные формы с фамилиями и отчествами ---
    ("Перевод от Саши Пушкина Александровича", "Александр Пушкин Александрович"),
    ("Оплата для Володи Высоцкого", "Владимир Высоцкий"),
    ("Платёж от Димы Медведева", "Дмитрий Медведев"),
    ("Для Аллы Борисовны Пугачевой", "Алла Борисовна Пугачева"),

    # --- Падежи и склонения ---
    ("Благодарность Петру Чайковскому", "Петр Чайковский"),
    ("Встреча с Анной Ахматовой", "Анна Ахматова"),
    ("Перевод средств Ивану Бунину", "Иван Бунин"),

    # --- Инициалы ---
    ("Отправлено для Есенина С. А.", "Есенин С. А."),
    ("Зачисление от Лермонтова М.Ю.", "Лермонтов М.Ю."),
]

@pytest.mark.parametrize("input_text, expected_name", russian_test_cases)
def test_russian_full_normalization(normalization_service, input_text, expected_name):
    """Проверяет полную нормализацию русских имен."""
    result = normalization_service.normalize(input_text, language="ru")
    assert_normalized_name(result, expected_name)


# ======================================================================================
# Категория 3: АНГЛИЙСКИЕ ИМЕНА (полная нормализация)
# ======================================================================================
english_test_cases = [
    # --- Стандартные случаи ---
    ("Payment from John Fitzgerald Kennedy", "John Fitzgerald Kennedy"),
    ("Transfer to Stephen E. King for services", "Stephen E. King"),
    ("For Mr. Sherlock Holmes, Baker st. 221b", "Sherlock Holmes"),
    ("Refund to Ms. Joanna Rowling", "Joanna Rowling"),
    
    # --- Варианты и сокращения ---
    ("From Bill Gates for charity", "William Gates"),
    ("For Liz Truss, former PM", "Elizabeth Truss"),
    ("Payment from Mike Johnson", "Michael Johnson"),
    
    # --- Разный регистр и лишние слова ---
    ("Sent to ELON MUSK for X corp", "Elon Musk"),
    ("For BARACK H. OBAMA, invoice 123", "Barack H. Obama"),
]

@pytest.mark.parametrize("input_text, expected_name", english_test_cases)
def test_english_full_normalization(normalization_service, input_text, expected_name):
    """Проверяет полную нормализацию английских имен."""
    result = normalization_service.normalize(input_text, language="en")
    assert_normalized_name(result, expected_name)


# ======================================================================================
# Дополнительные строгие тесты для критических случаев
# ======================================================================================

def test_critical_ukrainian_normalization(normalization_service):
    """Критический тест: Петра Порошенка -> Петро Порошенко"""
    input_text = "Оплата от Петра Порошенка по Договору 123"
    result = normalization_service.normalize(input_text, language="uk")
    
    # Строгие проверки
    assert result.success, f"Normalization failed: {result.errors}"
    assert result.tokens, "No tokens returned"
    
    tokens_lower = {token.lower() for token in result.tokens}
    expected_tokens = {"петро", "порошенко"}
    
    assert tokens_lower == expected_tokens, f"Expected {expected_tokens}, but got {tokens_lower}"
    
    print(f"✅ Critical test passed: {input_text} -> {result.tokens}")


def test_critical_russian_normalization(normalization_service):
    """Критический тест: Сергея Владимировича Петрова -> Сергей Владимирович Петров"""
    input_text = "Платеж в пользу Сергея Владимировича Петрова"
    result = normalization_service.normalize(input_text, language="ru")
    
    # Строгие проверки
    assert result.success, f"Normalization failed: {result.errors}"
    assert result.tokens, "No tokens returned"
    
    tokens_lower = {token.lower() for token in result.tokens}
    expected_tokens = {"сергей", "владимирович", "петров"}
    
    assert tokens_lower == expected_tokens, f"Expected {expected_tokens}, but got {tokens_lower}"
    
    print(f"✅ Critical test passed: {input_text} -> {result.tokens}")


if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v", "--tb=short"])

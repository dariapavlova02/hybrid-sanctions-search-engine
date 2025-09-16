import pytest
from src.ai_service.layers.normalization.morphology.gender_rules import (
    convert_given_name_to_nominative_ru, convert_patronymic_to_nominative_ru,
    convert_given_name_to_nominative_uk, to_feminine_nominative_ru,
    to_feminine_nominative_uk, is_invariable_surname
)


@pytest.mark.parametrize("w,exp", [
    ("Ивану", "Иван"), ("Марие", "Мария"), ("Анны", "Анна"), ("Марии", "Мария"),
])
def test_ru_given_cases(w, exp):
    assert convert_given_name_to_nominative_ru(w) == exp


@pytest.mark.parametrize("w,exp", [
    ("Андреевны", "Андреевна"), ("Андреевне", "Андреевна"), ("Андреевну", "Андреевна"),
])
def test_ru_patronymic_oblique_to_nom(w, exp):
    assert convert_patronymic_to_nominative_ru(w) == exp


@pytest.mark.parametrize("w,exp", [
    ("Дарʼї", "Дарʼя"), ("Марії", "Марія"), ("Анни", "Анна"),
])
def test_uk_given_cases(w, exp):
    assert convert_given_name_to_nominative_uk(w) == exp


@pytest.mark.parametrize("w,exp", [
    ("Ахматовой", "Ахматова"), ("Пугачевой", "Пугачева"),
])
def test_ru_feminine_surnames(w, exp):
    assert to_feminine_nominative_ru(w) == exp


@pytest.mark.parametrize("w,exp", [
    ("Павлової", "Павлова"), ("Кравцівської", "Кравцівська"),
])
def test_uk_feminine_surnames(w, exp):
    assert to_feminine_nominative_uk(w) == exp


@pytest.mark.parametrize("w", ["Порошенка", "Петренка"])
def test_invariable_declined_enko(w):
    assert is_invariable_surname(w) is True
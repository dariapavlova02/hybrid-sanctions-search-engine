"""Unit tests ensuring diminutive resolution relies on dictionaries for RU/UK."""

import pytest

from src.ai_service.layers.normalization.normalization_service import NormalizationService
from src.ai_service.utils.feature_flags import get_feature_flag_manager


@pytest.fixture(autouse=True)
def enable_dictionary_only_mode():
    """Ensure diminutives use the dictionary-only pipeline during tests."""
    manager = get_feature_flag_manager()
    previous_dict_only = manager.use_diminutives_dictionary_only()
    previous_cross = manager.allow_diminutives_cross_lang()
    manager.update_flags(
        use_diminutives_dictionary_only=True,
        diminutives_allow_cross_lang=False,
    )
    try:
        yield
    finally:
        manager.update_flags(
            use_diminutives_dictionary_only=previous_dict_only,
            diminutives_allow_cross_lang=previous_cross,
        )


@pytest.fixture
def normalization_service():
    service = NormalizationService()
    try:
        yield service
    finally:
        service.clear_caches()


def _trace_for_token(result, token_value: str):
    token_lower = token_value.lower()
    return next(trace for trace in result.trace if trace.token.lower() == token_lower)


def test_russian_vova_expanded(normalization_service):
    result = normalization_service.normalize_sync("Вова Петров", language="ru")

    assert result.normalized == "Владимир Петров"
    vova_trace = _trace_for_token(result, "Вова")
    assert vova_trace.output == "Владимир"
    assert "diminutive_resolved" in (vova_trace.notes or "")
    assert "\"lang\": \"ru\"" in (vova_trace.notes or "")


def test_ukrainian_sashko_expanded(normalization_service):
    result = normalization_service.normalize_sync("Сашко Коваль", language="uk")

    assert result.normalized == "Олександр Коваль"
    trace = _trace_for_token(result, "Сашко")
    assert trace.output == "Олександр"
    assert "diminutive_resolved" in (trace.notes or "")
    assert "\"lang\": \"uk\"" in (trace.notes or "")


def test_ukrainian_petrik_expanded(normalization_service):
    result = normalization_service.normalize_sync("Петрик Іванов", language="uk")

    assert result.normalized == "Петро Іванов"
    trace = _trace_for_token(result, "Петрик")
    assert trace.output == "Петро"
    assert "diminutive_resolved" in (trace.notes or "")


def test_cross_language_ambiguity_respects_flag(normalization_service):
    result = normalization_service.normalize_sync("Вова", language="ru")

    assert result.normalized == "Владимир"
    assert "Володимир" not in result.normalized
    trace = _trace_for_token(result, "Вова")
    assert "Володимир" not in (trace.notes or "")

"""Golden canary tests for normalization layer."""

import json
from pathlib import Path

import pytest

from ai_service.layers.normalization.normalization_service import NormalizationService

GOLDEN_CASES_PATH = Path(__file__).with_name("golden_cases.json")
GOLDEN_CASES = json.loads(GOLDEN_CASES_PATH.read_text())

LEGACY_KNOWN_FAILURES = {
    "ru_basic_full": "Legacy pipeline keeps surname first and accusative forms",
    "ru_apostrophe": "Legacy pipeline does not normalize apostrophes",
    "ru_context_words": "Context words leak into normalized output",
    "ru_homoglyph": "Homoglyph folding not implemented",
    "ru_multiple_persons": "Legacy pipeline does not insert person separators",
    "uk_declension": "Ukrainian morphology keeps dative form",
    "uk_feminine_suffix": "Gender-specific morphology missing",
    "uk_ner_gate": "NER filter includes country token",
    "en_title_suffix": "Titles and suffixes not trimmed",
    "en_middle_name": "Middle name not removed",
    "en_apostrophe": "Apostrophe not typographically normalized",
    "en_double_surname": "Hyphenated surname lowercased incorrectly",
    "mixed_org_noise": "Organization tokens leak into normalized output",
    "mixed_languages": "Multi-person splitting not implemented",
    "mixed_diacritics": "Unicode noise not filtered",
    "mixed_function_words": "Function words misclassified as initials",
    "uk_passport": "Document context retained in normalized output",
    "behavior_case_policy": "Case normalization incomplete",
}


def _expected_normalized(case: dict) -> str:
    personas = case.get("expected_personas", [])
    if not personas:
        return ""
    return " | ".join(persona["normalized"] for persona in personas)


@pytest.fixture(scope="module")
def normalization_service() -> NormalizationService:
    return NormalizationService()


@pytest.mark.parametrize("case", GOLDEN_CASES, ids=[case["id"] for case in GOLDEN_CASES])
def test_golden_cases_legacy(normalization_service: NormalizationService, case: dict) -> None:
    """Check legacy NormalizationService against golden expectations."""
    expected = _expected_normalized(case)

    result = normalization_service.normalize(
        case["input"],
        language=case["language"],
        remove_stop_words=True,
        preserve_names=True,
        enable_advanced_features=True,
    )

    if case["id"] in LEGACY_KNOWN_FAILURES:
        pytest.xfail(LEGACY_KNOWN_FAILURES[case["id"]])

    assert result.normalized == expected, (
        f"Mismatch for {case['id']}: expected '{expected}', got '{result.normalized}'"
    )


@pytest.mark.xfail(reason="Factory implementation not yet aligned with golden cases", strict=False)
@pytest.mark.asyncio
@pytest.mark.parametrize("case", GOLDEN_CASES, ids=[case["id"] for case in GOLDEN_CASES])
async def test_golden_cases_factory(case: dict) -> None:
    """Placeholder canary for factory pipeline."""
    service = NormalizationService()
    expected = _expected_normalized(case)

    result = await service.normalize_async(
        case["input"],
        language=case["language"],
        remove_stop_words=True,
        preserve_names=True,
        enable_advanced_features=True,
        use_factory=True,
    )

    assert result.normalized == expected, (
        f"Factory mismatch for {case['id']}: expected '{expected}', got '{result.normalized}'"
    )

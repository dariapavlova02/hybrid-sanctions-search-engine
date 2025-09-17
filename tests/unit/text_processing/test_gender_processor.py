import pytest

from ai_service.layers.normalization.processors.gender_processor import GenderProcessor


@pytest.fixture
def processor() -> GenderProcessor:
    return GenderProcessor()


def test_infer_gender_from_feminine_name(processor: GenderProcessor):
    gender, confidence, evidence = processor.infer_gender(
        ["Анна", "Ахматова"],
        ["given", "surname"],
        language="ru",
    )
    assert gender == "femn"
    assert confidence > 0.8
    assert any("Feminine" in note for note in evidence)


def test_adjust_surname_to_feminine(processor: GenderProcessor):
    surname, changed, trace = processor.adjust_surname_gender(
        "Ахматов", "femn", language="ru"
    )
    assert surname == "Ахматова"
    assert changed


def test_adjust_surname_respects_invariable(processor: GenderProcessor):
    surname, changed, trace = processor.adjust_surname_gender(
        "Грицько", "femn", language="uk"
    )
    assert surname == "Грицько"
    assert not changed
    assert any("invariable" in note.lower() for note in trace)

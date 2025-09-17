import pytest

from ai_service.layers.normalization.processors.role_classifier import RoleClassifier


@pytest.fixture
def classifier() -> RoleClassifier:
    name_dicts = {
        "ru": {"иван", "мария"},
        "ru_surnames": {"иванов", "пушкин"},
        "en": {"john", "bill"},
        "en_surnames": {"gates"},
    }
    dim2full = {
        "ru": {"сашка": "Александр"},
        "en": {"bill": "William"},
    }
    return RoleClassifier(name_dicts, dim2full)


def test_role_classifier_basic_russian(classifier: RoleClassifier):
    tokens = ["Иванов", "Иван", "Петрович"]
    tagged, _, organizations = classifier.tag_tokens(tokens, language="ru")
    assert tagged == [
        ("Иванов", "surname"),
        ("Иван", "given"),
        ("Петрович", "patronymic"),
    ]
    assert organizations == []


def test_role_classifier_initials_split(classifier: RoleClassifier):
    tokens = ["Иванов", "И.И."]
    tagged, _, organizations = classifier.tag_tokens(tokens, language="ru")
    assert tagged == [
        ("Иванов", "surname"),
        ("И.", "initial"),
        ("И.", "initial"),
    ]
    assert organizations == []


def test_role_classifier_diminutive(classifier: RoleClassifier):
    tokens = ["Сашка", "Пушкин"]
    tagged, _, organizations = classifier.tag_tokens(tokens, language="ru")
    assert tagged[0] == ("Сашка", "given")
    assert tagged[1] == ("Пушкин", "surname")
    assert organizations == []


def test_role_classifier_org_detection(classifier: RoleClassifier):
    tokens = ["ООО", "ПРИВАТБАНК"]
    tagged, _, organizations = classifier.tag_tokens(tokens, language="ru")
    assert tagged[0][1] == "unknown"
    assert tagged[1][1] == "org"
    assert organizations == ["ПРИВАТБАНК"]


def test_role_classifier_english_names(classifier: RoleClassifier):
    tokens = ["Bill", "Gates"]
    tagged, _, organizations = classifier.tag_tokens(tokens, language="en")
    assert tagged == [("Bill", "given"), ("Gates", "surname")]
    assert organizations == []


def test_role_classifier_quoted_org(classifier: RoleClassifier):
    tokens = ["ПРИВАТБАНК", "Иванов"]
    tagged, _, organizations = classifier.tag_tokens(
        tokens,
        language="ru",
        quoted_segments=["ПРИВАТБАНК"],
    )
    assert tagged[0][1] == "org"
    assert tagged[1][1] == "surname"
    assert organizations == ["ПРИВАТБАНК"]


def test_role_classifier_ukrainian_dative_surname(classifier: RoleClassifier):
    tokens = ["Івану", "Петренку"]
    tagged, _, _ = classifier.tag_tokens(tokens, language="uk")
    assert tagged == [("Івану", "given"), ("Петренку", "surname")]

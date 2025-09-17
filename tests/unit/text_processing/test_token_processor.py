import pytest

from ai_service.layers.normalization.processors.token_processor import TokenProcessor


@pytest.fixture
def processor() -> TokenProcessor:
    return TokenProcessor()


def test_token_processor_preserves_initials(processor: TokenProcessor):
    tokens, _, _ = processor.strip_noise_and_tokenize("Иванов И.И.")
    assert tokens == ["Иванов", "И.И."]


def test_token_processor_stop_words_removed(processor: TokenProcessor):
    tokens, _, _ = processor.strip_noise_and_tokenize("и Петров")
    assert tokens == ["и", "Петров"]


def test_token_processor_quoted_phrase(processor: TokenProcessor):
    text = "Оплата 'ПРИВАТБАНК' Ивану Петрову"
    tokens, _, meta = processor.strip_noise_and_tokenize(text)
    assert "ПРИВАТБАНК" in tokens
    assert "Ивану" in tokens
    assert meta.get("quoted_segments") == ["ПРИВАТБАНК"]


def test_token_processor_transliteration_and_nfc(processor: TokenProcessor):
    text = "Ёлка"
    tokens, _, _ = processor.strip_noise_and_tokenize(text)
    assert tokens == ["Елка"]


def test_token_processor_preserve_names_false(processor: TokenProcessor):
    tokens, _, _ = processor.strip_noise_and_tokenize(
        "Анна-Мария",
        preserve_names=False,
    )
    assert tokens == ["Анна", "Мария"]


def test_token_processor_digits_removed(processor: TokenProcessor):
    tokens, _, _ = processor.strip_noise_and_tokenize("12345 Иван 678")
    assert tokens == ["Иван"]

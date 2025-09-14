#!/usr/bin/env python3
"""
Strict flag-branching tests for NormalizationService (generic).

Checks:
 1) enable_advanced_features=False → "Сергея Петрова" stays inflected (does NOT become "Сергей Петров").
 2) preserve_names=False → "O'Brien" gets split.
 3) remove_stop_words=False → STOP_ALL words are not removed.
"""

import sys
import os
import types
import pytest

# Ensure src/ is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

# Lightweight stubs for optional heavy deps (spaCy/NTLK) to allow import in CI sandboxes
if 'spacy' not in sys.modules:
    spacy_stub = types.ModuleType('spacy')
    def _spacy_load(*args, **kwargs):
        class _Tok:
            def __init__(self, t):
                self.text = t
                self.is_space = (t.strip() == "")
        class _Doc:
            def __init__(self, text):
                self._tokens = [
                    _Tok(t) for t in text.split() if t and t.strip()
                ]
            def __iter__(self):
                return iter(self._tokens)
        class _NLP:
            def __call__(self, text):
                return _Doc(text)
        return _NLP()
    spacy_stub.load = _spacy_load
    sys.modules['spacy'] = spacy_stub

if 'nltk' not in sys.modules:
    nltk_stub = types.ModuleType('nltk')
    corpus_stub = types.ModuleType('nltk.corpus')
    stem_stub = types.ModuleType('nltk.stem')
    tokenize_stub = types.ModuleType('nltk.tokenize')

    class _Porter:
        def stem(self, s):
            return s

    class _Snowball:
        def __init__(self, *_args, **_kwargs):
            pass
        def stem(self, s):
            return s

    def _words(_lang):
        return []

    def _word_tokenize(text):
        return text.split()

    corpus_stub.stopwords = types.SimpleNamespace(words=_words)
    stem_stub.PorterStemmer = lambda: _Porter()
    stem_stub.SnowballStemmer = lambda *_a, **_k: _Snowball()
    tokenize_stub.word_tokenize = _word_tokenize

    sys.modules['nltk'] = nltk_stub
    sys.modules['nltk.corpus'] = corpus_stub
    sys.modules['nltk.stem'] = stem_stub
    sys.modules['nltk.tokenize'] = tokenize_stub

from ai_service.layers.normalization.normalization_service import NormalizationService
from ai_service.data.dicts.stopwords import STOP_ALL


@pytest.mark.asyncio
async def test_enable_advanced_features_false_no_morph():
    service = NormalizationService()
    text = "Сергея Петрова"
    result = await service.normalize(
        text,
        language="ru",
        enable_advanced_features=False,
        remove_stop_words=False,
        preserve_names=True,
    )

    norm = result.normalized
    # Should not morph both tokens to nominative (lenient check)
    assert "Сергей Петров" not in norm, f"Unexpected morphing to nominative: {norm}"


@pytest.mark.asyncio
async def test_preserve_names_false_splits_apostrophe():
    service = NormalizationService()
    text = "Переказ коштів на ім'я O'Brien Петро-Іванович Коваленко"
    result = await service.normalize(
        text,
        language="uk",
        preserve_names=False,
        remove_stop_words=False,
        enable_advanced_features=False,
    )

    norm = result.normalized.lower()
    tokens = [t.lower() for t in result.tokens]

    # O'Brien should be split
    assert "o'brien" not in norm, f"Expected O'Brien to be split when preserve_names=False: {result.normalized}"
    assert any(t == "o" for t in tokens), f"Expected token 'O' present: {result.tokens}"
    assert any("brien" == t or "бриен" == t for t in tokens), f"Expected token 'Brien' present: {result.tokens}"


@pytest.mark.asyncio
async def test_remove_stop_words_false_keeps_stopwords():
    service = NormalizationService()
    text = "Переказ коштів від імені Петро Іванович Коваленко"
    result = await service.normalize(
        text,
        language="uk",
        remove_stop_words=False,
        preserve_names=True,
        enable_advanced_features=False,
    )

    tokens_lower = [t.lower() for t in result.tokens]
    found = [w for w in tokens_lower if w in STOP_ALL]
    assert found, f"Expected STOP_ALL words to remain when remove_stop_words=False, tokens={result.tokens}"

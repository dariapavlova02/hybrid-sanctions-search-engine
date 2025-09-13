#!/usr/bin/env python3
"""
Performance test: p95 on mixed short corpus and cache behavior.

Runs 1000 calls per service (generic, morph) on a shuffled mix of short cases,
measures p95 latency for pass #1 and pass #2, and asserts that the second pass
is faster (accounting for small variance) to indicate cache effects.
"""

import sys
import os
import types
import time
import random
import math
import asyncio
import pytest

# Ensure src/ is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

# Lightweight stubs for optional heavy deps to run in CI sandboxes
if 'spacy' not in sys.modules:
    spacy_stub = types.ModuleType('spacy')
    def _spacy_load(*args, **kwargs):
        class _Tok:
            def __init__(self, t):
                self.text = t
                self.is_space = (t.strip() == "")
        class _Doc:
            def __init__(self, text):
                self._tokens = [_Tok(t) for t in text.split() if t and t.strip()]
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


def p95(values_ms):
    if not values_ms:
        return 0.0
    arr = sorted(values_ms)
    k = max(0, min(len(arr) - 1, int(math.ceil(0.95 * len(arr)) - 1)))
    return arr[k]


async def _call_normalize(service, text, language, flags):
    method = getattr(service, 'normalize_async', None) or getattr(service, 'normalize')
    
    # Check if the method accepts the flags parameters
    import inspect
    sig = inspect.signature(method)
    params = sig.parameters
    
    kwargs = {
        "text": text,
        "language": language,
    }
    
    # Add flags only if the method accepts them
    if "remove_stop_words" in params:
        kwargs["remove_stop_words"] = flags.get('remove_stop_words', False)
    if "preserve_names" in params:
        kwargs["preserve_names"] = flags.get('preserve_names', True)
    if "enable_advanced_features" in params:
        kwargs["enable_advanced_features"] = flags.get('enable_advanced_features', False)
    
    return await method(**kwargs)


@pytest.mark.asyncio
async def test_ab_p95_and_cache_behavior():
    # Import services here to leverage the stubs above
    from ai_service.services.morphology.normalization_service import NormalizationService as MorphNorm
    from ai_service.services.normalization_service import NormalizationService as GenericNorm

    morph = MorphNorm()
    generic = GenericNorm()

    # Mixed short corpus (keep inputs very short)
    base_cases = [
        ("Сергея Петрова", "ru"),
        ("Оплата від Петра Порошенка", "uk"),
        ("Bill Gates", "en"),
        ("Іванов-Петренко С.В.", "uk"),
        ("O'Brien", "en"),
        ("ООО 'Тест'", "ru"),
    ]
    flags = {"remove_stop_words": True, "preserve_names": True, "enable_advanced_features": True}

    # Build 1000-sample sequence by repeating and shuffling
    seq = (base_cases * (1000 // len(base_cases) + 1))[:1000]
    random.Random(12345).shuffle(seq)

    # Pass #1
    t_generic_1 = []
    t_morph_1 = []
    for text, lang in seq:
        t0 = time.perf_counter();
        await _call_normalize(generic, text, lang, flags)
        t_generic_1.append((time.perf_counter() - t0) * 1000.0)

        t0 = time.perf_counter();
        await _call_normalize(morph, text, lang, flags)
        t_morph_1.append((time.perf_counter() - t0) * 1000.0)

    # Pass #2 (same sequence → should benefit from any internal caches)
    t_generic_2 = []
    t_morph_2 = []
    for text, lang in seq:
        t0 = time.perf_counter();
        await _call_normalize(generic, text, lang, flags)
        t_generic_2.append((time.perf_counter() - t0) * 1000.0)

        t0 = time.perf_counter();
        await _call_normalize(morph, text, lang, flags)
        t_morph_2.append((time.perf_counter() - t0) * 1000.0)

    p95_g1, p95_g2 = p95(t_generic_1), p95(t_generic_2)
    p95_m1, p95_m2 = p95(t_morph_1), p95(t_morph_2)

    print(f"Generic p95: pass1={p95_g1:.2f}ms, pass2={p95_g2:.2f}ms")
    print(f"Morph   p95: pass1={p95_m1:.2f}ms, pass2={p95_m2:.2f}ms")

    # Assert pass2 is not slower; allow 10% tolerance to reduce flakiness
    assert p95_g2 <= p95_g1 * 1.10, f"Generic second pass not faster (p95: {p95_g1:.2f} -> {p95_g2:.2f})"
    assert p95_m2 <= p95_m1 * 1.10, f"Morph second pass not faster (p95: {p95_m1:.2f} -> {p95_m2:.2f})"


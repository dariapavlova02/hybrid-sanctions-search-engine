#!/usr/bin/env python3
"""
AB test dataset for comparing two normalizers under a unified interface.

Each case contains:
- input: raw text
- lang: language code ("en"|"ru"|"uk"|"auto")
- expected_normalized: list[str] of acceptable normalized outputs
- expected_orgs: list[str] or None (if org check should be skipped)
- flags: dict with keys remove_stop_words, preserve_names, enable_advanced_features
"""

CASES = [
    {
        "input": "Оплата від Петра Порошенка",
        "lang": "uk",
        "expected_normalized": ["Петро Порошенко"],
        "expected_orgs": None,
        "flags": {"remove_stop_words": True, "preserve_names": True, "enable_advanced_features": True},
    },
    {
        "input": "Сергея Петрова",
        "lang": "ru",
        # Accept either nominative (morph) or surface (generic)
        "expected_normalized": ["Сергей Петров", "Сергея Петрова"],
        "expected_orgs": None,
        "flags": {"remove_stop_words": False, "preserve_names": True, "enable_advanced_features": True},
    },
    {
        "input": "From Bill Gates for charity",
        "lang": "en",
        # Accept nickname mapping or literal
        "expected_normalized": ["William Gates", "Bill Gates"],
        "expected_orgs": None,
        "flags": {"remove_stop_words": True, "preserve_names": True, "enable_advanced_features": True},
    },
    {
        "input": "Для Іванова-Петренка С.В.",
        "lang": "uk",
        "expected_normalized": ["Іванов-Петренко С.В."],
        "expected_orgs": None,
        "flags": {"remove_stop_words": True, "preserve_names": True, "enable_advanced_features": True},
    },
    {
        "input": "OOO 'Тест' переводит средства Ивану Петрову",
        "lang": "ru",
        "expected_normalized": ["Иван Петров"],
        # Org tokens may include Тест; allow empty as some pipelines may drop quoted unknowns
        "expected_orgs": ["Тест"],
        "flags": {"remove_stop_words": True, "preserve_names": True, "enable_advanced_features": True},
    },
    {
        "input": "Переказ коштів від імені Петро Іванович Коваленко",
        "lang": "uk",
        "expected_normalized": ["Петро Іванович Коваленко"],
        "expected_orgs": None,
        "flags": {"remove_stop_words": True, "preserve_names": True, "enable_advanced_features": True},
    },
    {
        "input": "For Mr. Sherlock Holmes, Baker st. 221b",
        "lang": "en",
        "expected_normalized": ["Sherlock Holmes"],
        "expected_orgs": None,
        "flags": {"remove_stop_words": True, "preserve_names": True, "enable_advanced_features": True},
    },
    {
        "input": "Аллы Борисовны Пугачевой",
        "lang": "ru",
        "expected_normalized": ["Алла Борисовна Пугачева", "Аллы Борисовны Пугачевой"],
        "expected_orgs": None,
        "flags": {"remove_stop_words": True, "preserve_names": True, "enable_advanced_features": True},
    },
    {
        "input": "Stephen E. King",
        "lang": "en",
        "expected_normalized": ["Stephen E. King"],
        "expected_orgs": None,
        "flags": {"remove_stop_words": True, "preserve_names": True, "enable_advanced_features": True},
    },
    {
        "input": "Переказ коштів на ім'я O'Brien Петро-Іванович Коваленко",
        "lang": "uk",
        # Preserve compound and apostrophe when preserve_names=True
        "expected_normalized": ["O'Brien Петро-Іванович Коваленко", "O'Brien Петро Іванович Коваленко"],
        "expected_orgs": None,
        "flags": {"remove_stop_words": True, "preserve_names": True, "enable_advanced_features": True},
    },
]


#!/usr/bin/env python3
"""
Demo script for Russian normalization enhancements.

Demonstrates the new Russian-specific features:
1. Stopwords for initials conflict prevention
2. 'ё' policy (preserve/fold)
3. Enhanced patronymics detection and normalization
4. Expanded Russian nicknames
5. Hyphenated surnames handling
6. Optional Russian spaCy NER
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.ai_service.layers.normalization.normalization_service import NormalizationService
from src.ai_service.layers.normalization.morphology_adapter import MorphologyAdapter
from src.ai_service.layers.normalization.role_tagger_service import RoleTaggerService, RoleRules
from src.ai_service.layers.normalization.lexicon_loader import get_lexicons
from src.ai_service.layers.normalization.token_ops import normalize_hyphenated_name
from src.ai_service.layers.normalization.ner_gateways.spacy_ru import get_spacy_ru_ner


def print_section(title):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_result(result, title="Result"):
    """Print normalization result."""
    print(f"\n{title}:")
    print(f"  Original: {result.original_text}")
    print(f"  Normalized: {result.normalized}")
    print(f"  Tokens: {result.tokens}")
    print(f"  Language: {result.language}")
    print(f"  Success: {result.success}")
    if result.errors:
        print(f"  Errors: {result.errors}")


async def demo_stopwords_initials():
    """Demo stopwords for initials conflict prevention."""
    print_section("1. Stopwords for Initials Conflict Prevention")
    
    print("Testing: 'перевод с карты И. Иванов'")
    print("Expected: 'с' should NOT be marked as initial")
    
    # Test with strict stopwords enabled
    service = NormalizationService()
    
    result = await service.normalize_async(
        "перевод с карты И. Иванов",
        language="ru",
        strict_stopwords=True
    )
    
    print_result(result, "With strict_stopwords=True")
    
    # Test with strict stopwords disabled
    result = await service.normalize_async(
        "перевод с карты И. Иванов",
        language="ru",
        strict_stopwords=False
    )
    
    print_result(result, "With strict_stopwords=False")


async def demo_yo_strategy():
    """Demo 'ё' policy."""
    print_section("2. 'ё' Policy (preserve/fold)")
    
    morphology_adapter = MorphologyAdapter()
    
    test_cases = [
        "Семён",
        "Пётр",
        "Алёна",
        "Владимир"
    ]
    
    for token in test_cases:
        print(f"\nToken: {token}")
        
        # Test preserve strategy
        preserved, traces_preserve = morphology_adapter.apply_yo_strategy(token, "preserve")
        print(f"  Preserve: {preserved}")
        if traces_preserve:
            print(f"    Trace: {traces_preserve[0]}")
        
        # Test fold strategy
        folded, traces_fold = morphology_adapter.apply_yo_strategy(token, "fold")
        print(f"  Fold: {folded}")
        if traces_fold:
            print(f"    Trace: {traces_fold[0]}")


async def demo_patronymics():
    """Demo enhanced patronymics detection and normalization."""
    print_section("3. Enhanced Patronymics Detection and Normalization")
    
    morphology_adapter = MorphologyAdapter()
    
    test_cases = [
        "Иван Петрович Сидоров",
        "Анна Петровна Сидорова",
        "Иван Петровича Сидоров",  # Genitive
        "Анна Петровны Сидорова",  # Genitive
        "Ович работает в компании",  # Ambiguous case (Belarusian surname)
    ]
    
    for text in test_cases:
        print(f"\nText: {text}")
        
        # Test patronymic detection
        role_tagger_service = RoleTaggerService(get_lexicons(), RoleRules(strict_stopwords=True))
        tokens = text.split()
        tags = role_tagger_service.tag(tokens, "ru")
        
        for token, tag in zip(tokens, tags):
            if tag.role.value == "patronymic":
                print(f"  {token} -> {tag.role.value} ({tag.reason})")
                
                # Test normalization
                normalized, traces = morphology_adapter.normalize_patronymic_to_nominative(token, "ru")
                if normalized != token:
                    print(f"    Normalized: {token} -> {normalized}")
                    if traces:
                        print(f"    Trace: {traces[0]}")
            elif tag.role.value == "surname" and tag.reason == "ambiguous_ovich_surname":
                print(f"  {token} -> {tag.role.value} ({tag.reason}) - Belarusian surname")


async def demo_nicknames():
    """Demo expanded Russian nicknames."""
    print_section("4. Expanded Russian Nicknames")
    
    from src.ai_service.layers.normalization.morphology.diminutive_resolver import DiminutiveResolver
    
    diminutive_resolver = DiminutiveResolver()
    
    test_cases = [
        "Вова Петров",
        "Саша Смирнов",
        "Коля Иванов",
        "Лёша Петров",
        "Дима Сидоров",
        "Миша Козлов",
        "Женя Смирнова",  # Ambiguous - needs gender context
    ]
    
    for text in test_cases:
        print(f"\nText: {text}")
        tokens = text.split()
        
        for token in tokens:
            if token.lower() in ["вова", "саша", "коля", "лёша", "дима", "миша", "женя"]:
                result = diminutive_resolver.resolve(token, "ru")
                if result:
                    print(f"  {token} -> {result}")


async def demo_hyphenated_surnames():
    """Demo hyphenated surnames handling."""
    print_section("5. Hyphenated Surnames Handling")
    
    test_cases = [
        "петрова-сидорова",
        "петров-сидоров",
        "о'нил-смит",
        "петрова-сидорова-иванова",
        "петрова—сидорова",  # em-dash (should not be processed)
        "петрова--сидорова",  # double hyphen (should not be processed)
    ]
    
    for surname in test_cases:
        print(f"\nSurname: {surname}")
        
        # Test with titlecase
        normalized = normalize_hyphenated_name(surname, titlecase=True)
        print(f"  Normalized: {normalized}")
        
        # Test without titlecase
        normalized_no_title = normalize_hyphenated_name(surname, titlecase=False)
        print(f"  No titlecase: {normalized_no_title}")


async def demo_ner():
    """Demo optional Russian spaCy NER."""
    print_section("6. Optional Russian spaCy NER")
    
    ner = get_spacy_ru_ner()
    
    if ner and ner.is_available:
        print("Russian NER model is available!")
        
        test_texts = [
            "Иван Петров работает в ООО Рога и копыта",
            "Мария Сидорова и Анна Козлова работают в компании",
            "Обычный текст без именованных сущностей",
        ]
        
        for text in test_texts:
            print(f"\nText: {text}")
            hints = ner.extract_entities(text)
            
            print(f"  Person spans: {hints.person_spans}")
            print(f"  Organization spans: {hints.org_spans}")
            print(f"  Entities: {[(e.text, e.label) for e in hints.entities]}")
    else:
        print("Russian NER model is not available.")
        print("Install with: python -m spacy download ru_core_news_sm")


async def demo_full_normalization():
    """Demo full normalization with Russian features."""
    print_section("7. Full Normalization with Russian Features")
    
    service = NormalizationService()
    
    test_cases = [
        {
            "text": "перевод с карты Семён Петрович Иванов",
            "description": "Stopwords + 'ё' + patronymic"
        },
        {
            "text": "Вова Петров-Сидоров работает в компании",
            "description": "Nickname + hyphenated surname"
        },
        {
            "text": "Анна Петровна Сидорова-Козлова",
            "description": "Feminine patronymic + hyphenated surname"
        },
        {
            "text": "Иван Петровича Сидоров",  # Genitive patronymic
            "description": "Genitive patronymic normalization"
        },
    ]
    
    for case in test_cases:
        print(f"\n{case['description']}:")
        print(f"Text: {case['text']}")
        
        result = await service.normalize_async(
            case['text'],
            language="ru",
            strict_stopwords=True,
            ru_yo_strategy="fold",  # Convert 'ё' to 'е'
            enable_ru_nickname_expansion=True,
            enable_spacy_ru_ner=False  # Disable for demo (requires model)
        )
        
        print_result(result)


async def main():
    """Main demo function."""
    print("Russian Normalization Enhancements Demo")
    print("======================================")
    
    try:
        await demo_stopwords_initials()
        await demo_yo_strategy()
        await demo_patronymics()
        await demo_nicknames()
        await demo_hyphenated_surnames()
        await demo_ner()
        await demo_full_normalization()
        
        print_section("Demo Complete!")
        print("All Russian normalization features have been demonstrated.")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

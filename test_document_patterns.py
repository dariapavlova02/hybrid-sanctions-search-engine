#!/usr/bin/env python3
"""
Тестирование расширенных документных паттернов
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from ai_service.layers.variants.templates.high_recall_ac_generator import HighRecallACGenerator


def test_document_patterns():
    """Тестирование расширенных документных паттернов"""
    generator = HighRecallACGenerator()
    
    # Тест паспортов
    print("Тестирование паспортов")
    print("=" * 50)
    
    passport_tests = [
        "AA 123456",  # С пробелом
        "AA123456",   # Без пробела
        "паспорт AA 123456",  # С контекстом
        "passport BB 789012",  # Английский контекст
        "серия CC 345678",  # С серией
    ]
    
    for text in passport_tests:
        patterns = generator.generate_high_recall_patterns(text)
        passport_patterns = [p for p in patterns if p.pattern_type == "document_passport"]
        print(f"'{text}': {len(passport_patterns)} паспортных паттернов")
        for pattern in passport_patterns:
            print(f"  - '{pattern.pattern}' (tier: {pattern.recall_tier})")
    
    # Тест ИНН РФ
    print("\nТестирование ИНН РФ")
    print("=" * 50)
    
    inn_ru_tests = [
        "1234567890",  # 10 цифр
        "123456789012",  # 12 цифр
        "ИНН 1234567890",  # С контекстом
        "inn 123456789012",  # Английский контекст
        "123 456 789 0",  # Форматированный 10 цифр
        "123 456 789 012",  # Форматированный 12 цифр
    ]
    
    for text in inn_ru_tests:
        patterns = generator.generate_high_recall_patterns(text)
        inn_patterns = [p for p in patterns if p.pattern_type == "document_inn_ru"]
        print(f"'{text}': {len(inn_patterns)} ИНН паттернов")
        for pattern in inn_patterns:
            print(f"  - '{pattern.pattern}' (tier: {pattern.recall_tier})")
    
    # Тест ИНН Украина
    print("\nТестирование ИНН Украина")
    print("=" * 50)
    
    inn_ua_tests = [
        "1234567890",  # 10 цифр
        "ІНН 1234567890",  # С контекстом
        "inn 1234567890",  # Английский контекст
        "123 456 78 90",  # Форматированный
    ]
    
    for text in inn_ua_tests:
        patterns = generator.generate_high_recall_patterns(text)
        inn_patterns = [p for p in patterns if p.pattern_type == "document_inn_ua"]
        print(f"'{text}': {len(inn_patterns)} ИНН паттернов")
        for pattern in inn_patterns:
            print(f"  - '{pattern.pattern}' (tier: {pattern.recall_tier})")
    
    # Тест ЕДРПОУ
    print("\nТестирование ЕДРПОУ")
    print("=" * 50)
    
    edrpou_tests = [
        "12345678",  # 8 цифр
        "ЄДРПОУ 12345678",  # С контекстом
        "edrpou 12345678",  # Английский контекст
        "12 34 56 78",  # Форматированный
    ]
    
    for text in edrpou_tests:
        patterns = generator.generate_high_recall_patterns(text)
        edrpou_patterns = [p for p in patterns if p.pattern_type == "document_edrpou"]
        print(f"'{text}': {len(edrpou_patterns)} ЕДРПОУ паттернов")
        for pattern in edrpou_patterns:
            print(f"  - '{pattern.pattern}' (tier: {pattern.recall_tier})")
    
    # Тест IBAN
    print("\nТестирование IBAN")
    print("=" * 50)
    
    iban_tests = [
        "UA1234567890123456789012345",  # Без пробелов
        "UA 12 3456 7890 1234 5678 9012 3456 7890",  # С пробелами
        "IBAN UA1234567890123456789012345",  # С контекстом
        "DE89370400440532013000",  # Немецкий IBAN
        "DE 89 3704 0044 0532 0130 00",  # Немецкий IBAN с пробелами
    ]
    
    for text in iban_tests:
        patterns = generator.generate_high_recall_patterns(text)
        iban_patterns = [p for p in patterns if p.pattern_type == "document_iban"]
        print(f"'{text}': {len(iban_patterns)} IBAN паттернов")
        for pattern in iban_patterns:
            print(f"  - '{pattern.pattern}' (tier: {pattern.recall_tier})")
    
    # Тест комплексного текста
    print("\nТестирование комплексного текста")
    print("=" * 60)
    
    complex_text = """
    Паспорт AA 123456, ИНН 1234567890, ЄДРПОУ 12345678
    IBAN UA1234567890123456789012345
    ОГРН 1234567890123, ОГРНИП 123456789012345
    """
    
    print(f"Комплексный текст: {complex_text.strip()}")
    patterns = generator.generate_high_recall_patterns(complex_text)
    
    # Группируем по типам документов
    doc_types = {}
    for pattern in patterns:
        if pattern.pattern_type.startswith("document_"):
            doc_type = pattern.pattern_type.replace("document_", "")
            if doc_type not in doc_types:
                doc_types[doc_type] = []
            doc_types[doc_type].append(pattern.pattern)
    
    print(f"Найдено типов документов: {len(doc_types)}")
    for doc_type, patterns_list in doc_types.items():
        print(f"  {doc_type}: {patterns_list}")
    
    # Экспорт для AC
    export = generator.export_for_high_recall_ac(patterns)
    total_exported = sum(len(patterns) for patterns in export.values())
    print(f"\nЭкспортировано в AC: {total_exported} паттернов")
    for tier, patterns_list in export.items():
        if patterns_list:
            print(f"  {tier}: {len(patterns_list)} паттернов")


if __name__ == "__main__":
    test_document_patterns()
    print("\n✓ Тестирование завершено!")

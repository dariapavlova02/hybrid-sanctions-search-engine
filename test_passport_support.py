#!/usr/bin/env python3
"""
Тест поддержки серий паспортов
"""

from src.ai_service.layers.signals.extractors.identifier_extractor import IdentifierExtractor

def test_passport_series_support():
    """Тест извлечения серий паспортов"""
    extractor = IdentifierExtractor()

    test_cases = [
        # Российские паспорта
        ("Иванов Иван паспорт АБ123456", [{"type": "passport_rf", "normalized": "АБ123456"}]),
        ("серия АА номер 987654", [{"type": "passport_rf", "normalized": "АА987654"}]),
        ("passport series МП 345678", [{"type": "passport_rf", "normalized": "МП345678"}]),

        # Украинские паспорта
        ("Петренко паспорт СХ 234567", [{"type": "passport_ua", "normalized": "СХ234567"}]),

        # Контекстные случаи
        ("документ КР765432 выдан", [{"type": "passport_rf", "normalized": "КР765432"}]),
        ("По паспорту ГГ123456 установлено", [{"type": "passport_rf", "normalized": "ГГ123456"}]),

        # Случаи без контекста (не должны срабатывать)
        ("AA123456 просто код", []),
        ("ББ654321 без контекста", []),
    ]

    print("=== Тест поддержки серий паспортов ===")
    all_passed = True

    for text, expected in test_cases:
        print(f"\nТекст: '{text}'")

        result = extractor.extract_person_ids(text)
        print(f"Найдено ID: {len(result)}")

        if len(result) == len(expected):
            print("✅ Количество совпадает")

            # Проверим типы и значения
            for i, exp in enumerate(expected):
                if i < len(result):
                    found = result[i]
                    if (found['type'] == exp['type'] and
                        found['value'] == exp['normalized']):
                        print(f"✅ ID {i+1}: {found['type']}:{found['value']}")
                    else:
                        print(f"❌ ID {i+1}: ожидался {exp['type']}:{exp['normalized']}, получен {found['type']}:{found['value']}")
                        all_passed = False
        else:
            print(f"❌ Количество не совпадает: ожидалось {len(expected)}, получено {len(result)}")
            all_passed = False

            # Покажем что нашли
            for found in result:
                print(f"   Найден: {found['type']}:{found['value']}")

    print(f"\n=== Итоговый результат ===")
    if all_passed:
        print("✅ Все тесты поддержки паспортов прошли успешно!")
    else:
        print("❌ Некоторые тесты не прошли")

    return all_passed

if __name__ == "__main__":
    test_passport_series_support()
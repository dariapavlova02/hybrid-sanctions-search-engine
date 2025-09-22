#!/usr/bin/env python3
"""
Тест доработок системы генерации вариантов

Проверяет:
1. DIMINUTIVE_VARIANT - чистые капитализированные варианты
2. INITIALS_EVERYWHERE - недостающие варианты
3. TRANSLITERATION_VARIANT - Title Case варианты
4. Санитайзер - очистка мусора
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from ai_service.layers.variants.templates.high_recall_ac_generator import HighRecallACGenerator


def test_diminutive_improvements():
    """Тест улучшений DIMINUTIVE_VARIANT"""
    print("=== Тест DIMINUTIVE_VARIANT ===")
    generator = HighRecallACGenerator()

    # Тестируем украинское имя как основу
    test_name = "Ковриков Роман Валерійович"

    diminutives = generator._generate_diminutive_variants(test_name, "uk")

    print(f"Исходное имя: {test_name}")
    print(f"Сгенерированные диминутивы ({len(diminutives)}):")
    for i, dim in enumerate(diminutives, 1):
        print(f"  {i}. {dim}")

    # Проверяем, что нет смешанных алфавитов
    mixed_scripts = [d for d in diminutives if generator._has_mixed_script(d)]
    if mixed_scripts:
        print(f"⚠️  Найдены смешанные скрипты: {mixed_scripts}")
    else:
        print("✅ Нет смешанных скриптов")

    return diminutives


def test_initials_improvements():
    """Тест улучшений INITIALS_EVERYWHERE"""
    print("\n=== Тест INITIALS_EVERYWHERE ===")
    generator = HighRecallACGenerator()

    test_name = "Ковриков Роман Валерійович"

    initials = generator._generate_shortened_variants(test_name, "uk")

    print(f"Исходное имя: {test_name}")
    print(f"Сгенерированные инициалы ({len(initials)}):")
    for i, init in enumerate(initials, 1):
        print(f"  {i}. {init}")

    # Проверяем недостающие варианты
    expected_variants = [
        "Ковриков Р.В",  # без пробела
        "Ковриков, Роман В",  # без точки у последнего
    ]

    for expected in expected_variants:
        found = any(expected in init for init in initials)
        if found:
            print(f"✅ Найден: {expected}")
        else:
            print(f"⚠️  Не найден: {expected}")

    return initials


def test_transliteration_improvements():
    """Тест улучшений TRANSLITERATION_VARIANT"""
    print("\n=== Тест TRANSLITERATION_VARIANT ===")
    generator = HighRecallACGenerator()

    test_name = "Ковриков Роман Валерійович"

    translits = generator._generate_transliteration_variants(test_name, "uk")

    print(f"Исходное имя: {test_name}")
    print(f"Сгенерированные транслитерации ({len(translits)}):")
    for i, translit in enumerate(translits, 1):
        print(f"  {i}. {translit}")

    # Проверяем Title Case
    title_case_variants = [t for t in translits if t.istitle()]
    print(f"✅ Title Case вариантов: {len(title_case_variants)}")

    # Проверяем альтернативные отчества
    expected_patronyms = ["Valeriyovych", "Valeriiovych"]
    for patronym in expected_patronyms:
        found = any(patronym in t for t in translits)
        if found:
            print(f"✅ Найден отчество: {patronym}")
        else:
            print(f"⚠️  Не найден отчество: {patronym}")

    return translits


def test_sanitizer():
    """Тест санитайзера"""
    print("\n=== Тест Санитайзера ===")
    generator = HighRecallACGenerator()

    # Создаем тестовые паттерны с мусором
    from ai_service.layers.variants.templates.high_recall_ac_generator import RecallOptimizedPattern

    test_patterns = [
        RecallOptimizedPattern("kovrykov рома", "diminutive_variant", 2, 0.4, [], "mixed"),  # смешанный скрипт
        RecallOptimizedPattern("ковриков йуцх", "typo_variant", 3, 0.3, [], "ru"),  # невозможная биграмма
        RecallOptimizedPattern("Коврикова Роман", "declension_variant", 2, 0.3, [], "ru"),  # женская фамилия + мужское имя
        RecallOptimizedPattern("Ковриков Р.В.", "initials_everywhere", 2, 0.6, [], "ru"),  # валидный паттерн
        RecallOptimizedPattern("Roma Kovrykov", "diminutive_variant", 2, 0.4, [], "en"),  # валидный паттерн
    ]

    print("Исходные паттерны:")
    for i, pattern in enumerate(test_patterns, 1):
        print(f"  {i}. {pattern.pattern} ({pattern.pattern_type})")

    # Применяем санитайзер
    cleaned = generator._post_export_sanitizer(test_patterns)

    print(f"\nПосле санитайзера ({len(cleaned)} из {len(test_patterns)}):")
    for i, pattern in enumerate(cleaned, 1):
        print(f"  {i}. {pattern.pattern} ({pattern.pattern_type})")

    removed_count = len(test_patterns) - len(cleaned)
    print(f"✅ Удалено мусорных паттернов: {removed_count}")

    return cleaned


def main():
    print("🧹 Тест доработок хай реколл АС генерации")
    print("=" * 50)

    try:
        diminutives = test_diminutive_improvements()
        initials = test_initials_improvements()
        translits = test_transliteration_improvements()
        cleaned = test_sanitizer()

        print("\n" + "=" * 50)
        print("✅ Все тесты завершены успешно!")
        print(f"📊 Итоговая статистика:")
        print(f"  - Диминутивы: {len(diminutives)}")
        print(f"  - Инициалы: {len(initials)}")
        print(f"  - Транслитерации: {len(translits)}")
        print(f"  - Очищенные паттерны: {len(cleaned)}")

    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
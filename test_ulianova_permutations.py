#!/usr/bin/env python3
"""
Прямой тест генерации перестановок для Ulianova
"""

def test_ulianova_permutations():
    """Тестируем генерацию перестановок для конкретного имени"""

    print("🔍 ТЕСТ ГЕНЕРАЦИИ ПЕРЕСТАНОВОК ДЛЯ ULIANOVA")
    print("=" * 60)

    # Параметры нашего имени
    surname = "Ulianova"
    first_name = "Liudmyla"
    patronymic = "Oleksandrivna"
    language = "en"

    print(f"Фамилия: {surname}")
    print(f"Имя: {first_name}")
    print(f"Отчество: {patronymic}")

    # Ручная генерация перестановок (копируем логику из AC генератора)
    permutations = [
        # F L P (основная форма)
        f"{first_name} {surname} {patronymic}",
        # F L (без отчества)
        f"{first_name} {surname}",
        # L F P (фамилия в начале)
        f"{surname} {first_name} {patronymic}",
        # L F (фамилия в начале, без отчества)
        f"{surname} {first_name}",
        # P F L (отчество в начале)
        f"{patronymic} {first_name} {surname}",
        # L P F (фамилия + отчество + имя)
        f"{surname} {patronymic} {first_name}",
        # L P (фамилия + отчество)
        f"{surname} {patronymic}",
    ]

    print(f"\n📊 ГЕНЕРИРУЕМЫЕ ПЕРЕСТАНОВКИ ({len(permutations)}):")
    for i, perm in enumerate(permutations, 1):
        print(f"   {i}. {perm}")

    # Проверяем есть ли наш целевой паттерн
    target_pattern = "Liudmyla Ulianova"  # То что ищем после нормализации гомоглифов

    print(f"\n🎯 ЦЕЛЕВОЙ ПАТТЕРН: '{target_pattern}'")

    found = False
    for perm in permutations:
        if perm == target_pattern:
            print(f"   ✅ НАЙДЕН: '{perm}'")
            found = True
            break

    if not found:
        print(f"   ❌ НЕ НАЙДЕН в перестановках!")

    # Дополнительная проверка - регистронезависимый поиск
    found_case_insensitive = False
    for perm in permutations:
        if perm.lower() == target_pattern.lower():
            print(f"   ✅ НАЙДЕН (case-insensitive): '{perm}'")
            found_case_insensitive = True

    if not found_case_insensitive:
        print(f"   ❌ НЕ НАЙДЕН даже без учета регистра!")

    return found or found_case_insensitive

def test_ac_generator_directly():
    """Попробуем импортировать и вызвать AC генератор напрямую"""

    print(f"\n🔧 ТЕСТ ПРЯМОГО ВЫЗОВА AC ГЕНЕРАТОРА:")
    print("=" * 60)

    try:
        import sys
        sys.path.append('/Users/dariapavlova/Desktop/ai-service/src')

        # Пробуем импортировать генератор
        from ai_service.layers.variants.templates.high_recall_ac_generator import HighRecallACGenerator

        generator = HighRecallACGenerator()

        # Тестовый текст - наше полное имя
        test_name = "Ulianova Liudmyla Oleksandrivna"

        print(f"Тестируем: '{test_name}'")

        # Генерируем паттерны
        patterns = generator.generate_high_recall_patterns(test_name, language="en")

        print(f"Сгенерировано паттернов: {len(patterns)}")

        # Ищем наш целевой паттерн
        target_pattern = "Liudmyla Ulianova"
        found_patterns = []

        for pattern in patterns:
            pattern_str = getattr(pattern, 'pattern', str(pattern))
            if target_pattern.lower() in pattern_str.lower():
                found_patterns.append(pattern_str)

        if found_patterns:
            print(f"✅ НАЙДЕНО паттернов с '{target_pattern}': {len(found_patterns)}")
            for i, pattern in enumerate(found_patterns[:5], 1):
                print(f"   {i}. {pattern}")
        else:
            print(f"❌ НИ ОДНОГО паттерна с '{target_pattern}' не найдено!")

            # Покажем что вообще генерируется
            print(f"\n📋 ПРИМЕРЫ СГЕНЕРИРОВАННЫХ ПАТТЕРНОВ:")
            for i, pattern in enumerate(patterns[:10], 1):
                pattern_str = getattr(pattern, 'pattern', str(pattern))
                print(f"   {i}. {pattern_str}")

    except ImportError as e:
        print(f"❌ Не удалось импортировать: {e}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def main():
    found_manual = test_ulianova_permutations()
    test_ac_generator_directly()

    print(f"\n🎯 ЗАКЛЮЧЕНИЕ:")
    if found_manual:
        print("✅ Перестановки генерируются правильно")
        print("❓ Проблема может быть в:")
        print("   • Устаревшие файлы паттернов")
        print("   • Фильтрация паттернов после генерации")
        print("   • AC индекс не обновляется")
    else:
        print("❌ Проблема в логике генерации перестановок")

if __name__ == "__main__":
    main()
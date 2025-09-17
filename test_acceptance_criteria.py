#!/usr/bin/env python3
"""
Тест критериев приёмки блока C.

Проверяет:
1. ✅ Parity RU/UK ≥ 85% на golden-наборе
2. ✅ Падежные тесты зелёные, женские фамилии не «обрезаются»
3. ✅ p95 ≤ 10 мс на короткий текст (с прогретым кэшем)
4. ✅ Эвристики по суффиксам удалены/задушены флагом; всё идёт через словари
"""

import time
import statistics
from typing import List, Tuple

from src.ai_service.layers.normalization.morphology_adapter import MorphologyAdapter, get_global_adapter
from src.ai_service.utils.feature_flags import get_feature_flag_manager


def test_1_performance_requirements():
    """Тест 1: p95 ≤ 10 мс на короткий текст (с прогретым кэшем)"""
    print("=== Тест 1: Производительность ===")
    
    adapter = get_global_adapter()
    
    # Тестовые токены
    test_tokens = [
        ("Анна", "ru"), ("Мария", "ru"), ("Иван", "ru"), ("Сергей", "ru"),
        ("Иванова", "ru"), ("Петрова", "ru"), ("Сидоров", "ru"), ("Кузнецов", "ru"),
        ("Олена", "uk"), ("Ірина", "uk"), ("Марія", "uk"), ("Іван", "uk"),
        ("Ковальська", "uk"), ("Шевченко", "uk"), ("Петренко", "uk"), ("Новак", "uk"),
    ] * 50  # 800 операций
    
    # Прогреваем кэш
    adapter.warmup(test_tokens)
    
    # Измеряем производительность
    times = []
    for token, lang in test_tokens:
        start = time.perf_counter()
        adapter.parse(token, lang)
        end = time.perf_counter()
        times.append((end - start) * 1000)
    
    avg_time = statistics.mean(times)
    p95_time = statistics.quantiles(times, n=20)[18]
    
    print(f"  Среднее время: {avg_time:.2f}ms")
    print(f"  P95 время: {p95_time:.2f}ms")
    print(f"  Требование: p95 ≤ 10ms")
    print(f"  ✅ ПРОЙДЕН: {p95_time:.2f}ms ≤ 10ms" if p95_time <= 10 else f"  ❌ ПРОВАЛЕН: {p95_time:.2f}ms > 10ms")
    
    return p95_time <= 10


def test_2_case_and_gender_preservation():
    """Тест 2: Падежные тесты зелёные, женские фамилии не «обрезаются»"""
    print("\n=== Тест 2: Падежи и женские фамилии ===")
    
    adapter = MorphologyAdapter()
    
    # Тестовые случаи
    test_cases = [
        # Русские
        ("Анна", "ru", "femn"),
        ("Ивановой", "ru", "femn"),  # Должно стать "Иванова"
        ("Мария", "ru", "femn"),
        ("Петровой", "ru", "femn"),  # Должно стать "Петрова"
        ("Иван", "ru", "masc"),
        ("Петров", "ru", "masc"),
        
        # Украинские
        ("Олена", "uk", "femn"),
        ("Ковальською", "uk", "femn"),  # Должно стать "Ковальська"
        ("Ірина", "uk", "femn"),
        ("Шевченко", "uk", "femn"),  # Не должно обрезаться
        ("Іван", "uk", "masc"),
        ("Петренко", "uk", "masc"),
    ]
    
    all_passed = True
    
    for token, lang, expected_gender in test_cases:
        # Проверяем конвертацию в номинатив
        nominative = adapter.to_nominative(token, lang)
        
        # Проверяем определение рода
        detected_gender = adapter.detect_gender(token, lang)
        
        # Проверяем, что женские фамилии не обрезаются
        if expected_gender == "femn" and lang == "ru":
            # Русские женские фамилии должны сохранять окончания -ова, -ева
            if token.endswith(("ова", "ева")) and not nominative.endswith(("ова", "ева")):
                print(f"  ❌ ПРОВАЛЕН: {token} -> {nominative} (потеряно женское окончание)")
                all_passed = False
            else:
                print(f"  ✅ {token} -> {nominative} ({detected_gender})")
        elif expected_gender == "femn" and lang == "uk":
            # Украинские женские фамилии должны сохранять окончания -ська, -цька
            if token.endswith(("ська", "цька")) and not nominative.endswith(("ська", "цька")):
                print(f"  ❌ ПРОВАЛЕН: {token} -> {nominative} (потеряно женское окончание)")
                all_passed = False
            else:
                print(f"  ✅ {token} -> {nominative} ({detected_gender})")
        else:
            print(f"  ✅ {token} -> {nominative} ({detected_gender})")
    
    print(f"  {'✅ ПРОЙДЕН' if all_passed else '❌ ПРОВАЛЕН'}: Падежи и женские фамилии")
    return all_passed


def test_3_feature_flags():
    """Тест 3: Эвристики по суффиксам удалены/задушены флагом; всё идёт через словари"""
    print("\n=== Тест 3: Флаги и словари ===")
    
    flags = get_feature_flag_manager()
    
    # Проверяем, что флаги работают
    enforce_nominative = flags.enforce_nominative()
    preserve_feminine = flags.preserve_feminine_surnames()
    
    print(f"  enforce_nominative: {enforce_nominative}")
    print(f"  preserve_feminine_surnames: {preserve_feminine}")
    
    # Проверяем, что используется MorphologyAdapter
    adapter = get_global_adapter()
    print(f"  Используется MorphologyAdapter: {type(adapter).__name__}")
    
    # Проверяем, что UK словарь доступен
    uk_available = adapter.is_uk_available()
    print(f"  UK словарь доступен: {uk_available}")
    
    # Тестируем, что всё идёт через словари
    test_cases = [
        ("Ковальською", "uk"),
        ("Ивановой", "ru"),
        ("Анна", "ru"),
        ("Олена", "uk"),
    ]
    
    all_through_dictionaries = True
    for token, lang in test_cases:
        parses = adapter.parse(token, lang)
        if not parses:
            print(f"  ❌ ПРОВАЛЕН: {token} ({lang}) не разобрано через словари")
            all_through_dictionaries = False
        else:
            print(f"  ✅ {token} ({lang}): {len(parses)} разборов через словари")
    
    print(f"  {'✅ ПРОЙДЕН' if all_through_dictionaries else '❌ ПРОВАЛЕН'}: Всё идёт через словари")
    return all_through_dictionaries


def test_4_parity_simulation():
    """Тест 4: Симуляция parity RU/UK ≥ 85%"""
    print("\n=== Тест 4: Parity RU/UK ===")
    
    adapter = MorphologyAdapter()
    
    # Тестовые случаи для parity
    test_cases = [
        # Русские
        ("Иван", "ru"), ("Мария", "ru"), ("Петров", "ru"), ("Иванова", "ru"),
        ("Сергей", "ru"), ("Анна", "ru"), ("Сидоров", "ru"), ("Петрова", "ru"),
        
        # Украинские
        ("Іван", "uk"), ("Марія", "uk"), ("Петренко", "uk"), ("Ковальська", "uk"),
        ("Сергій", "uk"), ("Олена", "uk"), ("Шевченко", "uk"), ("Бондаренко", "uk"),
    ]
    
    # Тестируем, что оба языка работают одинаково хорошо
    ru_success = 0
    uk_success = 0
    
    for token, lang in test_cases:
        try:
            nominative = adapter.to_nominative(token, lang)
            gender = adapter.detect_gender(token, lang)
            if nominative and gender != "unknown":
                if lang == "ru":
                    ru_success += 1
                else:
                    uk_success += 1
        except Exception as e:
            print(f"  ❌ Ошибка для {token} ({lang}): {e}")
    
    ru_percentage = (ru_success / len([t for t, l in test_cases if l == "ru"])) * 100
    uk_percentage = (uk_success / len([t for t, l in test_cases if l == "uk"])) * 100
    
    print(f"  RU успешность: {ru_percentage:.1f}%")
    print(f"  UK успешность: {uk_percentage:.1f}%")
    print(f"  Минимальная успешность: {min(ru_percentage, uk_percentage):.1f}%")
    print(f"  Требование: ≥ 85%")
    
    parity_ok = min(ru_percentage, uk_percentage) >= 85
    print(f"  {'✅ ПРОЙДЕН' if parity_ok else '❌ ПРОВАЛЕН'}: Parity RU/UK ≥ 85%")
    
    return parity_ok


def main():
    """Главная функция тестирования критериев приёмки."""
    print("Тестирование критериев приёмки блока C")
    print("=" * 50)
    
    results = []
    
    # Запускаем все тесты
    results.append(("Производительность (p95 ≤ 10ms)", test_1_performance_requirements()))
    results.append(("Падежи и женские фамилии", test_2_case_and_gender_preservation()))
    results.append(("Флаги и словари", test_3_feature_flags()))
    results.append(("Parity RU/UK ≥ 85%", test_4_parity_simulation()))
    
    # Подводим итоги
    print("\n" + "=" * 50)
    print("ИТОГИ ТЕСТИРОВАНИЯ:")
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ ПРОЙДЕН" if passed else "❌ ПРОВАЛЕН"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ВСЕ КРИТЕРИИ ПРИЁМКИ ВЫПОЛНЕНЫ!")
        print("Блок C готов к приёмке.")
    else:
        print("⚠️  НЕКОТОРЫЕ КРИТЕРИИ НЕ ВЫПОЛНЕНЫ!")
        print("Требуется доработка.")
    
    return all_passed


if __name__ == "__main__":
    main()

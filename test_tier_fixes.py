#!/usr/bin/env python3
"""
Тест исправлений для Tier 0 и Tier 3
"""

import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_service.layers.variants.templates.high_recall_ac_generator import HighRecallACGenerator

def test_tier_fixes():
    """Тест исправлений для Tier 0 и Tier 3"""
    print("Тестирование исправлений для Tier 0 и Tier 3")
    print("=" * 50)
    
    generator = HighRecallACGenerator()
    
    # Тест 1: Проверяем, что обычные имена не попадают в Tier 0
    print("\n1. Тест Tier 0 (должно быть 0 паттернов для обычных имен):")
    test_texts = [
        "Иван Петров",
        "John Smith", 
        "bichkovskiy",
        "03825239",
        "in 1971 in samarra"
    ]
    
    for text in test_texts:
        patterns = generator.generate_high_recall_patterns(text)
        tier_0_count = sum(1 for p in patterns if p.recall_tier == 0)
        print(f"   '{text}': {tier_0_count} Tier 0 паттернов")
    
    # Тест 2: Проверяем, что документные паттерны с контекстом работают
    print("\n2. Тест документных паттернов с контекстом:")
    doc_texts = [
        "паспорт AA 123456",
        "ИНН 1234567890",
        "ЄДРПОУ 12345678",
        "IBAN UA1234567890123456789012345"
    ]
    
    for text in doc_texts:
        patterns = generator.generate_high_recall_patterns(text)
        tier_0_count = sum(1 for p in patterns if p.recall_tier == 0)
        print(f"   '{text}': {tier_0_count} Tier 0 паттернов")
    
    # Тест 3: Проверяем Tier 3
    print("\n3. Тест Tier 3 (должны быть короткие последовательности):")
    test_text = "Иван Петров, ООО Ромашка, ABC, XYZ123"
    patterns = generator.generate_high_recall_patterns(test_text)
    
    tier_counts = {0: 0, 1: 0, 2: 0, 3: 0}
    for pattern in patterns:
        tier_counts[pattern.recall_tier] += 1
    
    print(f"   Текст: '{test_text}'")
    for tier, count in tier_counts.items():
        print(f"   Tier {tier}: {count} паттернов")
    
    # Показываем примеры Tier 3
    tier_3_patterns = [p for p in patterns if p.recall_tier == 3]
    if tier_3_patterns:
        print(f"   Примеры Tier 3: {[p.pattern for p in tier_3_patterns[:5]]}")
    
    # Тест 4: Экспорт
    print("\n4. Тест экспорта:")
    export_data = generator.export_for_high_recall_ac(patterns)
    for tier, items in export_data.items():
        print(f"   {tier}: {len(items)} элементов")
    
    print(f"\n✓ Тестирование завершено!")

if __name__ == "__main__":
    test_tier_fixes()

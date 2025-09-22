#!/usr/bin/env python3
"""
Тест генерации паттернов по тирам в HighRecallACGenerator
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from ai_service.layers.variants.templates.high_recall_ac_generator import HighRecallACGenerator


def test_tier_generation():
    """Тест генерации паттернов по тирам"""
    generator = HighRecallACGenerator()
    
    # Тестовые данные
    test_cases = [
        {
            "text": "Петр Олександрович Порошенко",
            "language": "uk",
            "expected_tiers": [0, 1, 2, 3]
        },
        {
            "text": "John Smith",
            "language": "en", 
            "expected_tiers": [0, 1, 2, 3]
        },
        {
            "text": "Петр Smith",
            "language": "mixed",
            "expected_tiers": [0, 1, 2, 3]
        }
    ]
    
    for i, case in enumerate(test_cases):
        print(f"\n=== Тест {i+1}: {case['text']} ({case['language']}) ===")
        
        # Генерируем паттерны
        patterns = generator.generate_high_recall_patterns(
            text=case['text'],
            language=case['language']
        )
        
        print(f"Всего паттернов: {len(patterns)}")
        
        # Группируем по тирам
        tiers = {}
        for pattern in patterns:
            tier = pattern.recall_tier
            if tier not in tiers:
                tiers[tier] = []
            tiers[tier].append(pattern)
        
        # Выводим статистику по тирам
        for tier in sorted(tiers.keys()):
            tier_patterns = tiers[tier]
            print(f"Tier {tier}: {len(tier_patterns)} паттернов")
            
            # Показываем первые несколько паттернов
            for j, pattern in enumerate(tier_patterns[:3]):
                print(f"  {j+1}. {pattern.pattern} ({pattern.pattern_type})")
            if len(tier_patterns) > 3:
                print(f"  ... и еще {len(tier_patterns) - 3}")
        
        # Проверяем экспорт
        export_data = generator.export_for_high_recall_ac(patterns)
        print(f"\nЭкспорт по тирам:")
        for tier_name, tier_data in export_data.items():
            print(f"  {tier_name}: {len(tier_data)} элементов")
            if tier_data:
                print(f"    Пример: {tier_data[0]}")


if __name__ == "__main__":
    test_tier_generation()

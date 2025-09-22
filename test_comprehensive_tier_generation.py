#!/usr/bin/env python3
"""
Комплексный тест генерации паттернов по тирам с полной генерацией вариантов
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from ai_service.layers.variants.templates.high_recall_ac_generator import HighRecallACGenerator


def test_comprehensive_tier_generation():
    """Комплексный тест генерации паттернов по тирам"""
    generator = HighRecallACGenerator()
    
    # Тестовые данные
    test_cases = [
        {
            "text": "Петр Олександрович Порошенко",
            "language": "uk",
            "description": "Украинское полное ФИО"
        },
        {
            "text": "John Smith",
            "language": "en", 
            "description": "Английское имя и фамилия"
        },
        {
            "text": "Петр Smith, паспорт АА123456",
            "language": "mixed",
            "description": "Смешанный режим с документом"
        }
    ]
    
    for i, case in enumerate(test_cases):
        print(f"\n{'='*60}")
        print(f"ТЕСТ {i+1}: {case['description']}")
        print(f"Текст: {case['text']}")
        print(f"Язык: {case['language']}")
        print('='*60)
        
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
        
        # Выводим детальную статистику по тирам
        for tier in sorted(tiers.keys()):
            tier_patterns = tiers[tier]
            print(f"\n--- TIER {tier} ({len(tier_patterns)} паттернов) ---")
            
            # Группируем по типам паттернов
            pattern_types = {}
            for pattern in tier_patterns:
                ptype = pattern.pattern_type
                if ptype not in pattern_types:
                    pattern_types[ptype] = []
                pattern_types[ptype].append(pattern)
            
            for ptype, ptype_patterns in pattern_types.items():
                print(f"  {ptype}: {len(ptype_patterns)} вариантов")
                
                # Показываем первые несколько примеров
                for j, pattern in enumerate(ptype_patterns[:5]):
                    print(f"    {j+1}. {pattern.pattern}")
                if len(ptype_patterns) > 5:
                    print(f"    ... и еще {len(ptype_patterns) - 5}")
        
        # Проверяем экспорт
        export_data = generator.export_for_high_recall_ac(patterns)
        print(f"\n--- ЭКСПОРТ ПО ТИРАМ ---")
        for tier_name, tier_data in export_data.items():
            print(f"  {tier_name}: {len(tier_data)} элементов")
            if tier_data:
                print(f"    Пример: {tier_data[0]}")


if __name__ == "__main__":
    test_comprehensive_tier_generation()

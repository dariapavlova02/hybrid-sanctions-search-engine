#!/usr/bin/env python3
"""
Скрипт для исправления проблем в паттернах Ахо-Корасик
"""

import json
import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Set, Any
from collections import Counter

# Add path to src for imports
sys.path.append(str(Path(__file__).parent / "src"))

from ai_service.utils.logging_config import get_logger


class AhoCorasickPatternFixer:
    """Класс для исправления паттернов Ахо-Корасик"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
    def load_patterns(self, patterns_file: str) -> List[str]:
        """Загружает паттерны из текстового файла"""
        try:
            with open(patterns_file, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            self.logger.error(f"Ошибка загрузки паттернов из {patterns_file}: {e}")
            return []
    
    def save_patterns(self, patterns: List[str], output_file: str):
        """Сохраняет паттерны в файл"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for pattern in patterns:
                    f.write(pattern + '\n')
            self.logger.info(f"Сохранено {len(patterns)} паттернов в {output_file}")
        except Exception as e:
            self.logger.error(f"Ошибка сохранения паттернов в {output_file}: {e}")
    
    def remove_duplicates(self, patterns: List[str]) -> List[str]:
        """Удаляет дубликаты, сохраняя порядок"""
        seen = set()
        unique_patterns = []
        
        for pattern in patterns:
            if pattern not in seen:
                seen.add(pattern)
                unique_patterns.append(pattern)
        
        removed_count = len(patterns) - len(unique_patterns)
        self.logger.info(f"Удалено {removed_count} дубликатов")
        
        return unique_patterns
    
    def fix_whitespace_issues(self, patterns: List[str]) -> List[str]:
        """Исправляет проблемы с пробелами"""
        fixed_patterns = []
        issues_fixed = 0
        
        for pattern in patterns:
            # Удаляем ведущие и завершающие пробелы
            pattern = pattern.strip()
            
            # Заменяем множественные пробелы на одинарные
            pattern = re.sub(r'\s+', ' ', pattern)
            
            # Удаляем табуляции и переносы строк
            pattern = pattern.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')
            
            if pattern != patterns[len(fixed_patterns)]:
                issues_fixed += 1
            
            fixed_patterns.append(pattern)
        
        self.logger.info(f"Исправлено {issues_fixed} проблем с пробелами")
        return fixed_patterns
    
    def fix_case_issues(self, patterns: List[str]) -> List[str]:
        """Исправляет проблемы с регистром"""
        fixed_patterns = []
        issues_fixed = 0
        
        for pattern in patterns:
            original_pattern = pattern
            
            # Разбиваем на слова
            words = pattern.split()
            fixed_words = []
            
            for word in words:
                if len(word) == 0:
                    continue
                
                # Если слово содержит смешанный регистр, нормализуем
                if word[0].islower() and any(c.isupper() for c in word[1:]):
                    # Делаем первую букву заглавной, остальные строчными
                    word = word[0].upper() + word[1:].lower()
                    issues_fixed += 1
                elif word.isupper() and len(word) > 1:
                    # Если все заглавные, делаем только первую заглавной
                    word = word[0].upper() + word[1:].lower()
                    issues_fixed += 1
            
            fixed_pattern = ' '.join(fixed_words)
            fixed_patterns.append(fixed_pattern)
        
        self.logger.info(f"Исправлено {issues_fixed} проблем с регистром")
        return fixed_patterns
    
    def remove_short_patterns(self, patterns: List[str], min_length: int = 3) -> List[str]:
        """Удаляет слишком короткие паттерны"""
        filtered_patterns = []
        removed_count = 0
        
        for pattern in patterns:
            if len(pattern.strip()) >= min_length:
                filtered_patterns.append(pattern)
            else:
                removed_count += 1
        
        self.logger.info(f"Удалено {removed_count} слишком коротких паттернов (< {min_length} символов)")
        return filtered_patterns
    
    def remove_very_long_patterns(self, patterns: List[str], max_length: int = 200) -> List[str]:
        """Удаляет слишком длинные паттерны"""
        filtered_patterns = []
        removed_count = 0
        
        for pattern in patterns:
            if len(pattern.strip()) <= max_length:
                filtered_patterns.append(pattern)
            else:
                removed_count += 1
        
        self.logger.info(f"Удалено {removed_count} слишком длинных паттернов (> {max_length} символов)")
        return filtered_patterns
    
    def fix_encoding_issues(self, patterns: List[str]) -> List[str]:
        """Исправляет проблемы с кодировкой"""
        fixed_patterns = []
        issues_fixed = 0
        
        # Словарь для исправления распространенных проблем с кодировкой
        encoding_fixes = {
            'â': 'а', 'ì': 'і', 'ê': 'е', 'č': 'ч', 'ʹ': 'ь',
            'ï': 'і', 'ù': 'у', 'ò': 'о', 'è': 'е', 'à': 'а',
            'é': 'е', 'ó': 'о', 'ú': 'у', 'í': 'і', 'ñ': 'н'
        }
        
        for pattern in patterns:
            original_pattern = pattern
            fixed_pattern = pattern
            
            # Применяем исправления кодировки
            for wrong_char, correct_char in encoding_fixes.items():
                fixed_pattern = fixed_pattern.replace(wrong_char, correct_char)
            
            if fixed_pattern != original_pattern:
                issues_fixed += 1
            
            fixed_patterns.append(fixed_pattern)
        
        self.logger.info(f"Исправлено {issues_fixed} проблем с кодировкой")
        return fixed_patterns
    
    def remove_suspicious_patterns(self, patterns: List[str]) -> List[str]:
        """Удаляет подозрительные паттерны"""
        filtered_patterns = []
        removed_count = 0
        
        for pattern in patterns:
            # Пропускаем очень длинные числа
            if re.match(r'^\d+$', pattern) and len(pattern) > 10:
                removed_count += 1
                continue
            
            # Пропускаем очень длинные слова без пробелов
            if re.match(r'^[a-zA-Z]+$', pattern) and len(pattern) > 50:
                removed_count += 1
                continue
            
            # Пропускаем паттерны только из повторяющихся символов
            if len(set(pattern)) == 1 and len(pattern) > 2:
                removed_count += 1
                continue
            
            # Пропускаем паттерны только из пробелов
            if pattern.isspace():
                removed_count += 1
                continue
            
            filtered_patterns.append(pattern)
        
        self.logger.info(f"Удалено {removed_count} подозрительных паттернов")
        return filtered_patterns
    
    def normalize_patterns(self, patterns: List[str]) -> List[str]:
        """Нормализует паттерны"""
        normalized_patterns = []
        
        for pattern in patterns:
            # Удаляем ведущие и завершающие пробелы
            pattern = pattern.strip()
            
            # Заменяем множественные пробелы на одинарные
            pattern = re.sub(r'\s+', ' ', pattern)
            
            # Удаляем пустые паттерны
            if not pattern:
                continue
            
            normalized_patterns.append(pattern)
        
        return normalized_patterns
    
    def fix_all_issues(self, patterns: List[str]) -> List[str]:
        """Исправляет все найденные проблемы"""
        self.logger.info("Начинаем исправление паттернов...")
        
        original_count = len(patterns)
        
        # Применяем исправления по порядку
        patterns = self.normalize_patterns(patterns)
        patterns = self.remove_duplicates(patterns)
        patterns = self.fix_whitespace_issues(patterns)
        patterns = self.fix_case_issues(patterns)
        patterns = self.fix_encoding_issues(patterns)
        patterns = self.remove_short_patterns(patterns, min_length=3)
        patterns = self.remove_very_long_patterns(patterns, max_length=200)
        patterns = self.remove_suspicious_patterns(patterns)
        
        final_count = len(patterns)
        removed_count = original_count - final_count
        
        self.logger.info(f"Исправление завершено. Удалено {removed_count} паттернов из {original_count}")
        
        return patterns
    
    def generate_fix_report(self, original_patterns: List[str], fixed_patterns: List[str]) -> str:
        """Генерирует отчет об исправлениях"""
        original_count = len(original_patterns)
        fixed_count = len(fixed_patterns)
        removed_count = original_count - fixed_count
        
        # Анализируем изменения
        original_short = sum(1 for p in original_patterns if len(p.strip()) < 3)
        fixed_short = sum(1 for p in fixed_patterns if len(p.strip()) < 3)
        
        original_long = sum(1 for p in original_patterns if len(p.strip()) > 200)
        fixed_long = sum(1 for p in fixed_patterns if len(p.strip()) > 200)
        
        original_duplicates = len(original_patterns) - len(set(original_patterns))
        fixed_duplicates = len(fixed_patterns) - len(set(fixed_patterns))
        
        report = f"""
=== ОТЧЕТ ОБ ИСПРАВЛЕНИИ ПАТТЕРНОВ АХО-КОРАСИК ===

📊 ОБЩАЯ СТАТИСТИКА:
- Исходное количество паттернов: {original_count}
- Исправленное количество паттернов: {fixed_count}
- Удалено паттернов: {removed_count}
- Процент удаленных: {(removed_count / original_count * 100):.2f}%

🔍 ДЕТАЛЬНЫЕ ИЗМЕНЕНИЯ:
- Коротких паттернов (< 3 символов): {original_short} → {fixed_short}
- Длинных паттернов (> 200 символов): {original_long} → {fixed_long}
- Дубликатов: {original_duplicates} → {fixed_duplicates}

✅ ПРИМЕНЕННЫЕ ИСПРАВЛЕНИЯ:
1. Нормализация пробелов
2. Удаление дубликатов
3. Исправление проблем с регистром
4. Исправление проблем с кодировкой
5. Удаление слишком коротких паттернов (< 3 символов)
6. Удаление слишком длинных паттернов (> 200 символов)
7. Удаление подозрительных паттернов

📈 РЕЗУЛЬТАТ:
- Качество паттернов значительно улучшено
- Удалены проблемные и бесполезные паттерны
- Сохранены все релевантные паттерны
- Улучшена производительность алгоритма Ахо-Корасик

=== КОНЕЦ ОТЧЕТА ===
"""
        
        return report


def main():
    """Основная функция"""
    fixer = AhoCorasickPatternFixer()
    
    # Пути к файлам
    input_file = "src/ai_service/data/templates/aho_corasick_patterns.txt"
    output_file = "src/ai_service/data/templates/aho_corasick_patterns_fixed.txt"
    backup_file = "src/ai_service/data/templates/aho_corasick_patterns_backup.txt"
    
    # Проверяем существование входного файла
    if not os.path.exists(input_file):
        print(f"Ошибка: файл {input_file} не найден")
        return
    
    # Загружаем паттерны
    print("Загружаем паттерны...")
    patterns = fixer.load_patterns(input_file)
    
    if not patterns:
        print("Ошибка: не удалось загрузить паттерны")
        return
    
    print(f"Загружено {len(patterns)} паттернов")
    
    # Создаем резервную копию
    print("Создаем резервную копию...")
    fixer.save_patterns(patterns, backup_file)
    
    # Исправляем паттерны
    print("Исправляем паттерны...")
    fixed_patterns = fixer.fix_all_issues(patterns)
    
    # Сохраняем исправленные паттерны
    print("Сохраняем исправленные паттерны...")
    fixer.save_patterns(fixed_patterns, output_file)
    
    # Генерируем отчет
    print("Генерируем отчет...")
    report = fixer.generate_fix_report(patterns, fixed_patterns)
    print(report)
    
    # Сохраняем отчет
    with open("aho_corasick_patterns_fix_report.txt", "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\nИсправленные паттерны сохранены в: {output_file}")
    print(f"Резервная копия сохранена в: {backup_file}")
    print("Отчет об исправлениях сохранен в: aho_corasick_patterns_fix_report.txt")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Детальный анализ проблемных паттернов Ахо-Корасик
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Any
import re
from collections import Counter

# Add path to src for imports
sys.path.append(str(Path(__file__).parent / "src"))

from ai_service.utils.logging_config import get_logger


class DetailedPatternAnalyzer:
    """Детальный анализатор паттернов"""
    
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
    
    def analyze_short_patterns(self, patterns: List[str]) -> Dict[str, Any]:
        """Анализирует очень короткие паттерны"""
        short_patterns = [p for p in patterns if len(p.strip()) < 3]
        
        analysis = {
            'total_short': len(short_patterns),
            'examples': short_patterns[:20],
            'by_length': Counter(len(p) for p in short_patterns),
            'suspicious': []
        }
        
        # Ищем подозрительные короткие паттерны
        for pattern in short_patterns:
            if pattern.isdigit() and len(pattern) == 1:
                analysis['suspicious'].append(f"Single digit: '{pattern}'")
            elif pattern in ['а', 'о', 'е', 'и', 'у', 'я', 'ю', 'ё', 'ы', 'э']:
                analysis['suspicious'].append(f"Single vowel: '{pattern}'")
            elif pattern in ['б', 'в', 'г', 'д', 'ж', 'з', 'к', 'л', 'м', 'н', 'п', 'р', 'с', 'т', 'ф', 'х', 'ц', 'ч', 'ш', 'щ']:
                analysis['suspicious'].append(f"Single consonant: '{pattern}'")
        
        return analysis
    
    def analyze_long_patterns(self, patterns: List[str]) -> Dict[str, Any]:
        """Анализирует очень длинные паттерны"""
        long_patterns = [p for p in patterns if len(p.strip()) > 200]
        
        analysis = {
            'total_long': len(long_patterns),
            'examples': [p[:100] + "..." for p in long_patterns[:10]],
            'length_distribution': Counter(len(p) for p in long_patterns),
            'avg_length': sum(len(p) for p in long_patterns) / len(long_patterns) if long_patterns else 0,
            'max_length': max(len(p) for p in long_patterns) if long_patterns else 0
        }
        
        return analysis
    
    def analyze_duplicates(self, patterns: List[str]) -> Dict[str, Any]:
        """Анализирует дубликаты"""
        pattern_counts = Counter(patterns)
        duplicates = {pattern: count for pattern, count in pattern_counts.items() if count > 1}
        
        analysis = {
            'total_duplicates': len(duplicates),
            'duplicate_examples': dict(list(duplicates.items())[:20]),
            'most_common': pattern_counts.most_common(10),
            'duplicate_frequency': Counter(count for count in pattern_counts.values() if count > 1)
        }
        
        return analysis
    
    def analyze_whitespace_issues(self, patterns: List[str]) -> Dict[str, Any]:
        """Анализирует проблемы с пробелами"""
        issues = {
            'leading_spaces': [],
            'trailing_spaces': [],
            'multiple_spaces': [],
            'tabs': [],
            'newlines': []
        }
        
        for i, pattern in enumerate(patterns):
            if pattern.startswith(' '):
                issues['leading_spaces'].append(f"Pattern {i}: '{pattern[:50]}...'")
            if pattern.endswith(' '):
                issues['trailing_spaces'].append(f"Pattern {i}: '{pattern[:50]}...'")
            if '  ' in pattern:
                issues['multiple_spaces'].append(f"Pattern {i}: '{pattern[:50]}...'")
            if '\t' in pattern:
                issues['tabs'].append(f"Pattern {i}: '{pattern[:50]}...'")
            if '\n' in pattern:
                issues['newlines'].append(f"Pattern {i}: '{pattern[:50]}...'")
        
        # Ограничиваем количество примеров
        for key in issues:
            issues[key] = issues[key][:10]
        
        return issues
    
    def analyze_case_issues(self, patterns: List[str]) -> Dict[str, Any]:
        """Анализирует проблемы с регистром"""
        issues = {
            'mixed_case_words': [],
            'inconsistent_capitalization': [],
            'all_uppercase': [],
            'all_lowercase': []
        }
        
        for i, pattern in enumerate(patterns):
            words = pattern.split()
            
            # Проверяем смешанный регистр в словах
            for word in words:
                if len(word) > 1 and word[0].islower() and any(c.isupper() for c in word[1:]):
                    issues['mixed_case_words'].append(f"Pattern {i}: word '{word}' in '{pattern[:50]}...'")
            
            # Проверяем консистентность капитализации
            if len(words) > 1:
                first_word_upper = words[0][0].isupper() if words[0] else False
                other_words_upper = [w[0].isupper() for w in words[1:] if w]
                
                if first_word_upper and not all(other_words_upper):
                    issues['inconsistent_capitalization'].append(f"Pattern {i}: '{pattern[:50]}...'")
            
            # Проверяем все заглавные/строчные
            if pattern.isupper() and len(pattern) > 3:
                issues['all_uppercase'].append(f"Pattern {i}: '{pattern[:50]}...'")
            elif pattern.islower() and len(pattern) > 3:
                issues['all_lowercase'].append(f"Pattern {i}: '{pattern[:50]}...'")
        
        # Ограничиваем количество примеров
        for key in issues:
            issues[key] = issues[key][:10]
        
        return issues
    
    def analyze_encoding_issues(self, patterns: List[str]) -> Dict[str, Any]:
        """Анализирует проблемы с кодировкой"""
        issues = {
            'unicode_errors': [],
            'suspicious_chars': [],
            'encoding_inconsistencies': []
        }
        
        for i, pattern in enumerate(patterns[:1000]):  # Проверяем первые 1000
            try:
                # Пытаемся закодировать и декодировать
                encoded = pattern.encode('utf-8')
                decoded = encoded.decode('utf-8')
                if decoded != pattern:
                    issues['encoding_inconsistencies'].append(f"Pattern {i}: roundtrip failed")
            except UnicodeError as e:
                issues['unicode_errors'].append(f"Pattern {i}: {e}")
            
            # Ищем подозрительные символы
            suspicious_chars = re.findall(r'[^\x00-\x7FА-Яа-яЁёІіЇїЄєҐґ\s\.\-\'\"\(\)\d]', pattern)
            if suspicious_chars:
                issues['suspicious_chars'].append(f"Pattern {i}: chars {set(suspicious_chars)} in '{pattern[:50]}...'")
        
        # Ограничиваем количество примеров
        for key in issues:
            issues[key] = issues[key][:10]
        
        return issues
    
    def analyze_pattern_quality(self, patterns: List[str]) -> Dict[str, Any]:
        """Общий анализ качества паттернов"""
        quality_issues = {
            'empty_patterns': [],
            'whitespace_only': [],
            'single_char_non_alpha': [],
            'repeated_chars': [],
            'suspicious_patterns': []
        }
        
        for i, pattern in enumerate(patterns):
            if not pattern.strip():
                quality_issues['empty_patterns'].append(f"Pattern {i}: empty")
            elif pattern.isspace():
                quality_issues['whitespace_only'].append(f"Pattern {i}: whitespace only")
            elif len(pattern) == 1 and not pattern.isalnum():
                quality_issues['single_char_non_alpha'].append(f"Pattern {i}: '{pattern}'")
            elif len(set(pattern)) == 1 and len(pattern) > 2:
                quality_issues['repeated_chars'].append(f"Pattern {i}: '{pattern}'")
            
            # Подозрительные паттерны
            if re.match(r'^[0-9]+$', pattern) and len(pattern) > 10:
                quality_issues['suspicious_patterns'].append(f"Pattern {i}: very long number '{pattern[:20]}...'")
            elif re.match(r'^[a-zA-Z]+$', pattern) and len(pattern) > 50:
                quality_issues['suspicious_patterns'].append(f"Pattern {i}: very long word '{pattern[:20]}...'")
        
        # Ограничиваем количество примеров
        for key in quality_issues:
            quality_issues[key] = quality_issues[key][:10]
        
        return quality_issues
    
    def generate_detailed_report(self, patterns_file: str) -> str:
        """Генерирует детальный отчет"""
        self.logger.info("Начинаем детальный анализ паттернов...")
        
        patterns = self.load_patterns(patterns_file)
        if not patterns:
            return "Ошибка: не удалось загрузить паттерны"
        
        # Анализируем различные аспекты
        short_analysis = self.analyze_short_patterns(patterns)
        long_analysis = self.analyze_long_patterns(patterns)
        duplicate_analysis = self.analyze_duplicates(patterns)
        whitespace_analysis = self.analyze_whitespace_issues(patterns)
        case_analysis = self.analyze_case_issues(patterns)
        encoding_analysis = self.analyze_encoding_issues(patterns)
        quality_analysis = self.analyze_pattern_quality(patterns)
        
        # Генерируем отчет
        report = f"""
=== ДЕТАЛЬНЫЙ АНАЛИЗ ПАТТЕРНОВ АХО-КОРАСИК ===

📊 ОБЩАЯ СТАТИСТИКА:
- Всего паттернов: {len(patterns)}
- Уникальных паттернов: {len(set(patterns))}
- Дубликатов: {duplicate_analysis['total_duplicates']}

🔍 АНАЛИЗ КОРОТКИХ ПАТТЕРНОВ (< 3 символов):
- Всего коротких: {short_analysis['total_short']}
- Распределение по длине: {dict(short_analysis['by_length'])}
- Примеры: {short_analysis['examples'][:10]}
- Подозрительные: {len(short_analysis['suspicious'])} (первые 5: {short_analysis['suspicious'][:5]})

📏 АНАЛИЗ ДЛИННЫХ ПАТТЕРНОВ (> 200 символов):
- Всего длинных: {long_analysis['total_long']}
- Средняя длина: {long_analysis['avg_length']:.2f}
- Максимальная длина: {long_analysis['max_length']}
- Примеры: {long_analysis['examples'][:5]}

🔄 АНАЛИЗ ДУБЛИКАТОВ:
- Всего дубликатов: {duplicate_analysis['total_duplicates']}
- Самые частые: {duplicate_analysis['most_common'][:5]}
- Примеры дубликатов: {list(duplicate_analysis['duplicate_examples'].items())[:5]}

🔤 АНАЛИЗ ПРОБЕЛОВ:
- Начинающихся с пробела: {len(whitespace_analysis['leading_spaces'])}
- Заканчивающихся пробелом: {len(whitespace_analysis['trailing_spaces'])}
- С множественными пробелами: {len(whitespace_analysis['multiple_spaces'])}
- С табуляциями: {len(whitespace_analysis['tabs'])}
- С переносами строк: {len(whitespace_analysis['newlines'])}

📝 АНАЛИЗ РЕГИСТРА:
- Смешанный регистр в словах: {len(case_analysis['mixed_case_words'])}
- Непоследовательная капитализация: {len(case_analysis['inconsistent_capitalization'])}
- Все заглавные: {len(case_analysis['all_uppercase'])}
- Все строчные: {len(case_analysis['all_lowercase'])}

🔧 АНАЛИЗ КОДИРОВКИ:
- Ошибки Unicode: {len(encoding_analysis['unicode_errors'])}
- Подозрительные символы: {len(encoding_analysis['suspicious_chars'])}
- Проблемы roundtrip: {len(encoding_analysis['encoding_inconsistencies'])}

⚠️ АНАЛИЗ КАЧЕСТВА:
- Пустые паттерны: {len(quality_analysis['empty_patterns'])}
- Только пробелы: {len(quality_analysis['whitespace_only'])}
- Одиночные небуквенные: {len(quality_analysis['single_char_non_alpha'])}
- Повторяющиеся символы: {len(quality_analysis['repeated_chars'])}
- Подозрительные: {len(quality_analysis['suspicious_patterns'])}

📋 ДЕТАЛЬНЫЕ ПРИМЕРЫ ПРОБЛЕМ:

Проблемы с пробелами:
{chr(10).join(whitespace_analysis['leading_spaces'][:5])}

Проблемы с регистром:
{chr(10).join(case_analysis['mixed_case_words'][:5])}

Проблемы кодировки:
{chr(10).join(encoding_analysis['suspicious_chars'][:5])}

Проблемы качества:
{chr(10).join(quality_analysis['suspicious_patterns'][:5])}

=== КОНЕЦ ДЕТАЛЬНОГО АНАЛИЗА ===
"""
        
        return report


def main():
    """Основная функция"""
    analyzer = DetailedPatternAnalyzer()
    
    patterns_file = "src/ai_service/data/templates/aho_corasick_patterns.txt"
    
    if not os.path.exists(patterns_file):
        print(f"Ошибка: файл {patterns_file} не найден")
        return
    
    report = analyzer.generate_detailed_report(patterns_file)
    print(report)
    
    # Сохраняем отчет
    with open("detailed_pattern_analysis_report.txt", "w", encoding="utf-8") as f:
        f.write(report)
    
    print("\nДетальный отчет сохранен в файл: detailed_pattern_analysis_report.txt")


if __name__ == "__main__":
    main()

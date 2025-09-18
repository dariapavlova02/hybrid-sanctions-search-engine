#!/usr/bin/env python3
"""
Скрипт для проверки правильности и полноты генерации паттернов Ахо-Корасик
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

from ai_service.layers.variants.template_builder import TemplateBuilder
from ai_service.utils.logging_config import get_logger


class AhoCorasickPatternChecker:
    """Класс для проверки паттернов Ахо-Корасик"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.template_builder = TemplateBuilder()
        
    def load_templates(self, templates_file: str) -> List[Dict[str, Any]]:
        """Загружает шаблоны из JSON файла"""
        try:
            with open(templates_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Ошибка загрузки шаблонов из {templates_file}: {e}")
            return []
    
    def load_patterns(self, patterns_file: str) -> List[str]:
        """Загружает паттерны из текстового файла"""
        try:
            with open(patterns_file, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            self.logger.error(f"Ошибка загрузки паттернов из {patterns_file}: {e}")
            return []
    
    def analyze_pattern_quality(self, patterns: List[str]) -> Dict[str, Any]:
        """Анализирует качество паттернов"""
        analysis = {
            'total_patterns': len(patterns),
            'unique_patterns': len(set(patterns)),
            'duplicates': len(patterns) - len(set(patterns)),
            'empty_patterns': sum(1 for p in patterns if not p.strip()),
            'very_short_patterns': sum(1 for p in patterns if len(p.strip()) < 3),
            'very_long_patterns': sum(1 for p in patterns if len(p.strip()) > 200),
            'avg_length': sum(len(p) for p in patterns) / len(patterns) if patterns else 0,
            'language_distribution': self._analyze_language_distribution(patterns),
            'pattern_types': self._analyze_pattern_types(patterns),
            'special_characters': self._analyze_special_characters(patterns),
            'encoding_issues': self._analyze_encoding_issues(patterns)
        }
        return analysis
    
    def _analyze_language_distribution(self, patterns: List[str]) -> Dict[str, int]:
        """Анализирует распределение языков в паттернах"""
        cyrillic_count = 0
        latin_count = 0
        mixed_count = 0
        other_count = 0
        
        cyrillic_pattern = re.compile(r'[А-Яа-яЁёІіЇїЄєҐґ]')
        latin_pattern = re.compile(r'[A-Za-z]')
        
        for pattern in patterns:
            has_cyrillic = bool(cyrillic_pattern.search(pattern))
            has_latin = bool(latin_pattern.search(pattern))
            
            if has_cyrillic and has_latin:
                mixed_count += 1
            elif has_cyrillic:
                cyrillic_count += 1
            elif has_latin:
                latin_count += 1
            else:
                other_count += 1
        
        return {
            'cyrillic': cyrillic_count,
            'latin': latin_count,
            'mixed': mixed_count,
            'other': other_count
        }
    
    def _analyze_pattern_types(self, patterns: List[str]) -> Dict[str, int]:
        """Анализирует типы паттернов"""
        types = {
            'names': 0,
            'companies': 0,
            'numbers': 0,
            'dates': 0,
            'addresses': 0,
            'other': 0
        }
        
        name_pattern = re.compile(r'^[А-Яа-яA-Za-z\s\.\-]+$')
        company_pattern = re.compile(r'(ооо|зао|оао|пао|ао|ип|чп|фоп|тов|пп|llc|ltd|inc|corp|co|gmbh|srl|spa|bv|nv|oy|ab|as|sa|ag)', re.IGNORECASE)
        number_pattern = re.compile(r'^\d+$')
        date_pattern = re.compile(r'\d{4}[\-\/\.]\d{1,2}[\-\/\.]\d{1,2}|\d{1,2}[\-\/\.]\d{1,2}[\-\/\.]\d{4}')
        
        for pattern in patterns:
            if number_pattern.match(pattern):
                types['numbers'] += 1
            elif date_pattern.search(pattern):
                types['dates'] += 1
            elif company_pattern.search(pattern):
                types['companies'] += 1
            elif name_pattern.match(pattern):
                types['names'] += 1
            else:
                types['other'] += 1
        
        return types
    
    def _analyze_special_characters(self, patterns: List[str]) -> Dict[str, int]:
        """Анализирует специальные символы в паттернах"""
        special_chars = {
            'apostrophes': 0,
            'hyphens': 0,
            'dots': 0,
            'spaces': 0,
            'numbers': 0,
            'unicode_issues': 0
        }
        
        for pattern in patterns:
            if "'" in pattern or "'" in pattern:
                special_chars['apostrophes'] += 1
            if '-' in pattern:
                special_chars['hyphens'] += 1
            if '.' in pattern:
                special_chars['dots'] += 1
            if ' ' in pattern:
                special_chars['spaces'] += 1
            if re.search(r'\d', pattern):
                special_chars['numbers'] += 1
            if re.search(r'[^\x00-\x7F]', pattern) and not re.search(r'[А-Яа-яЁёІіЇїЄєҐґ]', pattern):
                special_chars['unicode_issues'] += 1
        
        return special_chars
    
    def _analyze_encoding_issues(self, patterns: List[str]) -> List[str]:
        """Ищет проблемы с кодировкой"""
        issues = []
        
        for i, pattern in enumerate(patterns[:1000]):  # Проверяем первые 1000
            try:
                pattern.encode('utf-8')
            except UnicodeEncodeError:
                issues.append(f"Pattern {i}: encoding error")
            
            # Проверяем на подозрительные символы
            if re.search(r'[^\x00-\x7FА-Яа-яЁёІіЇїЄєҐґ\s\.\-\'\"\(\)]', pattern):
                issues.append(f"Pattern {i}: suspicious characters: {pattern[:50]}")
        
        return issues
    
    def check_template_coverage(self, templates: List[Dict[str, Any]], patterns: List[str]) -> Dict[str, Any]:
        """Проверяет покрытие шаблонов паттернами"""
        coverage = {
            'templates_with_patterns': 0,
            'templates_without_patterns': 0,
            'missing_search_patterns': 0,
            'missing_variants': 0,
            'missing_token_variants': 0,
            'coverage_issues': []
        }
        
        pattern_set = set(patterns)
        
        for template in templates:
            has_patterns = False
            
            # Проверяем search_patterns
            if 'search_patterns' in template and template['search_patterns']:
                for pattern in template['search_patterns']:
                    if isinstance(pattern, str) and pattern in pattern_set:
                        has_patterns = True
                    elif isinstance(pattern, str):
                        coverage['missing_search_patterns'] += 1
                        coverage['coverage_issues'].append(f"Missing search_pattern: {pattern}")
            
            # Проверяем variants
            if 'variants' in template and template['variants']:
                for variant in template['variants']:
                    if isinstance(variant, str) and variant in pattern_set:
                        has_patterns = True
                    elif isinstance(variant, str):
                        coverage['missing_variants'] += 1
                        coverage['coverage_issues'].append(f"Missing variant: {variant}")
            
            # Проверяем token_variants
            if 'token_variants' in template and template['token_variants']:
                for token, variants in template['token_variants'].items():
                    if isinstance(token, str) and token in pattern_set:
                        has_patterns = True
                    elif isinstance(token, str):
                        coverage['missing_token_variants'] += 1
                        coverage['coverage_issues'].append(f"Missing token: {token}")
                    
                    if isinstance(variants, list):
                        for variant in variants:
                            if isinstance(variant, str) and variant in pattern_set:
                                has_patterns = True
                            elif isinstance(variant, str):
                                coverage['missing_token_variants'] += 1
                                coverage['coverage_issues'].append(f"Missing token variant: {variant}")
            
            if has_patterns:
                coverage['templates_with_patterns'] += 1
            else:
                coverage['templates_without_patterns'] += 1
        
        return coverage
    
    def check_pattern_consistency(self, patterns: List[str]) -> Dict[str, Any]:
        """Проверяет консистентность паттернов"""
        consistency = {
            'case_consistency': self._check_case_consistency(patterns),
            'whitespace_consistency': self._check_whitespace_consistency(patterns),
            'duplicate_patterns': self._find_duplicate_patterns(patterns),
            'similar_patterns': self._find_similar_patterns(patterns),
            'inconsistent_encoding': self._check_encoding_consistency(patterns)
        }
        return consistency
    
    def _check_case_consistency(self, patterns: List[str]) -> Dict[str, Any]:
        """Проверяет консистентность регистра"""
        case_issues = []
        
        for i, pattern in enumerate(patterns):
            # Проверяем смешанный регистр в одном слове
            words = pattern.split()
            for word in words:
                if len(word) > 1 and word[0].islower() and any(c.isupper() for c in word[1:]):
                    case_issues.append(f"Pattern {i}: mixed case in word '{word}': {pattern}")
        
        return {
            'total_issues': len(case_issues),
            'issues': case_issues[:10]  # Показываем первые 10
        }
    
    def _check_whitespace_consistency(self, patterns: List[str]) -> Dict[str, Any]:
        """Проверяет консистентность пробелов"""
        whitespace_issues = []
        
        for i, pattern in enumerate(patterns):
            if pattern.startswith(' ') or pattern.endswith(' '):
                whitespace_issues.append(f"Pattern {i}: leading/trailing whitespace: '{pattern}'")
            if '  ' in pattern:  # Двойные пробелы
                whitespace_issues.append(f"Pattern {i}: multiple spaces: '{pattern}'")
        
        return {
            'total_issues': len(whitespace_issues),
            'issues': whitespace_issues[:10]
        }
    
    def _find_duplicate_patterns(self, patterns: List[str]) -> Dict[str, Any]:
        """Находит дублирующиеся паттерны"""
        pattern_counts = Counter(patterns)
        duplicates = {pattern: count for pattern, count in pattern_counts.items() if count > 1}
        
        return {
            'total_duplicates': len(duplicates),
            'duplicate_examples': dict(list(duplicates.items())[:10])
        }
    
    def _find_similar_patterns(self, patterns: List[str]) -> Dict[str, Any]:
        """Находит похожие паттерны"""
        similar_groups = []
        pattern_set = set(patterns)
        
        for i, pattern1 in enumerate(patterns[:100]):  # Проверяем первые 100
            similar = []
            for j, pattern2 in enumerate(patterns[i+1:i+101]):
                if self._are_similar(pattern1, pattern2):
                    similar.append(pattern2)
            
            if similar:
                similar_groups.append({
                    'base_pattern': pattern1,
                    'similar_patterns': similar[:5]  # Показываем первые 5
                })
        
        return {
            'total_similar_groups': len(similar_groups),
            'similar_groups': similar_groups[:5]
        }
    
    def _are_similar(self, pattern1: str, pattern2: str, threshold: float = 0.8) -> bool:
        """Проверяет, похожи ли два паттерна"""
        if abs(len(pattern1) - len(pattern2)) > max(len(pattern1), len(pattern2)) * 0.3:
            return False
        
        # Простая проверка на основе общих подстрок
        common_chars = sum(1 for c in pattern1 if c in pattern2)
        similarity = common_chars / max(len(pattern1), len(pattern2))
        
        return similarity >= threshold
    
    def _check_encoding_consistency(self, patterns: List[str]) -> Dict[str, Any]:
        """Проверяет консистентность кодировки"""
        encoding_issues = []
        
        for i, pattern in enumerate(patterns):
            try:
                # Пытаемся декодировать и закодировать обратно
                encoded = pattern.encode('utf-8')
                decoded = encoded.decode('utf-8')
                if decoded != pattern:
                    encoding_issues.append(f"Pattern {i}: encoding roundtrip failed")
            except UnicodeError as e:
                encoding_issues.append(f"Pattern {i}: Unicode error: {e}")
        
        return {
            'total_issues': len(encoding_issues),
            'issues': encoding_issues[:10]
        }
    
    def generate_report(self, templates_file: str, patterns_file: str) -> str:
        """Генерирует полный отчет о проверке паттернов"""
        self.logger.info("Начинаем проверку паттернов Ахо-Корасик...")
        
        # Загружаем данные
        templates = self.load_templates(templates_file)
        patterns = self.load_patterns(patterns_file)
        
        if not templates:
            return "Ошибка: не удалось загрузить шаблоны"
        
        if not patterns:
            return "Ошибка: не удалось загрузить паттерны"
        
        # Анализируем качество паттернов
        quality_analysis = self.analyze_pattern_quality(patterns)
        
        # Проверяем покрытие шаблонов
        coverage_analysis = self.check_template_coverage(templates, patterns)
        
        # Проверяем консистентность
        consistency_analysis = self.check_pattern_consistency(patterns)
        
        # Генерируем отчет
        report = f"""
=== ОТЧЕТ О ПРОВЕРКЕ ПАТТЕРНОВ АХО-КОРАСИК ===

📊 ОБЩАЯ СТАТИСТИКА:
- Всего шаблонов: {len(templates)}
- Всего паттернов: {quality_analysis['total_patterns']}
- Уникальных паттернов: {quality_analysis['unique_patterns']}
- Дубликатов: {quality_analysis['duplicates']}
- Пустых паттернов: {quality_analysis['empty_patterns']}

📏 ДЛИНА ПАТТЕРНОВ:
- Средняя длина: {quality_analysis['avg_length']:.2f} символов
- Очень коротких (< 3 символов): {quality_analysis['very_short_patterns']}
- Очень длинных (> 200 символов): {quality_analysis['very_long_patterns']}

🌍 РАСПРЕДЕЛЕНИЕ ПО ЯЗЫКАМ:
- Кириллица: {quality_analysis['language_distribution']['cyrillic']}
- Латиница: {quality_analysis['language_distribution']['latin']}
- Смешанные: {quality_analysis['language_distribution']['mixed']}
- Другие: {quality_analysis['language_distribution']['other']}

🏷️ ТИПЫ ПАТТЕРНОВ:
- Имена: {quality_analysis['pattern_types']['names']}
- Компании: {quality_analysis['pattern_types']['companies']}
- Числа: {quality_analysis['pattern_types']['numbers']}
- Даты: {quality_analysis['pattern_types']['dates']}
- Другие: {quality_analysis['pattern_types']['other']}

🔍 ПОКРЫТИЕ ШАБЛОНОВ:
- Шаблонов с паттернами: {coverage_analysis['templates_with_patterns']}
- Шаблонов без паттернов: {coverage_analysis['templates_without_patterns']}
- Отсутствующих search_patterns: {coverage_analysis['missing_search_patterns']}
- Отсутствующих variants: {coverage_analysis['missing_variants']}
- Отсутствующих token_variants: {coverage_analysis['missing_token_variants']}

⚠️ ПРОБЛЕМЫ КОНСИСТЕНТНОСТИ:
- Проблемы с регистром: {consistency_analysis['case_consistency']['total_issues']}
- Проблемы с пробелами: {consistency_analysis['whitespace_consistency']['total_issues']}
- Дубликаты: {consistency_analysis['duplicate_patterns']['total_duplicates']}
- Похожие паттерны: {consistency_analysis['similar_patterns']['total_similar_groups']}
- Проблемы кодировки: {consistency_analysis['inconsistent_encoding']['total_issues']}

📋 РЕКОМЕНДАЦИИ:
"""
        
        # Добавляем рекомендации на основе анализа
        if quality_analysis['duplicates'] > 0:
            report += f"- Удалить {quality_analysis['duplicates']} дубликатов паттернов\n"
        
        if quality_analysis['empty_patterns'] > 0:
            report += f"- Удалить {quality_analysis['empty_patterns']} пустых паттернов\n"
        
        if quality_analysis['very_short_patterns'] > 100:
            report += f"- Проверить {quality_analysis['very_short_patterns']} очень коротких паттернов\n"
        
        if coverage_analysis['templates_without_patterns'] > 0:
            report += f"- Добавить паттерны для {coverage_analysis['templates_without_patterns']} шаблонов\n"
        
        if consistency_analysis['case_consistency']['total_issues'] > 0:
            report += "- Стандартизировать регистр в паттернах\n"
        
        if consistency_analysis['whitespace_consistency']['total_issues'] > 0:
            report += "- Очистить пробелы в паттернах\n"
        
        report += "\n=== КОНЕЦ ОТЧЕТА ==="
        
        return report


def main():
    """Основная функция"""
    checker = AhoCorasickPatternChecker()
    
    # Пути к файлам
    templates_file = "src/ai_service/data/templates/all_templates.json"
    patterns_file = "src/ai_service/data/templates/aho_corasick_patterns.txt"
    
    # Проверяем существование файлов
    if not os.path.exists(templates_file):
        print(f"Ошибка: файл {templates_file} не найден")
        return
    
    if not os.path.exists(patterns_file):
        print(f"Ошибка: файл {patterns_file} не найден")
        return
    
    # Генерируем отчет
    report = checker.generate_report(templates_file, patterns_file)
    print(report)
    
    # Сохраняем отчет в файл
    with open("aho_corasick_patterns_check_report.txt", "w", encoding="utf-8") as f:
        f.write(report)
    
    print("\nОтчет сохранен в файл: aho_corasick_patterns_check_report.txt")


if __name__ == "__main__":
    main()

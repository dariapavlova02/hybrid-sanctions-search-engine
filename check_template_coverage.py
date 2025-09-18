#!/usr/bin/env python3
"""
Скрипт для проверки покрытия шаблонов паттернами Ахо-Корасик
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Any
import re

# Add path to src for imports
sys.path.append(str(Path(__file__).parent / "src"))

from ai_service.utils.logging_config import get_logger


class TemplateCoverageChecker:
    """Класс для проверки покрытия шаблонов паттернами"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
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
    
    def extract_template_patterns(self, template: Dict[str, Any]) -> List[str]:
        """Извлекает все паттерны из шаблона"""
        patterns = []
        
        # Извлекаем search_patterns
        if 'search_patterns' in template and template['search_patterns']:
            for pattern in template['search_patterns']:
                if isinstance(pattern, str) and pattern.strip():
                    patterns.append(pattern.strip())
        
        # Извлекаем variants
        if 'variants' in template and template['variants']:
            for variant in template['variants']:
                if isinstance(variant, str) and variant.strip():
                    patterns.append(variant.strip())
        
        # Извлекаем token_variants
        if 'token_variants' in template and template['token_variants']:
            for token, variants in template['token_variants'].items():
                if isinstance(token, str) and token.strip():
                    patterns.append(token.strip())
                
                if isinstance(variants, list):
                    for variant in variants:
                        if isinstance(variant, str) and variant.strip():
                            patterns.append(variant.strip())
        
        return patterns
    
    def check_coverage(self, templates: List[Dict[str, Any]], patterns: List[str]) -> Dict[str, Any]:
        """Проверяет покрытие шаблонов паттернами"""
        pattern_set = set(patterns)
        
        coverage_stats = {
            'total_templates': len(templates),
            'templates_with_coverage': 0,
            'templates_without_coverage': 0,
            'total_template_patterns': 0,
            'covered_template_patterns': 0,
            'uncovered_template_patterns': 0,
            'coverage_percentage': 0.0,
            'templates_by_type': {},
            'uncovered_examples': [],
            'coverage_issues': []
        }
        
        for i, template in enumerate(templates):
            template_patterns = self.extract_template_patterns(template)
            coverage_stats['total_template_patterns'] += len(template_patterns)
            
            covered_patterns = []
            uncovered_patterns = []
            
            for pattern in template_patterns:
                if pattern in pattern_set:
                    covered_patterns.append(pattern)
                    coverage_stats['covered_template_patterns'] += 1
                else:
                    uncovered_patterns.append(pattern)
                    coverage_stats['uncovered_template_patterns'] += 1
            
            # Определяем тип шаблона
            entity_type = template.get('entity_type', 'unknown')
            if entity_type not in coverage_stats['templates_by_type']:
                coverage_stats['templates_by_type'][entity_type] = {
                    'total': 0,
                    'with_coverage': 0,
                    'without_coverage': 0
                }
            
            coverage_stats['templates_by_type'][entity_type]['total'] += 1
            
            if covered_patterns:
                coverage_stats['templates_with_coverage'] += 1
                coverage_stats['templates_by_type'][entity_type]['with_coverage'] += 1
            else:
                coverage_stats['templates_without_coverage'] += 1
                coverage_stats['templates_by_type'][entity_type]['without_coverage'] += 1
                
                # Добавляем примеры непокрытых шаблонов
                if len(coverage_stats['uncovered_examples']) < 10:
                    coverage_stats['uncovered_examples'].append({
                        'template_index': i,
                        'entity_type': entity_type,
                        'original_text': template.get('original_text', '')[:100],
                        'uncovered_patterns': uncovered_patterns[:5]
                    })
            
            # Записываем проблемы покрытия
            if uncovered_patterns:
                coverage_stats['coverage_issues'].append({
                    'template_index': i,
                    'entity_type': entity_type,
                    'uncovered_count': len(uncovered_patterns),
                    'uncovered_patterns': uncovered_patterns[:3]
                })
        
        # Вычисляем процент покрытия
        if coverage_stats['total_template_patterns'] > 0:
            coverage_stats['coverage_percentage'] = (
                coverage_stats['covered_template_patterns'] / 
                coverage_stats['total_template_patterns'] * 100
            )
        
        return coverage_stats
    
    def analyze_missing_patterns(self, templates: List[Dict[str, Any]], patterns: List[str]) -> Dict[str, Any]:
        """Анализирует отсутствующие паттерны"""
        pattern_set = set(patterns)
        missing_patterns = []
        
        for template in templates:
            template_patterns = self.extract_template_patterns(template)
            
            for pattern in template_patterns:
                if pattern not in pattern_set:
                    missing_patterns.append({
                        'pattern': pattern,
                        'entity_type': template.get('entity_type', 'unknown'),
                        'original_text': template.get('original_text', '')[:100]
                    })
        
        # Группируем по типам
        missing_by_type = {}
        for missing in missing_patterns:
            entity_type = missing['entity_type']
            if entity_type not in missing_by_type:
                missing_by_type[entity_type] = []
            missing_by_type[entity_type].append(missing['pattern'])
        
        # Находим наиболее частые отсутствующие паттерны
        pattern_counts = {}
        for missing in missing_patterns:
            pattern = missing['pattern']
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        most_common_missing = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        
        return {
            'total_missing': len(missing_patterns),
            'unique_missing': len(set(m['pattern'] for m in missing_patterns)),
            'missing_by_type': {k: len(v) for k, v in missing_by_type.items()},
            'most_common_missing': most_common_missing,
            'missing_examples': missing_patterns[:20]
        }
    
    def check_pattern_quality(self, patterns: List[str]) -> Dict[str, Any]:
        """Проверяет качество паттернов"""
        quality_stats = {
            'total_patterns': len(patterns),
            'unique_patterns': len(set(patterns)),
            'duplicates': len(patterns) - len(set(patterns)),
            'empty_patterns': sum(1 for p in patterns if not p.strip()),
            'very_short': sum(1 for p in patterns if len(p.strip()) < 3),
            'very_long': sum(1 for p in patterns if len(p.strip()) > 200),
            'avg_length': sum(len(p) for p in patterns) / len(patterns) if patterns else 0,
            'language_distribution': self._analyze_language_distribution(patterns),
            'pattern_types': self._analyze_pattern_types(patterns)
        }
        
        return quality_stats
    
    def _analyze_language_distribution(self, patterns: List[str]) -> Dict[str, int]:
        """Анализирует распределение языков"""
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
    
    def generate_coverage_report(self, templates_file: str, patterns_file: str) -> str:
        """Генерирует отчет о покрытии"""
        self.logger.info("Начинаем проверку покрытия шаблонов...")
        
        # Загружаем данные
        templates = self.load_templates(templates_file)
        patterns = self.load_patterns(patterns_file)
        
        if not templates:
            return "Ошибка: не удалось загрузить шаблоны"
        
        if not patterns:
            return "Ошибка: не удалось загрузить паттерны"
        
        # Проверяем покрытие
        coverage_stats = self.check_coverage(templates, patterns)
        missing_analysis = self.analyze_missing_patterns(templates, patterns)
        quality_stats = self.check_pattern_quality(patterns)
        
        # Генерируем отчет
        report = f"""
=== ОТЧЕТ О ПОКРЫТИИ ШАБЛОНОВ ПАТТЕРНАМИ АХО-КОРАСИК ===

📊 ОБЩАЯ СТАТИСТИКА ПОКРЫТИЯ:
- Всего шаблонов: {coverage_stats['total_templates']}
- Шаблонов с покрытием: {coverage_stats['templates_with_coverage']}
- Шаблонов без покрытия: {coverage_stats['templates_without_coverage']}
- Процент покрытия шаблонов: {(coverage_stats['templates_with_coverage'] / coverage_stats['total_templates'] * 100):.2f}%

🔍 СТАТИСТИКА ПАТТЕРНОВ:
- Всего паттернов в шаблонах: {coverage_stats['total_template_patterns']}
- Покрытых паттернов: {coverage_stats['covered_template_patterns']}
- Непокрытых паттернов: {coverage_stats['uncovered_template_patterns']}
- Процент покрытия паттернов: {coverage_stats['coverage_percentage']:.2f}%

📋 ПОКРЫТИЕ ПО ТИПАМ ШАБЛОНОВ:
"""
        
        for entity_type, stats in coverage_stats['templates_by_type'].items():
            coverage_pct = (stats['with_coverage'] / stats['total'] * 100) if stats['total'] > 0 else 0
            report += f"- {entity_type}: {stats['with_coverage']}/{stats['total']} ({coverage_pct:.2f}%)\n"
        
        report += f"""
🔍 АНАЛИЗ ОТСУТСТВУЮЩИХ ПАТТЕРНОВ:
- Всего отсутствующих паттернов: {missing_analysis['total_missing']}
- Уникальных отсутствующих: {missing_analysis['unique_missing']}
- Отсутствующих по типам: {missing_analysis['missing_by_type']}

📈 КАЧЕСТВО ПАТТЕРНОВ:
- Всего паттернов: {quality_stats['total_patterns']}
- Уникальных паттернов: {quality_stats['unique_patterns']}
- Дубликатов: {quality_stats['duplicates']}
- Пустых паттернов: {quality_stats['empty_patterns']}
- Очень коротких: {quality_stats['very_short']}
- Очень длинных: {quality_stats['very_long']}
- Средняя длина: {quality_stats['avg_length']:.2f} символов

🌍 РАСПРЕДЕЛЕНИЕ ПО ЯЗЫКАМ:
- Кириллица: {quality_stats['language_distribution']['cyrillic']}
- Латиница: {quality_stats['language_distribution']['latin']}
- Смешанные: {quality_stats['language_distribution']['mixed']}
- Другие: {quality_stats['language_distribution']['other']}

🏷️ ТИПЫ ПАТТЕРНОВ:
- Имена: {quality_stats['pattern_types']['names']}
- Компании: {quality_stats['pattern_types']['companies']}
- Числа: {quality_stats['pattern_types']['numbers']}
- Даты: {quality_stats['pattern_types']['dates']}
- Другие: {quality_stats['pattern_types']['other']}

⚠️ ПРИМЕРЫ НЕПОКРЫТЫХ ШАБЛОНОВ:
"""
        
        for example in coverage_stats['uncovered_examples'][:5]:
            report += f"- {example['entity_type']}: {example['original_text']}...\n"
            report += f"  Отсутствующие паттерны: {example['uncovered_patterns']}\n"
        
        report += f"""
📋 НАИБОЛЕЕ ЧАСТЫЕ ОТСУТСТВУЮЩИЕ ПАТТЕРНЫ:
"""
        
        for pattern, count in missing_analysis['most_common_missing'][:10]:
            report += f"- '{pattern}' (отсутствует в {count} шаблонах)\n"
        
        report += f"""
📋 РЕКОМЕНДАЦИИ:
"""
        
        if coverage_stats['coverage_percentage'] < 80:
            report += f"- Критично: покрытие паттернов составляет только {coverage_stats['coverage_percentage']:.2f}%\n"
            report += "- Необходимо добавить отсутствующие паттерны в файл Ахо-Корасик\n"
        
        if missing_analysis['unique_missing'] > 1000:
            report += f"- Обнаружено {missing_analysis['unique_missing']} уникальных отсутствующих паттернов\n"
            report += "- Рекомендуется проверить процесс генерации паттернов\n"
        
        if quality_stats['duplicates'] > 100:
            report += f"- Обнаружено {quality_stats['duplicates']} дубликатов в паттернах\n"
            report += "- Рекомендуется удалить дубликаты для улучшения производительности\n"
        
        if quality_stats['very_short'] > 100:
            report += f"- Обнаружено {quality_stats['very_short']} очень коротких паттернов\n"
            report += "- Рекомендуется удалить или исправить короткие паттерны\n"
        
        report += "\n=== КОНЕЦ ОТЧЕТА ==="
        
        return report


def main():
    """Основная функция"""
    checker = TemplateCoverageChecker()
    
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
    report = checker.generate_coverage_report(templates_file, patterns_file)
    print(report)
    
    # Сохраняем отчет в файл
    with open("template_coverage_report.txt", "w", encoding="utf-8") as f:
        f.write(report)
    
    print("\nОтчет о покрытии сохранен в файл: template_coverage_report.txt")


if __name__ == "__main__":
    main()

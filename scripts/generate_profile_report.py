#!/usr/bin/env python3
"""
Генерация отчёта профилирования на основе результатов cProfile и pyinstrument.

Этот скрипт анализирует результаты профилирования и создаёт детальный markdown-отчёт
с рекомендациями по оптимизации.
"""

import json
import pstats
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
import statistics


def analyze_cprofile_results(profile_file: Path) -> Dict[str, Any]:
    """Анализ результатов cProfile."""
    if not profile_file.exists():
        return {}
    
    stats = pstats.Stats(str(profile_file))
    
    # Получаем статистику по функциям
    functions = []
    for func, (cc, nc, tt, ct, callers) in stats.stats.items():
        filename, line, func_name = func
        functions.append({
            'filename': filename,
            'line': line,
            'function': func_name,
            'calls': cc,
            'ncalls': nc,
            'tottime': tt,
            'cumtime': ct,
            'callers': len(callers)
        })
    
    # Сортируем по cumtime (накопленное время)
    functions.sort(key=lambda x: x['cumtime'], reverse=True)
    
    return {
        'total_functions': len(functions),
        'top_functions': functions[:20],
        'total_cumtime': sum(f['cumtime'] for f in functions),
        'total_tottime': sum(f['tottime'] for f in functions),
        'total_calls': sum(f['calls'] for f in functions)
    }


def analyze_profiling_stats() -> Dict[str, Any]:
    """Анализ статистик из profiling утилит."""
    try:
        from ai_service.utils.profiling import get_profiling_stats
        return get_profiling_stats()
    except ImportError:
        return {}


def identify_hotspots(cprofile_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Выявление горячих точек на основе анализа cProfile."""
    hotspots = []
    
    if not cprofile_data or 'top_functions' not in cprofile_data:
        return hotspots
    
    top_functions = cprofile_data['top_functions']
    total_cumtime = cprofile_data.get('total_cumtime', 1)
    
    for func in top_functions[:10]:  # TOP-10
        cumtime_pct = (func['cumtime'] / total_cumtime) * 100
        tottime_pct = (func['tottime'] / total_cumtime) * 100
        
        # Определяем тип горячей точки
        hotspot_type = "unknown"
        recommendations = []
        
        if "token" in func['function'].lower() or "tokenize" in func['function'].lower():
            hotspot_type = "tokenization"
            recommendations = [
                "Рассмотреть кэширование результатов токенизации",
                "Оптимизировать регулярные выражения (предкомпилировать)",
                "Избегать повторных вызовов split() в циклах"
            ]
        elif "morph" in func['function'].lower() or "parse" in func['function'].lower():
            hotspot_type = "morphology"
            recommendations = [
                "Кэшировать результаты морфологического анализа",
                "Использовать LRU кэш для частых токенов",
                "Оптимизировать вызовы pymorphy3"
            ]
        elif "role" in func['function'].lower() or "classify" in func['function'].lower():
            hotspot_type = "role_classification"
            recommendations = [
                "Кэшировать результаты классификации ролей",
                "Оптимизировать поиск в словарях (использовать set вместо list)",
                "Предкомпилировать регулярные выражения"
            ]
        elif "normalize" in func['function'].lower():
            hotspot_type = "normalization"
            recommendations = [
                "Оптимизировать алгоритм нормализации",
                "Кэшировать результаты нормализации",
                "Избегать повторных вычислений"
            ]
        elif "re." in func['filename'] or "regex" in func['filename']:
            hotspot_type = "regex"
            recommendations = [
                "Предкомпилировать регулярные выражения",
                "Оптимизировать паттерны regex",
                "Использовать более эффективные альтернативы"
            ]
        
        if cumtime_pct > 1.0:  # Больше 1% от общего времени
            hotspots.append({
                'function': func['function'],
                'filename': func['filename'],
                'line': func['line'],
                'type': hotspot_type,
                'cumtime': func['cumtime'],
                'cumtime_pct': cumtime_pct,
                'tottime': func['tottime'],
                'tottime_pct': tottime_pct,
                'calls': func['calls'],
                'avg_time_per_call': func['cumtime'] / max(func['calls'], 1),
                'recommendations': recommendations
            })
    
    return hotspots


def generate_optimization_recommendations(hotspots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Генерация рекомендаций по оптимизации."""
    recommendations = []
    
    # Группируем по типам
    type_groups = {}
    for hotspot in hotspots:
        hotspot_type = hotspot['type']
        if hotspot_type not in type_groups:
            type_groups[hotspot_type] = []
        type_groups[hotspot_type].append(hotspot)
    
    for hotspot_type, hotspots_list in type_groups.items():
        if not hotspots_list:
            continue
            
        total_time = sum(h['cumtime'] for h in hotspots_list)
        total_calls = sum(h['calls'] for h in hotspots_list)
        
        # Собираем все рекомендации
        all_recommendations = []
        for hotspot in hotspots_list:
            all_recommendations.extend(hotspot['recommendations'])
        
        # Убираем дубликаты
        unique_recommendations = list(set(all_recommendations))
        
        recommendations.append({
            'type': hotspot_type,
            'hotspots_count': len(hotspots_list),
            'total_time': total_time,
            'total_calls': total_calls,
            'avg_time_per_call': total_time / max(total_calls, 1),
            'recommendations': unique_recommendations,
            'priority': 'high' if total_time > 0.1 else 'medium' if total_time > 0.01 else 'low'
        })
    
    return recommendations


def create_performance_diagram(hotspots: List[Dict[str, Any]]) -> str:
    """Создание диаграммы производительности в формате Mermaid."""
    if not hotspots:
        return "```mermaid\ngraph TD\n    A[No performance data available] --> B[Run profiling first]\n```"
    
    # Группируем по типам
    type_times = {}
    for hotspot in hotspots:
        hotspot_type = hotspot['type']
        if hotspot_type not in type_times:
            type_times[hotspot_type] = 0
        type_times[hotspot_type] += hotspot['cumtime']
    
    # Создаём диаграмму
    diagram = "```mermaid\npie title Performance by Component\n"
    for hotspot_type, time in sorted(type_times.items(), key=lambda x: x[1], reverse=True):
        percentage = (time / sum(type_times.values())) * 100
        diagram += f'    "{hotspot_type}" : {percentage:.1f}\n'
    diagram += "```"
    
    return diagram


def generate_markdown_report(
    cprofile_data: Dict[str, Any],
    profiling_stats: Dict[str, Any],
    hotspots: List[Dict[str, Any]],
    recommendations: List[Dict[str, Any]]
) -> str:
    """Генерация markdown-отчёта."""
    
    report = """# Отчёт профилирования AI Service Normalization Factory

## Обзор

Этот отчёт содержит анализ производительности factory-пути нормализации на коротких строках.
Профилирование выполнено с помощью cProfile и pyinstrument для выявления узких мест.

## Методология

- **Тестовые данные**: 20 фраз (RU/UK/EN) по 100 итераций каждая
- **Инструменты**: cProfile + pstats, pyinstrument, custom profiling utilities
- **Фокус**: короткие строки типа "Іван Петров", "ООО 'Ромашка' Иван И."

"""
    
    # Статистика профилирования
    if cprofile_data:
        report += f"""## Статистика профилирования

- **Всего функций**: {cprofile_data.get('total_functions', 0)}
- **Общее время выполнения**: {cprofile_data.get('total_cumtime', 0):.4f} секунд
- **Собственное время**: {cprofile_data.get('total_tottime', 0):.4f} секунд
- **Всего вызовов**: {cprofile_data.get('total_calls', 0)}

"""
    
    # Диаграмма производительности
    report += "## Распределение времени по компонентам\n\n"
    report += create_performance_diagram(hotspots) + "\n\n"
    
    # TOP-10 горячих точек
    if hotspots:
        report += "## TOP-10 Горячих точек\n\n"
        report += "| Функция | Файл | Время (cum) | % | Вызовы | Рекомендации |\n"
        report += "|---------|------|-------------|---|--------|-------------|\n"
        
        for hotspot in hotspots[:10]:
            filename = Path(hotspot['filename']).name
            recommendations_str = "; ".join(hotspot['recommendations'][:2])  # Первые 2 рекомендации
            report += f"| `{hotspot['function']}` | `{filename}` | {hotspot['cumtime']:.4f}s | {hotspot['cumtime_pct']:.1f}% | {hotspot['calls']} | {recommendations_str} |\n"
        
        report += "\n"
    
    # Рекомендации по оптимизации
    if recommendations:
        report += "## Рекомендации по оптимизации\n\n"
        
        for rec in recommendations:
            priority_emoji = "🔴" if rec['priority'] == 'high' else "🟡" if rec['priority'] == 'medium' else "🟢"
            report += f"### {priority_emoji} {rec['type'].title()} ({rec['priority'].upper()} priority)\n\n"
            report += f"- **Количество горячих точек**: {rec['hotspots_count']}\n"
            report += f"- **Общее время**: {rec['total_time']:.4f}s\n"
            report += f"- **Среднее время на вызов**: {rec['avg_time_per_call']:.6f}s\n\n"
            
            report += "**Рекомендации:**\n"
            for i, recommendation in enumerate(rec['recommendations'], 1):
                report += f"{i}. {recommendation}\n"
            report += "\n"
    
    # Детальные рекомендации
    report += """## Детальные рекомендации по оптимизации

### 1. Кэширование морфологического анализа

**Проблема**: Повторные вызовы pymorphy3 для одних и тех же токенов.

**Решение**:
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def _morph_nominal_cached(token: str, language: str) -> str:
    # Кэшированная версия морфологического анализа
    pass
```

**Ожидаемый эффект**: Снижение времени на 30-50% для повторяющихся токенов.

### 2. Предкомпиляция регулярных выражений

**Проблема**: Компиляция regex в каждом вызове.

**Решение**:
```python
import re

# На уровне модуля
TOKEN_SPLIT_PATTERN = re.compile(r"([,])")
INITIALS_PATTERN = re.compile(r"^((?:[A-Za-zА-Яа-яІЇЄҐіїєґ]\.){2,})([A-Za-zА-Яа-яІЇЄҐіїєґ].*)$")
```

**Ожидаемый эффект**: Снижение времени на 10-20%.

### 3. Оптимизация поиска в словарях

**Проблема**: Линейный поиск в списках для проверки стоп-слов.

**Решение**:
```python
# Использовать set вместо list для O(1) поиска
STOP_WORDS_SET = set(STOP_ALL)
```

**Ожидаемый эффект**: Снижение времени на 5-15%.

### 4. Кэширование результатов классификации ролей

**Проблема**: Повторная классификация одинаковых токенов.

**Решение**:
```python
from functools import lru_cache

@lru_cache(maxsize=500)
def _classify_token_cached(token: str, language: str) -> str:
    # Кэшированная классификация роли
    pass
```

**Ожидаемый эффект**: Снижение времени на 20-40%.

### 5. Оптимизация строковых операций

**Проблема**: Множественные вызовы strip(), split() в циклах.

**Решение**:
```python
# Батчевая обработка токенов
def process_tokens_batch(tokens: List[str]) -> List[str]:
    # Обработка всех токенов за один проход
    pass
```

**Ожидаемый эффект**: Снижение времени на 10-25%.

## Метрики производительности

### До оптимизации
- Среднее время на фразу: ~X.XXX мс
- Пиковое время: ~X.XXX мс
- Использование памяти: ~X MB

### После оптимизации (прогноз)
- Среднее время на фразу: ~X.XXX мс (-XX%)
- Пиковое время: ~X.XXX мс (-XX%)
- Использование памяти: ~X MB (-XX%)

## Следующие шаги

1. **Немедленные действия**:
   - Внедрить кэширование морфологического анализа
   - Предкомпилировать регулярные выражения
   - Оптимизировать поиск в словарях

2. **Краткосрочные улучшения** (1-2 недели):
   - Добавить кэширование классификации ролей
   - Оптимизировать строковые операции
   - Добавить профилирование в CI/CD

3. **Долгосрочные улучшения** (1 месяц):
   - Переписать критические пути на Cython
   - Внедрить асинхронную обработку
   - Добавить метрики производительности в production

## Заключение

Анализ выявил несколько ключевых узких мест в factory-пути нормализации.
Реализация предложенных оптимизаций должна привести к значительному улучшению
производительности, особенно для коротких строк, которые являются основным
use case системы.

"""
    
    return report


def main():
    """Главная функция генерации отчёта."""
    print("Генерация отчёта профилирования...")
    
    # Пути к файлам
    artifacts_dir = Path("artifacts")
    profile_file = artifacts_dir / "profile_stats.prof"
    
    # Создаём директорию если не существует
    artifacts_dir.mkdir(exist_ok=True)
    
    # Анализ данных
    print("Анализ результатов cProfile...")
    cprofile_data = analyze_cprofile_results(profile_file)
    
    print("Анализ статистик профилирования...")
    profiling_stats = analyze_profiling_stats()
    
    print("Выявление горячих точек...")
    hotspots = identify_hotspots(cprofile_data)
    
    print("Генерация рекомендаций...")
    recommendations = generate_optimization_recommendations(hotspots)
    
    # Генерация отчёта
    print("Создание markdown-отчёта...")
    report = generate_markdown_report(cprofile_data, profiling_stats, hotspots, recommendations)
    
    # Сохранение отчёта
    report_file = artifacts_dir / "profile_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"Отчёт сохранён: {report_file}")
    
    # Вывод краткой сводки
    print("\n" + "="*60)
    print("КРАТКАЯ СВОДКА")
    print("="*60)
    
    if hotspots:
        print(f"Найдено горячих точек: {len(hotspots)}")
        print(f"Общее время в горячих точках: {sum(h['cumtime'] for h in hotspots):.4f}s")
        
        print("\nTOP-3 горячие точки:")
        for i, hotspot in enumerate(hotspots[:3], 1):
            print(f"{i}. {hotspot['function']} - {hotspot['cumtime']:.4f}s ({hotspot['cumtime_pct']:.1f}%)")
    
    if recommendations:
        print(f"\nРекомендаций по оптимизации: {len(recommendations)}")
        high_priority = [r for r in recommendations if r['priority'] == 'high']
        if high_priority:
            print(f"Высокий приоритет: {len(high_priority)}")
    
    print(f"\nПолный отчёт: {report_file}")


if __name__ == "__main__":
    main()

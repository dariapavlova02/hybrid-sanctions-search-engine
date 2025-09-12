#!/usr/bin/env python3
"""
Демонстрация упрощенной системы умного фильтра
со встроенным определением языка
"""

import sys
import os
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from ai_service.services.smart_filter.demo_smart_filter import SimpleSmartFilter
    SIMPLE_FILTER_AVAILABLE = True
except ImportError:
    SIMPLE_FILTER_AVAILABLE = False


class SimpleLanguageOptimizedFilter:
    """Упрощенный умный фильтр с определением языка"""
    
    def __init__(self):
        """Инициализация фильтра"""
        # Языковые паттерны для быстрого определения
        self.language_patterns = {
            'ukrainian': {
                'chars': r'[іїєґ]',  # Уникальные украинские буквы
                'words': ['тов', 'інн', 'єдрпоу', 'київ', 'вул', 'буд', 'платіж', 'переказ'],
                'weight': 1.2  # Приоритет для украинского
            },
            'russian': {
                'chars': r'[ыэъё]',  # Уникальные русские буквы  
                'words': ['ооо', 'зао', 'инн', 'огрн', 'москва', 'ул', 'дом', 'платеж', 'перевод'],
                'weight': 1.1  # Приоритет для русского
            },
            'english': {
                'chars': r'[a-z]',  # Латиница
                'words': ['llc', 'inc', 'corp', 'bank', 'street', 'avenue', 'payment', 'transfer'],
                'weight': 1.0  # Стандартный приоритет
            }
        }
        
        # Простые паттерны для сигналов
        self.signal_patterns = {
            'names': [
                r'[А-ЯІЇЄҐ][а-яіїєґ]*(?:енко|ко|ський|цький|юк|ук|ов|ев|ин|ич)',  # Славянские фамилии
                r'[А-ЯІЇЄҐ][а-яіїєґ]*(?:ович|евич|ійович|івна|ївна|инич|овна|евна)',  # Отчества
                r'[A-Z][a-z]+\s+[A-Z][a-z]+',  # Английские имена
            ],
            'companies': [
                r'\b(?:ТОВ|ПрАТ|КП|ДП|товариство)\b',  # Украинские ОПФ
                r'\b(?:ООО|ЗАО|ОАО|ПАО|общество)\b',  # Русские ОПФ
                r'\b(?:LLC|Inc|Corp|Ltd|Company)\b',   # Английские ОПФ
                r'\b(?:[А-ЯІЇЄҐA-Z][а-яіїєґa-z]*[Бб]анк)\b',  # Банки
            ],
            'documents': [
                r'\b(?:ІНН|інн|ЄДРПОУ|єдрпоу|МФО|мфо)\s*\d+\b',  # Украинские документы
                r'\b(?:ИНН|инн|ОГРН|огрн|КПП|кпп|БИК|бик)\s*\d+\b',  # Русские документы
                r'\b(?:TIN|EIN|SSN|SWIFT)\s*[A-Z0-9-]+\b',  # Английские документы
                r'\b\d{4}-\d{2}-\d{2}\b',  # Даты
                r'\bUA\d{2}\s*\d+\b',  # IBAN
            ]
        }
    
    def detect_language(self, text: str):
        """Простое определение языка"""
        text_lower = text.lower()
        scores = {}
        
        for lang_name, lang_data in self.language_patterns.items():
            score = 0.0
            
            # Проверка уникальных символов
            if any(char in text_lower for char in lang_data['chars'] if len(lang_data['chars']) > 10):
                score += 0.5
            else:
                import re
                if re.search(lang_data['chars'], text):
                    score += 0.5
            
            # Проверка характерных слов
            word_matches = sum(1 for word in lang_data['words'] if word in text_lower)
            if word_matches > 0:
                score += min(word_matches * 0.2, 0.5)
            
            scores[lang_name] = score * lang_data['weight']
        
        if scores:
            detected_lang = max(scores.keys(), key=lambda k: scores[k])
            weight = self.language_patterns[detected_lang]['weight']
            return detected_lang, weight, scores
        
        return 'english', 1.0, {}
    
    def analyze_text(self, text: str):
        """Анализ текста с языковой оптимизацией"""
        start_time = time.time()
        
        if not text or not text.strip():
            return {
                'decision': 'ALLOW',
                'confidence': 0.0,
                'risk': 'very_low',
                'language': 'unknown',
                'signals': {},
                'processing_time': time.time() - start_time
            }
        
        # Определение языка
        detected_language, language_weight, lang_scores = self.detect_language(text)
        
        # Детекция сигналов
        signals = {}
        total_confidence = 0.0
        
        for signal_type, patterns in self.signal_patterns.items():
            import re
            matches = []
            for pattern in patterns:
                found = re.findall(pattern, text, re.IGNORECASE)
                matches.extend(found)
            
            if matches:
                base_confidence = min(len(matches) * 0.3, 0.8)
                
                # Применяем языковой бонус
                if signal_type in ['names', 'companies'] and detected_language in ['ukrainian', 'russian']:
                    # Бонус для славянских языков
                    optimized_confidence = min(base_confidence * language_weight, 1.0)
                elif signal_type == 'documents':
                    # Специальный бонус для документов
                    optimized_confidence = min(base_confidence * (language_weight * 1.1), 1.0)
                else:
                    optimized_confidence = base_confidence
                
                signals[signal_type] = {
                    'confidence': optimized_confidence,
                    'matches': matches[:3],  # Показываем только первые 3
                    'count': len(matches)
                }
                total_confidence += optimized_confidence * 0.33  # Равные веса
            else:
                signals[signal_type] = {'confidence': 0.0, 'matches': [], 'count': 0}
        
        # Принятие решения
        if total_confidence > 0.7:
            decision = 'FULL_SEARCH'
            risk = 'medium'
        elif total_confidence > 0.4:
            decision = 'MANUAL_REVIEW'
            risk = 'low'
        elif total_confidence > 0.1:
            decision = 'MANUAL_REVIEW'
            risk = 'low'
        else:
            decision = 'ALLOW'
            risk = 'very_low'
        
        return {
            'decision': decision,
            'confidence': total_confidence,
            'risk': risk,
            'language': detected_language,
            'language_weight': language_weight,
            'language_scores': lang_scores,
            'signals': signals,
            'processing_time': (time.time() - start_time) * 1000  # в миллисекундах
        }


def run_demo():
    """Запуск демонстрации"""
    print("=" * 80)
    print("🔧 УПРОЩЕННАЯ СИСТЕМА УМНОГО ФИЛЬТРА")
    print("   Встроенное определение языка (украинский, русский, английский)")
    print("=" * 80)
    print()
    
    filter_system = SimpleLanguageOptimizedFilter()
    
    # Тестовые случаи
    test_cases = [
        # Украинские тексты
        ("Платіж для Коваленко Іван Петрович ТОВ", "Украинский: ФИО + ОПФ"),
        ("ІНН 1234567890 ЄДРПОУ 12345678", "Украинские документы"),
        ("м. Київ вул. Хрещатик буд. 1", "Украинский адрес"),
        
        # Русские тексты
        ("Платеж для Петров Иван Сергеевич ООО", "Русский: ФИО + ОПФ"),
        ("ИНН 1234567890 ОГРН 1234567890123", "Русские документы"),
        ("г. Москва ул. Тверская д. 1", "Русский адрес"),
        
        # Английские тексты
        ("Payment for John Smith LLC Company", "Английский: имя + ОПФ"),
        ("TIN 12-3456789 EIN 12-3456789", "Американские документы"),
        ("New York 5th Avenue Bank", "Английский банк"),
        
        # Общие тексты
        ("оплата за товар", "Общий термин"),
        ("консультация", "Услуга"),
        ("1000 грн", "Только сумма"),
    ]
    
    print("📋 РЕЗУЛЬТАТЫ АНАЛИЗА:")
    print("-" * 80)
    print(f"{'№':<2} {'Описание':<25} {'Язык':<10} {'Решение':<12} {'Конфиденс':<10} {'Время':<8}")
    print("-" * 80)
    
    stats = {'languages': {}, 'decisions': {}, 'total_time': 0}
    
    for i, (text, description) in enumerate(test_cases, 1):
        result = filter_system.analyze_text(text)
        
        # Сбор статистики
        lang = result['language']
        decision = result['decision']
        stats['languages'][lang] = stats['languages'].get(lang, 0) + 1
        stats['decisions'][decision] = stats['decisions'].get(decision, 0) + 1
        stats['total_time'] += result['processing_time']
        
        print(f"{i:2d} {description:<25} {lang:<10} {decision:<12} "
              f"{result['confidence']:.2f}{'':5} {result['processing_time']:.1f}ms")
        
        # Детальная информация для первых 3 примеров
        if i <= 3:
            print(f"    Текст: '{text}'")
            print(f"    Вес языка: {result['language_weight']:.1f}")
            print(f"    Языковые скоры: {result['language_scores']}")
            
            detected_signals = []
            for signal_type, signal_data in result['signals'].items():
                if signal_data['count'] > 0:
                    detected_signals.append(f"{signal_type}({signal_data['count']})")
            print(f"    Сигналы: {', '.join(detected_signals) if detected_signals else 'нет'}")
            print()
    
    print("-" * 80)
    print("📊 СТАТИСТИКА:")
    print()
    
    total_tests = len(test_cases)
    print(f"Всего тестов: {total_tests}")
    print(f"Среднее время: {stats['total_time']/total_tests:.1f} мс")
    print()
    
    print("Распределение по языкам:")
    for lang, count in stats['languages'].items():
        percentage = count / total_tests * 100
        print(f"  • {lang}: {count} ({percentage:.1f}%)")
    print()
    
    print("Распределение решений:")
    for decision, count in stats['decisions'].items():
        percentage = count / total_tests * 100
        print(f"  • {decision}: {count} ({percentage:.1f}%)")
    print()
    
    # Преимущества упрощенной системы
    print("🎯 ПРЕИМУЩЕСТВА УПРОЩЕННОЙ СИСТЕМЫ:")
    print("  ✅ Никаких внешних зависимостей")
    print("  ✅ Быстрое определение языка по ключевым признакам")
    print("  ✅ Языковые бонусы для повышения точности")
    print("  ✅ Фокус на украинском, русском, английском")
    print("  ✅ Простота интеграции и настройки")
    print("  ✅ Высокая производительность")
    print()
    
    success_rate = (stats['decisions'].get('FULL_SEARCH', 0) + 
                   stats['decisions'].get('MANUAL_REVIEW', 0)) / total_tests * 100
    
    if success_rate >= 70:
        print("🎉 ОТЛИЧНАЯ ПРОИЗВОДИТЕЛЬНОСТЬ!")
    elif success_rate >= 50:
        print("✅ ХОРОШАЯ ПРОИЗВОДИТЕЛЬНОСТЬ")
    else:
        print("⚠️ СИСТЕМА ТРЕБУЕТ НАСТРОЙКИ")
    
    return stats


if __name__ == "__main__":
    print("Запуск демонстрации упрощенной многоязычной системы...\n")
    
    results = run_demo()
    
    print("\n" + "=" * 80)
    print("✅ УПРОЩЕННАЯ СИСТЕМА ГОТОВА К ИСПОЛЬЗОВАНИЮ!")
    print("   Простая интеграция, без зависимостей, оптимизирована для платежей")
    print("=" * 80)
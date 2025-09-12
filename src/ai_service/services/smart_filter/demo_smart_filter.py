"""
Демонстрация работы улучшенной системы умного фильтра

Показывает как работает новая система принятия решений
с детекторами всех типов сигналов.
"""

import re
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


# Упрощенные версии основных компонентов для демонстрации
class DecisionType(Enum):
    """Типы решений"""
    ALLOW = "allow"
    BLOCK = "block" 
    FULL_SEARCH = "full_search"
    MANUAL_REVIEW = "manual_review"
    PRIORITY_REVIEW = "priority_review"


class RiskLevel(Enum):
    """Уровни риска"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DecisionResult:
    """Результат принятия решения"""
    decision: DecisionType
    confidence: float
    risk_level: RiskLevel
    reasoning: str
    detected_signals: Dict[str, Any]
    processing_time: float


class SimpleSmartFilter:
    """Упрощенная версия умного фильтра для демонстрации"""
    
    def __init__(self):
        """Инициализация фильтра"""
        # Паттерны для имен (согласно вашим требованиям)
        self.name_patterns = [
            r'\b[А-ЯІЇЄҐ][а-яіїєґ]*(?:енко|ко)\b',  # -енко, -ко
            r'\b[А-ЯІЇЄҐ][а-яіїєґ]*(?:ов|ев|ін|ин)\b',  # -ов, -ев, -ін, -ин
            r'\b[А-ЯІЇЄҐ][а-яіїєґ]*(?:ович|евич|ійович|івна|ївна)\b',  # отчества
            r'\b[А-ЯІЇЄҐ][а-яіїєґ]+\s+[А-ЯІЇЄҐ][а-яіїєґ]*(?:ович|евич|івна|ївна)\s+[А-ЯІЇЄҐ][а-яіїєґ]*(?:енко|ов|ев)\b',  # полные имена
        ]
        
        # Паттерны для организаций
        self.company_patterns = [
            r'\b(?:ООО|ЗАО|LLC|товариство)\b',
            r'\b(?:банк|bank|банківський)\b',
            r'\b(?:компанія|компания|company|corp|корп)\b',
            r'\b(?:альфа|приват|сбербанк|goldman|jpmorgan)\b',
        ]
        
        # Паттерны для документов
        self.document_patterns = [
            r'\b(?:ІНН|інн|инн)\s*\d{8,12}\b',
            r'\b[А-ЯІЇЄҐA-Z]{2}\d{6}\b',  # паспорт
            r'\b\d{4}-\d{2}-\d{2}\b',     # дата
            r'\bUA\d{2}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\b',  # IBAN
        ]
        
        # Индикаторы терроризма (для демонстрации защитной системы)
        self.terrorism_patterns = [
            r'\b(?:operational|operations|mission)\s+(?:funding|support)\b',
            r'\b(?:brothers|comrades)\s+(?:in|from)\b',
            r'\b(?:equipment|training|preparation)\s+(?:acquisition|materials)\b',
        ]
        
    def analyze_text(self, text: str) -> DecisionResult:
        """Анализ текста и принятие решения"""
        start_time = time.time()
        
        if not text or not text.strip():
            return DecisionResult(
                decision=DecisionType.ALLOW,
                confidence=0.0,
                risk_level=RiskLevel.VERY_LOW,
                reasoning="Пустой текст",
                detected_signals={},
                processing_time=time.time() - start_time
            )
        
        # Анализ различных типов сигналов
        signals = {
            'names': self._detect_names(text),
            'companies': self._detect_companies(text), 
            'documents': self._detect_documents(text),
            'terrorism': self._detect_terrorism(text)
        }
        
        # Принятие решения
        decision, confidence, risk_level, reasoning = self._make_decision(signals, text)
        
        return DecisionResult(
            decision=decision,
            confidence=confidence,
            risk_level=risk_level,
            reasoning=reasoning,
            detected_signals=signals,
            processing_time=time.time() - start_time
        )
    
    def _detect_names(self, text: str) -> Dict[str, Any]:
        """Детекция имен"""
        matches = []
        for pattern in self.name_patterns:
            matches.extend(re.findall(pattern, text, re.IGNORECASE))
        
        confidence = min(len(matches) * 0.6, 0.9) if matches else 0.0
        return {
            'confidence': confidence,
            'matches': list(set(matches)),
            'count': len(matches)
        }
    
    def _detect_companies(self, text: str) -> Dict[str, Any]:
        """Детекция компаний"""
        matches = []
        for pattern in self.company_patterns:
            matches.extend(re.findall(pattern, text, re.IGNORECASE))
        
        confidence = min(len(matches) * 0.5, 0.8) if matches else 0.0
        return {
            'confidence': confidence,
            'matches': list(set(matches)),
            'count': len(matches)
        }
    
    def _detect_documents(self, text: str) -> Dict[str, Any]:
        """Детекция документов"""
        matches = []
        for pattern in self.document_patterns:
            matches.extend(re.findall(pattern, text, re.IGNORECASE))
        
        confidence = min(len(matches) * 0.7, 0.9) if matches else 0.0
        return {
            'confidence': confidence,
            'matches': list(set(matches)),
            'count': len(matches)
        }
    
    def _detect_terrorism(self, text: str) -> Dict[str, Any]:
        """Детекция индикаторов терроризма"""
        matches = []
        for pattern in self.terrorism_patterns:
            matches.extend(re.findall(pattern, text, re.IGNORECASE))
        
        confidence = min(len(matches) * 0.8, 1.0) if matches else 0.0
        return {
            'confidence': confidence,
            'matches': list(set(matches)),
            'count': len(matches),
            'risk_level': 'high' if confidence > 0.5 else 'low'
        }
    
    def _make_decision(self, signals: Dict[str, Any], text: str) -> Tuple[DecisionType, float, RiskLevel, str]:
        """Принятие решения на основе сигналов"""
        # Проверка на терроризм (высший приоритет)
        terrorism_confidence = signals['terrorism']['confidence']
        if terrorism_confidence > 0.7:
            return (
                DecisionType.BLOCK,
                terrorism_confidence,
                RiskLevel.CRITICAL,
                f"БЛОКИРОВКА: Обнаружены критические индикаторы терроризма (confidence: {terrorism_confidence:.2f})"
            )
        elif terrorism_confidence > 0.4:
            return (
                DecisionType.PRIORITY_REVIEW,
                terrorism_confidence,
                RiskLevel.HIGH,
                f"СРОЧНАЯ ПРОВЕРКА: Подозрительные индикаторы терроризма (confidence: {terrorism_confidence:.2f})"
            )
        
        # Расчет общей уверенности для остальных сигналов
        name_conf = signals['names']['confidence']
        company_conf = signals['companies']['confidence'] 
        document_conf = signals['documents']['confidence']
        
        # Взвешенная уверенность
        total_confidence = (name_conf * 0.4 + company_conf * 0.4 + document_conf * 0.2)
        
        # Принятие решения
        if total_confidence > 0.6:
            return (
                DecisionType.FULL_SEARCH,
                total_confidence,
                RiskLevel.MEDIUM,
                f"Высокая уверенность в наличии релевантных сигналов - запуск полного поиска (confidence: {total_confidence:.2f})"
            )
        elif total_confidence > 0.3:
            return (
                DecisionType.FULL_SEARCH,
                total_confidence,
                RiskLevel.LOW,
                f"Средняя уверенность в наличии релевантных сигналов - запуск полного поиска (confidence: {total_confidence:.2f})"
            )
        elif total_confidence > 0.1:
            return (
                DecisionType.MANUAL_REVIEW,
                total_confidence,
                RiskLevel.LOW,
                f"Низкая уверенность - отправка на ручную проверку (confidence: {total_confidence:.2f})"
            )
        else:
            return (
                DecisionType.ALLOW,
                total_confidence,
                RiskLevel.VERY_LOW,
                f"Очень низкая уверенность - разрешение без проверки (confidence: {total_confidence:.2f})"
            )


def run_demo():
    """Запуск демонстрации системы"""
    print("=== ДЕМОНСТРАЦИЯ УЛУЧШЕННОЙ СИСТЕМЫ УМНОГО ФИЛЬТРА ===\n")
    
    filter_system = SimpleSmartFilter()
    
    # Тестовые случаи
    test_cases = [
        # Имена людей
        ("Оплата для Коваленко Иван Петрович", "Имя человека с отчеством"),
        ("Платеж от Сидоренко", "Фамилия на -енко"),
        ("John Smith payment", "Английское имя"),
        
        # Компании
        ("ООО 'Рога и Копыта' услуги", "Российская компания"),
        ("ПриватБанк перевод средств", "Украинский банк"),
        ("Goldman Sachs investment", "Американский банк"),
        
        # Документы
        ("ІНН 1234567890 оплата товаров", "Документ с ИНН"),
        ("Паспорт АВ123456", "Серия и номер паспорта"), 
        ("Договор от 2024-01-15", "Документ с датой"),
        
        # Безопасный контент
        ("Оплата за товар", "Общий термин"),
        ("1000 грн", "Только сумма"),
        ("консультация", "Услуга"),
        
        # Подозрительный контент (для демонстрации защитных функций)
        ("operational funding for mission support", "Подозрительные термины"),
        ("equipment acquisition for training", "Потенциально опасный контент"),
    ]
    
    print("Анализ тестовых случаев:\n")
    
    for i, (text, description) in enumerate(test_cases, 1):
        print(f"{i:2d}. {description}")
        print(f"    Текст: '{text}'")
        
        result = filter_system.analyze_text(text)
        
        print(f"    Решение: {result.decision.value.upper()}")
        print(f"    Уверенность: {result.confidence:.2f}")
        print(f"    Риск: {result.risk_level.value}")
        print(f"    Обоснование: {result.reasoning}")
        
        # Детали обнаруженных сигналов
        signal_details = []
        for signal_type, signal_data in result.detected_signals.items():
            if signal_data.get('count', 0) > 0:
                matches = signal_data.get('matches', [])
                signal_details.append(f"{signal_type}: {matches}")
        
        if signal_details:
            print(f"    Обнаружено: {'; '.join(signal_details)}")
        
        print(f"    Время обработки: {result.processing_time*1000:.1f} мс")
        print()
    
    print("=== СТАТИСТИКА ДЕМОНСТРАЦИИ ===")
    
    # Статистика решений
    decisions = {}
    risk_levels = {}
    total_time = 0
    
    for text, _ in test_cases:
        result = filter_system.analyze_text(text)
        decisions[result.decision.value] = decisions.get(result.decision.value, 0) + 1
        risk_levels[result.risk_level.value] = risk_levels.get(result.risk_level.value, 0) + 1
        total_time += result.processing_time
    
    print(f"\nРаспределение решений:")
    for decision, count in decisions.items():
        percentage = count / len(test_cases) * 100
        print(f"  {decision}: {count} ({percentage:.1f}%)")
    
    print(f"\nРаспределение уровней риска:")
    for risk_level, count in risk_levels.items():
        percentage = count / len(test_cases) * 100
        print(f"  {risk_level}: {count} ({percentage:.1f}%)")
    
    print(f"\nСреднее время обработки: {total_time/len(test_cases)*1000:.1f} мс")
    
    print("\n✅ Демонстрация завершена успешно!")


if __name__ == "__main__":
    run_demo()
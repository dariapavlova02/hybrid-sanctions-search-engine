"""
Service for processing signals and text analysis
"""

import re
import logging
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from dataclasses import dataclass

from ..utils import get_logger


@dataclass
class SignalResult:
    """Signal analysis result"""
    signal_type: str
    confidence: float
    matches: List[str]
    count: int
    metadata: Dict[str, Any] = None


class SignalService:
    """Service for analyzing signals in text"""
    
    def __init__(self):
        """Initialize signal service"""
        self.logger = get_logger(__name__)
        
        # Patterns for detecting different types of signals
        self.signal_patterns = {
            'names': {
                'weight': 0.8,
                'patterns': [
                    r'\b[A-ZА-ЯІЇЄҐ][a-zа-яіїєґ]+\s+[A-ZА-ЯІЇЄҐ][a-zа-яіїєґ]+\s+[A-ZА-ЯІЇЄҐ][a-zа-яіїєґ]+\b',  # Full name
                    r'\b[A-ZА-ЯІЇЄҐ][a-zа-яіїєґ]+\s+[A-ZА-ЯІЇЄҐ][a-zа-яіїєґ]+\b',  # First name + Last name
                    r'\b[A-ZА-ЯІЇЄҐ][a-zа-яіїєґ]+\b',  # Single name
                    r'\b[A-Z]\.\s*[A-Z]\.\s*[A-Z][a-z]+\b',  # Initials + Last name
                    r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # English names
                    r'\b[A-Z][a-z]+\b'  # Single English name
                ]
            },
            'dates': {
                'weight': 0.6,
                'patterns': [
                    r'\b\d{1,2}\s+(січня|лютого|березня|квітня|травня|червня|липня|серпня|вересня|жовтня|листопада|грудня)\s+\d{4}\b',
                    r'\b\d{1,2}\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4}\b',
                    r'\b\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b',
                    r'\b\d{1,2}\.\d{1,2}\.\d{4}\b',  # DD.MM.YYYY
                    r'\b\d{4}-\d{1,2}-\d{1,2}\b'  # YYYY-MM-DD
                ]
            },
            'locations': {
                'weight': 0.7,
                'patterns': [
                    r'\b(Київ|Львів|Харків|Одеса|Дніпро|Запоріжжя|Кривий Ріг|Миколаїв|Маріуполь|Херсон|Полтава|Черкаси|Суми|Хмельницький|Вінниця|Житомир|Чернівці|Рівне|Тернопіль|Івано-Франківськ|Луцьк|Ужгород|Чернігів|Кропивницький)\b',
                    r'\b(Москва|Санкт-Петербург|Новосибирск|Екатеринбург|Казань|Нижний Новгород|Челябинск|Самара|Ростов-на-Дону|Уфа|Омск|Красноярск|Воронеж|Пермь|Волгоград)\b',
                    r'\b(New York|London|Paris|Berlin|Tokyo|Moscow|Kiev|Warsaw|Prague|Vienna|Budapest|Bucharest|Sofia|Belgrade|Zagreb|Ljubljana)\b'
                ]
            },
            'organizations': {
                'weight': 0.9,
                'patterns': [
                    r'\b(ТОВ|ПАТ|АТ|КП|ДП|ФОП|ІП)\b',  # Ukrainian ownership forms
                    r'\b(ООО|АО|ПАО|ЗАО|ОАО|ИП)\b',  # Russian ownership forms
                    r'\b(LLC|Inc|Corp|Ltd|PLC|AG|GmbH|SA|NV|BV)\b',  # Western ownership forms
                    r'\b(Company|Corporation|Enterprise|Organization|Foundation|Institute|University|College|School)\b'
                ]
            },
            'financial': {
                'weight': 0.8,
                'patterns': [
                    r'\b\d+\.?\d*\s*(USD|EUR|UAH|RUB|GBP|JPY|CHF|CAD|AUD)\b',  # Currency amounts
                    r'\b\d+\.?\d*\s*(долар|евро|гривня|рубль|фунт|йена|франк|долар|австралійський)\b',
                    r'\b\d+\.?\d*\s*(доллар|евро|гривна|рубль|фунт|йена|франк|доллар|австралийский)\b'
                ]
            }
        }
        
        self.logger.info("SignalService initialized")
    
    def analyze_signals(self, text: str) -> Dict[str, Any]:
        """
        Analyze text for presence of signals
        
        Args:
            text: Input text
            
        Returns:
            Dict with signal analysis results
        """
        if not text or not text.strip():
            return self._create_empty_result()
        
        results = {}
        total_confidence = 0.0
        total_signals = 0
        
        # Analyze each signal type
        for signal_type, config in self.signal_patterns.items():
            signal_result = self._analyze_signal_type(text, signal_type, config)
            results[signal_type] = signal_result
            
            if signal_result['confidence'] > 0:
                total_confidence += signal_result['confidence']
                total_signals += signal_result['count']
        
        # Calculate overall confidence
        overall_confidence = total_confidence / len(self.signal_patterns) if self.signal_patterns else 0.0
        
        # Create summary
        summary = {
            'total_signals': total_signals,
            'overall_confidence': overall_confidence,
            'signal_types_detected': [k for k, v in results.items() if v['confidence'] > 0],
            'high_confidence_signals': [k for k, v in results.items() if v['confidence'] > 0.7],
            'timestamp': datetime.now().isoformat()
        }
        
        return {
            'summary': summary,
            'signals': results,
            'text_length': len(text),
            'analysis_complete': True
        }
    
    def _analyze_signal_type(self, text: str, signal_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze specific signal type"""
        matches = []
        total_matches = 0
        
        for pattern in config['patterns']:
            try:
                found_matches = re.findall(pattern, text, re.IGNORECASE)
                if found_matches:
                    matches.extend(found_matches)
                    total_matches += len(found_matches)
            except re.error as e:
                self.logger.warning(f"Invalid regex pattern for {signal_type}: {e}")
                continue
        
        # Calculate confidence based on matches
        if total_matches > 0:
            confidence = config['weight'] * min(len(matches) / 10.0, 1.0)  # Normalize
        else:
            confidence = 0.0
        
        return {
            'signal_type': signal_type,
            'confidence': confidence,
            'matches': list(set(matches)),  # Remove duplicates
            'count': total_matches,
            'weight': config['weight'],
            'patterns_used': len(config['patterns'])
        }
    
    def get_name_signals(self, text: str) -> Dict[str, Any]:
        """
        Get signals related to names
        
        Args:
            text: Input text
            
        Returns:
            Dict with name signals
        """
        if 'names' not in self.signal_patterns:
            return {'confidence': 0.0, 'matches': [], 'count': 0}
        
        name_config = self.signal_patterns['names']
        return self._analyze_signal_type(text, 'names', name_config)
    
    def get_signal_summary(self, text: str) -> Dict[str, Any]:
        """
        Get overall signal summary
        
        Args:
            text: Input text
            
        Returns:
            Dict with signal summary
        """
        analysis = self.analyze_signals(text)
        
        # Group signals by type
        signal_groups = {}
        for signal_type, result in analysis['signals'].items():
            if result['confidence'] > 0:
                signal_groups[signal_type] = {
                    'confidence': result['confidence'],
                    'count': result['count'],
                    'examples': result['matches'][:3]  # First 3 examples
                }
        
        return {
            'total_signals': analysis['summary']['total_signals'],
            'overall_confidence': analysis['summary']['overall_confidence'],
            'signal_groups': signal_groups,
            'high_priority_signals': [k for k, v in signal_groups.items() if v['confidence'] > 0.8]
        }
    
    def _create_empty_result(self) -> Dict[str, Any]:
        """Create empty result"""
        return {
            'summary': {
                'total_signals': 0,
                'overall_confidence': 0.0,
                'signal_types_detected': [],
                'high_confidence_signals': [],
                'timestamp': datetime.now().isoformat()
            },
            'signals': {},
            'text_length': 0,
            'analysis_complete': False
        }

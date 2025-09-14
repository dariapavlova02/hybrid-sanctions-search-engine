"""
Smart Filter Module

Умный предварительный фильтр для определения потенциальных имен и названий компаний
в тексте назначения платежа. Позволяет избежать избыточного поиска по Ахо-Корасик
для текстов, которые не содержат релевантных сигналов.
"""

from .company_detector import CompanyDetector
from .confidence_scorer import ConfidenceScorer
from .name_detector import NameDetector
from .smart_filter_service import SmartFilterService

__all__ = ["SmartFilterService", "CompanyDetector", "NameDetector", "ConfidenceScorer"]

"""
Smart Filter Service

Intelligent pre-filtering service for Aho-Corasick search decisions.
"""

# Standard library imports
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Local imports
from ...config import SERVICE_CONFIG
from ...data.dicts.smart_filter_patterns import (
    CONFIDENCE_THRESHOLDS,
    DATE_TIME_PATTERNS,
    EXCLUSION_PATTERNS,
    SERVICE_WORDS,
)
from ...exceptions import LanguageDetectionError, SmartFilterError
from ...utils.logging_config import get_logger
from ..signals.signals_service import SignalsService

# from ..aho_corasick_service import AhoCorasickService  # Removed - templates only
from .company_detector import CompanyDetector
from .confidence_scorer import ConfidenceScorer
from .decision_logic import DecisionLogic, DecisionType, RiskLevel
from .document_detector import DocumentDetector
from .name_detector import NameDetector
from .terrorism_detector import TerrorismDetector


@dataclass
class FilterResult:
    """Result of smart filter operation"""

    should_process: bool
    confidence: float
    detected_signals: List[str]
    signal_details: Dict[str, Any]
    processing_recommendation: str
    estimated_complexity: str


class SmartFilterService:
    """Smart pre-filter for determining text relevance"""

    def __init__(
        self,
        language_service: Optional[Any] = None,
        signal_service: Optional[Any] = None,
        enable_terrorism_detection: bool = True,
        enable_aho_corasick: bool = False,  # Disabled - templates only
    ):
        """
        Initialize smart filter service

        Args:
            language_service: Language detection service instance
            signal_service: Signal detection service instance
            enable_terrorism_detection: Enable terrorism detection
            enable_aho_corasick: Enable Aho-Corasick pattern matching

        Raises:
            SmartFilterError: If service initialization fails
        """
        self.logger = get_logger(__name__)

        try:
            # Use existing services
            self.language_service = language_service
            self.signal_service = signal_service

            # Initialize base signal service
            self.signal_service = signal_service or SignalsService()

            # Aho-Corasick functionality disabled - only templates are generated
            self.aho_corasick_enabled = False
            self.aho_corasick_service = None

            # Initialize main decision module
            self.decision_logic = DecisionLogic(
                enable_terrorism_detection=enable_terrorism_detection
            )

            # Initialize detectors
            self.company_detector = CompanyDetector()
            self.name_detector = NameDetector()
            self.document_detector = DocumentDetector()
            if enable_terrorism_detection:
                self.terrorism_detector = TerrorismDetector()
            else:
                self.terrorism_detector = None
            self.confidence_scorer = ConfidenceScorer()

            # Decision thresholds (from dictionary)
            self.thresholds = CONFIDENCE_THRESHOLDS.copy()

            # Quick exclusion patterns
            self.exclusion_patterns = EXCLUSION_PATTERNS.copy()

            # Service word dictionaries for cleaning
            self.service_words = SERVICE_WORDS.copy()

            # Date and time patterns
            self.date_time_patterns = DATE_TIME_PATTERNS.copy()

            self.logger.info(
                f"SmartFilterService initialized (terrorism detection: {enable_terrorism_detection})"
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize SmartFilterService: {e}")
            raise SmartFilterError(f"Service initialization failed: {str(e)}")

    def should_process_text(self, text: str) -> FilterResult:
        """
        Determines whether to process text with full search

        Args:
            text: Text to analyze

        Returns:
            FilterResult with recommendation

        Raises:
            SmartFilterError: If text processing fails
        """
        if not text or not text.strip():
            return self._create_empty_result()

        try:
            # Keep original text for context analysis
            original_text = text.strip()
            
            # Light normalization for exclusion checks only
            normalized_text = self._normalize_text(original_text)

            # Quick exclusion check
            if self._is_excluded_text(normalized_text):
                return FilterResult(
                    should_process=False,
                    confidence=0.0,
                    detected_signals=[],
                    signal_details={},
                    processing_recommendation="Text excluded from processing (service information only)",
                    estimated_complexity="very_low",
                )

            # Date and time check
            if self._is_date_only_text(normalized_text):
                return FilterResult(
                    should_process=False,
                    confidence=0.0,
                    detected_signals=[],
                    signal_details={},
                    processing_recommendation="Text excluded from processing (date/time only)",
                    estimated_complexity="very_low",
                )

            # Context analysis with payment triggers
            context_signals = self._analyze_payment_context(original_text)

            # Signal analysis with original text (preserving context)
            company_signals = self.company_detector.detect_company_signals(
                original_text
            )
            name_signals = self.name_detector.detect_name_signals(original_text)

            # Combine results
            all_signals = {
                "companies": company_signals, 
                "names": name_signals,
                "context": context_signals
            }

            # Calculate total confidence
            total_confidence = self.confidence_scorer.calculate_confidence(all_signals)

            # Determine recommendation
            should_process, recommendation, complexity = self._make_processing_decision(
                total_confidence, all_signals, original_text
            )

            # Form list of detected signals
            detected_signals = []
            if company_signals["confidence"] > 0:
                detected_signals.append("company")
            if name_signals["confidence"] > 0:
                detected_signals.append("name")
            if context_signals["confidence"] > 0:
                detected_signals.append("payment_context")

            return FilterResult(
                should_process=should_process,
                confidence=total_confidence,
                detected_signals=detected_signals,
                signal_details=all_signals,
                processing_recommendation=recommendation,
                estimated_complexity=complexity,
            )
        except Exception as e:
            self.logger.error(f"Error in should_process_text: {e}")
            raise SmartFilterError(f"Text processing failed: {str(e)}")

    def analyze_payment_description(self, text: str) -> Dict[str, Any]:
        """
        Analyzes payment description and returns detailed information

        Args:
            text: Payment description text

        Returns:
            Detailed text analysis

        Raises:
            SmartFilterError: If analysis fails
        """
        try:
            result = self.should_process_text(text)

            # Additional statistics
            word_count = len(text.split())
            char_count = len(text)

            # Language composition analysis
            language_analysis = self._analyze_language_composition(text)

            return {
                "filter_result": result,
                "text_statistics": {
                    "word_count": word_count,
                    "char_count": char_count,
                    "average_word_length": (
                        char_count / word_count if word_count > 0 else 0
                    ),
                },
                "language_analysis": language_analysis,
                "processing_time": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Error in analyze_payment_description: {e}")
            raise SmartFilterError(f"Payment description analysis failed: {str(e)}")

    def search_aho_corasick(
        self, text: str, max_matches: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Perform Aho-Corasick pattern matching on text

        Args:
            text: Text to search in
            max_matches: Maximum number of matches to return

        Returns:
            Aho-Corasick search results

        Raises:
            SmartFilterError: If search fails
        """
        # Aho-Corasick functionality disabled - only templates are generated
        return {
            "matches": [],
            "total_matches": 0,
            "processing_time_ms": 0.0,
            "patterns_loaded": 0,
            "text_length": len(text),
            "enabled": False,
            "message": "Aho-Corasick search disabled - only pattern templates are generated",
        }

    def _analyze_payment_context(self, text: str) -> Dict[str, Any]:
        """
        Analyze payment context using payment triggers as signals
        
        Args:
            text: Original text to analyze
            
        Returns:
            Context analysis results
        """
        try:
            # Import payment triggers
            from ...data.dicts.payment_triggers import PAYMENT_TRIGGERS
            
            # Detect language
            detected_language = self._detect_language(text)
            
            # Get payment triggers for the language
            triggers = PAYMENT_TRIGGERS.get(detected_language, {})
            context_words = triggers.get("context", [])
            prep_words = triggers.get("preps", [])
            currency_words = triggers.get("currencies", [])
            
            # Find context signals
            context_matches = []
            prep_matches = []
            currency_matches = []
            
            text_lower = text.lower()
            
            # Check for context words
            for word in context_words:
                if word.lower() in text_lower:
                    context_matches.append(word)
            
            # Check for prepositional phrases that indicate names
            for prep in prep_words:
                if prep.lower() in text_lower:
                    prep_matches.append(prep)
            
            # Check for currency indicators
            for currency in currency_words:
                if currency.lower() in text_lower:
                    currency_matches.append(currency)
            
            # Calculate confidence based on matches
            total_matches = len(context_matches) + len(prep_matches) + len(currency_matches)
            confidence = min(total_matches * 0.2, 1.0)  # Max confidence of 1.0
            
            return {
                "confidence": confidence,
                "context_words": context_matches,
                "prepositional_phrases": prep_matches,
                "currencies": currency_matches,
                "total_matches": total_matches,
                "language": detected_language,
                "has_payment_context": len(context_matches) > 0,
                "has_name_indicators": len(prep_matches) > 0,
                "has_currency_indicators": len(currency_matches) > 0,
            }
            
        except Exception as e:
            self.logger.warning(f"Error analyzing payment context: {e}")
            return {
                "confidence": 0.0,
                "context_words": [],
                "prepositional_phrases": [],
                "currencies": [],
                "total_matches": 0,
                "language": "unknown",
                "has_payment_context": False,
                "has_name_indicators": False,
                "has_currency_indicators": False,
            }

    def _clean_service_words(self, text: str) -> str:
        """
        DEPRECATED: Pre-cleanup of service words
        This method is now deprecated as we preserve context for better name detection
        """
        # This method is kept for backward compatibility but should not be used
        # in the new context-aware approach
        self.logger.warning("_clean_service_words is deprecated - use context-aware analysis instead")
        return text

    def _detect_language(self, text: str) -> str:
        """Detect text language"""
        if self.language_service:
            try:
                result = self.language_service.detect_language(text)
                return result.get("language", "ukrainian")
            except Exception as e:
                self.logger.warning(f"Language detection error: {e}")

        # Fallback - simple character-based detection
        cyrillic_count = len(re.findall(r"[а-яёіїєґ]", text, re.IGNORECASE))
        latin_count = len(re.findall(r"[a-z]", text, re.IGNORECASE))

        if cyrillic_count > latin_count:
            return "ukrainian"  # Default Ukrainian for Cyrillic
        elif latin_count > 0:
            return "english"
        else:
            return "ukrainian"

    def _normalize_text(self, text: str) -> str:
        """Normalize text for analysis"""
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text.strip())

        # Convert to lowercase for some checks
        # (but preserve original for name analysis)
        return text

    def make_smart_decision(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make smart decision using all detectors

        Args:
            text: Text to analyze
            context: Additional context

        Returns:
            Decision result

        Raises:
            SmartFilterError: If decision making fails
        """
        try:
            decision_result = self.decision_logic.make_decision(text, context)

            # Convert result for API compatibility
            return {
                "should_process": decision_result.decision
                in [DecisionType.FULL_SEARCH, DecisionType.MANUAL_REVIEW],
                "decision_type": decision_result.decision.value,
                "confidence": decision_result.confidence,
                "risk_level": decision_result.risk_level.value,
                "reasoning": decision_result.reasoning,
                "recommendations": decision_result.recommendations,
                "requires_escalation": decision_result.requires_escalation,
                "processing_time": decision_result.processing_time,
                "detected_signals": decision_result.detected_signals,
                "metadata": decision_result.metadata,
                "blocked": decision_result.decision == DecisionType.BLOCK,
            }
        except Exception as e:
            self.logger.error(f"Error in make_smart_decision: {e}")
            raise SmartFilterError(f"Smart decision making failed: {str(e)}")

    def get_comprehensive_analysis(self, text: str) -> Dict[str, Any]:
        """
        Получение комплексного анализа текста со всеми детекторами

        Args:
            text: Текст для анализа

        Returns:
            Комплексный анализ с детальной информацией
        """
        # Basic analysis through old system
        legacy_result = self.should_process_text(text)

        # New analysis through decision system
        decision_analysis = self.decision_logic.get_detailed_analysis(text)

        # Additional detailed analyses
        name_analysis = (
            self.name_detector.get_detailed_name_analysis(text)
            if hasattr(self.name_detector, "get_detailed_name_analysis")
            else {}
        )
        company_analysis = (
            self.company_detector.get_enhanced_company_analysis(text)
            if hasattr(self.company_detector, "get_enhanced_company_analysis")
            else {}
        )

        # Terrorism analysis (if enabled)
        terrorism_analysis = {}
        if self.terrorism_detector:
            terrorism_signals = self.terrorism_detector.detect_terrorism_signals(text)
            terrorism_analysis = self.terrorism_detector.get_risk_assessment(
                terrorism_signals
            )

        return {
            "input_text": text,
            "legacy_analysis": {
                "should_process": legacy_result.should_process,
                "confidence": legacy_result.confidence,
                "detected_signals": legacy_result.detected_signals,
                "processing_recommendation": legacy_result.processing_recommendation,
                "estimated_complexity": legacy_result.estimated_complexity,
            },
            "decision_analysis": decision_analysis,
            "detailed_breakdowns": {
                "names": name_analysis,
                "companies": company_analysis,
                "terrorism": terrorism_analysis,
            },
            "summary": {
                "final_decision": decision_analysis["decision_result"]["decision"],
                "final_confidence": decision_analysis["decision_result"]["confidence"],
                "risk_level": decision_analysis["decision_result"]["risk_level"],
                "requires_action": decision_analysis["decision_result"][
                    "requires_escalation"
                ],
                "processing_recommendation": decision_analysis["decision_result"][
                    "reasoning"
                ],
            },
        }

    def _is_excluded_text(self, text: str) -> bool:
        """Проверка на исключение из обработки"""
        text_lower = text.lower().strip()

        for pattern in self.exclusion_patterns:
            if re.match(pattern, text_lower, re.IGNORECASE):
                return True

        return False

    def _is_date_only_text(self, text: str) -> bool:
        """Проверка, содержит ли текст только даты и время"""
        text_stripped = text.strip()

        # Check all date and time patterns
        all_date_patterns = []
        for pattern_group in self.date_time_patterns.values():
            all_date_patterns.extend(pattern_group)

        # Check if text consists only of dates/time
        for pattern in all_date_patterns:
            if re.fullmatch(pattern, text_stripped, re.IGNORECASE):
                return True

        # Additional check for relative dates
        relative_dates = [
            "сьогодні",
            "вчора",
            "позавчора",
            "завтра",
            "післязавтра",
            "сегодня",
            "вчера",
            "позавчера",
            "завтра",
            "послезавтра",
            "today",
            "yesterday",
            "tomorrow",
        ]

        if text_stripped.lower() in relative_dates:
            return True

        return False

    def _make_processing_decision(
        self, confidence: float, signals: Dict[str, Any], text: str
    ) -> Tuple[bool, str, str]:
        """Принятие решения о необходимости обработки"""

        if confidence >= self.thresholds["high"]:
            return True, "Высокая уверенность в наличии релевантных сигналов", "high"

        elif confidence >= self.thresholds["medium"]:
            return True, "Средняя уверенность в наличии релевантных сигналов", "medium"

        elif confidence >= self.thresholds["min_processing_threshold"]:
            return True, "Низкая уверенность, но есть потенциальные сигналы", "low"

        else:
            return False, "Недостаточно сигналов для обработки", "very_low"

    def _analyze_language_composition(self, text: str) -> Dict[str, Any]:
        """Анализ языкового состава текста"""
        # Count Cyrillic characters
        cyrillic_count = len(re.findall(r"[а-яёіїєґ]", text, re.IGNORECASE))

        # Count Latin characters
        latin_count = len(re.findall(r"[a-z]", text, re.IGNORECASE))

        # Count digits
        digit_count = len(re.findall(r"\d", text))

        # Count special characters
        special_count = len(re.findall(r"[^\w\s]", text))

        total_chars = len(text)

        return {
            "cyrillic_ratio": cyrillic_count / total_chars if total_chars > 0 else 0,
            "latin_ratio": latin_count / total_chars if total_chars > 0 else 0,
            "digit_ratio": digit_count / total_chars if total_chars > 0 else 0,
            "special_ratio": special_count / total_chars if total_chars > 0 else 0,
            "is_mixed_language": cyrillic_count > 0 and latin_count > 0,
        }

    def _create_empty_result(self) -> FilterResult:
        """Create empty result"""
        return FilterResult(
            should_process=False,
            confidence=0.0,
            detected_signals=[],
            signal_details={},
            processing_recommendation="Empty text",
            estimated_complexity="none",
        )

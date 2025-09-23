"""
Smart Filter Service

Intelligent pre-filtering service for Aho-Corasick search decisions.
"""

# Standard library imports
import asyncio
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
from ..patterns.unified_pattern_service import UnifiedPatternService
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
        enable_aho_corasick: Optional[bool] = None,  # Use config if None
        pattern_service: Optional[UnifiedPatternService] = None,
    ):
        """
        Initialize smart filter service

        Args:
            language_service: Language detection service instance
            signal_service: Signal detection service instance
            enable_terrorism_detection: Enable terrorism detection
            enable_aho_corasick: Enable Aho-Corasick pattern matching (None = use config)
            pattern_service: Unified pattern service for AC integration

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

            # Initialize pattern service for AC integration
            # Use config value if enable_aho_corasick is None
            if enable_aho_corasick is None:
                self.aho_corasick_enabled = SERVICE_CONFIG.enable_aho_corasick
            else:
                self.aho_corasick_enabled = enable_aho_corasick
            self.pattern_service = pattern_service or UnifiedPatternService()

            # Initialize main decision module
            self.decision_logic = DecisionLogic(
                enable_terrorism_detection=enable_terrorism_detection
            )

            # Initialize detectors
            self.company_detector = CompanyDetector()
            self.name_detector = NameDetector(smart_filter_service=self)
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
                    processing_recommendation="Текст исключен из обработки (служебная информация)",
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

            # Tier-0: Aho-Corasick search (if enabled)
            ac_matches = []
            ac_confidence_bonus = 0.0
            if self.aho_corasick_enabled:
                # Search original text
                ac_result = self.search_aho_corasick(original_text)
                ac_matches = ac_result.get("matches", [])

                # If no matches, try normalized name order variants
                if not ac_matches:
                    # Try to normalize names and check reversed order
                    text_variants = self._generate_name_variants(original_text)
                    for variant in text_variants:
                        variant_result = self.search_aho_corasick(variant)
                        variant_matches = variant_result.get("matches", [])
                        if variant_matches:
                            ac_matches.extend(variant_matches)
                            break  # Found matches, stop trying variants

                if ac_matches:
                    ac_confidence_bonus = SERVICE_CONFIG.aho_corasick_confidence_bonus

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
                "context": context_signals,
                "aho_corasick_matches": {
                    "matches": ac_matches,
                    "total_matches": len(ac_matches),
                    "confidence_bonus": ac_confidence_bonus,
                    "enabled": self.aho_corasick_enabled,
                },
            }

            # Calculate total confidence
            total_confidence = self.confidence_scorer.calculate_confidence(all_signals)
            
            # Apply AC confidence bonus if matches found
            if ac_confidence_bonus > 0:
                total_confidence = min(total_confidence + ac_confidence_bonus, 1.0)
            
            # Apply mixed language bonus if detected
            language_analysis = self._analyze_language_composition(original_text)
            if language_analysis.get("is_mixed_language", False):
                # Add script information to signals for mixed language detection
                # Extract matches from company signals structure
                company_matches = []
                if "signals" in company_signals:
                    for signal in company_signals["signals"]:
                        if "matches" in signal:
                            company_matches.extend(signal["matches"])
                
                company_signals["script"] = self._detect_script(company_matches)
                name_signals["script"] = self._detect_script(name_signals.get("names", []))
                
                # Check if we have valid name signals on both scripts
                has_cyrillic_names = any(
                    signal.get("confidence", 0) > 0 
                    for signal in [company_signals, name_signals] 
                    if signal.get("script", "") == "cyrillic"
                )
                has_latin_names = any(
                    signal.get("confidence", 0) > 0 
                    for signal in [company_signals, name_signals] 
                    if signal.get("script", "") == "latin"
                )
                has_mixed_names = any(
                    signal.get("confidence", 0) > 0 
                    for signal in [company_signals, name_signals] 
                    if signal.get("script", "") == "mixed"
                )
                
                # Apply bonus if we have signals on different scripts
                if (has_cyrillic_names and has_latin_names) or (has_cyrillic_names and has_mixed_names) or (has_latin_names and has_mixed_names):
                    # Bonus for having valid name signals on both scripts
                    mixed_bonus = 0.25  # Increased bonus for mixed language
                    total_confidence = min(total_confidence + mixed_bonus, 1.0)
                    all_signals["mixed_language_bonus"] = {
                        "applied": True,
                        "bonus": mixed_bonus,
                        "reason": "Valid name signals detected on both scripts"
                    }

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
            if ac_matches:
                detected_signals.append("ac_match")

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
        Perform real AC pattern matching using Elasticsearch AC patterns

        Args:
            text: Text to search in
            max_matches: Maximum number of matches to return

        Returns:
            Real AC pattern search results

        Raises:
            SmartFilterError: If search fails
        """
        if not self.aho_corasick_enabled:
            return {
                "matches": [],
                "total_matches": 0,
                "processing_time_ms": 0.0,
                "patterns_loaded": 0,
                "text_length": len(text),
                "enabled": False,
                "message": "AC integration disabled",
            }

        try:
            import time
            import requests
            from requests.auth import HTTPBasicAuth
            start_time = time.time()

            # ES connection details
            ES_HOST = "95.217.84.234"
            ES_PORT = 9200
            ES_USER = "elastic"
            ES_PASSWORD = "AiServiceElastic2024!"
            ES_INDEX = "ai_service_ac_patterns"

            # Normalize text for search (same as AC patterns)
            from ..unicode.unicode_service import UnicodeService
            unicode_service = UnicodeService()
            normalized_result = unicode_service.normalize_text(text, normalize_homoglyphs=True)
            normalized_text = normalized_result["normalized"]

            # Search for AC patterns that match this text
            search_url = f"http://{ES_HOST}:{ES_PORT}/{ES_INDEX}/_search"
            auth = HTTPBasicAuth(ES_USER, ES_PASSWORD)

            # Create search query to find patterns that match our text
            search_query = {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "wildcard": {
                                    "pattern": {
                                        "value": f"*{normalized_text.lower()}*",
                                        "case_insensitive": True
                                    }
                                }
                            },
                            {
                                "match": {
                                    "pattern": {
                                        "query": normalized_text,
                                        "fuzziness": "AUTO"
                                    }
                                }
                            }
                        ],
                        "minimum_should_match": 1
                    }
                },
                "size": max_matches or 50,
                "sort": [
                    {"tier": {"order": "asc"}},  # Lower tier = higher priority
                    {"confidence": {"order": "desc"}},
                    {"_score": {"order": "desc"}}
                ]
            }

            response = requests.post(search_url, json=search_query, auth=auth, timeout=5)

            matches = []
            patterns_loaded = 0

            if response.status_code == 200:
                result = response.json()
                hits = result.get("hits", {}).get("hits", [])
                patterns_loaded = result.get("hits", {}).get("total", {}).get("value", 0)

                for hit in hits:
                    source = hit["_source"]
                    pattern = source.get("pattern", "")

                    # Check if this pattern actually matches our normalized text
                    if pattern.lower() in normalized_text.lower() or normalized_text.lower() in pattern.lower():
                        matches.append({
                            "pattern": pattern,
                            "tier": f"tier_{source.get('tier', 3)}",
                            "start": normalized_text.lower().find(pattern.lower()),
                            "end": normalized_text.lower().find(pattern.lower()) + len(pattern),
                            "matched_text": pattern,
                            "confidence": source.get("confidence", 0.5),
                            "pattern_type": source.get("type", "unknown"),
                            "entity_type": source.get("entity_type", "unknown"),
                            "entity_id": source.get("entity_id", ""),
                            "es_score": hit.get("_score", 0)
                        })

            processing_time_ms = (time.time() - start_time) * 1000

            return {
                "matches": matches,
                "total_matches": len(matches),
                "processing_time_ms": processing_time_ms,
                "patterns_loaded": patterns_loaded,
                "text_length": len(text),
                "enabled": True,
                "normalized_text": normalized_text,
                "message": f"Real AC search completed with {len(matches)} matches from {patterns_loaded} total patterns",
            }

        except Exception as e:
            self.logger.error(f"Error in real AC search: {e}")
            # Fallback to empty result instead of failing
            return {
                "matches": [],
                "total_matches": 0,
                "processing_time_ms": 0.0,
                "patterns_loaded": 0,
                "text_length": len(text),
                "enabled": True,
                "error": str(e),
                "message": f"AC search failed: {str(e)}",
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
            total_matches = (
                len(context_matches) + len(prep_matches) + len(currency_matches)
            )
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
        self.logger.warning(
            "_clean_service_words is deprecated - use context-aware analysis instead"
        )
        
        # For backward compatibility, perform basic service words removal
        cleaned_text = text
        
        # Remove common service words from the beginning
        service_prefixes = [
            "оплата за", "платеж за", "платіж за", "перевод на", "счет за",
            "payment for", "transfer to", "invoice for"
        ]
        
        text_lower = text.lower().strip()
        for prefix in service_prefixes:
            if text_lower.startswith(prefix.lower()):
                # Remove the prefix and clean up spaces
                cleaned_text = text[len(prefix):].strip()
                break
        
        return cleaned_text

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

    def _detect_script(self, items: List[str]) -> str:
        """
        Detect the primary script (cyrillic, latin, or mixed) from a list of text items.
        
        Args:
            items: List of text items to analyze
            
        Returns:
            Script type: 'cyrillic', 'latin', or 'mixed'
        """
        if not items:
            return "unknown"
        
        cyrillic_count = 0
        latin_count = 0
        
        for item in items:
            if not item:
                continue
            # Count Cyrillic characters
            cyr_chars = len(re.findall(r"[а-яёіїєґ]", item, re.IGNORECASE))
            # Count Latin characters  
            lat_chars = len(re.findall(r"[a-z]", item, re.IGNORECASE))
            
            if cyr_chars > lat_chars:
                cyrillic_count += 1
            elif lat_chars > cyr_chars:
                latin_count += 1
            else:
                # Equal counts or both present - count as mixed
                if cyr_chars > 0 and lat_chars > 0:
                    cyrillic_count += 0.5
                    latin_count += 0.5
                elif cyr_chars > 0:
                    cyrillic_count += 1
                elif lat_chars > 0:
                    latin_count += 1
        
        if cyrillic_count > latin_count:
            return "cyrillic"
        elif latin_count > cyrillic_count:
            return "latin"
        else:
            return "mixed"

    def _generate_name_variants(self, text: str) -> List[str]:
        """
        Generate name order variants for better AC pattern matching

        For input "Петро Порошенко" generates:
        - "Порошенко Петро"
        - "петро порошенко"
        - "порошенко петро"
        """
        variants = []

        # Normalize whitespace and split
        words = text.strip().split()

        if len(words) == 2:
            # Two words - likely first name + surname
            first, second = words

            # Reversed order
            reversed_order = f"{second} {first}"
            variants.append(reversed_order)

            # Lowercase versions
            variants.append(text.lower())
            variants.append(reversed_order.lower())

        elif len(words) == 3:
            # Three words - try different combinations
            first, middle, third = words

            # Surname first variations
            variants.extend([
                f"{third} {first} {middle}",
                f"{third} {first}",
                f"{third} {middle}",
            ])

            # Lowercase versions
            variants.append(text.lower())
            for variant in variants[:]:
                variants.append(variant.lower())

        # Remove duplicates and empty strings
        unique_variants = []
        for variant in variants:
            if variant and variant.strip() and variant not in unique_variants and variant != text:
                unique_variants.append(variant.strip())

        return unique_variants

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

    def _get_pattern_confidence(self, pattern: str, tier: str) -> float:
        """Get confidence score for a pattern based on tier"""
        tier_confidence_map = {
            "tier_0_exact": 0.98,
            "tier_1_high_confidence": 0.90,
            "tier_2_medium_confidence": 0.75,
            "tier_3_low_confidence": 0.60,
        }
        return tier_confidence_map.get(tier, 0.50)

    def _get_tier_priority(self, tier: str) -> int:
        """Get priority weight for tier sorting"""
        tier_priority_map = {
            "tier_0_exact": 4,
            "tier_1_high_confidence": 3,
            "tier_2_medium_confidence": 2,
            "tier_3_low_confidence": 1,
        }
        return tier_priority_map.get(tier, 0)

    def _infer_pattern_type(self, pattern: str, all_patterns) -> str:
        """Infer pattern type from the pattern string and full pattern list"""
        # Find matching pattern in the full list to get its type
        for p in all_patterns:
            if p.pattern == pattern:
                return p.pattern_type

        # Fallback inference based on pattern characteristics
        if any(char.isdigit() for char in pattern) and len(pattern) >= 6:
            return "document_id"
        elif "." in pattern and len(pattern.split()) <= 3:
            return "structured_name"
        elif len(pattern.split()) >= 2:
            return "full_name"
        else:
            return "basic_pattern"

    def enhanced_pattern_analysis(self, text: str) -> Dict[str, Any]:
        """
        Perform enhanced pattern analysis combining smart filtering with AC patterns

        Args:
            text: Text to analyze

        Returns:
            Enhanced analysis results
        """
        try:
            # Get basic smart filter result
            filter_result = self.should_process_text(text)

            # Get AC pattern matches if enabled
            ac_result = self.search_aho_corasick(text, max_matches=50)

            # Generate comprehensive patterns
            language = self._detect_language(text)
            patterns = self.pattern_service.generate_patterns(text, language=language)
            pattern_stats = self.pattern_service.get_pattern_statistics(patterns)

            # Combine results for enhanced analysis
            enhanced_confidence = filter_result.confidence
            if ac_result["total_matches"] > 0:
                # Boost confidence based on AC matches
                match_boost = min(ac_result["total_matches"] * 0.1, 0.3)
                enhanced_confidence = min(enhanced_confidence + match_boost, 1.0)

            return {
                "text": text,
                "language": language,
                "smart_filter_result": {
                    "should_process": filter_result.should_process,
                    "confidence": filter_result.confidence,
                    "detected_signals": filter_result.detected_signals,
                    "processing_recommendation": filter_result.processing_recommendation,
                },
                "ac_pattern_result": ac_result,
                "pattern_analysis": {
                    "total_patterns_generated": len(patterns),
                    "pattern_statistics": pattern_stats,
                    "high_confidence_patterns": len([p for p in patterns if p.confidence >= 0.9]),
                },
                "enhanced_analysis": {
                    "final_confidence": enhanced_confidence,
                    "should_process": enhanced_confidence >= 0.3,
                    "processing_priority": "high" if enhanced_confidence >= 0.8 else
                                          "medium" if enhanced_confidence >= 0.5 else "low",
                    "match_quality": "excellent" if ac_result["total_matches"] >= 3 else
                                   "good" if ac_result["total_matches"] >= 1 else "basic",
                },
                "recommendations": self._generate_processing_recommendations(
                    enhanced_confidence, ac_result["total_matches"], filter_result.detected_signals
                ),
            }

        except Exception as e:
            self.logger.error(f"Error in enhanced pattern analysis: {e}")
            raise SmartFilterError(f"Enhanced analysis failed: {str(e)}")

    def _generate_processing_recommendations(
        self, confidence: float, ac_matches: int, detected_signals: List[str]
    ) -> List[str]:
        """Generate processing recommendations based on analysis results"""
        recommendations = []

        if confidence >= 0.9:
            recommendations.append("High priority - immediate processing recommended")
        elif confidence >= 0.7:
            recommendations.append("Medium priority - process within standard timeframe")
        elif confidence >= 0.3:
            recommendations.append("Low priority - consider batch processing")
        else:
            recommendations.append("Very low priority - may skip processing")

        if ac_matches >= 5:
            recommendations.append("Multiple pattern matches - potential high-value content")
        elif ac_matches >= 2:
            recommendations.append("Some pattern matches - moderate relevance detected")
        elif ac_matches == 1:
            recommendations.append("Single pattern match - basic relevance detected")

        if "company" in detected_signals and "name" in detected_signals:
            recommendations.append("Both company and name signals detected - likely business transaction")
        elif "payment_context" in detected_signals:
            recommendations.append("Payment context detected - financial transaction likely")

        return recommendations

    # ==================== ASYNC METHODS ====================

    async def should_process_text_async(self, text: str) -> FilterResult:
        """
        Async version of should_process_text using thread pool executor
        
        Args:
            text: Text to analyze

        Returns:
            FilterResult with recommendation
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,  # Use default thread pool executor
            self.should_process_text,
            text
        )


# Legacy compatibility for tests expecting SignalService in this module
try:
    from ..signals.signals_service import SignalsService as _SignalServiceAlias
    SignalService = _SignalServiceAlias  # legacy re-export for tests
except Exception:
    class SignalService:  # minimal stub for patching in tests
        """Minimal stub for SignalService when signals module is not available"""
        def __init__(self, *args, **kwargs):
            pass

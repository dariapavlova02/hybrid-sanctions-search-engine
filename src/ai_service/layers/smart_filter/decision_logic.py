"""
Decision Logic Module

Combines signal detector results and makes decisions about Aho-Corasick search.
"""

# Standard library imports
import json
import logging
import re
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Local imports
from ...utils.logging_config import get_logger
from .company_detector import CompanyDetector
from .confidence_scorer import ConfidenceScorer
from .document_detector import DocumentDetector
from .name_detector import NameDetector
from .terrorism_detector import TerrorismDetector


class DecisionType(Enum):
    """Decision types"""

    ALLOW = "allow"
    BLOCK = "block"
    FULL_SEARCH = "full_search"
    MANUAL_REVIEW = "manual_review"
    PRIORITY_REVIEW = "priority_review"


class RiskLevel(Enum):
    """Risk levels"""

    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DecisionResult:
    """Decision result"""

    decision: DecisionType
    confidence: float
    risk_level: RiskLevel
    reasoning: str
    detected_signals: Dict[str, Any]
    recommendations: List[str]
    processing_time: float
    requires_escalation: bool
    metadata: Dict[str, Any]


class DecisionLogic:
    """Analyzes signals and makes processing decisions"""

    def __init__(self, enable_terrorism_detection: bool = True):
        """Initialize decision module"""
        self.logger = get_logger(__name__)

        # Initialize detectors
        self.name_detector = NameDetector()
        self.company_detector = CompanyDetector()
        self.document_detector = DocumentDetector()
        self.terrorism_detector = (
            TerrorismDetector() if enable_terrorism_detection else None
        )
        self.confidence_scorer = ConfidenceScorer()

        # Simple language patterns for optimization (Ukrainian, Russian, English)
        self.language_patterns = {
            "ukrainian": {
                "chars": r"[іїєґІЇЄҐ]",  # Unique Ukrainian letters
                "words": ["тов", "інн", "єдрпоу", "київ", "вул", "буд"],
                "weight": 1.2,  # Priority for Ukrainian
            },
            "russian": {
                "chars": r"[ыэъёЫЭЪЁ]",  # Unique Russian letters
                "words": ["ооо", "зао", "инн", "огрн", "москва", "ул", "дом"],
                "weight": 1.1,  # Priority for Russian
            },
            "english": {
                "chars": r"[a-zA-Z]",  # Latin script
                "words": ["llc", "inc", "corp", "bank", "street", "avenue"],
                "weight": 1.0,  # Standard priority
            },
        }

        # Decision thresholds
        self.decision_thresholds = {
            "terrorism_block": 0.8,  # Block on terrorism suspicion
            "terrorism_review": 0.5,  # Send for review
            "full_search_high": 0.4,  # Run full search (high confidence) - further reduced
            "full_search_medium": 0.15,  # Run full search (medium confidence) - further reduced
            "manual_review": 0.05,  # Send for manual review - further reduced
            "allow_threshold": 0.005,  # Allow without verification (very low confidence) - maximally reduced
        }

        # Weights for different signal types in decision making
        self.signal_weights = {
            "terrorism": 1.0,  # Maximum priority
            "documents": 0.8,  # High priority (INN, documents)
            "names": 0.8,  # High priority (person names) - increased
            "companies": 0.7,  # Medium priority (companies) - increased
        }

        # Import exclusion patterns from centralized dictionary
        from ...data.dicts.smart_filter_patterns import EXCLUSION_PATTERNS
        
        # Exclusion patterns (do not require verification)
        self.exclusion_patterns = EXCLUSION_PATTERNS

        # Load name dictionaries for better language detection
        self._load_name_dictionaries()

        self.logger.info(
            f"DecisionLogic initialized (terrorism detection: {enable_terrorism_detection})"
        )

    def _load_name_dictionaries(self):
        """Load name dictionaries to enhance language patterns"""
        try:
            # Get data directory
            data_dir = Path(__file__).parent.parent.parent.parent.parent / "data"

            # Load diminutives (which include common names)
            ru_names = set()
            uk_names = set()
            en_names = set()

            # Load Russian diminutives/names
            ru_file = data_dir / "diminutives_ru.json"
            if ru_file.exists():
                with open(ru_file, 'r', encoding='utf-8') as f:
                    ru_data = json.load(f)
                    # Both keys (diminutives) and values (canonical) are names
                    ru_names.update(ru_data.keys())
                    ru_names.update(ru_data.values())

            # Load Ukrainian diminutives/names
            uk_file = data_dir / "diminutives_uk.json"
            if uk_file.exists():
                with open(uk_file, 'r', encoding='utf-8') as f:
                    uk_data = json.load(f)
                    uk_names.update(uk_data.keys())
                    uk_names.update(uk_data.values())

            # Load English nicknames
            en_file = data_dir / "lexicons" / "en_nicknames.json"
            if en_file.exists():
                with open(en_file, 'r', encoding='utf-8') as f:
                    en_data = json.load(f)
                    en_names.update(en_data.keys())
                    en_names.update(en_data.values())

            # Add top names to language patterns (limit to avoid bloat)
            if ru_names:
                common_ru = [name.lower() for name in list(ru_names)[:50]]  # Top 50
                self.language_patterns["russian"]["words"].extend(common_ru)

            if uk_names:
                common_uk = [name.lower() for name in list(uk_names)[:50]]  # Top 50
                self.language_patterns["ukrainian"]["words"].extend(common_uk)

            if en_names:
                common_en = [name.lower() for name in list(en_names)[:50]]  # Top 50
                self.language_patterns["english"]["words"].extend(common_en)

            self.logger.info(f"Enhanced language patterns with names: ru={len(common_ru) if ru_names else 0}, uk={len(common_uk) if uk_names else 0}, en={len(common_en) if en_names else 0}")

        except Exception as e:
            self.logger.warning(f"Failed to load name dictionaries for language detection: {e}")
            # Continue with basic patterns

    def make_decision(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> DecisionResult:
        """
        Make decision based on analysis of all signals

        Args:
            text: Text to analyze
            context: Additional context (source, operation type, etc.)

        Returns:
            Decision result
        """
        import time

        start_time = time.time()

        if not text or not text.strip():
            return self._create_allow_decision("Пустой текст", start_time)

        # Preliminary exclusion check
        if self._is_excluded_text(text):
            return self._create_allow_decision("Текст исключен по шаблонам", start_time)

        # Simple language detection
        detected_language, language_weight = self._detect_language_simple(text)
        self.logger.debug(
            f"Detected language: {detected_language} (weight: {language_weight:.2f})"
        )

        # Collect signals from all detectors with language optimization
        all_signals = self._collect_all_signals_optimized(
            text, detected_language, language_weight
        )

        # Terrorism analysis (highest priority)
        if self.terrorism_detector:
            terrorism_decision = self._analyze_terrorism_signals(
                all_signals, text, start_time
            )
            if terrorism_decision:
                return terrorism_decision

        # Analysis of other signals
        decision_result = self._analyze_regular_signals(
            all_signals, text, context, start_time
        )

        self.logger.debug(
            f"Decision made: {decision_result.decision.value} with confidence {decision_result.confidence}"
        )

        return decision_result

    def analyze(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> DecisionResult:
        """
        Analyze text and make decision (alias for make_decision)

        Args:
            text: Text to analyze
            context: Additional context (source, operation type, etc.)

        Returns:
            Decision result
        """
        return self.make_decision(text, context)

    def _collect_all_signals(self, text: str) -> Dict[str, Any]:
        """Collect signals from all detectors"""
        signals = {}

        try:
            # Name signals
            signals["names"] = self.name_detector.detect_name_signals(text)
        except Exception as e:
            self.logger.error(f"Error in name detection: {e}")
            signals["names"] = {"confidence": 0.0, "signals": []}

        try:
            # Company signals
            signals["companies"] = self.company_detector.detect_company_signals(text)
        except Exception as e:
            self.logger.error(f"Error in company detection: {e}")
            signals["companies"] = {"confidence": 0.0, "signals": []}

        try:
            # Document signals
            signals["documents"] = self.document_detector.detect_document_signals(text)
        except Exception as e:
            self.logger.error(f"Error in document detection: {e}")
            signals["documents"] = {"confidence": 0.0, "signals": []}

        try:
            # Terrorism signals
            if self.terrorism_detector:
                signals["terrorism"] = self.terrorism_detector.detect_terrorism_signals(
                    text
                )
            else:
                signals["terrorism"] = {
                    "confidence": 0.0,
                    "risk_level": "very_low",
                    "signals": [],
                }
        except Exception as e:
            self.logger.error(f"Error in terrorism detection: {e}")
            signals["terrorism"] = {
                "confidence": 0.0,
                "risk_level": "very_low",
                "signals": [],
            }

        return signals

    def _detect_language_simple(self, text: str) -> Tuple[str, float]:
        """Simple detection of main text language"""
        text_lower = text.lower()
        scores = {}

        for lang_name, lang_data in self.language_patterns.items():
            score = 0.0

            # Check unique characters
            if re.search(lang_data["chars"], text):
                score += 0.5

            # Check characteristic words
            word_matches = sum(1 for word in lang_data["words"] if word in text_lower)
            if word_matches > 0:
                score += min(word_matches * 0.2, 0.5)

            scores[lang_name] = score * lang_data["weight"]

        if scores:
            detected_lang = max(scores.keys(), key=lambda k: scores[k])
            weight = self.language_patterns[detected_lang]["weight"]
            return detected_lang, weight

        return "english", 1.0  # Default

    def _collect_all_signals_optimized(
        self, text: str, detected_language: str, language_weight: float
    ) -> Dict[str, Any]:
        """Collect signals from all detectors with language optimization"""
        signals = {}

        self.logger.debug(
            f"Optimization for language: {detected_language}, weight: {language_weight:.2f}"
        )

        try:
            # Name signals (with language optimization)
            signals["names"] = self.name_detector.detect_name_signals(text)
            if signals["names"]["confidence"] > 0:
                # Bonus for Slavic languages
                if detected_language in ["ukrainian", "russian"]:
                    slavic_patterns = [
                        "-енко",
                        "-ко",
                        "-ов",
                        "-ев",
                        "-ич",
                        "-ович",
                        "-овна",
                        "-евна",
                    ]
                    if any(pattern in text.lower() for pattern in slavic_patterns):
                        signals["names"]["confidence"] = min(
                            signals["names"]["confidence"] * language_weight, 1.0
                        )
                        self.logger.debug(
                            f"Applied bonus {language_weight:.1f} for {detected_language} names"
                        )

        except Exception as e:
            self.logger.error(f"Error in optimized name detection: {e}")
            signals["names"] = {"confidence": 0.0, "signals": []}

        try:
            # Company signals (with language optimization)
            signals["companies"] = self.company_detector.detect_company_signals(text)
            if signals["companies"]["confidence"] > 0:
                # Language bonuses for legal entity forms
                if detected_language == "ukrainian" and any(
                    form in text.lower() for form in ["тов", "прат", "товариство"]
                ):
                    signals["companies"]["confidence"] = min(
                        signals["companies"]["confidence"] * language_weight, 1.0
                    )
                    self.logger.debug("Applied Ukrainian bonus for companies")
                elif detected_language == "russian" and any(
                    form in text.lower() for form in ["ооо", "зао", "оао", "общество"]
                ):
                    signals["companies"]["confidence"] = min(
                        signals["companies"]["confidence"] * language_weight, 1.0
                    )
                    self.logger.debug("Applied Russian bonus for companies")
                elif detected_language == "english" and any(
                    form in text.lower() for form in ["llc", "inc", "corp", "company"]
                ):
                    signals["companies"]["confidence"] = min(
                        signals["companies"]["confidence"] * language_weight, 1.0
                    )
                    self.logger.debug("Applied English bonus for companies")

        except Exception as e:
            self.logger.error(f"Error in optimized company detection: {e}")
            signals["companies"] = {"confidence": 0.0, "signals": []}

        try:
            # Document signals (with language optimization)
            signals["documents"] = self.document_detector.detect_document_signals(text)
            if signals["documents"]["confidence"] > 0:
                # Language bonuses for documents
                if detected_language == "ukrainian" and any(
                    doc in text for doc in ["інн", "єдрпоу", "мфо"]
                ):
                    signals["documents"]["confidence"] = min(
                        signals["documents"]["confidence"] * language_weight, 1.0
                    )
                    self.logger.debug("Applied Ukrainian bonus for documents")
                elif detected_language == "russian" and any(
                    doc in text.lower() for doc in ["инн", "огрн", "кпп", "бик"]
                ):
                    signals["documents"]["confidence"] = min(
                        signals["documents"]["confidence"] * language_weight, 1.0
                    )
                    self.logger.debug("Applied Russian bonus for documents")
                elif detected_language == "english" and any(
                    doc in text.upper() for doc in ["TIN", "EIN", "SWIFT"]
                ):
                    signals["documents"]["confidence"] = min(
                        signals["documents"]["confidence"] * language_weight, 1.0
                    )
                    self.logger.debug("Applied English bonus for documents")

        except Exception as e:
            self.logger.error(f"Error in optimized document detection: {e}")
            signals["documents"] = {"confidence": 0.0, "signals": []}

        try:
            # Terrorism signals (without language correction - universal)
            if self.terrorism_detector:
                signals["terrorism"] = self.terrorism_detector.detect_terrorism_signals(
                    text
                )
            else:
                signals["terrorism"] = {
                    "confidence": 0.0,
                    "risk_level": "very_low",
                    "signals": [],
                }
        except Exception as e:
            self.logger.error(f"Error in terrorism detection: {e}")
            signals["terrorism"] = {
                "confidence": 0.0,
                "risk_level": "very_low",
                "signals": [],
            }

        # Add language information to result
        for signal_type in signals:
            if isinstance(signals[signal_type], dict):
                signals[signal_type]["language_info"] = {
                    "detected_language": detected_language,
                    "weight": language_weight,
                }

        return signals

    def _analyze_terrorism_signals(
        self, signals: Dict[str, Any], text: str, start_time: float
    ) -> Optional[DecisionResult]:
        """Terrorism signal analysis (highest priority)"""
        terrorism_signals = signals.get("terrorism", {})
        terrorism_confidence = terrorism_signals.get("confidence", 0.0)
        terrorism_risk = terrorism_signals.get("risk_level", "very_low")

        if terrorism_confidence >= self.decision_thresholds["terrorism_block"]:
            return DecisionResult(
                decision=DecisionType.BLOCK,
                confidence=terrorism_confidence,
                risk_level=RiskLevel.CRITICAL,
                reasoning=f"Critical terrorism indicators detected (confidence: {terrorism_confidence:.2f})",
                detected_signals=signals,
                recommendations=[
                    "Immediately block transaction",
                    "Notify security services",
                    "Conduct investigation",
                    "Record all details for report",
                ],
                processing_time=time.time() - start_time,
                requires_escalation=True,
                metadata={
                    "terrorism_risk": terrorism_risk,
                    "blocked_reason": "terrorism_indicators",
                },
            )

        elif terrorism_confidence >= self.decision_thresholds["terrorism_review"]:
            return DecisionResult(
                decision=DecisionType.PRIORITY_REVIEW,
                confidence=terrorism_confidence,
                risk_level=RiskLevel.HIGH,
                reasoning=f"Suspicious terrorism indicators detected (confidence: {terrorism_confidence:.2f})",
                detected_signals=signals,
                recommendations=[
                    "Suspend processing",
                    "Urgent manual review",
                    "Notify security service",
                    "Conduct additional analysis",
                ],
                processing_time=time.time() - start_time,
                requires_escalation=True,
                metadata={"terrorism_risk": terrorism_risk, "review_priority": "high"},
            )

        return None  # Continue normal analysis

    def _analyze_regular_signals(
        self,
        signals: Dict[str, Any],
        text: str,
        context: Optional[Dict[str, Any]],
        start_time: float,
    ) -> DecisionResult:
        """Analysis of regular signals (names, companies, documents)"""

        # Calculate total confidence with weights
        weighted_confidence = 0.0
        total_weight = 0.0
        signal_details = {}

        for signal_type, signal_data in signals.items():
            if signal_type == "terrorism":
                continue  # Already processed

            confidence = signal_data.get("confidence", 0.0)
            weight = self.signal_weights.get(signal_type, 0.5)

            weighted_confidence += confidence * weight
            total_weight += weight

            signal_details[signal_type] = {
                "confidence": confidence,
                "weight": weight,
                "signal_count": signal_data.get("signal_count", 0),
                "high_confidence_signals": len(
                    signal_data.get("high_confidence_signals", [])
                ),
            }

        # Normalize total confidence
        if total_weight > 0:
            normalized_confidence = weighted_confidence / total_weight
        else:
            normalized_confidence = 0.0

        # Determine risk level
        risk_level = self._determine_risk_level(normalized_confidence, signals)

        # Make decision based on confidence and context
        decision, reasoning, recommendations = self._make_regular_decision(
            normalized_confidence, signals, text, context
        )

        return DecisionResult(
            decision=decision,
            confidence=normalized_confidence,
            risk_level=risk_level,
            reasoning=reasoning,
            detected_signals=signals,
            recommendations=recommendations,
            processing_time=time.time() - start_time,
            requires_escalation=decision
            in [DecisionType.MANUAL_REVIEW, DecisionType.PRIORITY_REVIEW],
            metadata={"signal_details": signal_details, "context": context or {}},
        )

    def _make_regular_decision(
        self,
        confidence: float,
        signals: Dict[str, Any],
        text: str,
        context: Optional[Dict[str, Any]],
    ) -> Tuple[DecisionType, str, List[str]]:
        """Make regular decision based on confidence"""

        # Check for high confidence - run full search
        if confidence >= self.decision_thresholds["full_search_high"]:
            return (
                DecisionType.FULL_SEARCH,
                f"Высокая уверенность в наличии релевантных сигналов (уверенность: {confidence:.2f})",
                [
                    "Запустить полный поиск Ахо-Корасика",
                    "Проанализировать все найденные совпадения",
                    "Применить дополнительные фильтры",
                ],
            )

        # Check for medium confidence - run full search
        elif confidence >= self.decision_thresholds["full_search_medium"]:
            return (
                DecisionType.FULL_SEARCH,
                f"Средняя уверенность в наличии релевантных сигналов (уверенность: {confidence:.2f})",
                [
                    "Запустить полный поиск Ахо-Корасика",
                    "Проанализировать найденные совпадения",
                    "Рассмотреть возможность дополнительной проверки",
                ],
            )

        # Check for low confidence - manual review
        elif confidence >= self.decision_thresholds["manual_review"]:
            return (
                DecisionType.MANUAL_REVIEW,
                f"Низкая уверенность, но есть потенциальные сигналы (уверенность: {confidence:.2f})",
                [
                    "Отправить на ручную проверку",
                    "Проанализировать контекст операции",
                    "Учесть историю клиента",
                    "Принять решение о дальнейших действиях",
                ],
            )

        # Very low confidence - allow
        else:
            return (
                DecisionType.ALLOW,
                f"Очень низкая уверенность в наличии релевантных сигналов (уверенность: {confidence:.2f})",
                [
                    "Разрешить операцию без дополнительных проверок",
                    "Записать в статистику",
                ],
            )

    def _determine_risk_level(
        self, confidence: float, signals: Dict[str, Any]
    ) -> RiskLevel:
        """Determine risk level"""
        # Consider terrorism
        terrorism_signals = signals.get("terrorism", {})
        terrorism_risk = terrorism_signals.get("risk_level", "very_low")

        if terrorism_risk in ["high", "critical"]:
            return RiskLevel.CRITICAL
        elif terrorism_risk == "medium":
            return RiskLevel.HIGH

        # Regular logic based on confidence
        if confidence >= 0.8:
            return RiskLevel.HIGH
        elif confidence >= 0.6:
            return RiskLevel.MEDIUM
        elif confidence >= 0.3:
            return RiskLevel.LOW
        else:
            return RiskLevel.VERY_LOW

    def _is_excluded_text(self, text: str) -> bool:
        """Check for exclusions"""
        text_stripped = text.strip().lower()

        for pattern in self.exclusion_patterns:
            if re.match(pattern, text_stripped, re.IGNORECASE):
                return True

        return False

    def _create_allow_decision(self, reason: str, start_time: float) -> DecisionResult:
        """Create allow decision"""
        return DecisionResult(
            decision=DecisionType.ALLOW,
            confidence=0.0,
            risk_level=RiskLevel.VERY_LOW,
            reasoning=reason,
            detected_signals={},
            recommendations=["Разрешить без дополнительных проверок"],
            processing_time=time.time() - start_time,
            requires_escalation=False,
            metadata={},
        )

    def get_decision_statistics(
        self, decisions: List[DecisionResult]
    ) -> Dict[str, Any]:
        """Get decision statistics"""
        if not decisions:
            return {}

        total = len(decisions)
        decision_counts = {}
        risk_counts = {}
        avg_confidence = 0.0
        avg_processing_time = 0.0
        escalation_count = 0

        for decision in decisions:
            # Count decisions
            decision_type = decision.decision.value
            decision_counts[decision_type] = decision_counts.get(decision_type, 0) + 1

            # Count risk levels
            risk_level = decision.risk_level.value
            risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1

            # Sum for average values
            avg_confidence += decision.confidence
            avg_processing_time += decision.processing_time

            if decision.requires_escalation:
                escalation_count += 1

        return {
            "total_decisions": total,
            "decision_distribution": {k: v / total for k, v in decision_counts.items()},
            "risk_distribution": {k: v / total for k, v in risk_counts.items()},
            "average_confidence": avg_confidence / total,
            "average_processing_time": avg_processing_time / total,
            "escalation_rate": escalation_count / total,
            "decision_counts": decision_counts,
            "risk_counts": risk_counts,
        }

    def update_thresholds(self, new_thresholds: Dict[str, float]) -> None:
        """Update decision thresholds"""
        for key, value in new_thresholds.items():
            if key in self.decision_thresholds:
                old_value = self.decision_thresholds[key]
                self.decision_thresholds[key] = value
                self.logger.info(f"Updated threshold {key}: {old_value} -> {value}")
            else:
                self.logger.warning(f"Unknown threshold key: {key}")

    def get_detailed_analysis(self, text: str) -> Dict[str, Any]:
        """Get detailed analysis for diagnostics"""
        decision_result = self.make_decision(text)

        return {
            "input_text": text,
            "decision_result": {
                "decision": decision_result.decision.value,
                "confidence": decision_result.confidence,
                "risk_level": decision_result.risk_level.value,
                "reasoning": decision_result.reasoning,
                "requires_escalation": decision_result.requires_escalation,
                "processing_time": decision_result.processing_time,
            },
            "detected_signals": decision_result.detected_signals,
            "recommendations": decision_result.recommendations,
            "metadata": decision_result.metadata,
            "thresholds_used": self.decision_thresholds,
            "signal_weights_used": self.signal_weights,
        }

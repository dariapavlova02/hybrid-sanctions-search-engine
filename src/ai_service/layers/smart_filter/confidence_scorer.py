"""
Confidence Scorer

Confidence scoring system for smart filter.
Combines results from various detectors and calculates overall confidence
in the need to process text.
"""

# Standard library imports
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

# Local imports
from ...data.dicts.smart_filter_patterns import CONFIDENCE_THRESHOLDS, SIGNAL_WEIGHTS
from ...utils.logging_config import get_logger


@dataclass
class ScoringWeights:
    """Weights for different signal types"""

    company_keywords: float = 0.3
    company_legal_entities: float = 0.4
    company_business_types: float = 0.3
    company_addresses: float = 0.2
    company_registration: float = 0.5
    company_capitalized: float = 0.1

    name_full_names: float = 0.6
    name_initials: float = 0.5
    name_single_names: float = 0.3
    name_payment_context: float = 0.4
    name_phonetic: float = 0.2

    # General weights
    company_weight: float = 0.6
    name_weight: float = 0.4


class ConfidenceScorer:
    """Confidence scoring system"""

    def __init__(self):
        """Initialize scoring system"""
        self.logger = get_logger(__name__)

        # Weights for different signal types (from dictionary)
        self.weights = ScoringWeights(
            company_keywords=SIGNAL_WEIGHTS["company_keywords"],
            company_legal_entities=SIGNAL_WEIGHTS["company_legal_entities"],
            company_business_types=SIGNAL_WEIGHTS["company_business_types"],
            company_addresses=SIGNAL_WEIGHTS["company_addresses"],
            company_registration=SIGNAL_WEIGHTS["company_registration"],
            company_capitalized=SIGNAL_WEIGHTS["company_capitalized"],
            name_full_names=SIGNAL_WEIGHTS["name_full_names"],
            name_initials=SIGNAL_WEIGHTS["name_initials"],
            name_single_names=SIGNAL_WEIGHTS["name_single_names"],
            name_payment_context=SIGNAL_WEIGHTS["name_payment_context"],
            name_phonetic=SIGNAL_WEIGHTS["name_phonetic"],
            company_weight=SIGNAL_WEIGHTS["company_weight"],
            name_weight=SIGNAL_WEIGHTS["name_weight"],
        )

        # Thresholds for different confidence levels (from dictionary)
        self.thresholds = CONFIDENCE_THRESHOLDS.copy()

        # Normalization factors
        self.normalization_factors = {
            "company": 1.0,
            "name": 1.0,
            "combined": 1.2,  # Bonus for signal combination
        }

        self.logger.info("ConfidenceScorer initialized")

    def calculate_confidence(self, signals: Dict[str, Any]) -> float:
        """
        Calculate overall confidence based on all signals

        Args:
            signals: Dictionary with results from all detectors

        Returns:
            Overall confidence (0.0 - 1.0)
        """
        if not signals:
            return 0.0

        # Calculate confidence for companies
        company_confidence = self._calculate_company_confidence(
            signals.get("companies", {})
        )

        # Calculate confidence for names
        name_confidence = self._calculate_name_confidence(signals.get("names", {}))

        # Calculate confidence for payment context
        context_confidence = self._calculate_context_confidence(
            signals.get("context", {})
        )

        # Combine results
        combined_confidence = self._combine_confidences(
            company_confidence, name_confidence, context_confidence
        )

        # Apply normalization
        normalized_confidence = self._normalize_confidence(combined_confidence, signals)

        return min(normalized_confidence, 1.0)

    def _calculate_company_confidence(self, company_signals: Dict[str, Any]) -> float:
        """Calculate confidence for company signals"""
        if not company_signals or not company_signals.get("signals"):
            return 0.0

        total_confidence = 0.0
        signal_count = 0

        for signal in company_signals["signals"]:
            signal_type = signal.get("signal_type", "")
            confidence = signal.get("confidence", 0.0)
            count = signal.get("count", 0)

            # Apply weights based on signal type
            weight = self._get_company_signal_weight(signal_type)
            weighted_confidence = confidence * weight

            # Bonus for number of matches
            count_bonus = min(count * 0.1, 0.3)

            total_confidence += weighted_confidence + count_bonus
            signal_count += 1

        # Normalize by number of signals
        if signal_count > 0:
            avg_confidence = total_confidence / signal_count
            # Apply general weight for companies
            return avg_confidence * self.weights.company_weight

        return 0.0

    def _calculate_name_confidence(self, name_signals: Dict[str, Any]) -> float:
        """Calculate confidence for name signals"""
        if not name_signals or not name_signals.get("signals"):
            return 0.0

        total_confidence = 0.0
        signal_count = 0

        for signal in name_signals["signals"]:
            signal_type = signal.get("signal_type", "")
            confidence = signal.get("confidence", 0.0)
            count = signal.get("count", 0)

            # Apply weights based on signal type
            weight = self._get_name_signal_weight(signal_type)
            weighted_confidence = confidence * weight

            # Bonus for number of matches
            count_bonus = min(count * 0.1, 0.3)

            total_confidence += weighted_confidence + count_bonus
            signal_count += 1

        # Normalize by number of signals
        if signal_count > 0:
            avg_confidence = total_confidence / signal_count
            # Apply general weight for names
            return avg_confidence * self.weights.name_weight

        return 0.0

    def _combine_confidences(
        self, company_confidence: float, name_confidence: float, context_confidence: float = 0.0
    ) -> float:
        """Combine confidence for companies, names, and context"""
        # Collect all non-zero confidences
        confidences = [c for c in [company_confidence, name_confidence, context_confidence] if c > 0]
        
        if not confidences:
            return 0.0
        
        if len(confidences) == 1:
            return confidences[0]
        
        # If multiple signal types exist, give bonus
        max_confidence = max(confidences)
        min_confidence = min(confidences)
        
        # Combination bonus based on number of signal types
        combination_bonus = min_confidence * 0.3 * len(confidences)
        
        # Context bonus - if we have payment context, boost name detection
        if context_confidence > 0 and name_confidence > 0:
            context_bonus = context_confidence * name_confidence * 0.2
            combination_bonus += context_bonus
        
        return min(max_confidence + combination_bonus, 1.0)

    def _calculate_context_confidence(self, context_signals: Dict[str, Any]) -> float:
        """Calculate confidence for payment context signals"""
        if not context_signals:
            return 0.0
        
        confidence = context_signals.get("confidence", 0.0)
        
        # Bonus for having name indicators
        if context_signals.get("has_name_indicators", False):
            confidence += 0.2
        
        # Bonus for having payment context
        if context_signals.get("has_payment_context", False):
            confidence += 0.1
        
        # Bonus for having currency indicators
        if context_signals.get("has_currency_indicators", False):
            confidence += 0.1
        
        return min(confidence, 1.0)

    def _normalize_confidence(
        self, confidence: float, signals: Dict[str, Any]
    ) -> float:
        """Normalize confidence considering context"""
        if confidence <= 0:
            return 0.0

        # Basic normalization
        normalized = confidence

        # Bonus for high quality signals
        high_quality_bonus = self._calculate_high_quality_bonus(signals)
        normalized += high_quality_bonus

        # Penalty for low quality text
        quality_penalty = self._calculate_quality_penalty(signals)
        normalized -= quality_penalty

        # Apply logarithmic normalization for smoothing
        if normalized > 0.5:
            # For high values use square root
            normalized = math.sqrt(normalized)
        else:
            # For low values use square
            normalized = normalized**2

        return max(0.0, min(normalized, 1.0))

    def _get_company_signal_weight(self, signal_type: str) -> float:
        """Get weight for company signal"""
        weights_map = {
            "keywords": self.weights.company_keywords,
            "legal_entities": self.weights.company_legal_entities,
            "business_types": self.weights.company_business_types,
            "addresses": self.weights.company_addresses,
            "registration_numbers": self.weights.company_registration,
            "capitalized_names": self.weights.company_capitalized,
        }
        return weights_map.get(signal_type, 0.1)

    def _get_name_signal_weight(self, signal_type: str) -> float:
        """Get weight for name signal"""
        weights_map = {
            "full_names": self.weights.name_full_names,
            "initials": self.weights.name_initials,
            "single_names": self.weights.name_single_names,
            "payment_context": self.weights.name_payment_context,
            "phonetic_patterns": self.weights.name_phonetic,
        }
        return weights_map.get(signal_type, 0.1)

    def _calculate_high_quality_bonus(self, signals: Dict[str, Any]) -> float:
        """Calculate bonus for high quality signals"""
        bonus = 0.0

        # Bonus for high confidence in signals
        for signal_type, signal_data in signals.items():
            if (
                isinstance(signal_data, dict)
                and "high_confidence_signals" in signal_data
            ):
                high_conf_count = len(signal_data["high_confidence_signals"])
                if high_conf_count > 0:
                    bonus += min(high_conf_count * 0.05, 0.2)

        return bonus

    def _calculate_quality_penalty(self, signals: Dict[str, Any]) -> float:
        """Calculate penalty for low quality text"""
        penalty = 0.0

        # Penalty for very short texts
        for signal_type, signal_data in signals.items():
            if isinstance(signal_data, dict) and "text_length" in signal_data:
                text_length = signal_data["text_length"]
                if text_length < 10:
                    penalty += 0.3
                elif text_length < 20:
                    penalty += 0.1

        return penalty

    def get_confidence_level(self, confidence: float) -> str:
        """Get confidence level"""
        if confidence >= self.thresholds["very_high"]:
            return "very_high"
        elif confidence >= self.thresholds["high"]:
            return "high"
        elif confidence >= self.thresholds["medium"]:
            return "medium"
        elif confidence >= self.thresholds["low"]:
            return "low"
        else:
            return "very_low"

    def get_processing_recommendation(
        self, confidence: float, signals: Dict[str, Any]
    ) -> str:
        """Get processing recommendation"""
        level = self.get_confidence_level(confidence)

        recommendations = {
            "very_high": "Very high confidence - must process",
            "high": "High confidence - recommended to process",
            "medium": "Medium confidence - can process",
            "low": "Low confidence - processing not recommended",
            "very_low": "Very low confidence - do not process",
        }

        base_recommendation = recommendations.get(level, "Uncertain recommendation")

        # Additional recommendations based on signal types
        signal_types = []
        for signal_type, signal_data in signals.items():
            if isinstance(signal_data, dict) and signal_data.get("confidence", 0) > 0:
                signal_types.append(signal_type)

        if signal_types:
            base_recommendation += f" (detected signals: {', '.join(signal_types)})"

        return base_recommendation

    def get_detailed_analysis(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed confidence analysis"""
        company_confidence = self._calculate_company_confidence(
            signals.get("companies", {})
        )
        name_confidence = self._calculate_name_confidence(signals.get("names", {}))
        combined_confidence = self.combine_confidences(
            company_confidence, name_confidence
        )
        normalized_confidence = self._normalize_confidence(combined_confidence, signals)

        return {
            "company_confidence": company_confidence,
            "name_confidence": name_confidence,
            "combined_confidence": combined_confidence,
            "normalized_confidence": normalized_confidence,
            "confidence_level": self.get_confidence_level(normalized_confidence),
            "processing_recommendation": self.get_processing_recommendation(
                normalized_confidence, signals
            ),
            "high_quality_bonus": self._calculate_high_quality_bonus(signals),
            "quality_penalty": self._calculate_quality_penalty(signals),
        }

"""
Terrorism Indicators Signal Detector

Detector for identifying terrorism signals in text.
Uses characteristic short patterns for quick identification
of potential terrorist activity indicators.

IMPORTANT: This module is intended ONLY for defensive purposes and
counter-terrorism in financial systems.
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Set

from ...utils.logging_config import get_logger


@dataclass
class TerrorismSignal:
    """Terrorism indicator detection signal"""

    signal_type: str
    confidence: float
    matches: List[str]
    position: int
    context: str
    risk_level: str


class TerrorismDetector:
    """Terrorism indicators detector for defensive purposes"""

    def __init__(self):
        """Initialize detector"""
        self.logger = get_logger(__name__)

        # Patterns for terrorism financing (general indicators)
        self.financing_patterns = [
            # Suspicious terms for transfers
            r"\b(?:джихад|jihad|муджахид|mujahid|шахид|shahid|мученик|martyr)\b",
            r"\b(?:халифат|caliphate|emirate|эмират|имарат)\b",
            r"\b(?:фонд|fund|foundation|благотвор|charity|زكاة|закят|zakat)\s*(?:помощи|помощь|support|aid|relief)\b",
            # Code words (general patterns)
            r"\b(?:операция|operation|миссия|mission|проект|project)\s+[А-ЯІЇЄҐA-Z][а-яіїєґa-z]+\b",
            r"\b(?:братья|brothers|сестры|sisters|товарищи|comrades)\s+(?:по|in|from)\s+[а-яіїєґa-z]+\b",
            # Suspicious geographical regions (general)
            r"\b(?:syria|сирия|iraq|ирак|afghanistan|афганистан|somalia|сомали)\b",
            r"\b(?:tribal|племенн|region|регион|border|граница|frontier)\s+(?:area|зона|territory|территория)\b",
        ]

        # Patterns for weapons and explosives (defensive)
        self.weapons_patterns = [
            r"\b(?:explosive|взрывчат|bomb|бомба|ied|взрывн|device|устройство)\b",
            r"\b(?:ammunition|боеприпас|weapons|оружие|arms|вооружение)\b",
            r"\b(?:training|тренировк|preparation|подготовк|equipment|оборудование)\b",
            r"\b(?:chemical|химическ|biological|биологическ|nuclear|ядерн|radioactive|радиоактивн)\b",
        ]

        # Patterns for suspicious organizations (defensive lists)
        self.organization_patterns = [
            # General patterns for suspicious structures
            r"\b(?:cell|ячейка|network|сеть|group|группа|wing|крыло|brigade|бригада)\b",
            r"\b(?:movement|движение|front|фронт|liberation|освобождение|resistance|сопротивление)\b",
            r"\b(?:foundation|фонд|charity|благотвор|relief|помощь|aid|поддержка)\s+(?:international|международн|global|глобальн)\b",
        ]

        # Patterns for suspicious activity
        self.activity_patterns = [
            # Financial operations
            r"\b(?:cash|наличные|courier|курьер|transfer|перевод|hawala|хавала|informal|неформальн)\s+(?:service|сервис|system|система|network|сеть)\b",
            r"\b(?:multiple|множественн|frequent|частые|unusual|необычн|suspicious|подозрительн)\s+(?:transactions|операции|transfers|переводы|payments|платежи)\b",
            # Communications
            r"\b(?:encrypted|зашифрован|secure|защищен|anonymous|анонимн|coded|кодирован)\s+(?:message|сообщение|communication|связь|channel|канал)\b",
            r"\b(?:meeting|встреча|gathering|собрание|assembly|ассамблея|conference|конференция)\s+(?:secret|секретн|private|частн|closed|закрыт)\b",
            # Travel and movements
            r"\b(?:travel|поездка|journey|путешествие|trip|поход|visit|визит)\s+(?:to|в|from|из|via|через)\s+(?:conflict|конфликт|war|война|unstable|нестабильн)\b",
            r"\b(?:border|граница|crossing|пересечение|entry|въезд|exit|выезд)\s+(?:point|пункт|control|контроль)\b",
        ]

        # Exclusions (words that may cause false positives)
        self.exclusion_patterns = [
            r"\b(?:игра|game|фильм|movie|книга|book|история|story|новости|news)\b",
            r"\b(?:university|университет|school|школа|education|образование|academic|академическ)\b",
            r"\b(?:historical|историческ|documentary|документальн|research|исследование)\b",
            r"\b(?:legitimate|законн|official|официальн|registered|зарегистрирован)\b",
        ]

        # Weight coefficients for different indicator types
        self.pattern_weights = {
            "financing": 0.8,
            "weapons": 0.9,
            "organization": 0.7,
            "activity": 0.6,
        }

        # Risk thresholds
        self.risk_thresholds = {"high": 0.8, "medium": 0.5, "low": 0.3}

        self.logger.info("TerrorismDetector initialized for defensive purposes")

    def detect_terrorism_signals(self, text: str) -> Dict[str, Any]:
        """
        Detect terrorism indicators in text (defensive purposes)

        Args:
            text: Text to analyze

        Returns:
            Terrorism indicators detection results
        """
        if not text or not text.strip():
            return self._create_empty_result()

        # Preliminary exclusion check
        if self._is_excluded_content(text):
            return self._create_empty_result()

        signals = []
        total_confidence = 0.0
        max_risk_level = "low"

        # 1. Search for financial indicators
        financing_signals = self._detect_financing_patterns(text)
        if financing_signals["confidence"] > 0:
            signals.append(financing_signals)
            total_confidence += (
                financing_signals["confidence"] * self.pattern_weights["financing"]
            )
            if financing_signals["risk_level"] == "high":
                max_risk_level = "high"
            elif (
                financing_signals["risk_level"] == "medium" and max_risk_level != "high"
            ):
                max_risk_level = "medium"

        # 2. Search for weapons/explosives indicators
        weapons_signals = self._detect_weapons_patterns(text)
        if weapons_signals["confidence"] > 0:
            signals.append(weapons_signals)
            total_confidence += (
                weapons_signals["confidence"] * self.pattern_weights["weapons"]
            )
            if weapons_signals["risk_level"] == "high":
                max_risk_level = "high"
            elif weapons_signals["risk_level"] == "medium" and max_risk_level != "high":
                max_risk_level = "medium"

        # 3. Search for organizational indicators
        org_signals = self._detect_organization_patterns(text)
        if org_signals["confidence"] > 0:
            signals.append(org_signals)
            total_confidence += (
                org_signals["confidence"] * self.pattern_weights["organization"]
            )
            if org_signals["risk_level"] == "high":
                max_risk_level = "high"
            elif org_signals["risk_level"] == "medium" and max_risk_level != "high":
                max_risk_level = "medium"

        # 4. Search for suspicious activity
        activity_signals = self._detect_activity_patterns(text)
        if activity_signals["confidence"] > 0:
            signals.append(activity_signals)
            total_confidence += (
                activity_signals["confidence"] * self.pattern_weights["activity"]
            )
            if activity_signals["risk_level"] == "high":
                max_risk_level = "high"
            elif (
                activity_signals["risk_level"] == "medium" and max_risk_level != "high"
            ):
                max_risk_level = "medium"

        # Normalize total confidence
        normalized_confidence = min(total_confidence, 1.0)

        # Determine overall risk level
        if normalized_confidence >= self.risk_thresholds["high"]:
            overall_risk = "high"
        elif normalized_confidence >= self.risk_thresholds["medium"]:
            overall_risk = "medium"
        elif normalized_confidence >= self.risk_thresholds["low"]:
            overall_risk = "low"
        else:
            overall_risk = "very_low"

        return {
            "confidence": normalized_confidence,
            "risk_level": overall_risk,
            "signals": signals,
            "signal_count": len(signals),
            "high_risk_signals": [s for s in signals if s.get("risk_level") == "high"],
            "detected_indicators": self._extract_detected_indicators(signals),
            "text_length": len(text),
            "analysis_complete": True,
            "requires_manual_review": normalized_confidence
            >= self.risk_thresholds["medium"],
        }

    def _detect_financing_patterns(self, text: str) -> Dict[str, Any]:
        """Detect terrorism financing patterns"""
        matches = []

        for pattern in self.financing_patterns:
            found_matches = re.findall(pattern, text, re.IGNORECASE | re.UNICODE)
            matches.extend(found_matches)

        confidence = min(len(matches) * 0.3, 0.9) if matches else 0.0
        risk_level = self._determine_risk_level(confidence)

        return {
            "signal_type": "financing_terrorism",
            "confidence": confidence,
            "risk_level": risk_level,
            "matches": list(set(matches)),
            "count": len(matches),
        }

    def _detect_weapons_patterns(self, text: str) -> Dict[str, Any]:
        """Detect weapons and explosives patterns"""
        matches = []

        for pattern in self.weapons_patterns:
            found_matches = re.findall(pattern, text, re.IGNORECASE | re.UNICODE)
            matches.extend(found_matches)

        confidence = min(len(matches) * 0.4, 0.95) if matches else 0.0
        risk_level = self._determine_risk_level(confidence)

        return {
            "signal_type": "weapons_explosives",
            "confidence": confidence,
            "risk_level": risk_level,
            "matches": list(set(matches)),
            "count": len(matches),
        }

    def _detect_organization_patterns(self, text: str) -> Dict[str, Any]:
        """Detect suspicious organizations patterns"""
        matches = []

        for pattern in self.organization_patterns:
            found_matches = re.findall(pattern, text, re.IGNORECASE | re.UNICODE)
            matches.extend(found_matches)

        confidence = min(len(matches) * 0.25, 0.8) if matches else 0.0
        risk_level = self._determine_risk_level(confidence)

        return {
            "signal_type": "suspicious_organizations",
            "confidence": confidence,
            "risk_level": risk_level,
            "matches": list(set(matches)),
            "count": len(matches),
        }

    def _detect_activity_patterns(self, text: str) -> Dict[str, Any]:
        """Detect suspicious activity patterns"""
        matches = []

        for pattern in self.activity_patterns:
            found_matches = re.findall(pattern, text, re.IGNORECASE | re.UNICODE)
            matches.extend(found_matches)

        confidence = min(len(matches) * 0.2, 0.7) if matches else 0.0
        risk_level = self._determine_risk_level(confidence)

        return {
            "signal_type": "suspicious_activity",
            "confidence": confidence,
            "risk_level": risk_level,
            "matches": list(set(matches)),
            "count": len(matches),
        }

    def _is_excluded_content(self, text: str) -> bool:
        """Check for exclusions (false positives)"""
        text_lower = text.lower()

        for pattern in self.exclusion_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True

        return False

    def _determine_risk_level(self, confidence: float) -> str:
        """Determine risk level based on confidence"""
        if confidence >= self.risk_thresholds["high"]:
            return "high"
        elif confidence >= self.risk_thresholds["medium"]:
            return "medium"
        elif confidence >= self.risk_thresholds["low"]:
            return "low"
        else:
            return "very_low"

    def _extract_detected_indicators(self, signals: List[Dict[str, Any]]) -> List[str]:
        """Extract all detected indicators"""
        all_indicators = []
        for signal in signals:
            if "matches" in signal:
                all_indicators.extend(signal["matches"])
        return list(set(all_indicators))

    def _create_empty_result(self) -> Dict[str, Any]:
        """Create empty result"""
        return {
            "confidence": 0.0,
            "risk_level": "very_low",
            "signals": [],
            "signal_count": 0,
            "high_risk_signals": [],
            "detected_indicators": [],
            "text_length": 0,
            "analysis_complete": True,
            "requires_manual_review": False,
        }

    def get_risk_assessment(self, signals_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed risk assessment

        Args:
            signals_result: Signal analysis result

        Returns:
            Detailed risk assessment
        """
        risk_level = signals_result.get("risk_level", "very_low")
        confidence = signals_result.get("confidence", 0.0)

        recommendations = {
            "high": {
                "action": "IMMEDIATE_REVIEW_REQUIRED",
                "description": "High risk - immediate review required",
                "escalation": True,
                "block_transaction": True,
            },
            "medium": {
                "action": "MANUAL_REVIEW_RECOMMENDED",
                "description": "Medium risk - manual review recommended",
                "escalation": True,
                "block_transaction": False,
            },
            "low": {
                "action": "MONITOR",
                "description": "Low risk - monitoring required",
                "escalation": False,
                "block_transaction": False,
            },
            "very_low": {
                "action": "ALLOW",
                "description": "Very low risk - can be allowed",
                "escalation": False,
                "block_transaction": False,
            },
        }

        recommendation = recommendations.get(risk_level, recommendations["very_low"])

        return {
            "risk_level": risk_level,
            "confidence": confidence,
            "recommendation": recommendation,
            "signals_detected": signals_result.get("signal_count", 0),
            "high_risk_signals": len(signals_result.get("high_risk_signals", [])),
            "requires_escalation": recommendation["escalation"],
            "suggested_action": recommendation["action"],
            "description": recommendation["description"],
        }

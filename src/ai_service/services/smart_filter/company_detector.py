"""
Company Detector

Detector for identifying company and organization signals in text.
Uses linguistic patterns and keywords for quick identification
of potential company names.
"""

# Standard library imports
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Set

# Local imports
from ...data.dicts.smart_filter_patterns import (
    ADDRESS_PATTERNS,
    COMPANY_KEYWORDS,
    COMPANY_PATTERNS,
    REGISTRATION_PATTERNS,
    SIGNAL_WEIGHTS,
)
from ...utils.logging_config import get_logger


@dataclass
class CompanySignal:
    """Company detection signal"""

    signal_type: str
    confidence: float
    matches: List[str]
    position: int
    context: str


class CompanyDetector:
    """Company and organization detector"""

    def __init__(self):
        """Initialize detector"""
        self.logger = get_logger(__name__)

        # Keywords for company identification (from dictionary)
        self.company_keywords = COMPANY_KEYWORDS.copy()

        # Patterns for company identification (from dictionary)
        self.company_patterns = COMPANY_PATTERNS.copy()

        # Patterns for addresses and contact information (from dictionary)
        self.address_patterns = ADDRESS_PATTERNS.copy()

        # Patterns for registration numbers (from dictionary)
        self.registration_patterns = REGISTRATION_PATTERNS.copy()

        # Extended banking terms
        self.banking_terms = {
            "ukrainian": [
                "банк",
                "банківська",
                "банківський",
                "банківське",
                "кредитний",
                "кредитна",
                "кредитне",
                "фінансовий",
                "фінансова",
                "фінансове",
                "фінансові",
                "операції",
                "програми",
                "інвестиційний",
                "інвестиційна",
                "інвестиційне",
                "страховий",
                "страхова",
                "страхове",
                "лізинговий",
                "лізингова",
                "лізингове",
                "факторинговий",
                "факторингова",
                "факторингове",
                "мікрофінанс",
                "мікрокредит",
                "платіжний",
                "платіжна",
                "платіжне",
                "розрахунковий",
                "розрахункова",
                "розрахункове",
                "депозитний",
                "депозитна",
                "депозитне",
                "валютний",
                "валютна",
                "валютне",
                "біржовий",
                "біржова",
                "біржове",
                "брокерський",
                "брокерська",
                "брокерське",
                "трастовий",
                "трастова",
                "трастове",
                "клірингова",
                "клірингове",
                "клірингової",
                "національний банк",
                "центральний банк",
                "комерційний банк",
                "ощадний банк",
                "приват банк",
                "альфа банк",
                "укрексімбанк",
                "ощадбанк",
                "райффайзен",
                "кредитспілка",
                "кредитна спілка",
                "ломбард",
                "мікрофінансова організація",
            ],
            "russian": [
                "банк",
                "банковская",
                "банковский",
                "банковское",
                "кредитный",
                "кредитная",
                "кредитное",
                "финансовый",
                "финансовая",
                "финансовое",
                "инвестиционный",
                "инвестиционная",
                "инвестиционное",
                "страховой",
                "страховая",
                "страховое",
                "лизинговый",
                "лизинговая",
                "лизинговое",
                "факторинговый",
                "факторинговая",
                "факторинговое",
                "микрофинанс",
                "микрокредит",
                "платежный",
                "платежная",
                "платежное",
                "расчетный",
                "расчетная",
                "расчетное",
                "депозитный",
                "депозитная",
                "депозитное",
                "валютный",
                "валютная",
                "валютное",
                "биржевой",
                "биржевая",
                "биржевое",
                "брокерский",
                "брокерская",
                "брокерское",
                "трастовый",
                "трастовая",
                "трастовое",
                "клиринговая",
                "клиринговое",
                "клиринговой",
                "национальный банк",
                "центральный банк",
                "коммерческий банк",
                "сберегательный банк",
                "приват банк",
                "альфа банк",
                "сбербанк",
                "втб",
                "газпромбанк",
                "россельхозбанк",
                "кредитный союз",
                "ломбард",
                "микрофинансовая организация",
            ],
            "english": [
                "bank",
                "banking",
                "financial",
                "finance",
                "investment",
                "credit",
                "loan",
                "insurance",
                "leasing",
                "factoring",
                "microfinance",
                "microcredit",
                "payment",
                "settlement",
                "deposit",
                "currency",
                "exchange",
                "trading",
                "brokerage",
                "trust",
                "clearing",
                "custodial",
                "wealth",
                "asset",
                "fund",
                "capital",
                "national bank",
                "central bank",
                "commercial bank",
                "savings bank",
                "investment bank",
                "private bank",
                "retail bank",
                "corporate bank",
                "development bank",
                "jpmorgan",
                "goldman sachs",
                "morgan stanley",
                "wells fargo",
                "bank of america",
                "credit union",
                "credit card",
                "debit card",
                "atm",
                "swift",
                "wire transfer",
                "correspondent bank",
                "nostro",
                "vostro",
                "clearing house",
                "settlement system",
            ],
        }

        # Special patterns for financial services
        self.financial_services_patterns = [
            r"\b(?:банк|bank|банківський|банковский|banking)\b",
            r"\b(?:кредит|credit|loan|позика|заем)\b",
            r"\b(?:страхування|страхование|insurance|страховка)\b",
            r"\b(?:інвестиції|инвестиции|investment|вложения)\b",
            r"\b(?:біржа|биржа|exchange|trading|торги)\b",
            r"\b(?:брокер|broker|брокерський|брокерский)\b",
            r"\b(?:фінанси|финансы|finance|фінансовий|финансовый)\b",
            r"\b(?:платіжний|платежный|payment|оплата|платеж)\b",
            r"\b(?:депозит|deposit|вклад|депозитний|депозитный)\b",
            r"\b(?:валюта|currency|обмін|обмен|exchange)\b",
        ]

        self.logger.info("CompanyDetector initialized")

    def detect_company_signals(self, text: str) -> Dict[str, Any]:
        """
        Detect company signals in text

        Args:
            text: Text to analyze

        Returns:
            Company signal detection results
        """
        if not text or not text.strip():
            return self._create_empty_result()

        signals = []
        total_confidence = 0.0

        # 1. Search for company keywords
        keyword_signals = self._detect_keywords(text)
        if keyword_signals["confidence"] > 0:
            signals.append(keyword_signals)
            total_confidence += keyword_signals["confidence"]

        # 2. Search for legal entity patterns
        legal_entity_signals = self._detect_legal_entities(text)
        if legal_entity_signals["confidence"] > 0:
            signals.append(legal_entity_signals)
            total_confidence += legal_entity_signals["confidence"]

        # 3. Search for business type patterns
        business_type_signals = self._detect_business_types(text)
        if business_type_signals["confidence"] > 0:
            signals.append(business_type_signals)
            total_confidence += business_type_signals["confidence"]

        # 4. Search for address information
        address_signals = self._detect_addresses(text)
        if address_signals["confidence"] > 0:
            signals.append(address_signals)
            total_confidence += address_signals["confidence"]

        # 5. Search for registration numbers
        registration_signals = self._detect_registration_numbers(text)
        if registration_signals["confidence"] > 0:
            signals.append(registration_signals)
            total_confidence += registration_signals["confidence"]

        # 6. Search for capitalized names (potential company names)
        capitalized_signals = self._detect_capitalized_names(text)
        if capitalized_signals["confidence"] > 0:
            signals.append(capitalized_signals)
            total_confidence += capitalized_signals["confidence"]

        # 7. Search for banking terms
        banking_signals = self._detect_banking_terms(text)
        if banking_signals["confidence"] > 0:
            signals.append(banking_signals)
            total_confidence += banking_signals["confidence"]

        # 8. Search for financial services
        financial_services_signals = self._detect_financial_services(text)
        if financial_services_signals["confidence"] > 0:
            signals.append(financial_services_signals)
            total_confidence += financial_services_signals["confidence"]

        # Normalize total confidence
        normalized_confidence = min(total_confidence, 1.0)

        return {
            "confidence": normalized_confidence,
            "signals": signals,
            "signal_count": len(signals),
            "high_confidence_signals": [s for s in signals if s["confidence"] > 0.7],
            "detected_keywords": self._extract_detected_keywords(signals),
            "text_length": len(text),
            "analysis_complete": True,
        }

    def _detect_keywords(self, text: str) -> Dict[str, Any]:
        """Detect company keywords"""
        matches = []
        text_lower = text.lower()

        for language, keywords in self.company_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    matches.append(keyword)

        confidence = min(len(matches) * 0.2, 0.8) if matches else 0.0

        return {
            "signal_type": "keywords",
            "confidence": confidence,
            "matches": list(set(matches)),
            "count": len(matches),
        }

    def _detect_legal_entities(self, text: str) -> Dict[str, Any]:
        """Detect legal entities"""
        matches = []

        for pattern in self.company_patterns["legal_entities"]:
            found_matches = re.findall(pattern, text, re.IGNORECASE)
            matches.extend(found_matches)

        confidence = min(len(matches) * 0.3, 0.9) if matches else 0.0

        return {
            "signal_type": "legal_entities",
            "confidence": confidence,
            "matches": list(set(matches)),
            "count": len(matches),
        }

    def _detect_business_types(self, text: str) -> Dict[str, Any]:
        """Detect business types"""
        matches = []

        for pattern in self.company_patterns["business_types"]:
            found_matches = re.findall(pattern, text, re.IGNORECASE)
            matches.extend(found_matches)

        confidence = min(len(matches) * 0.25, 0.8) if matches else 0.0

        return {
            "signal_type": "business_types",
            "confidence": confidence,
            "matches": list(set(matches)),
            "count": len(matches),
        }

    def _detect_addresses(self, text: str) -> Dict[str, Any]:
        """Detect address information"""
        matches = []

        for pattern in self.address_patterns:
            found_matches = re.findall(pattern, text, re.IGNORECASE)
            matches.extend(found_matches)

        confidence = min(len(matches) * 0.4, 0.7) if matches else 0.0

        return {
            "signal_type": "addresses",
            "confidence": confidence,
            "matches": list(set(matches)),
            "count": len(matches),
        }

    def _detect_registration_numbers(self, text: str) -> Dict[str, Any]:
        """Detect registration numbers"""
        matches = []

        for pattern in self.registration_patterns:
            found_matches = re.findall(pattern, text, re.IGNORECASE)
            matches.extend(found_matches)

        confidence = min(len(matches) * 0.5, 0.8) if matches else 0.0

        return {
            "signal_type": "registration_numbers",
            "confidence": confidence,
            "matches": list(set(matches)),
            "count": len(matches),
        }

    def _detect_capitalized_names(self, text: str) -> Dict[str, Any]:
        """Detect capitalized names"""
        # Pattern for words starting with capital letter
        pattern = (
            r"\b[A-ZА-ЯІЇЄҐ][a-zа-яіїєґ]{2,}(?:\s+[A-ZА-ЯІЇЄҐ][a-zа-яіїєґ]{2,})*\b"
        )
        matches = re.findall(pattern, text)

        # Filter common words
        common_words = {"Оплата", "Платеж", "Перевод", "Счет", "Квитанция", "Документ"}
        filtered_matches = [match for match in matches if match not in common_words]

        confidence = min(len(filtered_matches) * 0.15, 0.6) if filtered_matches else 0.0

        return {
            "signal_type": "capitalized_names",
            "confidence": confidence,
            "matches": list(set(filtered_matches)),
            "count": len(filtered_matches),
        }

    def _extract_detected_keywords(self, signals: List[Dict[str, Any]]) -> List[str]:
        """Extract all detected keywords"""
        all_keywords = []
        for signal in signals:
            if "matches" in signal:
                all_keywords.extend(signal["matches"])
        return list(set(all_keywords))

    def _detect_banking_terms(self, text: str) -> Dict[str, Any]:
        """Detect banking terms"""
        matches = []
        text_lower = text.lower()

        # Search across all languages
        for language, terms in self.banking_terms.items():
            for term in terms:
                if term.lower() in text_lower:
                    matches.append(term)

        confidence = min(len(matches) * 0.6, 0.9) if matches else 0.0

        return {
            "signal_type": "banking_terms",
            "confidence": confidence,
            "matches": list(set(matches)),
            "count": len(matches),
        }

    def _detect_financial_services(self, text: str) -> Dict[str, Any]:
        """Detect financial services by patterns"""
        matches = []

        for pattern in self.financial_services_patterns:
            found_matches = re.findall(pattern, text, re.IGNORECASE)
            matches.extend(found_matches)

        confidence = min(len(matches) * 0.5, 0.8) if matches else 0.0

        return {
            "signal_type": "financial_services",
            "confidence": confidence,
            "matches": list(set(matches)),
            "count": len(matches),
        }

    def get_enhanced_company_analysis(self, text: str) -> Dict[str, Any]:
        """
        Get enhanced company analysis

        Args:
            text: Text to analyze

        Returns:
            Enhanced company analysis
        """
        result = self.detect_company_signals(text)

        # Additional statistics
        analysis = {
            "basic_result": result,
            "detailed_breakdown": {
                "legal_entities": 0,
                "business_types": 0,
                "banking_terms": 0,
                "financial_services": 0,
                "addresses": 0,
                "registration_numbers": 0,
                "capitalized_names": 0,
            },
            "company_type_analysis": {
                "is_financial_institution": False,
                "is_legal_entity": False,
                "has_registration_info": False,
                "most_likely_sector": "unknown",
            },
        }

        # Analyze signal types
        for signal in result.get("signals", []):
            signal_type = signal.get("signal_type", "")
            count = signal.get("count", 0)

            if signal_type in analysis["detailed_breakdown"]:
                analysis["detailed_breakdown"][signal_type] = count

            # Analyze company type
            if signal_type in ["banking_terms", "financial_services"]:
                analysis["company_type_analysis"]["is_financial_institution"] = True
            elif signal_type == "legal_entities":
                analysis["company_type_analysis"]["is_legal_entity"] = True
            elif signal_type == "registration_numbers":
                analysis["company_type_analysis"]["has_registration_info"] = True

        # Determine sector
        if analysis["company_type_analysis"]["is_financial_institution"]:
            analysis["company_type_analysis"]["most_likely_sector"] = "financial"
        elif analysis["detailed_breakdown"].get("legal_entities", 0) > 0:
            analysis["company_type_analysis"]["most_likely_sector"] = "commercial"
        elif analysis["detailed_breakdown"].get("business_types", 0) > 0:
            analysis["company_type_analysis"]["most_likely_sector"] = "business"

        return analysis

    def _create_empty_result(self) -> Dict[str, Any]:
        """Create empty result"""
        return {
            "confidence": 0.0,
            "signals": [],
            "signal_count": 0,
            "high_confidence_signals": [],
            "detected_keywords": [],
            "text_length": 0,
            "analysis_complete": True,
        }

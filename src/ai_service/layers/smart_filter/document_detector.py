"""
Document Signal Detector

Detector for identifying document signals in text.
Detects INN, dates, addresses, document numbers and other
documentary information.
"""

# Standard library imports
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Set

# Local imports
from ...utils.logging_config import get_logger


@dataclass
class DocumentSignal:
    """Document detection signal"""

    signal_type: str
    confidence: float
    matches: List[str]
    position: int
    context: str


class DocumentDetector:
    """Document signal detector"""

    def __init__(self):
        """Initialize detector"""
        self.logger = get_logger(__name__)

        # Pre-compile patterns for better performance
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile all regex patterns for better performance"""
        # Patterns for INN (various formats)
        inn_pattern_strings = [
            r"\b(?:ИНН|інн|inn|ідентифікаційний\s+номер|идентификационный\s+номер)[:\s]*(\d{8,12})\b",
            r"\b(\d{8})\b(?=.*(?:ИНН|інн|inn))",  # 8 digits in INN context
            r"\b(\d{10})\b(?=.*(?:ИНН|інн|inn))",  # 10 digits in INN context
            r"\b(\d{12})\b(?=.*(?:ИНН|інн|inn))",  # 12 digits in INN context
            r"\b\d{3}\s*\d{3}\s*\d{3}\s*\d{3}\b",  # Formatted INN
        ]
        self.inn_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in inn_pattern_strings
        ]

        # Patterns for dates (various formats)
        date_pattern_strings = [
            r"\b\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}\b",  # DD/MM/YYYY, DD-MM-YYYY
            r"\b\d{2,4}[./\-]\d{1,2}[./\-]\d{1,2}\b",  # YYYY/MM/DD, YYYY-MM-DD
            r"\b\d{1,2}\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{2,4}\b",
            r"\b\d{1,2}\s+(січня|лютого|березня|квітня|травня|червня|липня|серпня|вересня|жовтня|листопада|грудня)\s+\d{2,4}(?:\s+року)?\b",
            r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{2,4}\b",
        ]
        self.date_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in date_pattern_strings
        ]

        # Patterns for document numbers
        document_pattern_strings = [
            # Passport
            r"\b(?:паспорт|passport|пасп)[:\s]*([А-ЯІЇЄҐA-Z]{2}\d{6})\b",
            r"\b([А-ЯІЇЄҐA-Z]{2}\s*\d{6})\b",
            # Driver license
            r"\b(?:водій|водитель|driver|rights|посвідчення)[:\s]*([А-ЯІЇЄҐA-Z]{3}\d{6})\b",
            # Birth certificate
            r"\b(?:свідоцтво|свидетельство|birth|certificate)[:\s]*([А-ЯІЇЄҐA-Z]{1,3}-[А-ЯІЇЄҐA-Z]{1,3}\s*\d{6})\b",
            # Other documents with alphanumeric codes
            r"\b[А-ЯІЇЄҐA-Z]{2,4}\s*\d{6,10}\b",
            r"\b\d{4,6}-[А-ЯІЇЄҐA-Z]{2,4}-\d{4,6}\b",
        ]
        self.document_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in document_pattern_strings
        ]

        # Patterns for addresses
        address_pattern_strings = [
            # Postal codes
            r"\b\d{5,6}\b(?=.*(?:індекс|индекс|поштовий|почтовый|zip|postal))",
            r"\b(?:індекс|индекс|поштовий|почтовий|zip|postal)[:\s]*(\d{5,6})\b",
            # Full addresses
            r"\b(?:адреса|адрес|address)[:\s]*([^\n\r]{20,100})\b",
            r"\b(?:м\.|місто|город|city)[:\s]*([А-ЯІЇЄҐA-Z][а-яіїєґa-z\s\-\']+)\b",
            r"\b(?:вул\.|вулиця|улица|street)[:\s]*([А-ЯІЇЄҐA-Z][а-яіїєґa-z\s\-\']+)\b",
            r"\b(?:буд\.|будинок|дом|building)[:\s]*(\d+[а-яіїєґa-z]*)\b",
            r"\b(?:кв\.|квартира|квартира|apartment)[:\s]*(\d+)\b",
            # Coordinates
            r"\b\d{1,3}\.\d{4,6},?\s*\d{1,3}\.\d{4,6}\b",  # Latitude/longitude
        ]
        self.address_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in address_pattern_strings
        ]

        # Patterns for banking details
        bank_pattern_strings = [
            r"\b(?:МФО|мфо|BIC|bic|swift|SWIFT)[:\s]*([А-ЯІЇЄҐA-Z0-9]{6,11})\b",
            r"\b(?:рахунок|счет|account|IBAN|iban)[:\s]*([А-ЯІЇЄҐA-Z0-9\s]{10,34})\b",
            r"\b(?:картка|карта|card)[:\s]*(\d{4}\s*\*{4,12}\s*\d{4})\b",
            r"\bUA\d{2}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\b",  # IBAN Ukraine
        ]
        self.bank_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in bank_pattern_strings
        ]

        # Patterns for phone numbers
        phone_pattern_strings = [
            r"\b(?:\+?38)?[\s\-\(]?0[\d\s\-\(\)]{8,12}\b",  # Ukrainian phones
            r"\b\+?1[\s\-\(]?\d{3}[\s\-\)]?\d{3}[\s\-]?\d{4}\b",  # US phones
            r"\b\+?7[\s\-\(]?\d{3}[\s\-\)]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b",  # Russian phones
            r"\b\+?\d{1,4}[\s\-\(]?\d{1,4}[\s\-\)]?\d{1,4}[\s\-]?\d{1,4}[\s\-]?\d{1,4}\b",
        ]
        self.phone_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in phone_pattern_strings
        ]

        # Patterns for email addresses
        email_pattern_strings = [
            r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
        ]
        self.email_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in email_pattern_strings
        ]

        # Context words for documents
        self.document_context_words = {
            "ukrainian": [
                "документ",
                "документи",
                "паспорт",
                "посвідчення",
                "свідоцтво",
                "довідка",
                "довідки",
                "сертифікат",
                "ліцензія",
                "дозвіл",
                "договір",
                "контракт",
                "угода",
                "протокол",
                "акт",
                "рахунок",
                "інн",
                "податковий",
                "номер",
                "код",
            ],
            "russian": [
                "документ",
                "документы",
                "паспорт",
                "удостоверение",
                "свидетельство",
                "справка",
                "справки",
                "сертификат",
                "лицензия",
                "разрешение",
                "договор",
                "контракт",
                "соглашение",
                "протокол",
                "акт",
                "счет",
                "инн",
                "налоговый",
                "номер",
                "код",
            ],
            "english": [
                "document",
                "documents",
                "passport",
                "certificate",
                "license",
                "permit",
                "contract",
                "agreement",
                "protocol",
                "act",
                "account",
                "tax",
                "number",
                "code",
                "id",
                "identification",
            ],
        }

        self.logger.info("DocumentDetector initialized")

    def detect_document_signals(self, text: str) -> Dict[str, Any]:
        """
        Detect document signals in text

        Args:
            text: Text to analyze

        Returns:
            Document signal detection results
        """
        if not text or not text.strip():
            return self._create_empty_result()

        signals = []
        total_confidence = 0.0

        # 1. Search for INN
        inn_signals = self._detect_inn(text)
        if inn_signals["confidence"] > 0:
            signals.append(inn_signals)
            total_confidence += inn_signals["confidence"]

        # 2. Search for dates
        date_signals = self._detect_dates(text)
        if date_signals["confidence"] > 0:
            signals.append(date_signals)
            total_confidence += date_signals["confidence"]

        # 3. Search for document numbers
        document_signals = self._detect_document_numbers(text)
        if document_signals["confidence"] > 0:
            signals.append(document_signals)
            total_confidence += document_signals["confidence"]

        # 4. Search for addresses
        address_signals = self._detect_addresses(text)
        if address_signals["confidence"] > 0:
            signals.append(address_signals)
            total_confidence += address_signals["confidence"]

        # 5. Search for banking details
        bank_signals = self._detect_bank_details(text)
        if bank_signals["confidence"] > 0:
            signals.append(bank_signals)
            total_confidence += bank_signals["confidence"]

        # 6. Search for contact information
        contact_signals = self._detect_contact_info(text)
        if contact_signals["confidence"] > 0:
            signals.append(contact_signals)
            total_confidence += contact_signals["confidence"]

        # Normalize total confidence
        normalized_confidence = min(total_confidence, 1.0)

        return {
            "confidence": normalized_confidence,
            "signals": signals,
            "signal_count": len(signals),
            "high_confidence_signals": [s for s in signals if s["confidence"] > 0.7],
            "detected_documents": self._extract_detected_documents(signals),
            "text_length": len(text),
            "analysis_complete": True,
        }

    def _detect_inn(self, text: str) -> Dict[str, Any]:
        """Detect INN"""
        matches = []

        for pattern in self.inn_patterns:
            found_matches = pattern.findall(text)
            if isinstance(found_matches[0] if found_matches else None, tuple):
                matches.extend([match[0] for match in found_matches])
            else:
                matches.extend(found_matches)

        # INN validation (basic length check)
        validated_matches = []
        for match in matches:
            if re.match(r"^\d{8}$|^\d{10}$|^\d{12}$", match):
                validated_matches.append(match)

        confidence = (
            min(len(validated_matches) * 0.8, 0.95) if validated_matches else 0.0
        )

        return {
            "signal_type": "inn",
            "confidence": confidence,
            "matches": list(set(validated_matches)),
            "count": len(validated_matches),
        }

    def _detect_dates(self, text: str) -> Dict[str, Any]:
        """Detect dates"""
        matches = []

        for pattern in self.date_patterns:
            # Use finditer to get full matches instead of just groups
            full_matches = pattern.finditer(text)
            for match in full_matches:
                matches.append(match.group(0))

        # Date validation
        validated_matches = []
        for match in matches:
            if self._is_valid_date(match):
                validated_matches.append(match)

        confidence = (
            min(len(validated_matches) * 0.3, 0.7) if validated_matches else 0.0
        )

        return {
            "signal_type": "dates",
            "confidence": confidence,
            "matches": list(set(validated_matches)),
            "count": len(validated_matches),
        }

    def _detect_document_numbers(self, text: str) -> Dict[str, Any]:
        """Detect document numbers"""
        matches = []

        for pattern in self.document_patterns:
            found_matches = pattern.findall(text)
            if isinstance(found_matches[0] if found_matches else None, tuple):
                matches.extend([match[0] for match in found_matches])
            else:
                matches.extend(found_matches)

        confidence = min(len(matches) * 0.6, 0.9) if matches else 0.0

        return {
            "signal_type": "document_numbers",
            "confidence": confidence,
            "matches": list(set(matches)),
            "count": len(matches),
        }

    def _detect_addresses(self, text: str) -> Dict[str, Any]:
        """Detect addresses"""
        matches = []

        for pattern in self.address_patterns:
            found_matches = pattern.findall(text)
            if isinstance(found_matches[0] if found_matches else None, tuple):
                matches.extend([match[0] for match in found_matches])
            else:
                matches.extend(found_matches)

        confidence = min(len(matches) * 0.4, 0.8) if matches else 0.0

        return {
            "signal_type": "addresses",
            "confidence": confidence,
            "matches": list(set(matches)),
            "count": len(matches),
        }

    def _detect_bank_details(self, text: str) -> Dict[str, Any]:
        """Detect banking details"""
        matches = []

        for pattern in self.bank_patterns:
            found_matches = pattern.findall(text)
            if isinstance(found_matches[0] if found_matches else None, tuple):
                matches.extend([match[0] for match in found_matches])
            else:
                matches.extend(found_matches)

        confidence = min(len(matches) * 0.7, 0.9) if matches else 0.0

        return {
            "signal_type": "bank_details",
            "confidence": confidence,
            "matches": list(set(matches)),
            "count": len(matches),
        }

    def _detect_contact_info(self, text: str) -> Dict[str, Any]:
        """Detect contact information"""
        matches = []

        # Phones
        for pattern in self.phone_patterns:
            found_matches = pattern.findall(text)
            matches.extend(found_matches)

        # Email
        for pattern in self.email_patterns:
            found_matches = pattern.findall(text)
            matches.extend(found_matches)

        confidence = min(len(matches) * 0.5, 0.8) if matches else 0.0

        return {
            "signal_type": "contact_info",
            "confidence": confidence,
            "matches": list(set(matches)),
            "count": len(matches),
        }

    def _is_valid_date(self, date_str: str) -> bool:
        """Basic date validation"""
        # Simple check for reasonable dates
        try:
            # Try parsing various formats
            date_formats = [
                "%d/%m/%Y",
                "%d.%m.%Y",
                "%d-%m-%Y",
                "%Y/%m/%d",
                "%Y.%m.%d",
                "%Y-%m-%d",
            ]

            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    # Check that date is within reasonable range
                    if 1900 <= parsed_date.year <= 2100:
                        return True
                except ValueError:
                    continue

            # Check for Ukrainian months
            ukrainian_months = {
                "січня": 1,
                "лютого": 2,
                "березня": 3,
                "квітня": 4,
                "травня": 5,
                "червня": 6,
                "липня": 7,
                "серпня": 8,
                "вересня": 9,
                "жовтня": 10,
                "листопада": 11,
                "грудня": 12,
            }

            # Check for English months
            english_months = {
                "january": 1,
                "february": 2,
                "march": 3,
                "april": 4,
                "may": 5,
                "june": 6,
                "july": 7,
                "august": 8,
                "september": 9,
                "october": 10,
                "november": 11,
                "december": 12,
            }

            # Simple check for Ukrainian dates
            import re

            ukr_pattern = (
                r"(\d{1,2})\s+(" + "|".join(ukrainian_months.keys()) + r")\s+(\d{4})"
            )
            match = re.search(ukr_pattern, date_str)
            if match:
                day, month_name, year = match.groups()
                year = int(year)
                if 1900 <= year <= 2100 and 1 <= int(day) <= 31:
                    return True

            # Simple check for English dates
            eng_pattern = (
                r"(" + "|".join(english_months.keys()) + r")\s+(\d{1,2}),?\s+(\d{4})"
            )
            match = re.search(eng_pattern, date_str, re.IGNORECASE)
            if match:
                month_name, day, year = match.groups()
                year = int(year)
                if 1900 <= year <= 2100 and 1 <= int(day) <= 31:
                    return True

            return False
        except Exception:
            return False

    def _extract_detected_documents(self, signals: List[Dict[str, Any]]) -> List[str]:
        """Extract all detected documents"""
        all_documents = []
        for signal in signals:
            if "matches" in signal:
                all_documents.extend(signal["matches"])
        return list(set(all_documents))

    def _create_empty_result(self) -> Dict[str, Any]:
        """Create empty result"""
        return {
            "confidence": 0.0,
            "signals": [],
            "signal_count": 0,
            "high_confidence_signals": [],
            "detected_documents": [],
            "text_length": 0,
            "analysis_complete": True,
        }

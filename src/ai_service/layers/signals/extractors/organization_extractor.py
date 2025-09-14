"""
Organization entity extractor.
"""

import re
from typing import Any, Dict, List

from .base_extractor import BaseExtractor


class OrganizationExtractor(BaseExtractor):
    """Extracts organization names from text using legal form detection."""

    def extract(self, text: str, language: str = "uk", **kwargs) -> List[str]:
        """
        Extract organization names from text.

        Args:
            text: Input text
            language: Text language

        Returns:
            List of organization names
        """
        if not self._is_valid_text(text):
            return []

        try:
            from ....data.patterns.legal_forms import get_compiled_legal_forms_regex

            legal_forms_compiled = get_compiled_legal_forms_regex()
            organizations = []

            for match in legal_forms_compiled.finditer(text):
                org_text = self._extract_org_name_near_legal_form(text, match)
                if org_text and org_text != "UNNAMED_ORG":
                    organizations.append(org_text.strip().upper())

            # Remove duplicates while preserving order
            unique_orgs = []
            seen = set()
            for org in organizations:
                if org not in seen:
                    unique_orgs.append(org)
                    seen.add(org)

            self._log_extraction_result(text, len(unique_orgs), "organization")
            return unique_orgs

        except ImportError:
            self.logger.warning(
                "Legal forms patterns not available, falling back to empty result"
            )
            return []

    def _extract_org_name_near_legal_form(self, text: str, legal_form_match) -> str:
        """
        Extract organization name near a legal form match.

        Args:
            text: Input text
            legal_form_match: Regex match for legal form

        Returns:
            Organization name or "UNNAMED_ORG" if not found
        """
        start = legal_form_match.start()
        end = legal_form_match.end()
        legal_form = legal_form_match.group().strip()

        # Search in vicinity of legal form (±100 characters)
        search_start = max(0, start - 100)
        search_end = min(len(text), end + 100)
        search_area = text[search_start:search_end]
        legal_form_pos_in_area = start - search_start

        # 1. Look for quoted names near the legal form
        quoted_pattern = r'["\u201c\u201d\u00ab\u00bb]([^"\u201c\u201d\u00ab\u00bb]+)["\u201c\u201d\u00ab\u00bb]'
        quoted_matches = list(re.finditer(quoted_pattern, search_area))

        if quoted_matches:
            # Find closest quoted match to legal form
            closest_match = min(
                quoted_matches, key=lambda m: abs(m.start() - legal_form_pos_in_area)
            )
            return closest_match.group(1)

        # 2. Look for organization name adjacent to legal form (before or after)
        # Strategy: look for proper nouns (capitalized words) that directly adjoin legal form

        # Search after legal form (most common: "ООО Рога и Копыта")
        after_text = text[end:min(len(text), end + 50)].strip()
        if after_text:
            # Pattern: one or more capitalized words, possibly with connectors
            # Matches: "Рога и Копыта", "TechCorp", "Инноваційні Технології"
            after_org_pattern = r'^\s*([А-ЯЁЇІЄҐA-Z][а-яёїієґa-zA-Z0-9]*(?:\s+(?:и|і|and|&|[А-ЯЁЇІЄҐA-Z][а-яёїієґa-zA-Z0-9]*)){0,4})'
            after_match = re.match(after_org_pattern, after_text)
            if after_match:
                candidate = after_match.group(1).strip()
                if not self._is_common_word(candidate) and len(candidate) >= 3:
                    return candidate

        # Search before legal form (less common but possible: "Рога и Копыта ООО")
        before_text = text[max(0, start - 50):start].strip()
        if before_text:
            # Pattern: capitalized words ending right before legal form
            before_org_pattern = r'([А-ЯЁЇІЄҐA-Z][а-яёїієґa-zA-Z0-9]*(?:\s+(?:и|і|and|&|[А-ЯЁЇІЄҐA-Z][а-яёїієґa-zA-Z0-9]*)){0,4})\s*$'
            before_match = re.search(before_org_pattern, before_text)
            if before_match:
                candidate = before_match.group(1).strip()
                if not self._is_common_word(candidate) and len(candidate) >= 3:
                    return candidate

        # Fallback: return placeholder
        return "UNNAMED_ORG"

    def _is_common_word(self, word: str) -> bool:
        """Check if word is a common non-organization word."""
        common_words = {
            # Russian
            "ПЛАТЕЖ", "ОПЛАТА", "ПЕРЕВОД", "БАНК", "СЧЕТ", "КАРТА", "УСЛУГИ",
            "ТОВАРЫ", "ДОГОВОР", "СУММА", "РУБЛЬ", "РУБЛЕЙ", "КОПЕЙКА", "КОПЕЕК",
            "АДРЕС", "ГОРОД", "УЛИЦА", "ДОМ", "ОФИС", "ТЕЛЕФОН", "EMAIL",
            # Ukrainian
            "ПЛАТІЖ", "ОПЛАТА", "ПЕРЕКАЗ", "РАХУНОК", "ПОСЛУГИ", "ТОВАРИ",
            "ДОГОВІР", "СУМА", "ГРИВНА", "ГРИВЕНЬ", "КОПІЙКА", "КОПІЙОК",
            "АДРЕСА", "МІСТО", "ВУЛИЦЯ", "БУДИНОК", "ОФІС", "ТЕЛЕФОН",
            # English
            "PAYMENT", "TRANSFER", "BANK", "ACCOUNT", "SERVICES", "GOODS",
            "CONTRACT", "AMOUNT", "DOLLAR", "DOLLARS", "ADDRESS", "CITY",
            "STREET", "OFFICE", "PHONE", "EMAIL", "FOR", "TO", "FROM", "THE"
        }
        return word.upper() in common_words

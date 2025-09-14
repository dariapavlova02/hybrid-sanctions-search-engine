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
            from ...data.patterns.legal_forms import get_legal_forms_regex

            legal_forms_regex = get_legal_forms_regex()
            organizations = []

            for match in re.finditer(legal_forms_regex, text, re.IGNORECASE):
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

        # Look for quoted names near the legal form
        quoted_pattern = r'["\u201c\u201d\u00ab\u00bb]([^"\u201c\u201d\u00ab\u00bb]+)["\u201c\u201d\u00ab\u00bb]'

        # Search in vicinity of legal form (±100 characters)
        search_start = max(0, start - 100)
        search_end = min(len(text), end + 100)
        search_area = text[search_start:search_end]

        quoted_matches = list(re.finditer(quoted_pattern, search_area))

        if quoted_matches:
            # Find closest quoted match to legal form
            legal_form_pos_in_area = start - search_start
            closest_match = min(
                quoted_matches, key=lambda m: abs(m.start() - legal_form_pos_in_area)
            )
            return closest_match.group(1)

        # Fallback: return placeholder
        return "UNNAMED_ORG"

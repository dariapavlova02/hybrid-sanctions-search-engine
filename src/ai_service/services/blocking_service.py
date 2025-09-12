"""
Blocking service to compute cheap, deterministic candidate keys.

Keys target: surname-based buckets, initials, phonetics, legal forms, IDs.
Designed to maximize recall while keeping keys specific enough for filtering.
"""

from __future__ import annotations

# Standard library imports
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Local imports
from ..utils import get_logger


@dataclass
class BlockingKeys:
    """Container for computed blocking keys."""

    # Person-like keys
    surname_normalized: Optional[str] = None
    first_initial_surname: Optional[str] = None
    phonetic_surname: Optional[str] = None
    birth_year: Optional[int] = None
    birth_decade: Optional[int] = None
    country_code: Optional[str] = None

    # Company-like keys
    legal_form_key: Optional[str] = None
    org_core_stem: Optional[str] = None

    # IDs
    edrpou: Optional[str] = None
    tax_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "surname_normalized": self.surname_normalized,
            "first_initial_surname": self.first_initial_surname,
            "phonetic_surname": self.phonetic_surname,
            "birth_year": self.birth_year,
            "birth_decade": self.birth_decade,
            "country_code": self.country_code,
            "legal_form_key": self.legal_form_key,
            "org_core_stem": self.org_core_stem,
            "edrpou": self.edrpou,
            "tax_id": self.tax_id,
        }


class BlockingService:
    """Computes blocking keys from text + optional metadata."""

    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        # Basic legal entity markers (fallbacks if dict is missing)
        try:
            from ..data.dicts.company_triggers import COMPANY_TRIGGERS
        except Exception:
            COMPANY_TRIGGERS = {
                "ru": {
                    "legal_entities": ["ООО", "ЗАО", "ОАО", "ПАО", "АО", "ИП", "ФОП"]
                },
                "uk": {"legal_entities": ["ТОВ", "ПАТ", "АТ", "ПрАТ", "ФОП"]},
                "en": {"legal_entities": ["LLC", "Inc", "Ltd", "Corp", "LP", "LLP"]},
            }
        self.legal_forms = {
            lang: set([x.lower() for x in d.get("legal_entities", [])])
            for lang, d in COMPANY_TRIGGERS.items()
        }

    def compute_keys(self, text: str, metadata: Optional[Dict] = None) -> BlockingKeys:
        """
        Extract blocking keys from free-form text and optional metadata.
        Conservative approach: try to not miss plausible keys (high recall).
        """
        metadata = metadata or {}
        keys = BlockingKeys()

        # IDs first: strong keys
        keys.edrpou = self._extract_edrpou(text) or self._norm_digits(
            metadata.get("beneficiary_edrpou")
        )
        keys.tax_id = self._extract_tax_id(text) or self._norm_digits(
            metadata.get("tax_id")
        )

        # Country and DOB
        keys.country_code = self._norm_country(metadata.get("country_code"))
        byear = self._parse_birth_year(metadata)
        keys.birth_year = byear
        keys.birth_decade = (byear // 10 * 10) if byear else None

        # Try company first, else person
        company = self._extract_company(text)
        if company:
            legal, core = company
            keys.legal_form_key = legal
            keys.org_core_stem = core
            return keys

        # Person-like: surname + initial
        first, middle, last = self._extract_name_triplet(text)
        # Prefer last as surname if present
        surname = last or self._fallback_surname(text)
        if surname:
            keys.surname_normalized = self._normalize_token(surname)
            keys.phonetic_surname = self._phonetic_cyrillic_or_latin(surname)
        initial = (first or "").strip()[:1].upper() if first else None
        if initial and surname:
            keys.first_initial_surname = f"{initial}.{self._normalize_token(surname)}"

        return keys

    # ---- Extractors -----------------------------------------------------

    def _extract_edrpou(self, text: str) -> Optional[str]:
        m = re.search(r"\b(\d{8})\b", text)
        return m.group(1) if m else None

    def _extract_tax_id(self, text: str) -> Optional[str]:
        m = re.search(r"\b(\d{10,12})\b", text)
        return m.group(1) if m else None

    def _extract_company(self, text: str) -> Optional[Tuple[str, str]]:
        s = re.sub(r"\s+", " ", text).strip()
        # Look for legal form markers followed by a name
        for lang, forms in self.legal_forms.items():
            for form in sorted(forms, key=len, reverse=True):
                pat = rf'\b{re.escape(form)}[\s\."]+([^\n\r"]{{3,}})'
                m = re.search(pat, s, flags=re.IGNORECASE)
                if m:
                    core = m.group(1)
                    core = re.split(
                        r"\b(догов[оі]р|договор|контракт|№|#|от\s+\d|від\s+\d)",
                        core,
                        maxsplit=1,
                    )[0]
                    core = re.sub(r"\s+", " ", core).strip().strip('"«»“”')
                    if core:
                        return form.lower(), core
        return None

    def _extract_name_triplet(
        self, text: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        # Patterns: First Middle Last | Last First Middle | Initials + Surname
        # Cyrillic
        m = re.search(
            r"\b([А-ЯІЇЄҐ][а-яіїєґ']{2,})\s+([А-ЯІЇЄҐ][а-яіїєґ']{1,})\s+"
            r"([А-ЯІЇЄҐ][а-яіїєґ']{2,})\b",
            text,
        )
        if m:
            return m.group(1), m.group(2), m.group(3)
        m = re.search(
            r"\b([А-ЯІЇЄҐ])\.\s*([А-ЯІЇЄҐ])\.\s*([А-ЯІЇЄҐ][а-яіїєґ']{2,})\b", text
        )
        if m:
            # Expand initials as first/middle unknown
            return m.group(1), None, m.group(3)
        # Latin
        m = re.search(
            r"\b([A-Z][a-z']{2,})\s+([A-Z][a-z']{1,})\s+([A-Z][a-z']{2,})\b", text
        )
        if m:
            return m.group(1), m.group(2), m.group(3)
        m = re.search(r"\b([A-Z])\.\s*([A-Z])\.\s*([A-Z][a-z']{2,})\b", text)
        if m:
            return m.group(1), None, m.group(3)
        return None, None, None

    def _fallback_surname(self, text: str) -> Optional[str]:
        # Heuristic: take the longest capitalized token (Cyrillic/Latin)
        tokens = re.findall(r"\b([A-Z][a-z']{3,}|[А-ЯІЇЄҐ][а-яіїєґ']{3,})\b", text)
        return max(tokens, key=len) if tokens else None

    # ---- Normalization/phonetics ---------------------------------------

    def _normalize_token(self, s: str) -> str:
        s = s.strip().strip("\"'“”«»")
        s = re.sub(r"\s+", " ", s)
        return s

    def _phonetic_cyrillic_or_latin(self, s: str) -> str:
        # Simple Soundex-like for both scripts (very rough, but useful for blocking)
        s = s.lower()
        # Transliterate basic Cyrillic to Latin groups to unify keys
        mapping = {
            "а": "a",
            "б": "b",
            "в": "v",
            "г": "g",
            "ґ": "g",
            "д": "d",
            "е": "e",
            "ё": "e",
            "є": "e",
            "ж": "zh",
            "з": "z",
            "и": "i",
            "і": "i",
            "ї": "i",
            "й": "i",
            "к": "k",
            "л": "l",
            "м": "m",
            "н": "n",
            "о": "o",
            "п": "p",
            "р": "r",
            "с": "s",
            "т": "t",
            "у": "u",
            "ф": "f",
            "х": "h",
            "ц": "c",
            "ч": "ch",
            "ш": "sh",
            "щ": "sh",
            "ы": "y",
            "э": "e",
            "ю": "u",
            "я": "ya",
            "ь": "",
            "ъ": "",
        }
        t = "".join(mapping.get(ch, ch) for ch in s)
        # Collapse groups
        t = re.sub(r"(ch)+", "ch", t)
        t = re.sub(r"(sh)+", "sh", t)
        # Keep first letter, map the rest to digit groups
        first = t[0].upper() if t else ""
        rest = t[1:]
        groups = [
            ("[aeiouy]", "0"),
            ("[bfpv]", "1"),
            ("[cgjkqsxz]", "2"),
            ("[dt]", "3"),
            ("[l]", "4"),
            ("[mn]", "5"),
            ("[r]", "6"),
            ("h", ""),
        ]
        code = ""
        for ch in rest:
            d = ch
            for pat, rep in groups:
                if re.fullmatch(pat, ch):
                    d = rep
                    break
            if d and (not code or code[-1] != d):
                code += d
        return (first + code)[:6]

    def _norm_digits(self, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        m = re.search(r"\d{6,12}", str(v))
        return m.group(0) if m else None

    def _norm_country(self, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        s = str(v).strip().upper()
        return s[:2] if len(s) >= 2 else s

    def _parse_birth_year(self, metadata: Dict) -> Optional[int]:
        dob = (
            metadata.get("dob")
            or metadata.get("birth_date")
            or metadata.get("date_of_birth")
        )
        if not dob:
            return None
        m = re.search(r"(19\d{2}|20\d{2})", str(dob))
        try:
            return int(m.group(1)) if m else None
        except Exception:
            return None

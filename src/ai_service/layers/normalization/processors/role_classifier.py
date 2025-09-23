"""Role classification for normalization pipeline."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from ....utils.logging_config import get_logger
from ....utils.profiling import profile_function, profile_time
from ....utils.cache_utils import lru_cache_with_metrics
from ..morphology.gender_rules import convert_surname_to_nominative

# Import exclusion patterns to prevent classification of garbage as names
try:
    from ....data.dicts.smart_filter_patterns import EXCLUSION_PATTERNS
    _EXCLUSION_PATTERNS = EXCLUSION_PATTERNS
except ImportError:
    _EXCLUSION_PATTERNS = []

try:  # Optional dependency for Russian NER
    from natasha import MorphVocab, NewsEmbedding, NamesExtractor
except ImportError:  # pragma: no cover
    MorphVocab = None  # type: ignore
    NewsEmbedding = None  # type: ignore
    NamesExtractor = None  # type: ignore

# Use lazy import for consistency with other modules
from ....utils.lazy_imports import NAMEPARSER

def get_human_name():
    """Get HumanName class if nameparser is available."""
    if NAMEPARSER is not None:
        return NAMEPARSER.HumanName
    return None

HumanName = get_human_name()


ORG_LEGAL_FORMS: Set[str] = {
    "ооо",
    "зао",
    "оао",
    "пао",
    "ао",
    "ип",
    "чп",
    "фоп",
    "тов",
    "пп",
    "кс",
    "ooo",
    "llc",
    "ltd",
    "inc",
    "corp",
    "co",
    "gmbh",
    "srl",
    "spa",
    "s.a.",
    "s.r.l.",
    "s.p.a.",
    "bv",
    "nv",
    "oy",
    "ab",
    "as",
    "sa",
    "ag",
}

ORG_TOKEN_RE = re.compile(r"^(?:[A-ZА-ЯЁІЇЄҐ0-9][A-ZА-ЯЁІЇЄҐ0-9\-&\.']{1,39})$", re.U)

_CONTEXT_WORDS: Set[str] = {
    "и",
    "та",
    "and",
    "or",
    "но",
    "але",
    "but",
    "з",
    "в",
    "у",
    "по",
    "на",
    "до",
    "from",
    "of",
    "for",
    "the",
    "a",
    "an",
}

_DIM_SUFFIX_MAP = {
    "ru": [
        "ов",
        "ев",
        "ин",
        "ын",
        "ова",
        "ева",
        "ина",
        "ына",
        "ой",   # Добавляем падежные формы
        "ей",   # Добавляем падежные формы
        "ову",  # Дательный падеж: Петрову, Иванову
        "еву",  # Дательный падеж: Алексееву
        "ину",  # Дательный падеж: Смирнину
        "ыну",  # Дательный падеж:
        "ским", # Дательный падеж: Московскому -> Московскому
        "цким", # Дательный падеж:
        "ому",  # Дательный падеж для прилагательных фамилий
        "ему",  # Дательный падеж для прилагательных фамилий
        "ский",
        "ская",
        "цкий",
        "цкая",
        "ян",
        "дзе",
        "швили",
    ],
    "uk": [
        "енко",
        "енк",
        # Russian surname endings that appear in Ukrainian contexts
        "ов", "ев", "ин", "ын",
        "ова", "ева", "ина", "ына",
        "ський", "ська", "цький", "цька",
        "ко",
        "ський",
        "ська",
        "цький",
        "цька",
        "ук",
        "юк",
        "чук",
        "ян",
        "дзе",
        "швили",
        "ою",   # Добавляем падежные формы
        "ої",   # Добавляем падежные формы
    ],
}

_PATRONYMIC_SUFFIXES = {
    "ru": [
        # Мужские отчества
        "ович", "евич", "йович", "ич",
        # Женские отчества - все падежи
        "овна", "евна", "ична",        # Именительный падеж: Петровна, Сергеевна, Никитична
        "овны", "евны", "ичны",        # Родительный падеж: (у) Петровны, (у) Сергеевны
        "овне", "евне", "ичне",        # Дательный падеж: (к) Петровне, (к) Сергеевне
        "овну", "евну", "ичну",        # Винительный падеж: (на) Петровну, (на) Сергеевну
        "овной", "евной", "ичной",     # Творительный падеж: (с) Петровной, (с) Сергеевной
        "овнё", "евнё", "ичнё",        # Творительный падеж (альт): (с) Петровнё
    ],
    "uk": [
        # Мужские отчества
        "ович", "евич", "йович", "ич",
        # Женские отчества - все падежи
        "івна", "ївна", "овна", "евна", "ична",           # Називний відмінок
        "івни", "ївни", "овни", "евни", "ічни",           # Родовий відмінок
        "івні", "ївні", "овні", "евні", "ічні",           # Давальний відмінок
        "івну", "ївну", "овну", "евну", "ічну",           # Знахідний відмінок
        "івною", "ївною", "овною", "евною", "ічною",      # Орудний відмінок
    ]
}


class RoleClassifier:
    """Determines token roles (given/surname/patronymic/org/initial/unknown)."""

    def __init__(
        self,
        name_dictionaries: Optional[Dict[str, Set[str]]] = None,
        diminutive_maps: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> None:
        self.logger = get_logger(__name__)
        self._initial_pattern = re.compile(r"^[A-Za-zА-Яа-яІЇЄҐіїєґ]\.(?:[A-Za-zА-Яа-яІЇЄҐіїєґ]\.)*$")
        self._context_words = _CONTEXT_WORDS

        self.given_names: Dict[str, Set[str]] = {"ru": set(), "uk": set(), "en": set()}
        self.surnames: Dict[str, Set[str]] = {"ru": set(), "uk": set(), "en": set()}
        self.diminutives: Dict[str, Set[str]] = {"ru": set(), "uk": set(), "en": set()}
        if name_dictionaries:
            self._ingest_name_dictionaries(name_dictionaries)

        self.dim2full_maps = diminutive_maps or {}

        self._ru_names_extractor = None
        if NamesExtractor and MorphVocab and NewsEmbedding:
            try:
                self._ru_names_extractor = NamesExtractor(MorphVocab(), NewsEmbedding())
            except Exception as exc:  # pragma: no cover
                self.logger.debug("Failed to initialise Natasha NamesExtractor: %s", exc)
                self._ru_names_extractor = None

        self.logger.info("RoleClassifier initialised (NER=%s)", bool(self._ru_names_extractor))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @profile_function("role_classifier.tag_tokens")
    def tag_tokens(
        self,
        tokens: List[str],
        language: str = "ru",
        quoted_segments: Optional[List[str]] = None,
    ) -> Tuple[List[Tuple[str, str]], List[str], List[str]]:
        """Classify tokens, mirroring the legacy _tag_roles flow.

        Returns tagged tokens with roles, a list of trace messages, and the
        collection of organisation strings detected (quoted phrases or uppercase
        candidates).
        """
        traces: List[str] = []
        tagged: List[Tuple[str, str]] = []
        organizations: List[str] = []
        seen_organizations: Set[str] = set()

        quoted_word_map: Dict[str, str] = {}
        if quoted_segments:
            for phrase in quoted_segments:
                if not phrase:
                    continue
                for word in phrase.split():
                    cleaned = word.strip()
                    if cleaned:
                        quoted_word_map[cleaned.lower()] = phrase

        ner_roles = self._apply_ner(tokens, language)

        for index, token in enumerate(tokens):
            base = token
            cf = base.casefold()

            quoted_phrase = quoted_word_map.get(cf)

            if ner_roles.get(index):
                role = ner_roles[index]
                tagged.append((base, role))
                traces.append(f"NER assigned '{base}' -> {role}")
                if role == "org":
                    self._register_org(organizations, seen_organizations, quoted_phrase or base)
                continue

            if self._is_legal_form(cf):
                tagged.append((base, "unknown"))
                traces.append(f"Legal form detected for '{base}'")
                continue

            prelim_org = False
            if quoted_phrase:
                prelim_org = True
            elif self._looks_like_org(base) and cf not in ORG_LEGAL_FORMS:
                prelim_org = True

            if prelim_org and not quoted_phrase and self._is_personal_candidate(base, language):
                prelim_org = False

            if self._is_initial(base):
                for initial in self._split_multi_initial(base):
                    tagged.append((initial, "initial"))
                    traces.append(f"Initial token '{initial}' from '{base}'")
                continue

            if prelim_org and not self._is_personal_candidate(base, language):
                tagged.append((base, "org"))
                traces.append(f"Organisation candidate '{base}'")
                self._register_org(organizations, seen_organizations, quoted_phrase or base)
                continue

            if language in ("ru", "uk"):
                surname_role = self._classify_surname_by_suffix(base, language)
                if surname_role != "unknown":
                    tagged.append((base, surname_role))
                    traces.append(f"Surname by suffix for '{base}'")
                    continue

                patronymic_role = self._classify_patronymic_role(base, language)
                if patronymic_role != "unknown":
                    tagged.append((base, patronymic_role))
                    traces.append(f"Patronymic detected for '{base}'")
                    continue

                full_name = self._normalize_diminutive_to_full(base, language)
                if full_name:
                    role = self._classify_personal_role(full_name, language)
                    if role != "unknown":
                        tagged.append((base, role))
                        traces.append(f"Diminutive '{base}' -> '{full_name}' as {role}")
                        continue

            role = self._classify_personal_role(base, language)
            if role != "unknown":
                tagged.append((base, role))
                traces.append(f"Personal heuristics '{base}' -> {role}")
                continue

            if prelim_org:
                tagged.append((base, "org"))
                traces.append(f"Fallback organisation '{base}'")
                self._register_org(organizations, seen_organizations, quoted_phrase or base)
                continue

            # Handle single characters and numbers - they should be preserved
            if len(base) == 1 and (base.isdigit() or base.isalpha()):
                tagged.append((base, "other"))
                traces.append(f"Single character/number preserved: '{base}'")
            else:
                tagged.append((base, "unknown"))

        person_indices = [
            i
            for i, (token, role) in enumerate(tagged)
            if role in {"unknown", "given", "surname", "patronymic", "initial", "other"}
            and not self._is_context_word(token)
        ]

        tagged = self._apply_positional_heuristics(tagged, language, person_indices)
        tagged = self._filter_isolated_initials(tagged)

        return tagged, traces, organizations

    # ------------------------------------------------------------------
    # Helper ingestion/normalisation methods
    # ------------------------------------------------------------------

    def _ingest_name_dictionaries(self, dictionaries: Dict[str, Set[str]]) -> None:
        for key, values in dictionaries.items():
            if not values:
                continue
            if key in {"ru", "uk", "en"}:
                self.given_names[key].update({v.lower() for v in values})
                continue
            parts = key.split("_")
            if len(parts) < 2:
                continue
            
            # Handle both formats: "given_names_ru" and "ru_given"
            if len(parts) == 3 and parts[1] == "names":
                # Format: "given_names_ru"
                kind, _, lang = parts
            elif len(parts) == 2:
                # Format: "ru_given" or "given_names_ru" (fallback)
                if parts[0] in {"ru", "uk", "en"}:
                    lang, kind = parts
                else:
                    continue
            else:
                continue
                
            norm_values = {v.lower() for v in values}
            if lang not in self.given_names:
                self.given_names[lang] = set()
                self.surnames[lang] = set()
                self.diminutives[lang] = set()
            if kind.startswith("given"):
                self.given_names[lang].update(norm_values)
            elif kind.startswith("surname"):
                self.surnames[lang].update(norm_values)
            elif kind.startswith("diminutive"):
                self.diminutives[lang].update(norm_values)

    # ------------------------------------------------------------------
    # Low-level classification helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_legal_form(token: str) -> bool:
        return token.lower() in ORG_LEGAL_FORMS

    @staticmethod
    def _looks_like_org(token: str) -> bool:
        if not token:
            return False
        if token.isdigit():
            return False
        if ORG_TOKEN_RE.match(token.upper()):
            return True
        if len(token) >= 3 and token.isupper():
            return True
        return False

    def _is_personal_candidate(self, token: str, language: str) -> bool:
        role = self._classify_personal_role(token, language)
        if role in {"given", "surname", "patronymic"}:
            return True
        if language in {"ru", "uk"}:
            lowered = token.lower()
            case_suffixes = (
                "у",
                "ю",
                "ой",
                "ою",
                "ем",
                "ом",
                "ым",
                "им",
                "еву",
                "ову",
                "ами",
                "ями",
                "ых",
                "их",
            )
            if any(lowered.endswith(suffix) for suffix in case_suffixes):
                return True
        return False

    @lru_cache_with_metrics(maxsize=4096, cache_name="classify_personal_role")
    def _classify_personal_role(self, token: str, language: str, policy_flags: Optional[Dict[str, Any]] = None) -> str:
        if not token:
            return "unknown"

        # Check exclusion patterns FIRST - prevent garbage from being classified as names
        token_lower = token.lower()
        for pattern in _EXCLUSION_PATTERNS:
            if re.match(pattern, token_lower, re.IGNORECASE):
                return "unknown"  # Mark as unknown instead of given/surname

        if self._is_initial(token):
            return "initial"

        lower = token.lower()
        lang = language if language in self.given_names else "ru"

        # For English, check if this looks like an Irish/Scottish surname
        if language == "en" and self._is_irish_scottish_surname(token):
            return "surname"

        if lower in self.given_names.get(lang, set()):
            return "given"
        if lower in self.surnames.get(lang, set()):
            return "surname"
        if lower in self.diminutives.get(lang, set()):
            return "given"

        if language in ("ru", "uk"):
            # Check patronymic FIRST - they have priority over surname suffixes
            if self._classify_patronymic_role(token, language) == "patronymic":
                return "patronymic"
            if self._classify_surname_by_suffix(token, language) == "surname":
                return "surname"

        # Check for mixed-script personal names (e.g., O'Брайен-Смит)
        # These often contain apostrophes and hyphens but should be considered personal names
        if self._is_mixed_script_personal_name(token):
            return "surname"  # Mixed-script names are typically surnames

        # Check for pure English apostrophe names (O'Brien, D'Angelo) in Cyrillic contexts
        # These should be treated as surnames when in ru/uk contexts
        if language in ("ru", "uk") and self._is_english_apostrophe_name(token):
            return "surname"

        # Check for names with apostrophes (both Cyrillic and Latin contexts)
        # Examples: Д'яченко, O'Connor
        if token[0].isupper() and not token.isupper():
            # Allow letters, apostrophes, and hyphens in names
            name_chars = set(token.replace("'", "").replace("-", ""))
            if name_chars and all(c.isalpha() for c in name_chars):
                # For Russian/Ukrainian context, treat apostrophe names as surnames
                if language in ("ru", "uk") and "'" in token:
                    return "surname"
                # Otherwise, treat as given name
                return "given"

        return "unknown"

    def _is_mixed_script_personal_name(self, token: str) -> bool:
        """Check if token is a mixed-script personal name (e.g., O'Брайен-Смит)."""
        if not token or len(token) < 3:
            return False

        # Must start with uppercase letter
        if not token[0].isupper():
            return False

        # Check for mix of Latin and Cyrillic characters (including Ukrainian-specific)
        has_latin = any(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz' for c in token)
        has_cyrillic = any(c in 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюяІіЄєЇїҐґ' for c in token)

        if not (has_latin and has_cyrillic):
            return False

        # Should contain mostly letters with allowed special characters (apostrophe, hyphen)
        allowed_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
                           'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюяІіЄєЇїҐґ'
                           '\'-')

        for char in token:
            if char not in allowed_chars:
                return False

        # Additional heuristics: typical patterns for mixed-script names
        # Often start with Latin prefix like O', Mc, etc.
        latin_prefixes = ["O'", "Mc", "Mac", "De", "Di", "La", "Le", "Van", "Von"]
        for prefix in latin_prefixes:
            if token.startswith(prefix):
                return True

        return True

    def _is_english_apostrophe_name(self, token: str) -> bool:
        """Check if token is an English name with apostrophe (e.g., O'Brien, D'Angelo)."""
        if not token or len(token) < 3:
            return False

        # Must start with uppercase letter
        if not token[0].isupper():
            return False

        # Must contain apostrophe
        if "'" not in token:
            return False

        # Should contain only Latin letters, apostrophes, and optionally hyphens
        allowed_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz\'-')
        for char in token:
            if char not in allowed_chars:
                return False

        # Should be all Latin characters (no Cyrillic)
        has_cyrillic = any(c in 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюяІіЄєЇїҐґ' for c in token)
        if has_cyrillic:
            return False

        # Common Irish/Scottish prefixes with apostrophe
        apostrophe_prefixes = ["O'", "D'", "Mc'", "Mac'"]
        for prefix in apostrophe_prefixes:
            if token.startswith(prefix):
                return True

        # Generic pattern: starts with letter(s), has apostrophe, continues with letters
        if token.count("'") == 1:
            parts = token.split("'")
            if len(parts) == 2 and all(part.isalpha() for part in parts):
                return True

        return False

    def _classify_surname_by_suffix(self, token: str, language: str) -> str:
        token_lower = token.lower()
        suffixes = _DIM_SUFFIX_MAP.get(language, [])
        for suffix in suffixes:
            if token_lower.endswith(suffix):
                return "surname"
        return "unknown"

    def _classify_patronymic_role(self, token: str, language: str) -> str:
        token_lower = token.lower()
        for suffix in _PATRONYMIC_SUFFIXES.get(language, []):
            if token_lower.endswith(suffix):
                return "patronymic"
        return "unknown"

    def _normalize_diminutive_to_full(self, token: str, language: str) -> Optional[str]:
        lang_map = self.dim2full_maps.get(language, {})
        base = token.lower()
        if base in lang_map:
            return lang_map[base]
        return None

    # ------------------------------------------------------------------
    # Positional heuristics & cleanup
    # ------------------------------------------------------------------

    def _apply_positional_heuristics(
        self,
        tagged: List[Tuple[str, str]],
        language: str,
        person_indices: Optional[List[int]] = None,
    ) -> List[Tuple[str, str]]:
        if len(tagged) < 2:
            return tagged
        if person_indices is None:
            person_indices = list(range(len(tagged)))

        improved: List[Tuple[str, str]] = []
        for idx, (token, role) in enumerate(tagged):
            if idx not in person_indices:
                improved.append((token, role))
                continue

            new_role = role
            lower = token.lower()
            lang = language if language in self.given_names else "ru"

            if idx == 0 and role == "unknown":
                if lower in self.given_names.get(lang, set()) or (token.isalpha() and token[0].isupper() and not token.isupper()):
                    new_role = "given"
            elif idx == 1 and len(tagged) == 3 and role == "unknown":
                if self._classify_patronymic_role(token, language) == "patronymic":
                    new_role = "patronymic"
            elif role == "unknown" and idx > 0 and tagged[idx - 1][1] == "given":
                new_role = "surname"
            elif role == "given" and idx > 0 and tagged[idx - 1][1] == "given":
                # For English, assume second given name in sequence is a surname
                # For other languages, use surname candidate check
                # Also apply this for ASCII names in Cyrillic contexts (mixed-script support)
                if (language == "en" or
                    self._looks_like_surname_candidate(token, language) or
                    (token.isascii() and language in ("ru", "uk"))):
                    new_role = "surname"
            elif role == "given" and idx > 0 and tagged[idx - 1][1] == "initial":
                # Handle pattern: initial + initial + given -> initial + initial + surname
                if language == "en" or self._looks_like_surname_candidate(token, language):
                    new_role = "surname"

            improved.append((token, new_role))

        return improved

    def _filter_isolated_initials(self, tagged: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        # Don't filter isolated initials to maintain idempotency
        # All initials should be preserved regardless of context
        return tagged

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def _is_initial(self, token: str) -> bool:
        if self._initial_pattern.match(token):
            return True
        # Handle initials with multiple dots (e.g., "J.." -> "J.")
        if re.match(r'^[A-Za-zА-Яа-яІЇЄҐіїєґ]\.+$', token):
            return True
        if len(token) == 1 and token.isalpha() and token.lower() not in self._context_words:
            return True
        return False

    def _split_multi_initial(self, token: str) -> List[str]:
        if self._initial_pattern.match(token):
            return [f"{part}." for part in token.split(".") if part]
        # Handle initials with multiple dots (e.g., "J.." -> "J.")
        if re.match(r'^[A-Za-zА-Яа-яІЇЄҐіїєґ]\.+$', token):
            # Extract the letter and normalize to single dot
            letter = token[0]
            return [f"{letter}."]
        return [token]

    def _is_context_word(self, token: str) -> bool:
        return token.lower() in self._context_words

    def _is_irish_scottish_surname(self, token: str) -> bool:
        """Check if token looks like an Irish or Scottish surname with apostrophe."""
        if not token or len(token) < 3:
            return False

        # Irish surnames with apostrophes (O'Sullivan, O'Connor, etc.)
        if token.startswith("O'") and len(token) > 2:
            return True

        # Scottish surnames with apostrophes (D'Angelo, D'Artagnan, etc.)
        if token.startswith("D'") and len(token) > 2:
            return True

        # Mac/Mc surnames (MacDonald, McConnor, etc.)
        if token.lower().startswith(("mac", "mc")) and len(token) > 3:
            return True

        return False

    def _register_org(
        self,
        organizations: List[str],
        seen: Set[str],
        value: Optional[str],
    ) -> None:
        if not value:
            return
        normalized = value.strip()
        if not normalized:
            return
        key = normalized.lower()
        if key in seen:
            return
        organizations.append(normalized)
        seen.add(key)

    def _looks_like_surname_candidate(self, token: str, language: str) -> bool:
        converted = convert_surname_to_nominative(token, language)
        if converted.lower() != token.lower():
            return True

        lower = token.lower()
        if language == "uk" and lower.endswith("у"):
            candidate = lower[:-1] + "о"
            surname_suffixes = (
                "ко",
                "енко",
                "ько",
                "сько",
                "цько",
                "чук",
                "юк",
                "ук",
                "як",
                "ік",
            )
            if any(candidate.endswith(suffix) for suffix in surname_suffixes):
                return True

        return False

    # ------------------------------------------------------------------
    # Optional NER support
    # ------------------------------------------------------------------

    def _apply_ner(self, tokens: List[str], language: str) -> Dict[int, str]:
        roles: Dict[int, str] = {}
        if not tokens:
            return roles

        if language in {"ru", "mixed"} and self._ru_names_extractor:
            text = " ".join(tokens)
            try:
                matches = self._ru_names_extractor(text)
                for match in matches:
                    fact = match.fact.as_dict()
                    for part, role in (("first", "given"), ("last", "surname"), ("middle", "patronymic")):
                        value = fact.get(part)
                        if not value:
                            continue
                        for idx, token in enumerate(tokens):
                            if token.lower() == value.lower():
                                roles.setdefault(idx, role)
            except Exception as exc:  # pragma: no cover
                self.logger.debug("Natasha extraction failed: %s", exc)
                return {}

        if language == "en" and HumanName:
            text = " ".join(tokens)
            try:
                parsed = HumanName(text)
                mapping = [
                    (parsed.first, "given"),
                    (parsed.middle, "given"),
                    (parsed.last, "surname"),
                ]
                for value, role in mapping:
                    if not value:
                        continue
                    for idx, token in enumerate(tokens):
                        if token.lower() == value.lower():
                            roles.setdefault(idx, role)
            except Exception:  # pragma: no cover
                pass

        return roles

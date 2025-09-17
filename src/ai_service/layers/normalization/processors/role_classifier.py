"""Role classification for normalization pipeline."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from ....utils.logging_config import get_logger
from ....utils.profiling import profile_function, profile_time
from ....utils.cache_utils import lru_cache_with_metrics
from ..morphology.gender_rules import convert_surname_to_nominative

try:  # Optional dependency for Russian NER
    from natasha import MorphVocab, NewsEmbedding, NamesExtractor
except ImportError:  # pragma: no cover
    MorphVocab = None  # type: ignore
    NewsEmbedding = None  # type: ignore
    NamesExtractor = None  # type: ignore

try:  # Optional dependency for English name parsing
    from nameparser import HumanName
except ImportError:  # pragma: no cover
    HumanName = None  # type: ignore


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
    "ru": ["ович", "евич", "йович", "ич", "овна", "евна", "ична", "овны", "евны", "ичны"],  # Добавляем падежные формы
    "uk": ["ович", "евич", "йович", "ич", "івна", "ївна", "овна", "евна", "ична", "івни", "ївни", "овни", "евни", "ічни"],  # Добавляем падежные формы
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

            tagged.append((base, "unknown"))

        person_indices = [
            i
            for i, (token, role) in enumerate(tagged)
            if role in {"unknown", "given", "surname", "patronymic", "initial"}
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
            lang, kind = parts[0], parts[1]
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

        if self._is_initial(token):
            return "initial"

        lower = token.lower()
        lang = language if language in self.given_names else "ru"

        if lower in self.given_names.get(lang, set()):
            return "given"
        if lower in self.surnames.get(lang, set()):
            return "surname"
        if lower in self.diminutives.get(lang, set()):
            return "given"

        if language in ("ru", "uk"):
            if self._classify_patronymic_role(token, language) == "patronymic":
                return "patronymic"
            if self._classify_surname_by_suffix(token, language) == "surname":
                return "surname"

        if token[0].isupper() and token.isalpha() and not token.isupper():
            return "given"

        return "unknown"

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
                if self._looks_like_surname_candidate(token, language):
                    new_role = "surname"

            improved.append((token, new_role))

        return improved

    def _filter_isolated_initials(self, tagged: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        if len(tagged) <= 1:
            return tagged

        filtered: List[Tuple[str, str]] = []
        for idx, (token, role) in enumerate(tagged):
            if role != "initial":
                filtered.append((token, role))
                continue

            neighbours = []
            if idx > 0:
                neighbours.append(tagged[idx - 1][1])
            if idx < len(tagged) - 1:
                neighbours.append(tagged[idx + 1][1])

            if any(nbr in {"given", "surname", "patronymic", "initial"} for nbr in neighbours):
                filtered.append((token, role))
        return filtered

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def _is_initial(self, token: str) -> bool:
        if self._initial_pattern.match(token):
            return True
        if len(token) == 1 and token.isalpha() and token.lower() not in self._context_words:
            return True
        return False

    def _split_multi_initial(self, token: str) -> List[str]:
        if self._initial_pattern.match(token):
            return [f"{part}." for part in token.split(".") if part]
        return [token]

    def _is_context_word(self, token: str) -> bool:
        return token.lower() in self._context_words

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

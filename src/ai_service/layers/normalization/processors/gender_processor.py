"""Gender processing for name normalization.
Handles gender inference and surname gender adjustment.
"""

import re
from typing import Dict, List, Tuple, Optional, Set

from ....utils.logging_config import get_logger
from ..morphology.gender_rules import (
    convert_given_name_to_nominative,
    convert_patronymic_to_nominative,
    convert_surname_to_nominative,
    get_female_given_names,
    is_invariable_surname,
    looks_like_feminine_ru,
    looks_like_feminine_uk,
)


class GenderProcessor:
    """Handles gender inference and gender-specific name processing."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self._feminine_patterns = self._compile_feminine_patterns()
        self._masculine_patterns = self._compile_masculine_patterns()
        self._female_name_sets = {
            'ru': get_female_given_names('ru') or set(),
            'uk': get_female_given_names('uk') or set(),
        }

    def infer_gender(
        self,
        tokens: List[str],
        roles: List[str],
        language: str = 'ru'
    ) -> Tuple[Optional[str], float, List[str]]:
        """
        Infer gender from name tokens and their roles.

        Args:
            tokens: List of name tokens
            roles: List of corresponding roles
            language: Language code

        Returns:
            Tuple of (gender, confidence, evidence)
        """
        evidence = []
        gender_scores = {'masc': 0.0, 'femn': 0.0}

        nominative_tokens = [
            convert_given_name_to_nominative(token, language) if role == 'given'
            else convert_patronymic_to_nominative(token, language) if role == 'patronymic'
            else convert_surname_to_nominative(token, language) if role == 'surname'
            else token
            for token, role in zip(tokens, roles)
        ]

        for token, base_token, role in zip(tokens, nominative_tokens, roles):
            token_gender, confidence, token_evidence = self._infer_token_gender(
                base_token, role, language
            )

            if token_gender:
                gender_scores[token_gender] += confidence
                evidence.extend(token_evidence)

        # Determine final gender
        if gender_scores['femn'] > gender_scores['masc']:
            confidence = gender_scores['femn'] / (gender_scores['femn'] + gender_scores['masc'])
            return 'femn', confidence, evidence
        elif gender_scores['masc'] > gender_scores['femn']:
            confidence = gender_scores['masc'] / (gender_scores['femn'] + gender_scores['masc'])
            return 'masc', confidence, evidence
        else:
            return None, 0.0, evidence

    def _infer_token_gender(
        self,
        token: str,
        role: str,
        language: str
    ) -> Tuple[Optional[str], float, List[str]]:
        """Infer gender from a single token."""
        evidence = []

        if role == 'surname':
            return self._infer_surname_gender(token, language)
        if role == 'patronymic':
            return self._infer_patronymic_gender(token, language)
        if role == 'given':
            return self._infer_given_name_gender(token, language)

        return None, 0.0, evidence

    def _infer_surname_gender(
        self,
        surname: str,
        language: str
    ) -> Tuple[Optional[str], float, List[str]]:
        """Infer gender from surname patterns."""
        evidence: List[str] = []
        surname_lower = surname.lower()

        if language == 'ru':
            is_feminine, fem_form = looks_like_feminine_ru(surname)
            if is_feminine:
                evidence.append("Feminine surname indicators (ru)")
                return 'femn', 0.9, evidence
        elif language == 'uk':
            is_feminine, fem_form = looks_like_feminine_uk(surname)
            if is_feminine:
                evidence.append("Feminine surname indicators (uk)")
                return 'femn', 0.9, evidence

        for pattern_name, pattern in self._feminine_patterns.get(language, {}).items():
            if pattern.search(surname_lower):
                evidence.append(f"Feminine surname pattern: {pattern_name}")
                return 'femn', 0.8, evidence

        for pattern_name, pattern in self._masculine_patterns.get(language, {}).items():
            if pattern.search(surname_lower):
                evidence.append(f"Masculine surname pattern: {pattern_name}")
                return 'masc', 0.6, evidence

        return None, 0.0, evidence

    def _infer_patronymic_gender(
        self,
        patronymic: str,
        language: str
    ) -> Tuple[Optional[str], float, List[str]]:
        """Infer gender from patronymic endings."""
        evidence = []
        pat_lower = patronymic.lower()

        if language == 'ru':
            if re.search(r'(овна|евна|ична)$', pat_lower):
                evidence.append("Feminine patronymic ending")
                return 'femn', 0.95, evidence
            elif re.search(r'(ович|евич|ич)$', pat_lower):
                evidence.append("Masculine patronymic ending")
                return 'masc', 0.95, evidence
        elif language == 'uk':
            if re.search(r'(івна|овна|ївна)$', pat_lower):
                evidence.append("Feminine Ukrainian patronymic ending")
                return 'femn', 0.95, evidence
            elif re.search(r'(ович|евич|іч|йович)$', pat_lower):
                evidence.append("Masculine Ukrainian patronymic ending")
                return 'masc', 0.95, evidence

        return None, 0.0, evidence

    def _infer_given_name_gender(
        self,
        given_name: str,
        language: str
    ) -> Tuple[Optional[str], float, List[str]]:
        """Infer gender from given name patterns."""
        evidence: List[str] = []
        name_lower = given_name.lower()
        female_names = self._female_name_sets.get(language, set())

        if female_names and name_lower in female_names:
            evidence.append("Known feminine given name")
            return 'femn', 0.95, evidence

        # Common feminine endings
        fem_endings = {
            'ru': ['а', 'я', 'ия', 'ья'],
            'uk': ['а', 'я', 'на', 'та']
        }

        # Common masculine endings
        masc_endings = {
            'ru': ['ий', 'ей', 'ён', 'ь'],
            'uk': ['ій', 'ей', 'о', 'ь']
        }

        lang_fem = fem_endings.get(language, [])
        lang_masc = masc_endings.get(language, [])

        for ending in lang_fem:
            if name_lower.endswith(ending):
                evidence.append(f"Feminine given name ending: -{ending}")
                return 'femn', 0.7, evidence

        for ending in lang_masc:
            if name_lower.endswith(ending):
                evidence.append(f"Masculine given name ending: -{ending}")
                return 'masc', 0.7, evidence

        return None, 0.0, evidence

    def adjust_surname_gender(
        self,
        surname: str,
        target_gender: str,
        language: str = 'ru'
    ) -> Tuple[str, bool, List[str]]:
        """
        Adjust surname to match target gender.

        Args:
            surname: Original surname
            target_gender: Target gender (masc/femn)
            language: Language code

        Returns:
            Tuple of (adjusted_surname, was_changed, trace)
        """
        trace = []

        if not surname or target_gender not in {'masc', 'femn'}:
            trace.append("Invalid input for gender adjustment")
            return surname, False, trace

        if is_invariable_surname(surname):
            trace.append("Surname is invariable; no adjustment")
            return surname, False, trace

        current_gender, confidence, gender_evidence = self._infer_surname_gender(surname, language)
        trace.extend(gender_evidence)

        if current_gender == target_gender:
            trace.append(f"Surname already matches target gender: {target_gender}")
            return surname, False, trace

        # Attempt gender conversion
        converted = self._convert_surname_gender(surname, target_gender, language)
        if converted != surname:
            trace.append(f"Converted surname gender: '{surname}' -> '{converted}'")
            return converted, True, trace

        trace.append("No gender conversion pattern matched")
        return surname, False, trace

    def _convert_surname_gender(
        self,
        surname: str,
        target_gender: str,
        language: str
    ) -> str:
        """Convert surname to target gender using pattern rules."""
        if language == 'ru':
            return self._convert_russian_surname_gender(surname, target_gender)
        if language == 'uk':
            return self._convert_ukrainian_surname_gender(surname, target_gender)
        return surname

    def _convert_russian_surname_gender(self, surname: str, target_gender: str) -> str:
        """Convert Russian surname gender."""
        base = convert_surname_to_nominative(surname, 'ru')
        base_title = self._title_case(base) if base else surname

        if target_gender == 'femn':
            is_feminine, fem_form = looks_like_feminine_ru(surname)
            if is_feminine and fem_form:
                return self._title_case(fem_form)
            is_feminine, fem_form = looks_like_feminine_ru(base_title)
            if is_feminine and fem_form:
                return self._title_case(fem_form)

            for suffix, replacement in (
                ('ов', 'ова'),
                ('ев', 'ева'),
                ('ин', 'ина'),
                ('ын', 'ына'),
                ('ский', 'ская'),
                ('цкий', 'цкая'),
            ):
                if base_title.endswith(suffix):
                    return base_title[:-len(suffix)] + replacement
            return surname

        lower = surname.lower()
        for suffix, replacement in (
            ('ова', 'ов'),
            ('ева', 'ев'),
            ('ина', 'ин'),
            ('ская', 'ский'),
            ('цкая', 'цкий'),
        ):
            if lower.endswith(suffix):
                trimmed = surname[:-len(suffix)] + replacement
                return self._title_case(trimmed)

        masculine = convert_surname_to_nominative(surname, 'ru')
        if masculine and masculine.lower() != lower:
            return self._title_case(masculine)
        return surname

    def _convert_ukrainian_surname_gender(self, surname: str, target_gender: str) -> str:
        """Convert Ukrainian surname gender."""
        base = convert_surname_to_nominative(surname, 'uk')
        base_title = self._title_case(base) if base else surname

        if target_gender == 'femn':
            is_feminine, fem_form = looks_like_feminine_uk(surname)
            if is_feminine and fem_form:
                return self._title_case(fem_form)
            is_feminine, fem_form = looks_like_feminine_uk(base_title)
            if is_feminine and fem_form:
                return self._title_case(fem_form)

            for suffix, replacement in (
                ('ський', 'ська'),
                ('цький', 'цька'),
                ('ий', 'а'),
            ):
                if base_title.endswith(suffix):
                    return base_title[:-len(suffix)] + replacement
            return surname

        lower = surname.lower()
        for suffix, replacement in (
            ('ська', 'ський'),
            ('цька', 'цький'),
        ):
            if lower.endswith(suffix):
                trimmed = surname[:-len(suffix)] + replacement
                return self._title_case(trimmed)

        masculine = convert_surname_to_nominative(surname, 'uk')
        if masculine and masculine.lower() != lower:
            return self._title_case(masculine)
        return surname

    def _title_case(self, token: str) -> str:
        if not token:
            return token
        return token[0].upper() + token[1:].lower()

    def _compile_feminine_patterns(self) -> Dict[str, Dict[str, re.Pattern]]:
        """Compile feminine surname patterns."""
        return {
            'ru': {
                'adjective_fem': re.compile(r'(ская|цкая|ная)$'),
                'possessive_fem': re.compile(r'(ова|ева|ина|ына)$'),
            },
            'uk': {
                'adjective_fem': re.compile(r'(ська|цька)$'),
                'possessive_fem': re.compile(r'(ова|ева|іна)$'),
            }
        }

    def _compile_masculine_patterns(self) -> Dict[str, Dict[str, re.Pattern]]:
        """Compile masculine surname patterns."""
        return {
            'ru': {
                'adjective_masc': re.compile(r'(ский|цкий|ный)$'),
                'possessive_masc': re.compile(r'(ов|ев|ин|ын)$'),
            },
            'uk': {
                'adjective_masc': re.compile(r'(ський|цький)$'),
                'possessive_masc': re.compile(r'(енко|ук|юк|чук)$'),  # These are unisex in Ukrainian
            }
        }

"""
Role classification for personal name tokens.
Extracted from NormalizationService to handle the complex 581-line _classify_personal_role method.
"""

import re
from typing import List, Dict, Set, Optional, Tuple
from ....utils.logging_config import get_logger


class RoleClassifier:
    """Handles role classification for name tokens."""

    def __init__(self, name_dictionaries: Dict[str, Set[str]] = None):
        self.logger = get_logger(__name__)
        self.name_dicts = name_dictionaries or {}

        # Precompile common patterns
        self._initial_pattern = re.compile(r'^[A-ZА-ЯЁІ][.]?$', re.IGNORECASE)
        self._patronymic_patterns = self._compile_patronymic_patterns()
        self._surname_patterns = self._compile_surname_patterns()

    def classify_personal_role(
        self,
        token: str,
        position: int,
        total_tokens: int,
        language: str = 'ru',
        context_tokens: List[str] = None
    ) -> Tuple[str, float, List[str]]:
        """
        Classify the role of a personal name token.

        Args:
            token: Token to classify
            position: Position in token sequence
            total_tokens: Total number of tokens
            language: Language context
            context_tokens: Surrounding tokens for context

        Returns:
            Tuple of (role, confidence, evidence)
        """
        if not token:
            return 'unknown', 0.0, ['Empty token']

        context_tokens = context_tokens or []
        evidence = []

        # Step 1: Check for initials
        role, confidence, initial_evidence = self._check_initial(token)
        if role == 'initial':
            return role, confidence, initial_evidence

        # Step 2: Check patronymic patterns
        role, confidence, patronymic_evidence = self._check_patronymic(token, language)
        if role == 'patronymic':
            return role, confidence, patronymic_evidence

        # Step 3: Check against name dictionaries
        role, confidence, dict_evidence = self._check_name_dictionaries(token, language)
        if confidence > 0.7:  # High confidence from dictionary
            return role, confidence, dict_evidence

        # Step 4: Check surname patterns
        role, confidence, surname_evidence = self._check_surname_patterns(token, language)
        if confidence > 0.6:
            return role, confidence, surname_evidence

        # Step 5: Positional heuristics
        role, confidence, pos_evidence = self._apply_positional_heuristics(
            token, position, total_tokens, context_tokens
        )

        return role, confidence, pos_evidence + dict_evidence + surname_evidence

    def _check_initial(self, token: str) -> Tuple[str, float, List[str]]:
        """Check if token is an initial."""
        if self._initial_pattern.match(token):
            return 'initial', 0.95, [f"Matches initial pattern: '{token}'"]
        return 'unknown', 0.0, []

    def _check_patronymic(self, token: str, language: str) -> Tuple[str, float, List[str]]:
        """Check if token matches patronymic patterns."""
        evidence = []

        for pattern_name, pattern in self._patronymic_patterns.get(language, {}).items():
            if pattern.search(token.lower()):
                confidence = 0.9 if 'strong' in pattern_name else 0.7
                evidence.append(f"Matches {pattern_name} patronymic pattern")
                return 'patronymic', confidence, evidence

        return 'unknown', 0.0, evidence

    def _check_name_dictionaries(self, token: str, language: str) -> Tuple[str, float, List[str]]:
        """Check token against name dictionaries."""
        token_lower = token.lower()
        evidence = []

        # Check given names
        given_key = f'{language}_given_names'
        if given_key in self.name_dicts and token_lower in self.name_dicts[given_key]:
            evidence.append(f"Found in {language} given names dictionary")
            return 'given', 0.8, evidence

        # Check surnames
        surname_key = f'{language}_surnames'
        if surname_key in self.name_dicts and token_lower in self.name_dicts[surname_key]:
            evidence.append(f"Found in {language} surnames dictionary")
            return 'surname', 0.8, evidence

        # Check diminutives
        dim_key = f'{language}_diminutives'
        if dim_key in self.name_dicts and token_lower in self.name_dicts[dim_key]:
            evidence.append(f"Found in {language} diminutives dictionary")
            return 'given', 0.7, evidence

        return 'unknown', 0.0, evidence

    def _check_surname_patterns(self, token: str, language: str) -> Tuple[str, float, List[str]]:
        """Check if token matches surname patterns."""
        evidence = []

        for pattern_name, pattern in self._surname_patterns.get(language, {}).items():
            if pattern.search(token.lower()):
                confidence = 0.8 if 'strong' in pattern_name else 0.6
                evidence.append(f"Matches {pattern_name} surname pattern")
                return 'surname', confidence, evidence

        return 'unknown', 0.0, evidence

    def _apply_positional_heuristics(
        self,
        token: str,
        position: int,
        total_tokens: int,
        context_tokens: List[str]
    ) -> Tuple[str, float, List[str]]:
        """Apply positional heuristics for role classification."""
        evidence = []

        # First position bias towards given name
        if position == 0 and total_tokens > 1:
            evidence.append("First position suggests given name")
            return 'given', 0.4, evidence

        # Last position bias towards surname
        if position == total_tokens - 1 and total_tokens > 1:
            evidence.append("Last position suggests surname")
            return 'surname', 0.4, evidence

        # Middle position in 3+ token names often patronymic
        if total_tokens >= 3 and position == 1:
            evidence.append("Middle position in 3+ tokens suggests patronymic")
            return 'patronymic', 0.3, evidence

        return 'unknown', 0.1, evidence

    def _compile_patronymic_patterns(self) -> Dict[str, Dict[str, re.Pattern]]:
        """Compile patronymic patterns for different languages."""
        patterns = {
            'ru': {
                'strong_masc': re.compile(r'.*(ович|евич|ич)$'),
                'strong_fem': re.compile(r'.*(овна|евна|ична)$'),
                'weak': re.compile(r'.*(оич|еич)$')
            },
            'uk': {
                'strong_masc': re.compile(r'.*(ович|евич|іч|йович)$'),
                'strong_fem': re.compile(r'.*(івна|овна|ївна)$')
            }
        }
        return patterns

    def _compile_surname_patterns(self) -> Dict[str, Dict[str, re.Pattern]]:
        """Compile surname patterns for different languages."""
        patterns = {
            'ru': {
                'strong_endings': re.compile(r'.*(ов|ев|ин|ын|ск|цк|енко)$'),
                'feminine_endings': re.compile(r'.*(ова|ева|ина|ына|ская|цкая)$'),
                'weak_endings': re.compile(r'.*(ский|цкий|ной|ная)$')
            },
            'uk': {
                'strong_endings': re.compile(r'.*(енко|ук|юк|чук|ич|енко|ський|цький)$'),
                'feminine_endings': re.compile(r'.*(енко|ська|цька)$')
            }
        }
        return patterns

    def is_organization_form(self, token: str) -> bool:
        """Check if token is an organizational legal form."""
        legal_forms = {
            'ооо', 'зао', 'оао', 'пао', 'ао', 'ип', 'чп', 'фоп', 'тов',
            'llc', 'ltd', 'inc', 'corp', 'co', 'gmbh', 'sa', 'ag'
        }
        return token.lower() in legal_forms
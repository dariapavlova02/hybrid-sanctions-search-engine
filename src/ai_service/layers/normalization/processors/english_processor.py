"""
English name processing utilities for normalization.
"""

import re
from typing import Dict, List, Optional, Set, Tuple

from .config import NormalizationConfig


class EnglishNameProcessor:
    """Handles English-specific name normalization."""

    def __init__(self):
        """Initialize the English processor."""
        self.nicknames = {}
        self.lexicons_loaded = False

    def normalize_english_name_token(self, token: str, role: str, config: NormalizationConfig) -> str:
        """Normalize a single English name token."""
        if not token:
            return token

        # Normalize apostrophes to canonical form for person tokens
        if role in {'given', 'surname', 'patronymic', 'initial'} and "'" in token:
            token = self._normalize_apostrophe(token)

        # Handle apostrophes and hyphens
        if "'" in token or "-" in token:
            # Preserve apostrophes and hyphens, normalize case
            return self._title_case_with_punctuation(token)

        # Apply title case
        return token.title()

    def _normalize_apostrophe(self, token: str) -> str:
        """Normalize apostrophes to canonical form."""
        if not token:
            return token

        # Replace ASCII apostrophe with canonical apostrophe
        return token.replace("'", "'")

    def _title_case_with_punctuation(self, token: str) -> str:
        """Apply title case while preserving punctuation."""
        if not token:
            return token

        # Split by common punctuation but preserve it
        parts = []
        current = ""

        for char in token:
            if char in ["'", "-", "."]:
                if current:
                    parts.append(current.title())
                    current = ""
                parts.append(char)
            else:
                current += char

        if current:
            parts.append(current.title())

        return "".join(parts)

    def resolve_english_nickname(self, token: str, config: NormalizationConfig) -> Tuple[str, List[str]]:
        """Resolve English nicknames to full names."""
        expansions = []

        if not config.enable_en_nickname_expansion or not token:
            return token, expansions

        # Load lexicons if needed
        if not self.lexicons_loaded:
            self._load_english_lexicons()

        # Check for nickname expansion
        token_lower = token.lower()
        if token_lower in self.nicknames:
            full_names = self.nicknames[token_lower]
            if full_names:
                expansions.extend(full_names)
                # Return the first (most common) expansion as primary
                return full_names[0].title(), [name.title() for name in full_names[1:]]

        return token, expansions

    def normalize_english_tokens(
        self,
        tokens: List[str],
        roles: List[str],
        config: NormalizationConfig
    ) -> Tuple[List[str], List[str]]:
        """Normalize a list of English tokens."""
        if not tokens:
            return [], []

        normalized_tokens = []
        normalized_roles = []

        for i, (token, role) in enumerate(zip(tokens, roles)):
            if not token or not token.strip():
                continue

            # Skip non-personal tokens in English processing
            if role not in {'given', 'surname', 'patronymic', 'initial'}:
                continue

            # Normalize the token
            normalized_token = self.normalize_english_name_token(token, role, config)

            # Handle nickname expansion
            if role == 'given' and config.enable_en_nickname_expansion:
                expanded_token, alternatives = self.resolve_english_nickname(normalized_token, config)
                normalized_token = expanded_token

            if normalized_token:
                normalized_tokens.append(normalized_token)
                normalized_roles.append(role)

        return normalized_tokens, normalized_roles

    def _load_english_lexicons(self) -> None:
        """Load English nickname and name lexicons."""
        # Basic English nicknames mapping
        self.nicknames = {
            # Common nicknames to full names
            "alex": ["Alexander", "Alexandra", "Alexis"],
            "mike": ["Michael", "Mitchell"],
            "bob": ["Robert", "Bobby"],
            "bill": ["William", "Billy"],
            "dick": ["Richard", "Rick"],
            "tom": ["Thomas"],
            "jim": ["James"],
            "joe": ["Joseph", "Joel"],
            "kate": ["Katherine", "Katelyn"],
            "liz": ["Elizabeth"],
            "sue": ["Susan", "Suzanne"],
            "beth": ["Elizabeth", "Bethany"],
            "nick": ["Nicholas", "Nicole"],
            "chris": ["Christopher", "Christina", "Christine"],
            "sam": ["Samuel", "Samantha"],
            "pat": ["Patrick", "Patricia"],
            "max": ["Maxwell", "Maximilian"],
            "ben": ["Benjamin"],
            "dan": ["Daniel", "Danny"],
            "matt": ["Matthew"],
            "steve": ["Steven", "Stephen"],
            "dave": ["David"],
            "john": ["Jonathan", "Johnson"],
            "will": ["William"],
            "tony": ["Anthony"],
            "tim": ["Timothy"],
            "ann": ["Anna", "Anne", "Annette"],
            "jen": ["Jennifer", "Jenny"],
            "lisa": ["Elisabeth", "Melissa"]
        }

        self.lexicons_loaded = True

    def check_english_gates(self, config: NormalizationConfig) -> Dict[str, bool]:
        """Check which English processing features are enabled."""
        gates = {
            "nameparser_enabled": config.en_use_nameparser,
            "nickname_expansion_enabled": config.enable_en_nickname_expansion,
            "spacy_ner_enabled": config.enable_spacy_en_ner,
            "rules_enabled": config.enable_en_rules,
            "titles_filtering_enabled": config.filter_titles_suffixes
        }

        return gates

    def extract_english_name_components(self, text: str) -> List[str]:
        """Extract name components from English text."""
        if not text:
            return []

        # Basic tokenization and cleaning for English names
        # Remove common prefixes and suffixes
        prefixes = r'\b(mr|mrs|ms|dr|prof|sir|lord|lady|hon)\b\.?\s*'
        suffixes = r'\s*(jr|sr|ii|iii|iv|v|phd|md|esq)\.?\s*$'

        cleaned = re.sub(prefixes, '', text.lower())
        cleaned = re.sub(suffixes, '', cleaned)

        # Split into components
        components = [comp.strip().title() for comp in cleaned.split() if comp.strip()]

        return components

    def validate_english_name(self, name: str) -> bool:
        """Validate if a name looks like a valid English name."""
        if not name or len(name) < 2:
            return False

        # Check for Latin characters only
        if not all(c.isalpha() or c in " '-." for c in name):
            return False

        # Check for reasonable length
        if len(name) > 50:
            return False

        # Check for repeated characters (likely not a real name)
        if re.search(r'(.)\1{3,}', name):
            return False

        return True
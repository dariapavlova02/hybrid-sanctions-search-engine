"""
Token processing utilities for normalization service.
Extracted from the monolithic NormalizationService for better maintainability.
"""

import re
from typing import List, Dict, Set, Tuple, Optional
from ....utils.logging_config import get_logger


class TokenProcessor:
    """Handles token-level operations like noise filtering and role classification."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self._context_words_cache = None

    def strip_noise_and_tokenize(
        self,
        text: str,
        preserve_names: bool = True,
        stop_words: Set[str] = None
    ) -> Tuple[List[str], List[str]]:
        """
        Strip noise and tokenize text for normalization.

        Args:
            text: Input text to tokenize
            preserve_names: Whether to preserve name-related punctuation
            stop_words: Set of stop words to filter out

        Returns:
            Tuple of (clean_tokens, traces)
        """
        if not text or not text.strip():
            return [], []

        stop_words = stop_words or set()
        traces = []

        # Step 1: Basic text cleanup
        cleaned_text = self._basic_cleanup(text)
        traces.append(f"Basic cleanup: '{text}' -> '{cleaned_text}'")

        # Step 2: Split into tokens
        raw_tokens = self._split_tokens(cleaned_text, preserve_names)
        traces.append(f"Tokenized into {len(raw_tokens)} tokens")

        # Step 3: Filter noise tokens
        clean_tokens = []
        for token in raw_tokens:
            if self._is_valid_token(token, stop_words):
                clean_tokens.append(token)
            else:
                traces.append(f"Filtered out noise token: '{token}'")

        return clean_tokens, traces

    def _basic_cleanup(self, text: str) -> str:
        """Basic text cleanup operations."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())

        # Fix common punctuation issues
        text = re.sub(r'([.])([a-zA-ZА-Яа-яІіЇїЄєҐґ])', r'\1 \2', text)

        return text

    def _split_tokens(self, text: str, preserve_names: bool) -> List[str]:
        """Split text into tokens with name preservation options."""
        if preserve_names:
            # Preserve dots and hyphens in names
            pattern = r"[^\w\s\.\-']+"
        else:
            # More aggressive splitting
            pattern = r"[^\w\s]+"

        # Replace punctuation with spaces but preserve some for names
        if preserve_names:
            # Keep dots for initials, hyphens for compound names, apostrophes
            tokens = re.findall(r"[\w\.\-']+", text)
        else:
            tokens = re.findall(r"\w+", text)

        return [token for token in tokens if token.strip()]

    def _is_valid_token(self, token: str, stop_words: Set[str]) -> bool:
        """Check if token is valid for normalization."""
        if not token or len(token.strip()) == 0:
            return False

        # Filter out stop words
        if token.lower() in stop_words:
            return False

        # Filter out pure punctuation
        if re.match(r'^[^\w]+$', token):
            return False

        # Filter out pure numbers (unless they might be part of names)
        if re.match(r'^\d+$', token) and len(token) > 4:
            return False

        return True

    def normalize_case(self, token: str, role: str = None) -> str:
        """Normalize token case based on role and content."""
        if not token:
            return token

        # Handle initials specially
        if self._is_initial(token):
            return self._normalize_initial(token)

        # Title case for names
        if role in {'given', 'surname', 'patronymic'}:
            return token.capitalize()

        # Default case normalization
        return token.lower()

    def _is_initial(self, token: str) -> bool:
        """Check if token is an initial."""
        return bool(re.match(r'^[A-ZА-ЯЁІ][.]?$', token, re.IGNORECASE))

    def _normalize_initial(self, token: str) -> str:
        """Normalize initial to standard format."""
        if not token:
            return token

        # Ensure single letter followed by dot
        letter = re.sub(r'[^A-ZА-ЯЁІa-zа-яёі]', '', token)
        if letter:
            return letter.upper() + '.'
        return token

    def split_quoted_tokens(self, text: str) -> Tuple[List[str], List[str]]:
        """
        Extract quoted organization names and remaining tokens.

        Returns:
            Tuple of (quoted_cores, remaining_tokens)
        """
        quoted_cores = []
        remaining_text = text

        # Find quoted strings
        quote_pattern = r'["\'\"\"]([^"\'\"\"]+)["\'\"\"]'
        matches = re.finditer(quote_pattern, text)

        for match in matches:
            quoted_content = match.group(1).strip()
            if quoted_content and len(quoted_content) > 1:
                quoted_cores.append(quoted_content)
                # Remove from remaining text
                remaining_text = remaining_text.replace(match.group(0), ' ')

        # Tokenize remaining text
        remaining_tokens = self._split_tokens(remaining_text, preserve_names=True)

        return quoted_cores, remaining_tokens
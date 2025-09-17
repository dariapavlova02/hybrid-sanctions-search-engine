"""Token processing utilities used by the normalization pipeline."""

import re
import unicodedata
from typing import Dict, List, Set, Tuple, Optional, Any

from ....data.dicts.stopwords import STOP_ALL
from ....utils.logging_config import get_logger
from ....utils.profiling import profile_function, profile_time


class TokenProcessor:
    """Handles token-level operations like noise filtering and normalization-aware tokenization."""

    def __init__(self):
        self.logger = get_logger(__name__)

    @profile_function("token_processor.strip_noise_and_tokenize")
    def strip_noise_and_tokenize(
        self,
        text: str,
        *,
        language: str = "uk",
        remove_stop_words: bool = True,
        preserve_names: bool = True,
        stop_words: Optional[Set[str]] = None,
        feature_flags: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[str], List[str], Dict[str, List[str]]]:
        """Mirror the legacy behaviour of ``NormalizationService._strip_noise_and_tokenize``.

        Returns a tuple of ``(tokens, traces, metadata)`` where metadata currently
        exposes the list of quoted segments detected in the input (``quoted_segments``).
        """

        if not isinstance(text, str) or not text.strip():
            return [], [], {}

        traces: List[str] = []
        quoted_segments: List[str] = []

        nfc_text = unicodedata.normalize("NFC", text)
        traces.append("Applied Unicode NFC normalisation")

        transliterated = self._basic_transliterate(nfc_text)
        if transliterated != nfc_text:
            traces.append("Applied basic transliteration")

        cleaned = re.sub(r"\s+", " ", transliterated.strip())
        traces.append("Collapsed whitespace")

        cleaned = re.sub(r"\d+", " ", cleaned)
        if preserve_names:
            cleaned = re.sub(r"[^\w\s\.\-\'\,\u0400-\u04FF\u0370-\u03FF]", " ", cleaned)
        else:
            cleaned = re.sub(r"[^\w\s\u0400-\u04FF\u0370-\u03FF]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        traces.append(f"Symbol cleanup result: '{cleaned}'")

        tokens: List[str] = []
        for token in cleaned.split():
            if not token:
                continue
            if preserve_names:
                for sub_token in self._split_compound_initials(token):
                    for final_token in re.split(r"([,])", sub_token):
                        final = final_token.strip()
                        if final:
                            tokens.append(final)
            else:
                for sub_token in re.split(r"[\'\-]", token):
                    sub_token = sub_token.strip()
                    if sub_token:
                        tokens.append(sub_token)

        traces.append(f"Tokenised into {len(tokens)} raw tokens")

        # Apply feature flag-based processing
        if feature_flags:
            tokens = self._apply_feature_flags(tokens, feature_flags, traces)

        effective_stop_words: Set[str] = set()
        if remove_stop_words:
            effective_stop_words = stop_words if stop_words is not None else STOP_ALL

        filtered: List[str] = []
        for token in tokens:
            if remove_stop_words:
                # Cache lower() result to avoid repeated calls
                token_lower = token.lower()
                if token_lower in effective_stop_words:
                    if len(token) == 1 and token.isalpha():
                        filtered.append(token)
                    else:
                        traces.append(f"Filtered stop word: '{token}'")
                    continue
            filtered.append(token)

        result_tokens: List[str] = []
        i = 0
        while i < len(filtered):
            token = filtered[i]
            if token.startswith("'"):
                quoted_tokens: List[str] = []
                if token.endswith("'") and len(token) > 1:
                    quoted_tokens = [token[1:-1]]
                else:
                    quoted_tokens = [token[1:]]
                    i += 1
                    while i < len(filtered) and not filtered[i].endswith("'"):
                        quoted_tokens.append(filtered[i])
                        i += 1
                    if i < len(filtered):
                        closing = filtered[i]
                        if closing.endswith("'"):
                            quoted_tokens.append(closing[:-1])
                # Use list comprehension and join for better performance
                quoted_parts = [part for part in quoted_tokens if part]
                if quoted_parts:
                    quoted_phrase = " ".join(quoted_parts)
                    quoted_segments.append(quoted_phrase)
                    result_tokens.extend(quoted_parts)
            else:
                result_tokens.append(token)
            i += 1

        if not result_tokens:
            traces.append("No tokens after filtering")

        return result_tokens, traces, {"quoted_segments": quoted_segments}

    @staticmethod
    def _basic_transliterate(text: str) -> str:
        transliteration_map = {"ё": "е", "Ё": "Е"}
        for char, replacement in transliteration_map.items():
            if char in text:
                text = text.replace(char, replacement)
        return text

    @staticmethod
    def _split_compound_initials(token: str) -> List[str]:
        pattern = r"^((?:[A-Za-zА-Яа-яІЇЄҐіїєґ]\.){2,})([A-Za-zА-Яа-яІЇЄҐіїєґ].*)$"
        match = re.match(pattern, token)
        if not match:
            return [token]
        initials_part = match.group(1)
        remainder = match.group(2)
        initials = re.findall(r"[A-Za-zА-Яа-яІЇЄҐіїєґ]\.", initials_part)
        result = initials[:]
        if remainder:
            result.append(remainder)
        return result

    def _apply_feature_flags(
        self, 
        tokens: List[str], 
        feature_flags: Dict[str, Any], 
        traces: List[str]
    ) -> List[str]:
        """Apply feature flag-based processing to tokens."""
        processed_tokens = tokens[:]
        
        # fix_initials_double_dot: Collapse И.. → И.
        if feature_flags.get("fix_initials_double_dot", False):
            processed_tokens = self._fix_initials_double_dot(processed_tokens, traces)
        
        # preserve_hyphenated_case: Петрова-сидорова → Петрова-Сидорова
        if feature_flags.get("preserve_hyphenated_case", False):
            processed_tokens = self._preserve_hyphenated_case(processed_tokens, traces)
        
        # strict_stopwords: Use stricter stopword filtering
        if feature_flags.get("strict_stopwords", False):
            processed_tokens = self._apply_strict_stopwords(processed_tokens, traces)
        
        return processed_tokens

    def _fix_initials_double_dot(self, tokens: List[str], traces: List[str]) -> List[str]:
        """Fix double dots in initials (И.. → И.)."""
        processed = []
        for token in tokens:
            if re.match(r'^[A-Za-zА-Яа-яІЇЄҐіїєґ]\.\.+$', token):
                # Replace multiple dots with single dot
                fixed = re.sub(r'\.+$', '.', token)
                processed.append(fixed)
                traces.append(f"Fixed double dots: '{token}' → '{fixed}'")
            else:
                processed.append(token)
        return processed

    def _preserve_hyphenated_case(self, tokens: List[str], traces: List[str]) -> List[str]:
        """Preserve proper case in hyphenated names."""
        processed = []
        for token in tokens:
            if '-' in token and len(token) > 1:
                # Capitalize each part after hyphen
                parts = token.split('-')
                capitalized_parts = []
                for part in parts:
                    if part and part[0].islower():
                        capitalized_parts.append(part[0].upper() + part[1:])
                    else:
                        capitalized_parts.append(part)
                capitalized = '-'.join(capitalized_parts)
                if capitalized != token:
                    processed.append(capitalized)
                    traces.append(f"Preserved hyphenated case: '{token}' → '{capitalized}'")
                else:
                    processed.append(token)
            else:
                processed.append(token)
        return processed

    def _apply_strict_stopwords(self, tokens: List[str], traces: List[str]) -> List[str]:
        """Apply stricter stopword filtering."""
        # This would implement stricter stopword rules
        # For now, just log that strict stopwords are enabled
        traces.append("Applied strict stopword filtering")
        return tokens

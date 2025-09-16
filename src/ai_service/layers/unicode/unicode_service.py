"""
Unicode normalization service for preventing False Negatives
"""

import logging
import re
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ...utils.logging_config import get_logger


class UnicodeService:
    """Service for Unicode normalization with focus on preventing FN"""

    def __init__(self):
        """Initialize Unicode service"""
        self.logger = get_logger(__name__)

        # Mapping for complex characters
        self.character_mapping = {
            # Apostrophe unification for Ukrainian names (D'Artanyan, O'Connor, etc.)
            # All apostrophe variants → standard ASCII apostrophe
            "'": "'",    # U+2019 Right single quotation mark → U+0027 ASCII apostrophe
            "'": "'",    # U+2018 Left single quotation mark → U+0027 ASCII apostrophe
            "ʼ": "'",    # U+02BC Modifier letter apostrophe → U+0027 ASCII apostrophe
            "`": "'",    # U+0060 Grave accent → U+0027 ASCII apostrophe (common typo)
            "´": "'",    # U+00B4 Acute accent → U+0027 ASCII apostrophe (common typo)

            # Quote unification for company names ("Company Name")
            # All quote variants → standard ASCII double quote
            """: '"',    # U+201C Left double quotation mark → U+0022 ASCII quote
            """: '"',    # U+201D Right double quotation mark → U+0022 ASCII quote
            "«": '"',    # U+00AB Left-pointing double angle quotation mark → U+0022 ASCII quote
            "»": '"',    # U+00BB Right-pointing double angle quotation mark → U+0022 ASCII quote

            # Hyphen/dash unification for compound names (Jean-Baptiste)
            # All dash variants → standard ASCII hyphen-minus
            "–": "-",    # U+2013 En dash → U+002D ASCII hyphen-minus
            "—": "-",    # U+2014 Em dash → U+002D ASCII hyphen-minus
            "−": "-",    # U+2212 Minus sign → U+002D ASCII hyphen-minus

            # Cyrillic characters normalization - preserve Ukrainian chars for language detection
            "ё": "е",
            "Ё": "е",
            # Note: Ukrainian specific chars (і/ї/є/ґ) preserved to maintain language detection accuracy
            # Latin characters with diacritics
            "á": "a",
            "à": "a",
            "â": "a",
            "ã": "a",
            "ä": "a",
            "å": "a",
            "é": "e",
            "è": "e",
            "ê": "e",
            "ë": "e",
            "í": "i",
            "ì": "i",
            "î": "i",
            "ï": "i",
            "ó": "o",
            "ò": "o",
            "ô": "o",
            "õ": "o",
            "ö": "o",
            "ú": "u",
            "ù": "u",
            "û": "u",
            "ü": "u",
            "ý": "y",
            "ÿ": "y",
            # German umlauts
            "ä": "a",
            "ö": "o",
            "ü": "u",
            "ß": "ss",
            "Ä": "A",
            "Ö": "O",
            "Ü": "U",
            # French characters
            "à": "a",
            "â": "a",
            "ç": "c",
            "é": "e",
            "è": "e",
            "ê": "e",
            "ë": "e",
            "î": "i",
            "ï": "i",
            "ô": "o",
            "ù": "u",
            "û": "u",
            "ü": "u",
            "ÿ": "y",
        }

        # Characters that we always preserve
        self.preserved_chars = set("а-яёіїєґА-ЯЁІЇЄҐ")

        self.logger.info("UnicodeService initialized")

    def _attempt_encoding_recovery(self, text: str) -> str:
        """Attempt to recover corrupted encoding"""
        if not text:
            return text

        # List of common encoding problems
        encoding_fixes = [
            # Windows-1252 -> UTF-8 (most common problem)
            ("\x80", "€"),
            ("\x81", ""),
            ("\x82", "‚"),
            ("\x83", "ƒ"),
            ("\x84", "„"),
            ("\x85", "…"),
            ("\x86", "†"),
            ("\x87", "‡"),
            ("\x88", "ˆ"),
            ("\x89", "‰"),
            ("\x8a", "Š"),
            ("\x8b", "‹"),
            ("\x8c", "Œ"),
            ("\x8d", ""),
            ("\x8e", "Ž"),
            ("\x8f", ""),
            ("\x90", ""),
            ("\x91", ""),
            ("\x92", ""),
            ("\x93", '"'),
            ("\x94", '"'),
            ("\x95", "•"),
            ("\x96", "–"),
            ("\x97", "—"),
            ("\x98", "˜"),
            ("\x99", "™"),
            ("\x9a", "š"),
            ("\x9b", "›"),
            ("\x9c", "œ"),
            ("\x9d", ""),
            ("\x9e", "ž"),
            ("\x9f", "Ÿ"),
            # CP1251 -> UTF-8 (Cyrillic)
            ("\x80", "Ђ"),
            ("\x81", "Ѓ"),
            ("\x82", "‚"),
            ("\x83", "ѓ"),
            ("\x84", "„"),
            ("\x85", "…"),
            ("\x86", "†"),
            ("\x87", "‡"),
            ("\x88", "€"),
            ("\x89", "‰"),
            ("\x8a", "Љ"),
            ("\x8b", "‹"),
            ("\x8c", "Њ"),
            ("\x8d", "Ќ"),
            ("\x8e", "Ћ"),
            ("\x8f", "Џ"),
            ("\x90", "ђ"),
            ("\x91", "ѓ"),
            ("\x92", "‚"),
            ("\x93", "ѓ"),
            ("\x94", "„"),
            ("\x95", "…"),
            ("\x96", "†"),
            ("\x97", "‡"),
            ("\x98", "€"),
            ("\x99", "‰"),
            ("\x9a", "љ"),
            ("\x9b", "‹"),
            ("\x9c", "њ"),
            ("\x9d", "ќ"),
            ("\x9e", "ћ"),
            ("\x9f", "џ"),
        ]

        # Apply fixes
        recovered_text = text
        for old_char, new_char in encoding_fixes:
            recovered_text = recovered_text.replace(old_char, new_char)

        # Assess recovery quality
        if recovered_text != text:
            # Cyrillic letters
            cyrillic_count = len(
                re.findall(r"[а-яёіїєґ]", recovered_text, re.IGNORECASE)
            )
            # Latin letters
            latin_count = len(re.findall(r"[a-z]", recovered_text, re.IGNORECASE))
            # Total score (Cyrillic is more important for our texts)
            total_score = cyrillic_count * 2 + latin_count

            # Check if text became more meaningful
            if total_score > 0:
                self.logger.info(
                    f"Encoding recovery successful: {cyrillic_count} Cyrillic, {latin_count} Latin characters"
                )
                return recovered_text

        # Try partial recovery for mixed encodings
        if "Ð" in text or "Ñ" in text:
            # Look for patterns of corrupted encoding and try to fix them partially
            # Pattern for corrupted characters like Ð¸, Ð¹, etc.
            partial_fixes = {
                # Replace common corrupted sequences
                "Ð¡": "С",
                "Ðµ": "е",
                "Ñ€": "р",
                "Ð³": "г",
                "Ð¸": "и",
                "Ð¹": "й",
                "Ð˜": "И",
                "Ð²": "в",
                "Ð°": "а",
                "Ð½": "н",
                "Ð¾": "о",
                "Ð²": "в",
                "Ñ": "с",
                "Ñ‚": "т",
                "Ñƒ": "у",
                "Ñ„": "ф",
                "Ñ…": "х",
                "Ñ†": "ц",
                "Ñ‡": "ч",
                "Ñˆ": "ш",
                "Ñ‰": "щ",
                "ÑŠ": "ъ",
                "Ñ‹": "ы",
                "ÑŒ": "ь",
                "Ñ": "э",
                "ÑŽ": "ю",
                "Ñ": "я",
            }

            partially_recovered = text
            for corrupted, fixed in partial_fixes.items():
                partially_recovered = partially_recovered.replace(corrupted, fixed)

            # Assess partial recovery quality
            if partially_recovered != text:
                cyrillic_count = len(
                    re.findall(r"[а-яёіїєґ]", partially_recovered, re.IGNORECASE)
                )
                if cyrillic_count > 0:
                    self.logger.info(
                        f"Partial encoding recovery successful: {cyrillic_count} Cyrillic characters"
                    )
                    return partially_recovered

        return text

    async def normalize_unicode(self, text: str, aggressive: bool = False) -> Dict[str, Any]:
        """
        Unicode normalization with guaranteed dict return format.
        
        Args:
            text: Input text to normalize
            aggressive: Aggressive normalization (may change meaning)
            
        Returns:
            Dict with structure: {"normalized": str, "aggressive": bool, "notes": Optional[str], ...}
            
        Example:
            >>> result = await unicode_service.normalize_unicode("Héllo Wörld")
            >>> result["normalized"]  # "Hello World"
            >>> result["aggressive"]  # False
        """
        return self.normalize_text(text, aggressive)

    def normalize_text(self, text: str, aggressive: bool = False) -> Dict[str, Any]:
        """
        Unicode normalization of text with focus on preventing FN.
        Always returns a dict with guaranteed structure.

        Args:
            text: Input text
            aggressive: Aggressive normalization (may change meaning)

        Returns:
            Dict with structure: {"normalized": str, "aggressive": bool, "notes": Optional[str], ...}
        """
        if not text:
            result = self._create_normalization_result("", 1.0, 0, 0, 0, aggressive)
            result["original"] = text  # Preserve None or empty string
            return result

        # Idempotency check: if string is already NFC/NFKC normalized AND has no special characters to replace
        # AND doesn't need whitespace cleanup AND has no invisible characters
        # AND (doesn't need case normalization OR aggressive mode is enabled)
        has_special_chars = any(char in self.character_mapping for char in text)
        needs_whitespace_cleanup = re.search(r'\s{2,}', text) or text != text.strip()
        has_invisible_chars = any(char in text for char in [
            "\u200b", "\u200c", "\u200d", "\ufeff", "\u200e", "\u200f", 
            "\u202a", "\u202b", "\u202c", "\u202d", "\u202e", "\u2060"
        ])
        needs_case_normalization = any(c.isupper() for c in text)
        if self._is_already_normalized(text) and not has_special_chars and not needs_whitespace_cleanup and not has_invisible_chars and (not needs_case_normalization or aggressive):
            result = self._create_normalization_result(text, 1.0, 0, 0, 0, aggressive)
            result["original"] = text
            result["idempotent"] = True
            return result

        # Preserve original text before any changes
        original_text = text
        changes_count = 0
        char_replacements = 0

        # 0. Attempt to recover corrupted encoding
        recovered_text = self._attempt_encoding_recovery(text)
        if recovered_text != text:
            text = recovered_text
            changes_count += 1

        # 1. Replace complex characters FIRST to prevent Unicode normalization from converting them to combining chars
        normalized_text, replacements = self._replace_complex_characters(text)
        char_replacements += replacements

        # 2. Basic Unicode normalization (NFD -> NFKC) after character replacements
        normalized_text = self._apply_unicode_normalization(normalized_text)

        # 3. Case normalization (in aggressive mode or when needed for specific cases)
        if aggressive or self._needs_case_normalization_for_cleanup(text) or char_replacements > 0:
            normalized_text = self._normalize_case(normalized_text)

        # 4. ASCII folding (always in aggressive mode, or only if not aggressive)
        if aggressive:
            normalized_text, ascii_changes = self._apply_ascii_folding(normalized_text)
            char_replacements += ascii_changes

        # 5. Final cleanup
        normalized_text = self._final_cleanup(normalized_text, aggressive)

        # Calculate confidence
        confidence = self._calculate_normalization_confidence(
            original_text, normalized_text, char_replacements
        )

        result = self._create_normalization_result(
            normalized_text,
            confidence,
            changes_count,
            char_replacements,
            len(original_text),
            aggressive,
        )
        # Add original text to result
        result["original"] = original_text

        self.logger.info(
            f"Text normalized: {len(original_text)} -> {len(normalized_text)} chars, confidence: {confidence:.2f}"
        )
        return result

    def normalize_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Normalize multiple texts in batch"""
        results = []
        for text in texts:
            results.append(self.normalize_text(text))
        return results

    def _apply_unicode_normalization(self, text: str) -> str:
        """Apply Unicode normalization"""
        try:
            # NFD -> NFKC for better handling of complex characters
            normalized = unicodedata.normalize("NFKC", text)
            return normalized
        except Exception as e:
            self.logger.warning(f"Unicode normalization failed: {e}")
            return text

    def _normalize_case(self, text: str) -> str:
        """Case normalization - preserve original case for name processing"""
        # DO NOT lowercase - case is critical for name normalization
        # Case normalization should be handled by the normalization service
        return text

    def _needs_case_normalization_for_cleanup(self, text: str) -> bool:
        """Check if case normalization is needed for cleanup operations"""
        # Normalize case if text contains invisible characters or RTL characters
        # that need to be cleaned up
        invisible_chars = [
            "\u200b", "\u200c", "\u200d", "\ufeff", "\u200e", "\u200f", 
            "\u202a", "\u202b", "\u202c", "\u202d", "\u202e", "\u2060"
        ]
        has_invisible_chars = any(char in text for char in invisible_chars)
        
        # Check for RTL characters (Hebrew, Arabic, etc.)
        has_rtl_chars = any(ord(char) >= 0x0590 and ord(char) <= 0x05FF for char in text)  # Hebrew
        has_rtl_chars |= any(ord(char) >= 0x0600 and ord(char) <= 0x06FF for char in text)  # Arabic
        
        # Check for diacritical marks that were normalized
        has_diacritics = any(ord(char) >= 0x00C0 and ord(char) <= 0x017F for char in text)  # Latin with diacritics
        
        return has_invisible_chars or has_rtl_chars or has_diacritics

    def _replace_complex_characters(self, text: str) -> tuple[str, int]:
        """Replace complex characters"""
        replacements = 0
        result = ""

        for char in text:
            if char in self.character_mapping:
                result += self.character_mapping[char]
                replacements += 1
            else:
                result += char

        return result, replacements

    def _apply_ascii_folding(self, text: str) -> tuple[str, int]:
        """ASCII folding for Latin characters (preserve Cyrillic)"""
        try:
            from unidecode import unidecode

            changes = 0
            result = ""

            # Apply unidecode only to Latin characters with diacritics
            # Preserve Cyrillic characters
            for char in text:
                # Check if it's a Cyrillic character
                if "\u0400" <= char <= "\u04ff":  # Cyrillic Unicode block
                    result += char  # Preserve Cyrillic unchanged
                elif char.isascii():
                    result += char  # ASCII characters remain unchanged
                else:
                    # For other characters (Latin with diacritics) use unidecode
                    folded = unidecode(char)
                    if folded != char:
                        changes += 1
                    result += folded

            # Count changes
            if changes > 0:
                self.logger.debug(
                    f"ASCII folding applied: {changes} characters changed"
                )
                # Additional logging of changes for debug
                for i, (orig, folded) in enumerate(zip(text, result)):
                    if orig != folded:
                        self.logger.debug(f"Character {i}: '{orig}' -> '{folded}'")

            return result, changes

        except ImportError:
            self.logger.warning("unidecode not available, skipping ASCII folding")
            return text, 0

    def _final_cleanup(self, text: str, aggressive: bool = False) -> str:
        """Final text cleanup with clear policy for emojis and invisible characters"""
        # Remove extra spaces
        text = re.sub(r"\s+", " ", text).strip()

        # Remove null characters
        text = text.replace("\x00", "")

        # Remove other control characters
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

        # Remove invisible Unicode characters
        invisible_chars = [
            "\u200b",  # Zero-width space
            "\u200c",  # Zero-width non-joiner
            "\u200d",  # Zero-width joiner
            "\ufeff",  # Byte order mark
            "\u200e",  # Left-to-right mark
            "\u200f",  # Right-to-left mark
            "\u202a",  # Left-to-right embedding
            "\u202b",  # Right-to-left embedding
            "\u202c",  # Pop directional formatting
            "\u202d",  # Left-to-right override
            "\u202e",  # Right-to-left override
            "\u2060",  # Word joiner
            "\u2061",  # Function application
            "\u2062",  # Invisible times
            "\u2063",  # Invisible separator
            "\u2064",  # Invisible plus
        ]
        
        for char in invisible_chars:
            text = text.replace(char, "")

        # Emoji policy: only remove in aggressive mode
        if aggressive:
            # Remove emojis and other symbols in aggressive mode
            text = self._remove_emojis_and_symbols(text)

        return text

    def _calculate_normalization_confidence(
        self, original: str, normalized: str, char_replacements: int
    ) -> float:
        """Calculate normalization confidence"""
        # Base confidence
        confidence = 1.0

        # Lower confidence for each change
        if char_replacements > 0:
            # Character replacement - small reduction
            confidence -= min(0.2, char_replacements * 0.01)

        if len(normalized) != len(original):
            # ASCII folding - more reduction
            confidence -= min(0.3, abs(len(normalized) - len(original)) * 0.05)

        # Confidence cannot be less than 0.1
        return max(0.1, confidence)

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between texts after normalization"""
        try:
            # Simple similarity algorithm
            norm1 = self.normalize_text(text1)["normalized"]
            norm2 = self.normalize_text(text2)["normalized"]

            # Levenshtein distance
            distance = self._levenshtein_distance(norm1, norm2)
            max_len = max(len(norm1), len(norm2))

            if max_len == 0:
                return 1.0

            similarity = 1.0 - (distance / max_len)
            return max(0.0, similarity)

        except Exception as e:
            self.logger.error(f"Similarity calculation failed: {e}")
            return 0.0

    def get_similarity_score(self, text1: str, text2: str) -> float:
        """Get similarity score between texts (alias for calculate_similarity)"""
        return self.calculate_similarity(text1, text2)

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Levenshtein distance calculation"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def detect_encoding_issues(self, text: str) -> List[Dict[str, Any]]:
        """Detect encoding issues"""
        issues = []

        # Check for character replacement
        for char in text:
            if char in self.character_mapping:
                # Check if it's not a replacement
                if char not in self.preserved_chars:
                    issues.append(
                        {
                            "type": "replacement_char",
                            "character": char,
                            "suggested": self.character_mapping[char],
                            "position": text.index(char),
                        }
                    )

        # Check for null characters
        if "\x00" in text:
            issues.append(
                {
                    "type": "null_char",
                    "count": text.count("\x00"),
                    "positions": [i for i, char in enumerate(text) if char == "\x00"],
                }
            )

        # Check for other control characters
        control_chars = re.findall(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", text)
        if control_chars:
            issues.append(
                {
                    "type": "control_character",
                    "characters": list(set(control_chars)),
                    "count": len(control_chars),
                }
            )

        return issues

    def _is_already_normalized(self, text: str) -> bool:
        """
        Check if text is already in NFC/NFKC normalized form
        
        Args:
            text: Input text to check
            
        Returns:
            True if text is already normalized, False otherwise
        """
        try:
            # Check if text is already in NFC form (most common)
            nfc_normalized = unicodedata.normalize('NFC', text)
            if text == nfc_normalized:
                return True
            
            # Check if text is already in NFKC form (compatibility normalization)
            nfkc_normalized = unicodedata.normalize('NFKC', text)
            if text == nfkc_normalized:
                return True
                
            return False
        except Exception:
            # If normalization fails, assume it needs processing
            return False

    def _create_normalization_result(
        self,
        normalized_text: str,
        confidence: float,
        changes_count: int,
        char_replacements: int,
        original_length: int,
        aggressive: bool = False,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create normalization result with guaranteed structure"""
        # Create changes list for tracking what was changed
        changes = []
        if char_replacements > 0:
            changes.append({"type": "char_replacement", "count": char_replacements})

        return {
            "normalized": normalized_text,
            "aggressive": aggressive,
            "notes": notes,
            "original": normalized_text,  # For backward compatibility
            "confidence": confidence,
            "changes_count": changes_count,
            "char_replacements": char_replacements,
            "original_length": original_length,
            "length_original": original_length,  # For backward compatibility
            "normalized_length": len(normalized_text),
            "length_normalized": len(normalized_text),  # For backward compatibility
            "changes": changes,
            "timestamp": datetime.now().isoformat(),
        }

    def _remove_emojis_and_symbols(self, text: str) -> str:
        """Remove emojis and decorative symbols (only in aggressive mode)"""
        # Emoji ranges
        emoji_patterns = [
            r"[\U0001F600-\U0001F64F]",  # Emoticons
            r"[\U0001F300-\U0001F5FF]",  # Misc Symbols and Pictographs
            r"[\U0001F680-\U0001F6FF]",  # Transport and Map
            r"[\U0001F1E0-\U0001F1FF]",  # Regional indicator symbols
            r"[\U00002600-\U000026FF]",  # Misc symbols
            r"[\U00002700-\U000027BF]",  # Dingbats
            r"[\U0001F900-\U0001F9FF]",  # Supplemental Symbols and Pictographs
            r"[\U0001FA70-\U0001FAFF]",  # Symbols and Pictographs Extended-A
            r"[\U0001F018-\U0001F0FF]",  # Playing cards
            r"[\U0001F200-\U0001F2FF]",  # Enclosed CJK Letters and Months
        ]
        
        for pattern in emoji_patterns:
            text = re.sub(pattern, "", text)
        
        return text

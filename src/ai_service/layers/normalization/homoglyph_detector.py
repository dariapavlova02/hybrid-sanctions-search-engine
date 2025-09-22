"""
Homoglyph detection and normalization for security.

Detects and normalizes visually similar characters that could be used
for security attacks or bypassing filters.
"""

import re
import unicodedata
from typing import Dict, List, Tuple, Set
from ...utils.logging_config import get_logger

logger = get_logger(__name__)

# Common homoglyph mappings for Cyrillic/Latin substitution attacks
CYRILLIC_LATIN_HOMOGLYPHS = {
    # Latin to Cyrillic mappings (for normalization)
    'A': 'А',  # Latin A (U+0041) -> Cyrillic А (U+0410)
    'B': 'В',  # Latin B (U+0042) -> Cyrillic В (U+0412)
    'C': 'С',  # Latin C (U+0043) -> Cyrillic С (U+0421)
    'E': 'Е',  # Latin E (U+0045) -> Cyrillic Е (U+0415)
    'H': 'Н',  # Latin H (U+0048) -> Cyrillic Н (U+041D)
    'K': 'К',  # Latin K (U+004B) -> Cyrillic К (U+041A)
    'M': 'М',  # Latin M (U+004D) -> Cyrillic М (U+041C)
    'O': 'О',  # Latin O (U+004F) -> Cyrillic О (U+041E)
    'P': 'Р',  # Latin P (U+0050) -> Cyrillic Р (U+0420)
    'T': 'Т',  # Latin T (U+0054) -> Cyrillic Т (U+0422)
    'X': 'Х',  # Latin X (U+0058) -> Cyrillic Х (U+0425)
    'Y': 'У',  # Latin Y (U+0059) -> Cyrillic У (U+0423)

    # Lowercase variants
    'a': 'а',  # Latin a (U+0061) -> Cyrillic а (U+0430)
    'c': 'с',  # Latin c (U+0063) -> Cyrillic с (U+0441)
    'e': 'е',  # Latin e (U+0065) -> Cyrillic е (U+0435)
    'o': 'о',  # Latin o (U+006F) -> Cyrillic о (U+043E)
    'p': 'р',  # Latin p (U+0070) -> Cyrillic р (U+0440)
    'x': 'х',  # Latin x (U+0078) -> Cyrillic х (U+0445)
    'y': 'у',  # Latin y (U+0079) -> Cyrillic у (U+0443)
}

# Additional lookalike characters
ADDITIONAL_HOMOGLYPHS = {
    # Greek letters often confused with Latin/Cyrillic
    'Α': 'А',  # Greek Alpha -> Cyrillic А
    'Β': 'В',  # Greek Beta -> Cyrillic В
    'Ε': 'Е',  # Greek Epsilon -> Cyrillic Е
    'Η': 'Н',  # Greek Eta -> Cyrillic Н
    'Κ': 'К',  # Greek Kappa -> Cyrillic К
    'Μ': 'М',  # Greek Mu -> Cyrillic М
    'Ο': 'О',  # Greek Omicron -> Cyrillic О
    'Ρ': 'Р',  # Greek Rho -> Cyrillic Р
    'Τ': 'Т',  # Greek Tau -> Cyrillic Т
    'Υ': 'У',  # Greek Upsilon -> Cyrillic У
    'Χ': 'Х',  # Greek Chi -> Cyrillic Х

    # Lowercase Greek
    'α': 'а',  # Greek alpha -> Cyrillic а
    'ε': 'е',  # Greek epsilon -> Cyrillic е
    'ο': 'о',  # Greek omicron -> Cyrillic о
    'ρ': 'р',  # Greek rho -> Cyrillic р
    'υ': 'у',  # Greek upsilon -> Cyrillic у
    'χ': 'х',  # Greek chi -> Cyrillic х
}

# Combined homoglyph mapping
ALL_HOMOGLYPHS = {**CYRILLIC_LATIN_HOMOGLYPHS, **ADDITIONAL_HOMOGLYPHS}


class HomoglyphDetector:
    """Detects and normalizes homoglyph attacks in text."""

    def __init__(self):
        """Initialize the homoglyph detector."""
        self.homoglyph_map = ALL_HOMOGLYPHS
        self.suspicious_patterns = self._compile_suspicious_patterns()

    def _compile_suspicious_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns for detecting suspicious character combinations."""
        patterns = []

        # Mixed script detection (Latin + Cyrillic in same word)
        patterns.append(re.compile(r'\b[A-Za-z\u0410-\u044F]+\b'))

        # Words with both Latin and Cyrillic characters
        patterns.append(re.compile(r'\b(?=.*[A-Za-z])(?=.*[\u0410-\u044F])[A-Za-z\u0410-\u044F]+\b'))

        return patterns

    def detect_homoglyphs(self, text: str) -> Dict[str, any]:
        """
        Detect potential homoglyph attacks in text.

        Args:
            text: Input text to analyze

        Returns:
            Dictionary with detection results
        """
        if not text:
            return {
                'has_homoglyphs': False,
                'suspicious_chars': [],
                'suspicious_words': [],
                'confidence': 0.0,
                'details': []
            }

        suspicious_chars = []
        suspicious_words = []
        details = []

        # Check for homoglyph characters
        for i, char in enumerate(text):
            if char in self.homoglyph_map:
                suspicious_chars.append({
                    'char': char,
                    'position': i,
                    'unicode': f'U+{ord(char):04X}',
                    'suggested': self.homoglyph_map[char],
                    'type': 'homoglyph'
                })
                details.append(f"Character '{char}' at position {i} looks like '{self.homoglyph_map[char]}'")

        # Check for mixed-script words
        words = text.split()
        for word_idx, word in enumerate(words):
            if self._is_mixed_script(word):
                suspicious_words.append({
                    'word': word,
                    'position': word_idx,
                    'type': 'mixed_script',
                    'scripts': self._get_scripts(word)
                })
                details.append(f"Word '{word}' contains mixed scripts: {self._get_scripts(word)}")

        # Calculate confidence score
        total_chars = len(text)
        suspicious_char_count = len(suspicious_chars)
        confidence = min(1.0, suspicious_char_count / max(1, total_chars) * 10)  # Scale to 0-1

        return {
            'has_homoglyphs': len(suspicious_chars) > 0 or len(suspicious_words) > 0,
            'suspicious_chars': suspicious_chars,
            'suspicious_words': suspicious_words,
            'confidence': confidence,
            'details': details
        }

    def normalize_homoglyphs(self, text: str) -> Tuple[str, List[str]]:
        """
        Normalize homoglyphs to their canonical forms.

        Args:
            text: Input text with potential homoglyphs

        Returns:
            Tuple of (normalized_text, applied_transformations)
        """
        if not text:
            return text, []

        normalized = text
        transformations = []

        # Apply homoglyph normalization
        for suspicious_char, canonical_char in self.homoglyph_map.items():
            if suspicious_char in normalized:
                count = normalized.count(suspicious_char)
                normalized = normalized.replace(suspicious_char, canonical_char)
                transformations.append(
                    f"Normalized {count}x '{suspicious_char}' (U+{ord(suspicious_char):04X}) "
                    f"-> '{canonical_char}' (U+{ord(canonical_char):04X})"
                )
                logger.debug(f"Homoglyph normalization: '{suspicious_char}' -> '{canonical_char}' ({count} occurrences)")

        return normalized, transformations

    def _is_mixed_script(self, word: str) -> bool:
        """Check if word contains mixed scripts (Latin + Cyrillic)."""
        has_latin = any('\u0041' <= char <= '\u007A' for char in word)  # A-Z, a-z
        has_cyrillic = any('\u0410' <= char <= '\u044F' for char in word)  # А-я
        return has_latin and has_cyrillic

    def _get_scripts(self, word: str) -> List[str]:
        """Get list of scripts present in word."""
        scripts = set()
        for char in word:
            if '\u0041' <= char <= '\u007A':  # A-Z, a-z
                scripts.add('Latin')
            elif '\u0410' <= char <= '\u044F':  # А-я
                scripts.add('Cyrillic')
            elif '\u0370' <= char <= '\u03FF':  # Greek
                scripts.add('Greek')
            elif char.isdigit():
                scripts.add('Digit')
            elif not char.isalpha():
                scripts.add('Other')
        return list(scripts)

    def is_likely_attack(self, text: str, threshold: float = 0.3) -> bool:
        """
        Determine if text is likely a homoglyph attack.

        Args:
            text: Text to analyze
            threshold: Confidence threshold for attack detection (0.0-1.0)

        Returns:
            True if likely attack, False otherwise
        """
        detection = self.detect_homoglyphs(text)
        return detection['confidence'] >= threshold

    def secure_normalize(self, text: str) -> Tuple[str, Dict[str, any]]:
        """
        Perform secure normalization with full analysis.

        Args:
            text: Input text

        Returns:
            Tuple of (normalized_text, analysis_report)
        """
        if not text:
            return text, {'safe': True, 'transformations': [], 'warnings': []}

        # Detect homoglyphs
        detection = self.detect_homoglyphs(text)

        # Normalize homoglyphs
        normalized, transformations = self.normalize_homoglyphs(text)

        # Generate warnings
        warnings = []
        if detection['has_homoglyphs']:
            warnings.append("Potential homoglyph attack detected")
        if detection['suspicious_words']:
            warnings.append(f"Found {len(detection['suspicious_words'])} mixed-script words")

        analysis_report = {
            'safe': not detection['has_homoglyphs'],
            'original_text': text,
            'normalized_text': normalized,
            'transformations': transformations,
            'warnings': warnings,
            'detection': detection,
            'changed': text != normalized
        }

        return normalized, analysis_report


# Global instance
homoglyph_detector = HomoglyphDetector()
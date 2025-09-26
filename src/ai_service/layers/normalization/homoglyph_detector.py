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
    # Cyrillic to Latin mappings (for normalization to Latin)
    'А': 'A',  # Cyrillic А (U+0410) -> Latin A (U+0041)
    'В': 'B',  # Cyrillic В (U+0412) -> Latin B (U+0042)
    'С': 'C',  # Cyrillic С (U+0421) -> Latin C (U+0043)
    'Е': 'E',  # Cyrillic Е (U+0415) -> Latin E (U+0045)
    'Н': 'H',  # Cyrillic Н (U+041D) -> Latin H (U+0048)
    'К': 'K',  # Cyrillic К (U+041A) -> Latin K (U+004B)
    'М': 'M',  # Cyrillic М (U+041C) -> Latin M (U+004D)
    'О': 'O',  # Cyrillic О (U+041E) -> Latin O (U+004F)
    'Р': 'P',  # Cyrillic Р (U+0420) -> Latin P (U+0050)
    'Т': 'T',  # Cyrillic Т (U+0422) -> Latin T (U+0054)
    'Х': 'X',  # Cyrillic Х (U+0425) -> Latin X (U+0058)
    'У': 'Y',  # Cyrillic У (U+0423) -> Latin Y (U+0059)

    # Lowercase variants
    'а': 'a',  # Cyrillic а (U+0430) -> Latin a (U+0061)
    'с': 'c',  # Cyrillic с (U+0441) -> Latin c (U+0063)
    'е': 'e',  # Cyrillic е (U+0435) -> Latin e (U+0065)
    'о': 'o',  # Cyrillic о (U+043E) -> Latin o (U+006F)
    'р': 'p',  # Cyrillic р (U+0440) -> Latin p (U+0070)
    'х': 'x',  # Cyrillic х (U+0445) -> Latin x (U+0078)
    'у': 'y',  # Cyrillic у (U+0443) -> Latin y (U+0079)
    'м': 'm',  # Cyrillic м (U+043C) -> Latin m (U+006D)
}

# Additional lookalike characters
ADDITIONAL_HOMOGLYPHS = {
    # Greek letters often confused with Latin (normalize to Latin)
    'Α': 'A',  # Greek Alpha -> Latin A
    'Β': 'B',  # Greek Beta -> Latin B
    'Ε': 'E',  # Greek Epsilon -> Latin E
    'Η': 'H',  # Greek Eta -> Latin H
    'Κ': 'K',  # Greek Kappa -> Latin K
    'Μ': 'M',  # Greek Mu -> Latin M
    'Ο': 'O',  # Greek Omicron -> Latin O
    'Ρ': 'P',  # Greek Rho -> Latin P
    'Τ': 'T',  # Greek Tau -> Latin T
    'Υ': 'Y',  # Greek Upsilon -> Latin Y
    'Χ': 'X',  # Greek Chi -> Latin X

    # Lowercase Greek
    'α': 'a',  # Greek alpha -> Latin a
    'ε': 'e',  # Greek epsilon -> Latin e
    'ο': 'o',  # Greek omicron -> Latin o
    'ρ': 'p',  # Greek rho -> Latin p
    'υ': 'y',  # Greek upsilon -> Latin y
    'χ': 'x',  # Greek chi -> Latin x
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

        # Check for mixed-script words first (this is the real attack)
        words = text.split()
        text_scripts = set()

        for word_idx, word in enumerate(words):
            word_scripts = self._get_scripts(word)
            text_scripts.update(word_scripts)

            if self._is_mixed_script(word):
                suspicious_words.append({
                    'word': word,
                    'position': word_idx,
                    'type': 'mixed_script_word',
                    'scripts': word_scripts
                })
                details.append(f"Word '{word}' contains mixed scripts: {word_scripts}")

                # For mixed script words, identify specific suspicious characters
                for i, char in enumerate(word):
                    if char in self.homoglyph_map:
                        char_pos_in_text = text.find(word) + i
                        suspicious_chars.append({
                            'char': char,
                            'position': char_pos_in_text,
                            'unicode': f'U+{ord(char):04X}',
                            'suggested': self.homoglyph_map[char],
                            'type': 'homoglyph'
                        })
                        details.append(f"Character '{char}' at position {char_pos_in_text} looks like '{self.homoglyph_map[char]}'")

        # Check for mixed scripts across the entire text (different words using different scripts)
        suspicious_scripts = {'Latin', 'Cyrillic'}.intersection(text_scripts)
        if len(suspicious_scripts) > 1:
            # Flag as suspicious if we have both Latin and Cyrillic across different words
            details.append(f"Text contains mixed scripts across words: {list(text_scripts)}")
            if not suspicious_words:  # Only add if we don't already have mixed script words
                suspicious_words.append({
                    'word': text,  # Entire text
                    'position': 0,
                    'type': 'mixed_script_text',
                    'scripts': list(text_scripts)
                })

        # Calculate confidence score based on mixed scripts
        confidence = len(suspicious_words) * 0.3  # Each mixed script detection adds 30% confidence

        return {
            'has_homoglyphs': len(suspicious_words) > 0,  # Flag if there are any mixed script detections
            'suspicious_chars': suspicious_chars,
            'suspicious_words': suspicious_words,
            'confidence': min(1.0, confidence),
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
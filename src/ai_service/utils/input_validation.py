"""
Input validation and sanitization utilities for sanctions screening
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..config import SERVICE_CONFIG
from ..exceptions import ValidationError


@dataclass
class ValidationResult:
    """Result of input validation"""

    is_valid: bool
    sanitized_text: str
    warnings: List[str]
    blocked_patterns: List[str]
    risk_level: str


class InputValidator:
    """Validates and sanitizes input for sanctions screening"""

    def __init__(self):
        """Initialize input validator"""
        # Maximum text length for processing
        # Use correct attribute from ServiceConfig; fallback to a safe default
        self.max_length = getattr(SERVICE_CONFIG, "max_input_length", 10000)

        # Suspicious patterns that should be flagged
        self.suspicious_patterns = [
            r"<script[^>]*>.*?</script>",  # Script injection
            r"javascript:",  # JavaScript URLs
            r"data:.*base64",  # Base64 data URIs
            r"\\x[0-9a-fA-F]{2}",  # Hex encoded characters
            r"%[0-9a-fA-F]{2}",  # URL encoded characters
            r"&#x?[0-9a-fA-F]+;",  # HTML entities
        ]

        # Control characters to remove (except newlines and tabs)
        self.control_chars = [
            "\x00",
            "\x01",
            "\x02",
            "\x03",
            "\x04",
            "\x05",
            "\x06",
            "\x07",
            "\x08",
            "\x0b",
            "\x0c",
            "\x0e",
            "\x0f",
            "\x10",
            "\x11",
            "\x12",
            "\x13",
            "\x14",
            "\x15",
            "\x16",
            "\x17",
            "\x18",
            "\x19",
            "\x1a",
            "\x1b",
            "\x1c",
            "\x1d",
            "\x1e",
            "\x1f",
            "\x7f",
        ]

        # Zero-width characters that can be used for obfuscation
        self.zero_width_chars = [
            "\u200b",  # ZERO WIDTH SPACE
            "\u200c",  # ZERO WIDTH NON-JOINER
            "\u200d",  # ZERO WIDTH JOINER
            "\u2060",  # WORD JOINER
            "\ufeff",  # ZERO WIDTH NO-BREAK SPACE
        ]

        # Homoglyph patterns for common substitutions (applied only for Latin-only texts)
        # Note: we avoid mapping Cyrillic letters to Latin to preserve legitimate Cyrillic content
        self.homoglyph_map = {
            # Keep only conservative mappings when text is Latin-only
            # (Digits that are often used to spoof Latin letters)
            "0": "o",
            "1": "l",
            "3": "e",
            "5": "s",
            # Extended homoglyph mappings
            # Cyrillic to Latin (common confusables)
            "а": "a",  # Cyrillic 'а' to Latin 'a'
            "о": "o",  # Cyrillic 'о' to Latin 'o'  
            "р": "p",  # Cyrillic 'р' to Latin 'p'
            "е": "e",  # Cyrillic 'е' to Latin 'e'
            "у": "y",  # Cyrillic 'у' to Latin 'y'
            "х": "x",  # Cyrillic 'х' to Latin 'x'
            "с": "c",  # Cyrillic 'с' to Latin 'c'
            "к": "k",  # Cyrillic 'к' to Latin 'k'
            "м": "m",  # Cyrillic 'м' to Latin 'm'
            "н": "h",  # Cyrillic 'н' to Latin 'h'
            "т": "t",  # Cyrillic 'т' to Latin 't'
            "в": "b",  # Cyrillic 'в' to Latin 'b'
            # Latin to Cyrillic (reverse mappings for mixed-script detection)
            "A": "А",  # Latin 'A' to Cyrillic 'А'
            "B": "В",  # Latin 'B' to Cyrillic 'В'
            "C": "С",  # Latin 'C' to Cyrillic 'С'
            "E": "Е",  # Latin 'E' to Cyrillic 'Е'
            "H": "Н",  # Latin 'H' to Cyrillic 'Н'
            "K": "К",  # Latin 'K' to Cyrillic 'К'
            "M": "М",  # Latin 'M' to Cyrillic 'М'
            "O": "О",  # Latin 'O' to Cyrillic 'О'
            "P": "Р",  # Latin 'P' to Cyrillic 'Р'
            "T": "Т",  # Latin 'T' to Cyrillic 'Т'
            "X": "Х",  # Latin 'X' to Cyrillic 'Х'
            "Y": "У",  # Latin 'Y' to Cyrillic 'У'
        }

    def validate_and_sanitize(
        self, text: str, strict_mode: bool = False, remove_homoglyphs: bool = True
    ) -> ValidationResult:
        """
        Validate and sanitize input text for sanctions screening

        Args:
            text: Input text to validate
            strict_mode: Enable strict validation mode
            remove_homoglyphs: Replace homoglyphs with standard characters

        Returns:
            ValidationResult with validation status and sanitized text
        """
        if not isinstance(text, str):
            raise ValidationError(f"Input must be string, got {type(text)}")

        warnings = []
        blocked_patterns = []
        risk_level = "low"

        # 1. Check length
        if len(text) > self.max_length:
            if strict_mode:
                raise ValidationError(f"Text too long: {len(text)} > {self.max_length}")
            else:
                text = text[: self.max_length]
                warnings.append(f"Text truncated to {self.max_length} characters")
                risk_level = "medium"

        # 2. Check for empty or whitespace-only input
        if not text.strip():
            return ValidationResult(
                is_valid=False,
                sanitized_text="",
                warnings=["Empty input"],
                blocked_patterns=[],
                risk_level="low",
            )

        # 3. Check for suspicious patterns
        for pattern in self.suspicious_patterns:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                blocked_patterns.append(pattern)
                if strict_mode:
                    raise ValidationError(f"Suspicious pattern detected: {pattern}")
                risk_level = "high"

        # Pre-scan to classify benign vs risky changes
        zero_width_count_before = sum(text.count(ch) for ch in self.zero_width_chars)
        control_count_before = sum(text.count(ch) for ch in self.control_chars)
        had_whitespace_collapse = (
            bool(re.search(r"\s{2,}", text)) or text != text.strip()
        )

        # 4. Sanitize the text
        sanitized = self._sanitize_text(text, remove_homoglyphs)

        # 5. Additional checks after sanitization
        if len(sanitized) != len(text):
            # Do not warn for benign whitespace/zero-width cleanup if no control chars were present
            if control_count_before == 0 and (
                zero_width_count_before > 0 or had_whitespace_collapse
            ):
                pass  # benign changes – skip noisy warning
            else:
                warnings.append("Text was modified during sanitization")
                if len(text) - len(sanitized) > 50:  # Significant changes
                    risk_level = "medium"

        # 6. Check for Unicode normalization (informational)
        try:
            normalized = unicodedata.normalize("NFC", sanitized)
            if len(normalized) != len(sanitized):
                warnings.append("Unicode normalization applied")
        except Exception:
            warnings.append("Unicode normalization failed")

        return ValidationResult(
            is_valid=len(blocked_patterns) == 0 or not strict_mode,
            sanitized_text=sanitized,
            warnings=warnings,
            blocked_patterns=blocked_patterns,
            risk_level=risk_level,
        )

    def _sanitize_text(self, text: str, remove_homoglyphs: bool = True) -> str:
        """
        Sanitize text by removing dangerous characters and patterns

        Args:
            text: Input text
            remove_homoglyphs: Replace homoglyphs with standard characters

        Returns:
            Sanitized text
        """
        # 1. Remove control characters (except newlines and tabs)
        for char in self.control_chars:
            text = text.replace(char, "")

        # 2. Remove zero-width characters that can be used for obfuscation
        for char in self.zero_width_chars:
            text = text.replace(char, "")

        # 3. Replace homoglyphs if requested (smart script detection)
        if remove_homoglyphs:
            try:
                # Detect mixed scripts or suspicious homoglyph usage
                has_cyrillic = re.search(r"[А-Яа-яІіЇїЄєҐґ]", text) is not None
                has_latin = re.search(r"[A-Za-z]", text) is not None

                # Only apply homoglyph replacement for truly mixed scripts or suspicious patterns
                # Don't convert legitimate pure Cyrillic text to Latin
                if has_cyrillic and has_latin:
                    # Mixed script detected - apply selective homoglyph normalization
                    # Only replace obviously suspicious characters that might be intentional obfuscation
                    suspicious_cyrillic_to_latin = {
                        # Only replace the most common homoglyphs that are often used for spoofing
                        "а": "a", "о": "o", "р": "p", "е": "e"
                    }
                    for homoglyph, replacement in suspicious_cyrillic_to_latin.items():
                        text = text.replace(homoglyph, replacement)
                elif has_latin and not has_cyrillic:
                    # Pure Latin - only apply digit-to-letter mappings for obvious spoofing
                    digit_mappings = {"0": "o", "1": "l", "3": "e", "5": "s"}
                    for homoglyph, replacement in digit_mappings.items():
                        text = text.replace(homoglyph, replacement)
                # If has_cyrillic and not has_latin: leave pure Cyrillic text alone
            except Exception:
                # Best-effort; skip on regex issues
                pass

        # 4. Normalize excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # 5. Strip leading/trailing whitespace
        text = text.strip()

        # 6. Apply basic Unicode normalization (use NFC to preserve compatibility chars like '№')
        try:
            text = unicodedata.normalize("NFC", text)
        except Exception:
            # If normalization fails, continue with original text
            pass

        return text

    def validate_sanctions_input(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate sanctions screening input data

        Args:
            data: Input data dictionary

        Returns:
            Validated and sanitized data
        """
        if not isinstance(data, dict):
            raise ValidationError(f"Input data must be dict, got {type(data)}")

        validated_data = {}

        # Required fields for sanctions screening
        required_fields = ["name"]

        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")

        # Validate and sanitize text fields
        text_fields = ["name", "name_en", "name_ru", "address", "description"]

        for field in text_fields:
            if field in data and data[field]:
                validation_result = self.validate_and_sanitize(
                    str(data[field]),
                    strict_mode=True,  # Strict mode for sanctions data
                    remove_homoglyphs=True,
                )

                if not validation_result.is_valid:
                    raise ValidationError(
                        f"Invalid {field}: {', '.join(validation_result.blocked_patterns)}"
                    )

                validated_data[field] = validation_result.sanitized_text

                # Log warnings for audit trail
                if validation_result.warnings:
                    validated_data[f"{field}_validation_warnings"] = (
                        validation_result.warnings
                    )

        # Copy non-text fields as-is (with basic validation)
        safe_fields = ["id", "entity_type", "birthdate", "itn", "status", "source"]
        for field in safe_fields:
            if field in data:
                validated_data[field] = data[field]

        return validated_data

    def is_text_suspicious(self, text: str) -> Dict[str, Any]:
        """
        Check if text contains suspicious patterns without sanitizing

        Args:
            text: Text to check

        Returns:
            Dictionary with suspicion analysis
        """
        analysis = {
            "is_suspicious": False,
            "risk_level": "low",
            "detected_patterns": [],
            "warnings": [],
        }

        # Check for suspicious patterns
        for pattern in self.suspicious_patterns:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                analysis["detected_patterns"].append(pattern)
                analysis["is_suspicious"] = True
                analysis["risk_level"] = "high"

        # Check for excessive zero-width characters
        zero_width_count = sum(text.count(char) for char in self.zero_width_chars)
        if zero_width_count > 5:
            analysis["warnings"].append(
                f"High zero-width character count: {zero_width_count}"
            )
            analysis["is_suspicious"] = True
            analysis["risk_level"] = (
                "medium" if analysis["risk_level"] == "low" else analysis["risk_level"]
            )

        # Check for excessive homoglyphs
        homoglyph_count = sum(text.count(char) for char in self.homoglyph_map.keys())
        total_chars = len(re.findall(r"[a-zA-Zа-яёіїєґА-ЯЁІЇЄҐ]", text))
        if total_chars > 0 and homoglyph_count / total_chars > 0.3:
            analysis["warnings"].append(
                f"High homoglyph ratio: {homoglyph_count}/{total_chars}"
            )
            analysis["is_suspicious"] = True
            analysis["risk_level"] = (
                "medium" if analysis["risk_level"] == "low" else analysis["risk_level"]
            )

        return analysis


# Global validator instance
input_validator = InputValidator()

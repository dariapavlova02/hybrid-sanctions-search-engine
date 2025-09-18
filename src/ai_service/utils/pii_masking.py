"""PII masking utilities for safe logging."""

import re
import hashlib
from typing import Optional


def mask_pii_for_logging(text: str, preserve_length: bool = True) -> str:
    """
    Mask PII in text for safe logging.

    Args:
        text: Input text that may contain PII
        preserve_length: If True, preserves the original text length with asterisks

    Returns:
        Masked text safe for logging
    """
    if not text or not isinstance(text, str):
        return str(text)

    # For very short text (likely not PII), just mask partially
    if len(text) <= 3:
        return "*" * len(text)

    # Generate a deterministic hash prefix for debugging correlation
    hash_prefix = hashlib.sha256(text.encode()).hexdigest()[:8]

    if preserve_length:
        # Show first and last character, mask the rest
        if len(text) <= 6:
            masked = "*" * len(text)
        else:
            masked = text[0] + "*" * (len(text) - 2) + text[-1]
        return f"[{hash_prefix}]{masked}"
    else:
        # Just show hash and length
        return f"[{hash_prefix}]({len(text)} chars)"


def mask_normalized_result_for_logging(normalized: str) -> str:
    """
    Mask normalized results for logging.

    Args:
        normalized: Normalized text result

    Returns:
        Masked version safe for logging
    """
    if not normalized:
        return "[empty]"

    # For normalized results, show structure but mask content
    tokens = normalized.split()
    if len(tokens) <= 1:
        return mask_pii_for_logging(normalized, preserve_length=False)

    # Show token count and pattern
    token_lengths = [len(token) for token in tokens]
    hash_prefix = hashlib.sha256(normalized.encode()).hexdigest()[:6]

    return f"[{hash_prefix}]{len(tokens)} tokens({','.join(map(str, token_lengths))})"


def safe_text_preview(text: str, max_chars: int = 20) -> str:
    """
    Create a safe preview of text for logging.

    Args:
        text: Input text
        max_chars: Maximum characters to show

    Returns:
        Safe preview with PII masked
    """
    if not text:
        return "[empty]"

    if len(text) <= max_chars:
        return mask_pii_for_logging(text, preserve_length=True)

    # Truncate and mask
    truncated = text[:max_chars]
    masked = mask_pii_for_logging(truncated, preserve_length=True)
    return f"{masked}..."


# Predefined patterns for common logging scenarios
def log_processing_start(text: str) -> str:
    """Generate safe log message for processing start."""
    return f"Processing text: {safe_text_preview(text)}"


def log_processing_result(original: str, normalized: str) -> str:
    """Generate safe log message for processing result."""
    original_preview = safe_text_preview(original)
    normalized_preview = mask_normalized_result_for_logging(normalized)
    return f"Result: {original_preview} -> {normalized_preview}"


def log_validation_error(text: str, error: Exception) -> str:
    """Generate safe log message for validation errors."""
    text_preview = safe_text_preview(text)
    return f"Validation failed for {text_preview}: {error}"
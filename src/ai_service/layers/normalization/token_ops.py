#!/usr/bin/env python3
"""
Token operations for normalization improvements.

This module provides atomic operations for improving tokenization:
- Collapsing double dots in initials
- Normalizing hyphenated names with proper case handling
"""

import re
from typing import List


def collapse_double_dots(tokens: List[str]) -> List[str]:
    """
    Collapse double dots in initials while preserving special cases.

    Rules:
    - "И..", "O..", "І.." → "И.", "O.", "І."
    - Don't touch "..." (ellipsis) and "и.о." (abbreviations)

    Args:
        tokens: List of token strings

    Returns:
        List of tokens with collapsed double dots

    Examples:
        >>> collapse_double_dots(["И..", "И."])
        ["И.", "И."]
        >>> collapse_double_dots(["..."])  # ellipsis preserved
        ["..."]
        >>> collapse_double_dots(["и.о."])  # abbreviation preserved
        ["и.о."]
    """
    if not tokens:
        return tokens

    result = []

    for token in tokens:
        # Skip empty tokens
        if not token:
            result.append(token)
            continue

        # Preserve ellipsis (exactly 3 dots)
        if token == "...":
            result.append(token)
            continue

        # Preserve common abbreviations with internal dots
        if re.match(r'^[а-яё]{1,3}\.о\.$', token.lower()):  # и.о., т.о., etc.
            result.append(token)
            continue

        # Pattern for initials with double dots: single letter + two dots
        # Supports Cyrillic, Latin, and other Unicode letters
        # Note: Python doesn't support \p{L}, so we use character ranges
        double_dot_pattern = r'^([А-Яа-яЁёІіЇїЄєʼ\'A-Za-z])\.\.+$'

        # Use Unicode-aware regex
        match = re.match(double_dot_pattern, token, re.UNICODE)
        if match:
            # Collapse to single dot
            letter = match.group(1)
            result.append(f"{letter}.")
        else:
            result.append(token)

    return result


def normalize_hyphenated_name(token: str, *, titlecase: bool = False) -> str:
    """
    Normalize hyphenated names with proper segmentation and case handling.

    Rules:
    - Split by single '-' only (preserve '—' and '--')
    - Each segment must be alphabetic + allowed apostrophes (''`)
    - No dots allowed inside segments
    - titlecase=True → capitalize each segment with Unicode support

    Args:
        token: Token string to normalize
        titlecase: Whether to apply title case to segments

    Returns:
        Normalized hyphenated token

    Examples:
        >>> normalize_hyphenated_name("петрова-сидорова", titlecase=True)
        "Петрова-Сидорова"
        >>> normalize_hyphenated_name("O'Neil-Smith", titlecase=True)
        "O'Neil-Smith"
        >>> normalize_hyphenated_name("test—dash")  # em-dash preserved
        "test—dash"
    """
    if not token or '-' not in token:
        return token

    # Only process tokens with single hyphens, not em-dashes or double hyphens
    if '—' in token or '--' in token:
        return token

    # Split by single hyphen
    segments = token.split('-')

    # Process each segment
    normalized_segments = []

    for segment in segments:
        if not segment:  # Empty segment (e.g., from leading/trailing hyphens)
            normalized_segments.append(segment)
            continue

        # Check if segment is valid (letters + allowed apostrophes, no dots)
        # Note: Python doesn't support \p{L}, so we use character ranges
        if not re.match(r"^[А-Яа-яЁёІіЇїЄєʼ\'A-Za-z''`]+$", segment, re.UNICODE):
            # Invalid segment, return original token
            return token

        # Apply titlecase if requested
        if titlecase:
            # Use title() for proper capitalization including apostrophes
            # title() handles cases like "o'neil" -> "O'Neil" correctly
            normalized_segment = segment.title()
        else:
            normalized_segment = segment

        normalized_segments.append(normalized_segment)

    return '-'.join(normalized_segments)


def _is_valid_name_segment(segment: str) -> bool:
    """
    Check if a segment is valid for name processing.

    Valid segments contain only:
    - Unicode letters (\p{L})
    - Allowed apostrophes: ' ' `
    - No dots, numbers, or other punctuation

    Args:
        segment: String segment to validate

    Returns:
        True if segment is valid for name processing
    """
    if not segment:
        return False

    # Pattern for valid name segments
    # Unicode letters + apostrophes only
    # Note: Python doesn't support \p{L}, so we use character ranges
    return bool(re.match(r"^[А-Яа-яЁёІіЇїЄєʼ\'A-Za-z''`]+$", segment, re.UNICODE))


def _has_internal_dots(token: str) -> bool:
    """
    Check if token has dots inside (not just at the end).

    Args:
        token: Token to check

    Returns:
        True if token has internal dots
    """
    if not token or '.' not in token:
        return False

    # Remove trailing dots and check if any remain
    stripped = token.rstrip('.')
    return '.' in stripped
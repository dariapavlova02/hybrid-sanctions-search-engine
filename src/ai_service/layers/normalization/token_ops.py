#!/usr/bin/env python3
"""
Token operations for normalization improvements.

This module provides atomic operations for improving tokenization:
- Collapsing double dots in initials
- Normalizing hyphenated names with proper case handling
"""

import re
from typing import List, Optional, Any
from ...contracts.base_contracts import TokenTrace


def collapse_double_dots_token(token: str, trace: Optional[List[Any]] = None) -> str:
    """
    Collapse double dots in a single token.

    Rules:
    - "И..", "O..", "І.." → "И.", "O.", "І."
    - Don't touch "..." (ellipsis) and "и.о." (abbreviations)

    Args:
        token: Single token string
        trace: Optional trace list for debugging

    Returns:
        Token with collapsed double dots

    Examples:
        >>> collapse_double_dots_token("И..")
        "И."
        >>> collapse_double_dots_token("...")  # ellipsis preserved
        "..."
        >>> collapse_double_dots_token("и.о.")  # abbreviation preserved
        "и.о."
    """
    if not token:
        return token

    # Preserve ellipsis (exactly 3 dots)
    if token == "...":
        return token

    # Preserve common abbreviations with internal dots
    if re.match(r'^[а-яё]{1,3}\.о\.$', token.lower()):  # и.о., т.о., etc.
        return token

    # Pattern for initials with double dots: single letter + two or more dots
    # Supports Cyrillic, Latin, and extended Unicode letters
    double_dot_pattern = r'^([А-Яа-яЁёІіЇїЄєʼ\'A-Za-zÀ-ÿĀ-žА-я])\.\.+$'

    # Use Unicode-aware regex
    match = re.match(double_dot_pattern, token, re.UNICODE)
    if match:
        # Collapse to single dot
        letter = match.group(1)
        collapsed_token = f"{letter}."

        # Add trace step if tracing is enabled
        if trace is not None:
            trace.append({
                'stage': 'tokenize',
                'rule': 'collapse_double_dots',
                'token_before': token,
                'token_after': collapsed_token,
                'evidence': 'initials'
            })

        return collapsed_token

    return token


def collapse_double_dots(tokens: List[str], trace: Optional[List[Any]] = None) -> List[str]:
    """
    Collapse double dots in initials while preserving special cases.

    Rules:
    - "И..", "O..", "І.." → "И.", "O.", "І."
    - Don't touch "..." (ellipsis) and "и.о." (abbreviations)

    Args:
        tokens: List of token strings
        trace: Optional trace list for debugging

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
        # Use the single token function for consistency
        processed_token = collapse_double_dots_token(token, trace)
        result.append(processed_token)

    return result


def normalize_apostrophe_name(token: str, *, titlecase: bool = False, trace: Optional[List[Any]] = None) -> str:
    """
    Normalize names with apostrophes with proper case handling.
    
    Rules:
    - Preserve apostrophes in names
    - Apply titlecase to segments around apostrophes
    - Remove dangling apostrophes at the end
    
    Args:
        token: Token string to normalize
        titlecase: Whether to apply title case
        trace: Optional trace list for debugging
        
    Returns:
        Normalized token with proper apostrophe handling
        
    Examples:
        >>> normalize_apostrophe_name("o'brien", titlecase=True)
        "O'Brien"
        >>> normalize_apostrophe_name("d'angelo", titlecase=True)
        "D'Angelo"
        >>> normalize_apostrophe_name("o'connor'", titlecase=True)  # dangling apostrophe
        "O'Connor"
    """
    if not token or "'" not in token:
        return token
    
    # Remove dangling apostrophes at the end
    cleaned_token = token.rstrip("'")
    if not cleaned_token:
        return token
    
    # Apply titlecase if requested
    if titlecase:
        # Use title() for proper capitalization including apostrophes
        # title() handles cases like "o'neil" -> "O'Neil" correctly
        normalized_token = cleaned_token.title()
    else:
        normalized_token = cleaned_token
    
    # Add trace step if tracing is enabled and token was changed
    if trace is not None and normalized_token != token:
        trace.append({
            'stage': 'tokenize',
            'rule': 'apostrophe_preserved',
            'token_before': token,
            'token_after': normalized_token
        })
    
    return normalized_token


def normalize_hyphenated_name(token: str, *, titlecase: bool = False, trace: Optional[List[Any]] = None) -> str:
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
        # Include extended Latin characters for international names
        if not re.match(r"^[А-Яа-яЁёІіЇїЄєʼ\'A-Za-zÀ-ÿĀ-žА-я''`]+$", segment, re.UNICODE):
            # Invalid segment, return original token
            return token

        # Apply titlecase if requested
        if titlecase:
            # First normalize apostrophes in the segment, then apply titlecase
            if "'" in segment:
                # Remove dangling apostrophes and apply titlecase
                cleaned_segment = segment.rstrip("'")
                normalized_segment = cleaned_segment.title()
            else:
                # Use title() for proper capitalization
                normalized_segment = segment.title()
        else:
            normalized_segment = segment

        normalized_segments.append(normalized_segment)

    normalized_token = '-'.join(normalized_segments)

    # Add trace step if tracing is enabled and token was changed
    if trace is not None and normalized_token != token:
        trace.append({
            'stage': 'tokenize',
            'rule': 'hyphenated_join',
            'token_before': token,
            'token_after': normalized_token
        })

    return normalized_token


def _is_valid_name_segment(segment: str) -> bool:
    """
    Check if a segment is valid for name processing.

    Valid segments contain only:
    - Unicode letters (Cyrillic, Latin, extended Latin)
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
    # Include extended Latin characters for international names
    return bool(re.match(r"^[А-Яа-яЁёІіЇїЄєʼ\'A-Za-zÀ-ÿĀ-žА-я''`]+$", segment, re.UNICODE))


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


def is_hyphenated_surname(token: str) -> bool:
    """
    Detect if token is a valid hyphenated surname.

    Rules for valid hyphenated surnames:
    - Contains single hyphen (not em-dash or double hyphen)
    - Each segment has 2+ characters
    - Segments contain only ru/uk/en letters and apostrophes
    - No dots or other punctuation

    Args:
        token: Token to check

    Returns:
        True if token matches hyphenated surname pattern

    Examples:
        >>> is_hyphenated_surname("петров-сидоров")
        True
        >>> is_hyphenated_surname("O'Neil-Smith")
        True
        >>> is_hyphenated_surname("А-Б")  # Too short segments
        False
        >>> is_hyphenated_surname("test—dash")  # Em-dash
        False
        >>> is_hyphenated_surname("И.-петров")  # Dot in segment
        False
    """
    if not token or '-' not in token:
        return False

    # Only process tokens with single hyphens, not em-dashes or double hyphens
    if '—' in token or '--' in token:
        return False

    # Split by single hyphen
    segments = token.split('-')

    # Must have exactly 2 segments for a hyphenated surname
    if len(segments) != 2:
        return False

    # Check each segment
    for segment in segments:
        # Each segment must have 2+ characters
        if len(segment) < 2:
            return False

        # Must contain only letters and apostrophes (no dots, numbers, etc.)
        # Include extended Latin characters for international names
        if not re.match(r"^[А-Яа-яЁёІіЇїЄєʼ\'A-Za-zÀ-ÿĀ-žА-я''`]+$", segment, re.UNICODE):
            return False

    return True
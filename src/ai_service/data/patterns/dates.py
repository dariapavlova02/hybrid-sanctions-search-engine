"""
Date Patterns

Contains patterns and utilities for detecting and extracting dates
in various formats (DD/MM/YYYY, DD.MM.YYYY, etc.).
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# Date patterns for different formats
DATE_PATTERNS = [
    # DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
    r"\b(0?[1-9]|[12][0-9]|3[01])[./\-](0?[1-9]|1[0-2])[./\-]((19|20)\d{2})\b",
    
    # YYYY/MM/DD, YYYY-MM-DD, YYYY.MM.DD
    r"\b((19|20)\d{2})[./\-](0?[1-9]|1[0-2])[./\-](0?[1-9]|[12][0-9]|3[01])\b",
    
    # MM/DD/YYYY (US format)
    r"\b(0?[1-9]|1[0-2])[./\-](0?[1-9]|[12][0-9]|3[01])[./\-]((19|20)\d{2})\b",
    
    # Russian date format
    r"\b(0?[1-9]|[12][0-9]|3[01])\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+((19|20)\d{2})\b",
    
    # Ukrainian date format
    r"\b(0?[1-9]|[12][0-9]|3[01])\s+(січня|лютого|березня|квітня|травня|червня|липня|серпня|вересня|жовтня|листопада|грудня)\s+((19|20)\d{2})(?:\s+року)?\b",
    
    # English date format
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(0?[1-9]|[12][0-9]|3[01]),?\s+((19|20)\d{2})\b",
    
    # English date format (month first)
    r"\b(0?[1-9]|[12][0-9]|3[01])\s+(January|February|March|April|May|June|July|August|September|October|November|December),?\s+((19|20)\d{2})\b",
]

# Month name mappings
MONTH_NAMES = {
    # Russian
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
    
    # Ukrainian
    "січня": 1, "лютого": 2, "березня": 3, "квітня": 4, "травня": 5, "червня": 6,
    "липня": 7, "серпня": 8, "вересня": 9, "жовтня": 10, "листопада": 11, "грудня": 12,
    
    # English
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}

# Compiled patterns cache
_compiled_patterns_cache: List[re.Pattern] = None


def get_compiled_patterns() -> List[re.Pattern]:
    """Get compiled date patterns with caching."""
    global _compiled_patterns_cache
    
    if _compiled_patterns_cache is None:
        _compiled_patterns_cache = [
            re.compile(pattern, re.IGNORECASE) for pattern in DATE_PATTERNS
        ]
    
    return _compiled_patterns_cache


def extract_birthdates_from_text(text: str) -> List[Dict]:
    """
    Extract birth dates from text.
    
    Args:
        text: Text to search in
        
    Returns:
        List of found dates with metadata
    """
    found_dates = []
    
    for pattern in get_compiled_patterns():
        for match in pattern.finditer(text):
            try:
                date_info = _parse_date_match(match)
                if date_info:
                    found_dates.append(date_info)
            except Exception:
                # Skip invalid dates
                continue
    
    return found_dates


def _parse_date_match(match: re.Match) -> Optional[Dict]:
    """Parse a date match into structured information."""
    groups = match.groups()
    if not groups:
        return None
    
    # Determine format and extract components
    date_str = match.group(0)
    
    # Try different parsing strategies
    parsed_date = None
    format_type = "unknown"
    
    # Strategy 1: DD/MM/YYYY or DD.MM.YYYY or DD-MM-YYYY
    if len(groups) >= 3 and groups[2] and len(groups[2]) == 4:
        try:
            day = int(groups[0])
            month = int(groups[1])
            year = int(groups[2])
            parsed_date = datetime(year, month, day)
            format_type = "dd_mm_yyyy"
        except ValueError:
            pass
    
    # Strategy 2: YYYY/MM/DD or YYYY.MM.DD or YYYY-MM-DD
    if not parsed_date and len(groups) >= 3 and groups[0] and len(groups[0]) == 4:
        try:
            year = int(groups[0])
            month = int(groups[1])
            day = int(groups[2])
            parsed_date = datetime(year, month, day)
            format_type = "yyyy_mm_dd"
        except ValueError:
            pass
    
    # Strategy 3: MM/DD/YYYY (US format)
    if not parsed_date and len(groups) >= 3 and groups[2] and len(groups[2]) == 4:
        try:
            month = int(groups[0])
            day = int(groups[1])
            year = int(groups[2])
            parsed_date = datetime(year, month, day)
            format_type = "mm_dd_yyyy"
        except ValueError:
            pass
    
    # Strategy 4: Russian month names
    if not parsed_date and len(groups) >= 3:
        month_name = groups[1].lower() if groups[1] else None
        if month_name in MONTH_NAMES:
            try:
                day = int(groups[0])
                month = MONTH_NAMES[month_name]
                year = int(groups[2])
                parsed_date = datetime(year, month, day)
                format_type = "russian_month"
            except ValueError:
                pass
    
    # Strategy 5: Ukrainian month names
    if not parsed_date and len(groups) >= 3:
        month_name = groups[1].lower() if groups[1] else None
        if month_name in MONTH_NAMES:
            try:
                day = int(groups[0])
                month = MONTH_NAMES[month_name]
                year = int(groups[2])
                parsed_date = datetime(year, month, day)
                format_type = "ukrainian_month"
            except ValueError:
                pass
    
    # Strategy 6: English month names
    if not parsed_date and len(groups) >= 3:
        month_name = groups[0].lower() if groups[0] else None
        if month_name in MONTH_NAMES:
            try:
                month = MONTH_NAMES[month_name]
                day = int(groups[1])
                year = int(groups[2])
                parsed_date = datetime(year, month, day)
                format_type = "english_month"
            except ValueError:
                pass
    
    if not parsed_date:
        return None
    
    # Validate date range (reasonable birth date range)
    current_year = datetime.now().year
    if parsed_date.year < 1900 or parsed_date.year > current_year:
        return None
    
    return {
        "raw": date_str,
        "parsed": parsed_date,
        "iso_format": parsed_date.strftime("%Y-%m-%d"),
        "format_type": format_type,
        "position": match.span(),
        "confidence": 0.9,
        "is_birthdate": True,
    }


def is_valid_date(day: int, month: int, year: int) -> bool:
    """Check if date components form a valid date."""
    try:
        datetime(year, month, day)
        return True
    except ValueError:
        return False


def format_date_iso(date_obj: datetime) -> str:
    """Format date object to ISO format (YYYY-MM-DD)."""
    return date_obj.strftime("%Y-%m-%d")


def extract_dates_near_text(text: str, target_text: str, max_distance: int = 50) -> List[Dict]:
    """
    Extract dates near specific text.
    
    Args:
        text: Full text to search in
        target_text: Text to search near
        max_distance: Maximum distance in characters
        
    Returns:
        List of dates found near target text
    """
    target_positions = []
    for match in re.finditer(re.escape(target_text), text, re.IGNORECASE):
        target_positions.append(match.span())
    
    if not target_positions:
        return []
    
    all_dates = extract_birthdates_from_text(text)
    nearby_dates = []
    
    for date_info in all_dates:
        date_start, date_end = date_info["position"]
        
        for target_start, target_end in target_positions:
            # Calculate distance between date and target
            distance = min(
                abs(date_start - target_end),
                abs(target_start - date_end),
                abs(date_start - target_start),
                abs(date_end - target_end)
            )
            
            if distance <= max_distance:
                nearby_dates.append({
                    **date_info,
                    "distance_to_target": distance,
                    "target_text": target_text
                })
                break
    
    return nearby_dates

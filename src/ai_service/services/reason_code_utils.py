"""
Utilities for detecting anomalies contributing to reason codes:
- Mixed script (Latin + Cyrillic)
- Homoglyph usage (confusable characters across scripts)
- Zero-width characters (ZWSP/ZWNJ/ZWJ/WORD JOINER)
"""

from __future__ import annotations

import re
from typing import List

# Zero width characters of interest
ZW_CHARS = [
    "\u200b",  # ZERO WIDTH SPACE
    "\u200c",  # ZERO WIDTH NON-JOINER
    "\u200d",  # ZERO WIDTH JOINER
    "\u2060",  # WORD JOINER
]


def _has_cyrillic(s: str) -> bool:
    return bool(re.search(r"[\u0400-\u04FF]", s))


def _has_latin(s: str) -> bool:
    return bool(re.search(r"[A-Za-z]", s))


def _has_zwsp(s: str) -> bool:
    return any(ch in s for ch in ZW_CHARS)


_CONFUSABLES = set(list("AaBCcEeHKkMOoPpTxXYy"))


def _has_homoglyphs(s: str) -> bool:
    # Heuristic: if both scripts present and any confusable ASCII letters are present
    # we flag potential homoglyph usage
    if not (_has_cyrillic(s) and _has_latin(s)):
        return False
    return any(ch in _CONFUSABLES for ch in s)


def compute_anomaly_reason_codes(text: str) -> List[str]:
    """Return list of anomaly reason codes found in text."""
    rc: List[str] = []
    if _has_latin(text) and _has_cyrillic(text):
        rc.append("RC_MIXED_SCRIPT")
    if _has_homoglyphs(text):
        rc.append("RC_HOMOGLYPH")
    if _has_zwsp(text):
        rc.append("RC_ZWSP")
    return rc

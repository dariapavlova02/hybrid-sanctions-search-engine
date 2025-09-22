"""
English nicknames dictionary
Loads data from JSON file to maintain compatibility
"""

import json
from pathlib import Path

# Load English nicknames from JSON file
_data_dir = Path(__file__).parent.parent.parent.parent.parent / "data"
_nicknames_file = _data_dir / "lexicons" / "en_nicknames.json"

try:
    with open(_nicknames_file, "r", encoding="utf-8") as f:
        ENGLISH_NICKNAMES = json.load(f)
except FileNotFoundError:
    # Fallback empty dict if file not found
    ENGLISH_NICKNAMES = {}

# Export for backward compatibility
__all__ = ["ENGLISH_NICKNAMES"]
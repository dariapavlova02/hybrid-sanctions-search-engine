"""
Ukrainian diminutives dictionary
Loads data from JSON file to maintain compatibility
"""

import json
from pathlib import Path

# Load Ukrainian diminutives from JSON file
_data_dir = Path(__file__).parent.parent.parent.parent.parent / "data"
_diminutives_file = _data_dir / "diminutives_uk.json"

try:
    with open(_diminutives_file, "r", encoding="utf-8") as f:
        UKRAINIAN_DIMINUTIVES = json.load(f)
except FileNotFoundError:
    # Fallback empty dict if file not found
    UKRAINIAN_DIMINUTIVES = {}

# Export for backward compatibility
__all__ = ["UKRAINIAN_DIMINUTIVES"]
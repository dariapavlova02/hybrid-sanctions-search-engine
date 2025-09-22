"""
Russian diminutives dictionary
Loads data from JSON file to maintain compatibility
"""

import json
from pathlib import Path

# Load Russian diminutives from JSON file
_data_dir = Path(__file__).parent.parent.parent.parent.parent / "data"
_diminutives_file = _data_dir / "diminutives_ru.json"

try:
    with open(_diminutives_file, "r", encoding="utf-8") as f:
        RUSSIAN_DIMINUTIVES = json.load(f)
except FileNotFoundError:
    # Fallback empty dict if file not found
    RUSSIAN_DIMINUTIVES = {}

# Export for backward compatibility
__all__ = ["RUSSIAN_DIMINUTIVES"]
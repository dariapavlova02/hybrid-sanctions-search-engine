"""
Base extractor class with common functionality.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ai_service.utils.logging_config import get_logger


class BaseExtractor(ABC):
    """Base class for entity extractors."""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def extract(self, text: str, **kwargs) -> List[Dict[str, Any]]:
        """Extract entities from text."""
        pass

    def _is_valid_text(self, text: str) -> bool:
        """Check if text is valid for extraction."""
        return text and text.strip()

    def _log_extraction_result(self, text: str, result_count: int, entity_type: str):
        """Log extraction results."""
        self.logger.debug(
            f"Extracted {result_count} {entity_type} entities from text: "
            f"{text[:50]}{'...' if len(text) > 50 else ''}"
        )

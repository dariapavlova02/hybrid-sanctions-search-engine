"""
Decomposed normalization service - stub implementation.
"""

from typing import Any, Dict, List
from .normalization_service import NormalizationService


class NormalizationServiceDecomposed(NormalizationService):
    """Decomposed version of normalization service."""

    def __init__(self, *args, **kwargs):
        """Initialize decomposed service."""
        super().__init__(*args, **kwargs)

    async def normalize_decomposed(self, text: str, config: Any = None) -> Dict[str, Any]:
        """Normalize with decomposed approach."""
        # Fallback to regular normalization
        result = await self.normalize(text, config)
        return {
            "normalized": result.normalized,
            "tokens": result.tokens,
            "success": result.success,
            "decomposed": True
        }
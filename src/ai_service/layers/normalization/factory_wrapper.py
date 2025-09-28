"""
Factory wrapper that provides NormalizationService interface using NormalizationFactory.
This enables morphological processing with proper name declension.
"""

from typing import Optional, Dict, Any
from ...contracts.base_contracts import NormalizationResult
from ...utils.logging_config import get_logger
from .processors.normalization_factory import NormalizationFactory, NormalizationConfig


class FactoryBasedNormalizationService:
    """
    Wrapper that provides NormalizationService interface using NormalizationFactory.

    This enables proper morphological processing and name declension that was
    disabled in the original NormalizationService.
    """

    def __init__(self):
        self.logger = get_logger(__name__)
        self.factory = NormalizationFactory()

    async def normalize_async(
        self,
        text: str,
        *,
        language: Optional[str] = None,
        remove_stop_words: bool = True,
        preserve_names: bool = True,
        enable_advanced_features: bool = True,
        user_id: Optional[str] = None,
        request_context: Optional[Dict] = None,
        **kwargs  # Accept any additional kwargs for compatibility
    ) -> NormalizationResult:
        """
        Normalize text using the factory with proper morphological processing.

        Args:
            text: Input text to normalize
            language: Language code (ru/uk/en)
            remove_stop_words: Whether to remove stop words
            preserve_names: Whether to preserve name formatting
            enable_advanced_features: Whether to enable morphology
            user_id: Optional user ID for tracking
            request_context: Optional request context

        Returns:
            NormalizationResult with proper morphological processing
        """
        try:
            # Create configuration for factory
            config = NormalizationConfig(
                language=language or "ru",  # Default to Russian
                remove_stop_words=remove_stop_words,
                preserve_names=preserve_names,
                enable_advanced_features=enable_advanced_features,
                enable_fsm_tuned_roles=True  # Always enable FSM for proper role classification
            )

            # Log what we're doing
            self.logger.debug(
                f"FactoryWrapper: normalizing '{text}' with config: "
                f"lang={config.language}, advanced={config.enable_advanced_features}, "
                f"fsm={getattr(config, 'enable_fsm_tuned_roles', False)}"
            )

            # Use factory to normalize
            result = await self.factory.normalize_text(text, config)

            self.logger.debug(
                f"FactoryWrapper: normalized '{text}' -> '{result.normalized}' "
                f"(success={result.success}, tokens={len(result.tokens)})"
            )

            return result

        except Exception as e:
            self.logger.error(f"FactoryWrapper error normalizing '{text}': {e}", exc_info=True)
            # Return empty result on error
            return NormalizationResult(
                normalized="",
                tokens=[],
                trace=[],
                errors=[str(e)],
                language=language or "ru",
                confidence=0.0,
                original_length=len(text),
                normalized_length=0,
                token_count=0,
                processing_time=0.0,
                success=False
            )
"""
Legacy Normalization Adapter

This adapter provides backward compatibility for old normalization APIs
and converts between different result formats.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Union

from ..contracts.base_contracts import NormalizationResult, UnifiedProcessingResult
from ..exceptions import NormalizationError
from ..layers.normalization.normalization_service import NormalizationService
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class LegacyNormalizationAdapter:
    """
    Adapter for legacy normalization API compatibility.

    This adapter bridges the gap between old and new normalization APIs,
    providing format conversion and backward compatibility.
    """

    def __init__(self, normalization_service: Optional[NormalizationService] = None):
        """
        Initialize the legacy adapter.

        Args:
            normalization_service: Optional normalization service instance
        """
        self.normalization_service = normalization_service or NormalizationService()
        self.logger = get_logger(__name__)

    # Legacy format conversion methods
    def convert_to_legacy_format(self, result: NormalizationResult) -> Dict[str, Any]:
        """
        Convert new NormalizationResult to legacy format.

        Args:
            result: New format NormalizationResult

        Returns:
            Legacy format dictionary
        """
        return {
            "normalized_text": result.normalized,
            "original_text": getattr(result, 'original_text', ''),
            "tokens": result.tokens or [],
            "language": result.language or "auto",
            "confidence": result.confidence or 0.0,
            "success": result.success,
            "processing_time": result.processing_time,
            "error": result.errors[0] if result.errors else None,
            "trace": [
                {
                    "token": trace.token,
                    "role": trace.role,
                    "rule": trace.rule,
                    "output": trace.output,
                    "morph_lang": trace.morph_lang,
                    "normal_form": trace.normal_form,
                    "fallback": trace.fallback,
                    "notes": trace.notes,
                }
                for trace in (result.trace or [])
            ],
        }

    def convert_from_legacy_format(self, legacy_result: Dict[str, Any]) -> NormalizationResult:
        """
        Convert legacy format to new NormalizationResult.

        Args:
            legacy_result: Legacy format dictionary

        Returns:
            New format NormalizationResult
        """
        from ..contracts.base_contracts import TokenTrace

        traces = []
        if legacy_result.get("trace"):
            for trace_data in legacy_result["trace"]:
                traces.append(TokenTrace(
                    token=trace_data.get("token", ""),
                    role=trace_data.get("role", "unknown"),
                    rule=trace_data.get("rule"),
                    output=trace_data.get("output", ""),
                    morph_lang=trace_data.get("morph_lang"),
                    normal_form=trace_data.get("normal_form"),
                    fallback=trace_data.get("fallback", False),
                    notes=trace_data.get("notes"),
                ))

        return NormalizationResult(
            normalized=legacy_result.get("normalized_text", ""),
            tokens=legacy_result.get("tokens", []),
            trace=traces,
            errors=[legacy_result["error"]] if legacy_result.get("error") else [],
            language=legacy_result.get("language", "auto"),
            confidence=legacy_result.get("confidence"),
            original_length=len(legacy_result.get("original_text", "")),
            normalized_length=len(legacy_result.get("normalized_text", "")),
            token_count=len(legacy_result.get("tokens", [])),
            processing_time=legacy_result.get("processing_time", 0.0),
            success=legacy_result.get("success", True),
        )

    # Legacy API methods
    async def normalize_legacy(
        self,
        text: str,
        language: str = "auto",
        remove_stop_words: bool = True,
        preserve_names: bool = True,
        apply_lemmatization: bool = True,
        clean_unicode: bool = True,
        apply_stemming: bool = False,  # Legacy parameter, ignored
        **kwargs
    ) -> Dict[str, Any]:
        """
        Legacy normalization method that returns old format.

        Args:
            text: Input text to normalize
            language: Language code or 'auto'
            remove_stop_words: Whether to remove stop words
            preserve_names: Whether to preserve name formatting
            apply_lemmatization: Whether to apply morphological analysis
            clean_unicode: Whether to clean unicode (legacy parameter)
            apply_stemming: Legacy parameter, ignored
            **kwargs: Additional legacy parameters

        Returns:
            Legacy format result dictionary
        """
        try:
            start_time = time.time()

            # Convert legacy parameters to new format
            enable_advanced_features = apply_lemmatization

            # Call new normalization service
            result = await self.normalization_service.normalize_async(
                text=text,
                language=language,
                remove_stop_words=remove_stop_words,
                preserve_names=preserve_names,
                enable_advanced_features=enable_advanced_features,
            )

            # Convert to legacy format
            legacy_result = self.convert_to_legacy_format(result)
            legacy_result["original_text"] = text

            processing_time = time.time() - start_time
            legacy_result["processing_time"] = processing_time

            self.logger.debug(f"Legacy normalization completed in {processing_time:.3f}s")

            return legacy_result

        except Exception as e:
            self.logger.error(f"Legacy normalization failed: {e}")
            return {
                "normalized_text": "",
                "original_text": text,
                "tokens": [],
                "language": language,
                "confidence": 0.0,
                "success": False,
                "processing_time": time.time() - start_time,
                "error": str(e),
                "trace": [],
            }

    def normalize_legacy_sync(
        self,
        text: str,
        language: str = "auto",
        remove_stop_words: bool = True,
        preserve_names: bool = True,
        apply_lemmatization: bool = True,
        clean_unicode: bool = True,
        apply_stemming: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Synchronous legacy normalization method.

        Args:
            text: Input text to normalize
            language: Language code or 'auto'
            remove_stop_words: Whether to remove stop words
            preserve_names: Whether to preserve name formatting
            apply_lemmatization: Whether to apply morphological analysis
            clean_unicode: Whether to clean unicode (legacy parameter)
            apply_stemming: Legacy parameter, ignored
            **kwargs: Additional legacy parameters

        Returns:
            Legacy format result dictionary
        """
        try:
            # Run async method in sync context
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                # If loop is already running, we need to use a different approach
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.normalize_legacy(
                            text, language, remove_stop_words, preserve_names,
                            apply_lemmatization, clean_unicode, apply_stemming, **kwargs
                        )
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self.normalize_legacy(
                        text, language, remove_stop_words, preserve_names,
                        apply_lemmatization, clean_unicode, apply_stemming, **kwargs
                    )
                )

        except Exception as e:
            self.logger.error(f"Legacy sync normalization failed: {e}")
            return {
                "normalized_text": "",
                "original_text": text,
                "tokens": [],
                "language": language,
                "confidence": 0.0,
                "success": False,
                "processing_time": 0.0,
                "error": str(e),
                "trace": [],
            }

    # Batch processing for legacy API
    async def process_batch_legacy(
        self,
        texts: List[str],
        language: str = "auto",
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Legacy batch processing method.

        Args:
            texts: List of texts to process
            language: Language code or 'auto'
            **kwargs: Additional legacy parameters

        Returns:
            List of legacy format results
        """
        results = []
        for text in texts:
            result = await self.normalize_legacy(text, language, **kwargs)
            results.append(result)
        return results

    # Compatibility shims for old method names
    async def process_text(self, text: str, **kwargs) -> Dict[str, Any]:
        """Legacy alias for normalize_legacy"""
        return await self.normalize_legacy(text, **kwargs)

    def process_text_sync(self, text: str, **kwargs) -> Dict[str, Any]:
        """Legacy alias for normalize_legacy_sync"""
        return self.normalize_legacy_sync(text, **kwargs)

    # Health check for legacy adapter
    def health_check(self) -> Dict[str, Any]:
        """
        Health check for legacy adapter.

        Returns:
            Health status information
        """
        try:
            # Test basic functionality
            test_result = self.normalize_legacy_sync("тест", language="ru")

            return {
                "status": "healthy",
                "adapter_version": "1.0.0",
                "normalization_service": "available",
                "test_successful": test_result.get("success", False),
                "supported_formats": ["legacy_dict", "new_normalization_result"],
                "supported_methods": [
                    "normalize_legacy",
                    "normalize_legacy_sync",
                    "process_text",
                    "process_text_sync",
                    "process_batch_legacy"
                ]
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "adapter_version": "1.0.0",
            }
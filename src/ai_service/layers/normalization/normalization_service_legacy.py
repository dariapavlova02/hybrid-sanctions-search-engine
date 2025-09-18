#!/usr/bin/env python3
"""
Legacy Normalization Service Shim

This module provides a thin legacy shim for parity harness compatibility.
It wraps the current NormalizationService via LegacyNormalizationAdapter
to maintain backward compatibility with existing tests.

The shim ensures that:
- All async/sync methods are preserved
- The interface matches what parity tests expect
- No breaking changes to existing test infrastructure
"""

import asyncio
from typing import Any, Dict, Optional

from ...adapters.legacy_normalization_adapter import LegacyNormalizationAdapter
from .normalization_service import NormalizationService


class NormalizationServiceLegacy:
    """
    Legacy shim for NormalizationService.
    
    This class provides a thin wrapper around the current NormalizationService
    via LegacyNormalizationAdapter to maintain parity harness compatibility.
    """

    def __init__(self, normalization_service: Optional[NormalizationService] = None):
        """
        Initialize the legacy shim.
        
        Args:
            normalization_service: Optional NormalizationService instance.
                                 If None, creates a new instance.
        """
        self._normalization_service = normalization_service or NormalizationService()
        self._legacy_adapter = LegacyNormalizationAdapter(self._normalization_service)

    # Delegate all methods to the legacy adapter
    async def normalize_async(
        self,
        text: str,
        *,
        language: Optional[str] = None,
        remove_stop_words: bool = True,
        preserve_names: bool = True,
        enable_advanced_features: bool = True,
        **kwargs
    ) -> Any:
        """
        Async normalization method for parity compatibility.
        
        Args:
            text: Input text to normalize
            language: Language code (optional)
            remove_stop_words: Whether to remove stop words
            preserve_names: Whether to preserve names
            enable_advanced_features: Whether to enable advanced features
            **kwargs: Additional parameters
            
        Returns:
            Normalization result
        """
        return await self._legacy_adapter.normalize_legacy(
            text=text,
            language=language or "auto",
            remove_stop_words=remove_stop_words,
            preserve_names=preserve_names,
            apply_lemmatization=enable_advanced_features,
            **kwargs
        )

    def normalize_sync(
        self,
        text: str,
        *,
        language: Optional[str] = None,
        remove_stop_words: bool = True,
        preserve_names: bool = True,
        enable_advanced_features: bool = True,
        **kwargs
    ) -> Any:
        """
        Sync normalization method for parity compatibility.
        
        Args:
            text: Input text to normalize
            language: Language code (optional)
            remove_stop_words: Whether to remove stop words
            preserve_names: Whether to preserve names
            enable_advanced_features: Whether to enable advanced features
            **kwargs: Additional parameters
            
        Returns:
            Normalization result
        """
        return self._legacy_adapter.normalize_legacy_sync(
            text=text,
            language=language or "auto",
            remove_stop_words=remove_stop_words,
            preserve_names=preserve_names,
            apply_lemmatization=enable_advanced_features,
            **kwargs
        )

    # Additional legacy methods for full compatibility
    async def normalize_legacy(
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
        Legacy async normalization method.
        
        Args:
            text: Input text to normalize
            language: Language code
            remove_stop_words: Whether to remove stop words
            preserve_names: Whether to preserve names
            apply_lemmatization: Whether to apply lemmatization
            clean_unicode: Whether to clean unicode
            apply_stemming: Whether to apply stemming (ignored)
            **kwargs: Additional parameters
            
        Returns:
            Legacy format dictionary
        """
        return await self._legacy_adapter.normalize_legacy(
            text=text,
            language=language,
            remove_stop_words=remove_stop_words,
            preserve_names=preserve_names,
            apply_lemmatization=apply_lemmatization,
            clean_unicode=clean_unicode,
            apply_stemming=apply_stemming,
            **kwargs
        )

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
        Legacy sync normalization method.
        
        Args:
            text: Input text to normalize
            language: Language code
            remove_stop_words: Whether to remove stop words
            preserve_names: Whether to preserve names
            apply_lemmatization: Whether to apply lemmatization
            clean_unicode: Whether to clean unicode
            apply_stemming: Whether to apply stemming (ignored)
            **kwargs: Additional parameters
            
        Returns:
            Legacy format dictionary
        """
        return self._legacy_adapter.normalize_legacy_sync(
            text=text,
            language=language,
            remove_stop_words=remove_stop_words,
            preserve_names=preserve_names,
            apply_lemmatization=apply_lemmatization,
            clean_unicode=clean_unicode,
            apply_stemming=apply_stemming,
            **kwargs
        )

    # Property access for backward compatibility
    @property
    def normalization_service(self) -> NormalizationService:
        """Access to the underlying normalization service."""
        return self._normalization_service

    @property
    def legacy_adapter(self) -> LegacyNormalizationAdapter:
        """Access to the legacy adapter."""
        return self._legacy_adapter

    # Delegate other common methods if needed
    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to the underlying service."""
        return getattr(self._normalization_service, name)


# Backward compatibility alias - use a different name to avoid circular import
LegacyNormalizationService = NormalizationServiceLegacy

__all__ = ["NormalizationServiceLegacy", "LegacyNormalizationService"]

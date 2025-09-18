#!/usr/bin/env python3
"""
Smoke test for legacy normalization service shim.

This test verifies that the legacy shim can be imported and
performs basic normalization calls without errors.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch

from src.ai_service.layers.normalization.normalization_service_legacy import (
    NormalizationServiceLegacy,
    LegacyNormalizationService
)


class TestLegacyShimSmoke:
    """Smoke tests for legacy shim compatibility."""

    def test_import_and_instantiation(self):
        """Test that the legacy shim can be imported and instantiated."""
        # Test direct import
        from src.ai_service.layers.normalization.normalization_service_legacy import NormalizationServiceLegacy
        
        # Test instantiation
        service = NormalizationServiceLegacy()
        assert service is not None
        assert hasattr(service, 'normalize_async')
        assert hasattr(service, 'normalize_sync')
        assert hasattr(service, 'normalize_legacy')
        assert hasattr(service, 'normalize_legacy_sync')

    def test_alias_import(self):
        """Test that the LegacyNormalizationService alias works."""
        # Test alias import
        from src.ai_service.layers.normalization.normalization_service_legacy import LegacyNormalizationService
        
        # Test instantiation via alias
        service = LegacyNormalizationService()
        assert service is not None
        assert isinstance(service, NormalizationServiceLegacy)

    @pytest.mark.asyncio
    async def test_async_method_call(self):
        """Test that async methods can be called without errors."""
        with patch('src.ai_service.layers.normalization.normalization_service_legacy.LegacyNormalizationAdapter') as mock_adapter:
            # Mock the adapter's normalize_legacy method to return a coroutine
            async def mock_normalize_legacy(*args, **kwargs):
                return {
                    "normalized_text": "Test Output",
                    "language": "en",
                    "confidence": 0.9
                }
            
            mock_adapter.return_value.normalize_legacy = mock_normalize_legacy
            
            service = NormalizationServiceLegacy()
            
            # Test async call
            result = await service.normalize_async(
                "Test Input",
                language="en",
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True
            )
            
            assert result is not None
            assert "normalized_text" in result

    def test_sync_method_call(self):
        """Test that sync methods can be called without errors."""
        with patch('src.ai_service.layers.normalization.normalization_service_legacy.LegacyNormalizationAdapter') as mock_adapter:
            # Mock the adapter's normalize_legacy_sync method
            mock_adapter.return_value.normalize_legacy_sync = Mock(return_value={
                "normalized_text": "Test Output",
                "language": "en",
                "confidence": 0.9
            })
            
            service = NormalizationServiceLegacy()
            
            # Test sync call
            result = service.normalize_sync(
                "Test Input",
                language="en",
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True
            )
            
            assert result is not None
            assert "normalized_text" in result

    def test_legacy_methods_call(self):
        """Test that legacy methods can be called without errors."""
        with patch('src.ai_service.layers.normalization.normalization_service_legacy.LegacyNormalizationAdapter') as mock_adapter:
            # Mock the adapter's methods
            mock_adapter.return_value.normalize_legacy_sync = Mock(return_value={
                "normalized_text": "Test Output",
                "language": "en",
                "confidence": 0.9
            })
            
            service = NormalizationServiceLegacy()
            
            # Test legacy sync call
            result = service.normalize_legacy_sync(
                "Test Input",
                language="en",
                remove_stop_words=True,
                preserve_names=True,
                apply_lemmatization=True,
                clean_unicode=True,
                apply_stemming=False
            )
            
            assert result is not None
            assert "normalized_text" in result

    def test_property_access(self):
        """Test that properties are accessible."""
        with patch('src.ai_service.layers.normalization.normalization_service_legacy.NormalizationService') as mock_service:
            with patch('src.ai_service.layers.normalization.normalization_service_legacy.LegacyNormalizationAdapter') as mock_adapter:
                service = NormalizationServiceLegacy()
                
                # Test property access
                assert hasattr(service, 'normalization_service')
                assert hasattr(service, 'legacy_adapter')
                
                # Test that properties return the expected types
                assert service.normalization_service is not None
                assert service.legacy_adapter is not None

    def test_delegation(self):
        """Test that unknown attributes are delegated to the underlying service."""
        with patch('src.ai_service.layers.normalization.normalization_service_legacy.NormalizationService') as mock_service:
            with patch('src.ai_service.layers.normalization.normalization_service_legacy.LegacyNormalizationAdapter'):
                # Mock a method on the underlying service
                mock_service.return_value.some_method = Mock(return_value="delegated")
                
                service = NormalizationServiceLegacy()
                
                # Test delegation
                result = service.some_method()
                assert result == "delegated"

    def test_parity_import_compatibility(self):
        """Test that the shim can be imported the way parity tests expect."""
        # This simulates how parity tests import the service
        try:
            from src.ai_service.layers.normalization.normalization_service_legacy import LegacyNormalizationService
            
            # Test that it can be instantiated
            service = LegacyNormalizationService()
            assert service is not None
            
            # Test that it has the expected methods
            assert hasattr(service, 'normalize_async')
            assert hasattr(service, 'normalize_sync')
            
        except ImportError as e:
            pytest.fail(f"Failed to import LegacyNormalizationService: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

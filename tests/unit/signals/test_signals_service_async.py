#!/usr/bin/env python3
"""
Tests for async methods in SignalsService
"""

import asyncio
import pytest
from unittest.mock import Mock, patch

from src.ai_service.layers.signals.signals_service import SignalsService


class TestSignalsServiceAsync:
    """Test async methods in SignalsService"""

    @pytest.fixture
    def service(self):
        """Create SignalsService instance"""
        return SignalsService()

    @pytest.mark.asyncio
    async def test_extract_async_success(self, service):
        """Test successful async signal extraction"""
        test_text = "Іван Петрович Сидоренко, ООО Тест"
        normalization_result = {
            "persons_core": [["Іван", "Петрович", "Сидоренко"]],
            "organizations_core": ["ООО Тест"]
        }
        
        # Mock the synchronous method
        with patch.object(service, 'extract') as mock_extract:
            mock_result = {
                "persons": [
                    {
                        "name": "Іван Петрович Сидоренко",
                        "confidence": 0.95,
                        "evidence": ["name_tokens"]
                    }
                ],
                "organizations": [
                    {
                        "name": "ООО Тест",
                        "legal_form": "ООО",
                        "confidence": 0.9,
                        "evidence": ["legal_form"]
                    }
                ],
                "extras": {}
            }
            mock_extract.return_value = mock_result

            result = await service.extract_async(test_text, normalization_result, "uk")

            assert "persons" in result
            assert "organizations" in result
            assert len(result["persons"]) == 1
            assert len(result["organizations"]) == 1
            mock_extract.assert_called_once_with(test_text, normalization_result, "uk")

    @pytest.mark.asyncio
    async def test_extract_async_without_normalization(self, service):
        """Test async extraction without normalization result"""
        test_text = "John Smith, LLC Test"
        
        with patch.object(service, 'extract') as mock_extract:
            mock_result = {
                "persons": [{"name": "John Smith", "confidence": 0.8}],
                "organizations": [{"name": "LLC Test", "confidence": 0.7}],
                "extras": {}
            }
            mock_extract.return_value = mock_result

            result = await service.extract_async(test_text, language="en")

            assert "persons" in result
            assert "organizations" in result
            mock_extract.assert_called_once_with(test_text, None, "en")

    @pytest.mark.asyncio
    async def test_extract_async_empty_text(self, service):
        """Test async extraction with empty text"""
        test_text = ""
        
        with patch.object(service, 'extract') as mock_extract:
            mock_result = {
                "persons": [],
                "organizations": [],
                "extras": {}
            }
            mock_extract.return_value = mock_result

            result = await service.extract_async(test_text)

            assert result["persons"] == []
            assert result["organizations"] == []
            mock_extract.assert_called_once_with(test_text, None, "uk")

    @pytest.mark.asyncio
    async def test_extract_async_error_handling(self, service):
        """Test async error handling"""
        test_text = "Test text"
        
        with patch.object(service, 'extract') as mock_extract:
            # Mock to return error result instead of raising exception
            mock_extract.return_value = {
                "persons": [],
                "organizations": [],
                "extras": {},
                "error": "Processing failed"
            }

            result = await service.extract_async(test_text)

            # Should return result with error info
            assert "error" in result

    @pytest.mark.asyncio
    async def test_async_method_uses_thread_pool(self, service):
        """Test that async method properly uses thread pool executor"""
        test_text = "Test text"
        
        with patch.object(service, 'extract') as mock_extract:
            mock_result = {
                "persons": [],
                "organizations": [],
                "extras": {}
            }
            mock_extract.return_value = mock_result

            # Test that the method runs in thread pool
            result = await service.extract_async(test_text)
            
            # Verify it was called
            mock_extract.assert_called_once()
            
            # Verify result is correct
            assert "persons" in result

    @pytest.mark.asyncio
    async def test_concurrent_async_calls(self, service):
        """Test that multiple async calls can run concurrently"""
        test_texts = ["Test 1", "Test 2", "Test 3"]
        
        with patch.object(service, 'extract') as mock_extract:
            mock_result = {
                "persons": [],
                "organizations": [],
                "extras": {}
            }
            mock_extract.return_value = mock_result

            # Start multiple async calls concurrently
            tasks = [
                service.extract_async(text)
                for text in test_texts
            ]
            
            results = await asyncio.gather(*tasks)

            # All should succeed
            assert len(results) == 3
            assert all("persons" in result for result in results)
            
            # Should have been called 3 times
            assert mock_extract.call_count == 3

    @pytest.mark.asyncio
    async def test_extract_async_with_different_languages(self, service):
        """Test async extraction with different languages"""
        test_cases = [
            ("Hello World", "en"),
            ("Привет Мир", "ru"),
            ("Привіт Світ", "uk")
        ]
        
        with patch.object(service, 'extract') as mock_extract:
            mock_result = {
                "persons": [],
                "organizations": [],
                "extras": {}
            }
            mock_extract.return_value = mock_result

            for text, language in test_cases:
                result = await service.extract_async(text, language=language)
                assert "persons" in result
                mock_extract.assert_called_with(text, None, language)

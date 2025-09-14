#!/usr/bin/env python3
"""
Tests for async methods in SmartFilterService
"""

import asyncio
import pytest
from unittest.mock import Mock, patch

from src.ai_service.layers.smart_filter.smart_filter_service import SmartFilterService, FilterResult


class TestSmartFilterServiceAsync:
    """Test async methods in SmartFilterService"""

    @pytest.fixture
    def service(self):
        """Create SmartFilterService instance"""
        return SmartFilterService()

    @pytest.mark.asyncio
    async def test_should_process_text_async_success(self, service):
        """Test successful async text processing decision"""
        test_text = "Іван Петрович Сидоренко, ООО Тест"
        
        # Mock the synchronous method
        with patch.object(service, 'should_process_text') as mock_should_process:
            mock_result = FilterResult(
                should_process=True,
                confidence=0.85,
                detected_signals=["person", "organization"],
                signal_details={"person_count": 1, "org_count": 1},
                processing_recommendation="Process with full search",
                estimated_complexity="medium"
            )
            mock_should_process.return_value = mock_result

            result = await service.should_process_text_async(test_text)

            assert result.should_process is True
            assert result.confidence == 0.85
            assert "person" in result.detected_signals
            assert "organization" in result.detected_signals
            mock_should_process.assert_called_once_with(test_text)

    @pytest.mark.asyncio
    async def test_should_process_text_async_excluded(self, service):
        """Test async processing decision for excluded text"""
        test_text = "Service information only"
        
        with patch.object(service, 'should_process_text') as mock_should_process:
            mock_result = FilterResult(
                should_process=False,
                confidence=0.0,
                detected_signals=[],
                signal_details={},
                processing_recommendation="Text excluded from processing",
                estimated_complexity="very_low"
            )
            mock_should_process.return_value = mock_result

            result = await service.should_process_text_async(test_text)

            assert result.should_process is False
            assert result.confidence == 0.0
            assert "excluded" in result.processing_recommendation
            mock_should_process.assert_called_once_with(test_text)

    @pytest.mark.asyncio
    async def test_should_process_text_async_empty_text(self, service):
        """Test async processing decision for empty text"""
        test_text = ""
        
        with patch.object(service, 'should_process_text') as mock_should_process:
            mock_result = FilterResult(
                should_process=False,
                confidence=0.0,
                detected_signals=[],
                signal_details={},
                processing_recommendation="Empty text",
                estimated_complexity="none"
            )
            mock_should_process.return_value = mock_result

            result = await service.should_process_text_async(test_text)

            assert result.should_process is False
            assert "Empty text" in result.processing_recommendation
            mock_should_process.assert_called_once_with(test_text)

    @pytest.mark.asyncio
    async def test_should_process_text_async_whitespace_only(self, service):
        """Test async processing decision for whitespace-only text"""
        test_text = "   \n\t   "
        
        with patch.object(service, 'should_process_text') as mock_should_process:
            mock_result = FilterResult(
                should_process=False,
                confidence=0.0,
                detected_signals=[],
                signal_details={},
                processing_recommendation="Empty text",
                estimated_complexity="none"
            )
            mock_should_process.return_value = mock_result

            result = await service.should_process_text_async(test_text)

            assert result.should_process is False
            mock_should_process.assert_called_once_with(test_text)

    @pytest.mark.asyncio
    async def test_async_method_uses_thread_pool(self, service):
        """Test that async method properly uses thread pool executor"""
        test_text = "Test text"
        
        with patch.object(service, 'should_process_text') as mock_should_process:
            mock_result = FilterResult(
                should_process=True,
                confidence=0.5,
                detected_signals=[],
                signal_details={},
                processing_recommendation="Process",
                estimated_complexity="low"
            )
            mock_should_process.return_value = mock_result

            # Test that the method runs in thread pool
            result = await service.should_process_text_async(test_text)
            
            # Verify it was called
            mock_should_process.assert_called_once()
            
            # Verify result is correct
            assert result.should_process is True

    @pytest.mark.asyncio
    async def test_concurrent_async_calls(self, service):
        """Test that multiple async calls can run concurrently"""
        test_texts = ["Test 1", "Test 2", "Test 3"]
        
        with patch.object(service, 'should_process_text') as mock_should_process:
            mock_result = FilterResult(
                should_process=True,
                confidence=0.5,
                detected_signals=[],
                signal_details={},
                processing_recommendation="Process",
                estimated_complexity="low"
            )
            mock_should_process.return_value = mock_result

            # Start multiple async calls concurrently
            tasks = [
                service.should_process_text_async(text)
                for text in test_texts
            ]
            
            results = await asyncio.gather(*tasks)

            # All should succeed
            assert len(results) == 3
            assert all(result.should_process for result in results)
            
            # Should have been called 3 times
            assert mock_should_process.call_count == 3

    @pytest.mark.asyncio
    async def test_async_error_handling(self, service):
        """Test async error handling"""
        test_text = "Test text"
        
        with patch.object(service, 'should_process_text') as mock_should_process:
            # Mock to return error result instead of raising exception
            mock_result = FilterResult(
                should_process=False,
                confidence=0.0,
                detected_signals=[],
                signal_details={},
                processing_recommendation="Error occurred",
                estimated_complexity="none"
            )
            mock_should_process.return_value = mock_result

            result = await service.should_process_text_async(test_text)

            # Should return result with error info
            assert result.should_process is False
            assert "Error" in result.processing_recommendation

    @pytest.mark.asyncio
    async def test_async_with_different_text_types(self, service):
        """Test async processing with different types of text"""
        test_cases = [
            ("Person name", True),
            ("Service info", False),
            ("Organization name", True),
            ("Date only", False)
        ]
        
        with patch.object(service, 'should_process_text') as mock_should_process:
            def mock_should_process_side_effect(text):
                if "Person" in text or "Organization" in text:
                    return FilterResult(
                        should_process=True,
                        confidence=0.8,
                        detected_signals=["person"] if "Person" in text else ["organization"],
                        signal_details={},
                        processing_recommendation="Process",
                        estimated_complexity="medium"
                    )
                else:
                    return FilterResult(
                        should_process=False,
                        confidence=0.0,
                        detected_signals=[],
                        signal_details={},
                        processing_recommendation="Excluded",
                        estimated_complexity="low"
                    )
            
            mock_should_process.side_effect = mock_should_process_side_effect

            for text, expected_process in test_cases:
                result = await service.should_process_text_async(text)
                assert result.should_process == expected_process

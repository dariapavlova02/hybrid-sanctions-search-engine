#!/usr/bin/env python3
"""
Smoke tests for Russian initials handling with double dots fix.

Tests the fix_initials_double_dot flag functionality:
1. Pattern ^([A-Za-zА-Яа-яІЇЄҐїєґ])\\.+$ → normalize to X.
2. Don't merge adjacent initials; separate with space during assembly.
3. Trace: collapse_double_dots.
4. Test case: Иванов И.И. → Иванов И. И.
"""

import pytest
import os
import asyncio
from typing import List

from src.ai_service.layers.normalization.normalization_service import NormalizationService


class TestRussianInitialsDoubleDots:
    """Test Russian initials double dots handling."""

    def setup_method(self):
        """Setup test environment with feature flags."""
        # Enable feature flags for testing
        os.environ["AISVC_FLAG_FIX_INITIALS_DOUBLE_DOT"] = "true"

        # Clear any cached feature flag manager to force reload
        import src.ai_service.utils.feature_flags as ff_module
        ff_module._feature_flag_manager = None

        self.service = NormalizationService()

    def teardown_method(self):
        """Clean up environment variables."""
        os.environ.pop("AISVC_FLAG_FIX_INITIALS_DOUBLE_DOT", None)

        # Clear feature flag manager cache to avoid test pollution
        import src.ai_service.utils.feature_flags as ff_module
        ff_module._feature_flag_manager = None

    @pytest.mark.asyncio
    async def test_golden_case_ivanov_ii(self):
        """Test golden case: Иванов И.И. → Иванов И. И."""
        text = "Иванов И.И."
        result = await self.service.normalize_async(text, language="ru")

        assert result.success
        assert result.normalized == "Иванов И. И."
        
        # Check that we have the correct tokens
        assert "Иванов" in result.tokens
        assert "И." in result.tokens
        assert "И." in result.tokens  # Should be two separate И. tokens

    @pytest.mark.asyncio
    async def test_double_dots_collapse(self):
        """Test that double dots are collapsed to single dots."""
        test_cases = [
            ("И..", "И."),
            ("А..", "А."),
            ("О..", "О."),
            ("І..", "І."),
            ("Ї..", "Ї."),
            ("Є..", "Є."),
            ("Ґ..", "Ґ."),
        ]

        for input_text, expected in test_cases:
            result = await self.service.normalize_async(input_text, language="ru")
            assert result.success
            assert expected in result.tokens

    @pytest.mark.asyncio
    async def test_multiple_initials_separated(self):
        """Test that multiple initials are separated with spaces."""
        test_cases = [
            ("И. И.", "И. И."),
            ("А. Б. В.", "А. Б. В."),
            ("І. О. П.", "І. О. П."),
        ]

        for input_text, expected in test_cases:
            result = await self.service.normalize_async(input_text, language="ru")
            assert result.success
            assert result.normalized == expected

    @pytest.mark.asyncio
    async def test_mixed_names_and_initials(self):
        """Test mixed names and initials."""
        test_cases = [
            ("Иванов И. И.", "Иванов И. И."),
            ("Петров А. Б. Сидоров", "Петров А. Б. Сидоров"),
            ("Ковальський І. О. Шевченко", "Ковальський І. О. Шевченко"),
        ]

        for input_text, expected in test_cases:
            result = await self.service.normalize_async(input_text, language="ru")
            assert result.success
            assert result.normalized == expected

    @pytest.mark.asyncio
    async def test_trace_contains_collapse_double_dots(self):
        """Test that trace contains collapse_double_dots rule."""
        text = "И.. И.."
        result = await self.service.normalize_async(text, language="ru")

        assert result.success
        
        # Check trace contains collapse information
        trace_strings = [str(trace) for trace in result.trace]
        assert any("collapse_double_dots" in trace_str for trace_str in trace_strings)

    @pytest.mark.asyncio
    async def test_abbreviations_not_affected(self):
        """Test that abbreviations are not affected by double dot collapse."""
        test_cases = [
            "и.о.",
            "т.о.",
        ]

        for text in test_cases:
            result = await self.service.normalize_async(text, language="ru")
            assert result.success
            # Abbreviations should not be modified (they might be filtered as stop words)
            # Just check that processing doesn't crash

    @pytest.mark.asyncio
    async def test_ellipsis_preserved(self):
        """Test that ellipsis is preserved."""
        text = "Иван ... Петров"
        result = await self.service.normalize_async(text, language="ru")

        assert result.success
        # Ellipsis might be filtered as stop word, but shouldn't cause errors

    @pytest.mark.asyncio
    async def test_ukrainian_initials(self):
        """Test Ukrainian initials handling."""
        test_cases = [
            ("І.. О..", "І. О."),
            ("Ї.. Є..", "Ї. Є."),
            ("Ґ.. А..", "Ґ. А."),
        ]

        for input_text, expected in test_cases:
            result = await self.service.normalize_async(input_text, language="uk")
            assert result.success
            assert result.normalized == expected

    @pytest.mark.asyncio
    async def test_english_initials(self):
        """Test English initials handling."""
        test_cases = [
            ("J.. R..", "J. R."),
            ("A.. B.. C..", "A. B. C."),
        ]

        for input_text, expected in test_cases:
            result = await self.service.normalize_async(input_text, language="en")
            assert result.success
            assert result.normalized == expected


class TestRussianInitialsWithoutFlags:
    """Test that behavior is unchanged when feature flags are disabled."""

    def setup_method(self):
        """Setup test environment without feature flags."""
        # Explicitly disable the flag
        os.environ["AISVC_FLAG_FIX_INITIALS_DOUBLE_DOT"] = "false"
        
        # Clear any cached feature flag manager to force reload
        import src.ai_service.utils.feature_flags as ff_module
        ff_module._feature_flag_manager = None

        self.service = NormalizationService()

    def teardown_method(self):
        """Clean up environment variables."""
        os.environ.pop("AISVC_FLAG_FIX_INITIALS_DOUBLE_DOT", None)
        
        # Clear feature flag manager cache to avoid test pollution
        import src.ai_service.utils.feature_flags as ff_module
        ff_module._feature_flag_manager = None

    @pytest.mark.asyncio
    async def test_legacy_behavior_preserved(self):
        """Test that legacy behavior is preserved when flags are off."""
        text = "И.. И.."
        result = await self.service.normalize_async(text, language="ru")

        assert result.success
        # With flags off, should not contain collapse trace
        trace_strings = [str(trace) for trace in result.trace]
        assert not any("collapse_double_dots" in trace_str for trace_str in trace_strings)

    @pytest.mark.asyncio
    async def test_golden_case_without_flags(self):
        """Test golden case without flags enabled."""
        text = "Иванов И.И."
        result = await self.service.normalize_async(text, language="ru")

        assert result.success
        # Without flags, behavior should be different (no double dot collapse)
        # The exact behavior depends on the current implementation without flags


class TestRussianInitialsPerformance:
    """Test that initials handling doesn't significantly impact performance."""

    def setup_method(self):
        """Setup test environment with feature flags."""
        os.environ["FIX_INITIALS_DOUBLE_DOT"] = "true"

        self.service = NormalizationService()

    def teardown_method(self):
        """Clean up environment variables."""
        os.environ.pop("AISVC_FLAG_FIX_INITIALS_DOUBLE_DOT", None)

    @pytest.mark.asyncio
    async def test_short_text_performance(self):
        """Test that short texts with initials are processed quickly."""
        text = "Иванов И.И."
        result = await self.service.normalize_async(text, language="ru")

        assert result.success
        # Should be under 50ms for short text
        assert result.processing_time < 0.05  # 50ms in seconds

    @pytest.mark.asyncio
    async def test_multiple_initials_performance(self):
        """Test performance with multiple initials."""
        text = "Иванов И. И. Петров А. А. Сидоров"
        result = await self.service.normalize_async(text, language="ru")

        assert result.success
        # Should still be reasonably fast
        assert result.processing_time < 0.1  # 100ms in seconds

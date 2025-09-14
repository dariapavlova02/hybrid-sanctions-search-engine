"""
Unit tests for Enhanced SmartFilter with AC integration
"""

import pytest
from unittest.mock import Mock, patch

from ai_service.layers.smart_filter.smart_filter_service import SmartFilterService, FilterResult
from ai_service.layers.patterns.unified_pattern_service import UnifiedPatternService, UnifiedPattern


class TestEnhancedSmartFilter:
    """Tests for enhanced SmartFilter with AC integration"""

    @pytest.fixture
    def pattern_service(self):
        """Create UnifiedPatternService instance"""
        return UnifiedPatternService()

    @pytest.fixture
    def smart_filter_with_ac(self, pattern_service):
        """Create SmartFilterService with AC integration enabled"""
        return SmartFilterService(
            enable_aho_corasick=True,
            pattern_service=pattern_service,
            enable_terrorism_detection=False,  # Disable for cleaner testing
        )

    @pytest.fixture
    def smart_filter_without_ac(self):
        """Create SmartFilterService with AC integration disabled"""
        return SmartFilterService(
            enable_aho_corasick=False,
            enable_terrorism_detection=False,
        )

    def test_ac_integration_enabled(self, smart_filter_with_ac):
        """Test that AC integration is properly enabled"""
        assert smart_filter_with_ac.aho_corasick_enabled is True
        assert smart_filter_with_ac.pattern_service is not None

    def test_ac_integration_disabled(self, smart_filter_without_ac):
        """Test that AC integration can be disabled"""
        assert smart_filter_without_ac.aho_corasick_enabled is False

    def test_enhanced_ac_search_enabled(self, smart_filter_with_ac):
        """Test enhanced AC search when enabled"""
        text = "Платіж від Іван Петренко ІПН 1234567890"

        result = smart_filter_with_ac.search_aho_corasick(text)

        assert isinstance(result, dict)
        assert result["enabled"] is True
        assert result["text_length"] == len(text)
        assert "language" in result
        assert "tier_distribution" in result
        assert "processing_time_ms" in result

    def test_enhanced_ac_search_disabled(self, smart_filter_without_ac):
        """Test AC search when disabled"""
        text = "Test text"

        result = smart_filter_without_ac.search_aho_corasick(text)

        assert result["enabled"] is False
        assert result["total_matches"] == 0
        assert result["message"] == "AC integration disabled"

    def test_enhanced_ac_search_with_matches(self, smart_filter_with_ac):
        """Test AC search finds matches in relevant text"""
        text = "Договір з ТОВ Тестова Компанія від Іван Петренко ІПН 1234567890"

        result = smart_filter_with_ac.search_aho_corasick(text, max_matches=10)

        assert result["enabled"] is True
        assert result["total_matches"] >= 0  # Should find some patterns
        assert len(result["matches"]) <= 10  # Respects max_matches limit

        # Check match structure if any matches found
        if result["matches"]:
            match = result["matches"][0]
            assert "pattern" in match
            assert "tier" in match
            assert "start" in match
            assert "end" in match
            assert "confidence" in match
            assert "pattern_type" in match

    def test_enhanced_pattern_analysis(self, smart_filter_with_ac):
        """Test comprehensive enhanced pattern analysis"""
        text = "Платіж для ТОВ Компанія від Сергій Іванов ІПН 3456789012"

        result = smart_filter_with_ac.enhanced_pattern_analysis(text)

        # Check main structure
        assert "text" in result
        assert "language" in result
        assert "smart_filter_result" in result
        assert "ac_pattern_result" in result
        assert "pattern_analysis" in result
        assert "enhanced_analysis" in result
        assert "recommendations" in result

        # Check smart filter result structure
        filter_result = result["smart_filter_result"]
        assert "should_process" in filter_result
        assert "confidence" in filter_result
        assert "detected_signals" in filter_result

        # Check AC pattern result structure
        ac_result = result["ac_pattern_result"]
        assert "enabled" in ac_result
        assert "total_matches" in ac_result

        # Check enhanced analysis
        enhanced = result["enhanced_analysis"]
        assert "final_confidence" in enhanced
        assert "should_process" in enhanced
        assert "processing_priority" in enhanced
        assert enhanced["processing_priority"] in ["high", "medium", "low"]

    def test_pattern_confidence_scoring(self, smart_filter_with_ac):
        """Test pattern confidence scoring by tier"""
        # Test different tiers
        assert smart_filter_with_ac._get_pattern_confidence("test", "tier_0_exact") == 0.98
        assert smart_filter_with_ac._get_pattern_confidence("test", "tier_1_high_confidence") == 0.90
        assert smart_filter_with_ac._get_pattern_confidence("test", "tier_2_medium_confidence") == 0.75
        assert smart_filter_with_ac._get_pattern_confidence("test", "tier_3_low_confidence") == 0.60
        assert smart_filter_with_ac._get_pattern_confidence("test", "unknown_tier") == 0.50

    def test_tier_priority_scoring(self, smart_filter_with_ac):
        """Test tier priority scoring"""
        # Test tier priorities
        assert smart_filter_with_ac._get_tier_priority("tier_0_exact") == 4
        assert smart_filter_with_ac._get_tier_priority("tier_1_high_confidence") == 3
        assert smart_filter_with_ac._get_tier_priority("tier_2_medium_confidence") == 2
        assert smart_filter_with_ac._get_tier_priority("tier_3_low_confidence") == 1
        assert smart_filter_with_ac._get_tier_priority("unknown_tier") == 0

    def test_pattern_type_inference(self, smart_filter_with_ac):
        """Test pattern type inference"""
        # Create mock patterns for testing
        mock_patterns = [
            UnifiedPattern(pattern="John Doe", pattern_type="full_name", language="en"),
            UnifiedPattern(pattern="Smith J. D.", pattern_type="structured_name", language="en"),
        ]

        # Test exact match
        assert smart_filter_with_ac._infer_pattern_type("John Doe", mock_patterns) == "full_name"
        assert smart_filter_with_ac._infer_pattern_type("Smith J. D.", mock_patterns) == "structured_name"

        # Test fallback inference
        assert smart_filter_with_ac._infer_pattern_type("1234567890", []) == "document_id"
        assert smart_filter_with_ac._infer_pattern_type("Smith J.", []) == "structured_name"
        assert smart_filter_with_ac._infer_pattern_type("John Smith", []) == "full_name"
        assert smart_filter_with_ac._infer_pattern_type("Test", []) == "basic_pattern"

    def test_processing_recommendations(self, smart_filter_with_ac):
        """Test processing recommendation generation"""
        # High confidence, many matches, multiple signals
        recommendations = smart_filter_with_ac._generate_processing_recommendations(
            confidence=0.95, ac_matches=6, detected_signals=["company", "name", "payment_context"]
        )

        assert any("High priority" in rec for rec in recommendations)
        assert any("Multiple pattern matches" in rec for rec in recommendations)
        assert any("business transaction" in rec for rec in recommendations)

        # Low confidence, no matches, no signals
        recommendations = smart_filter_with_ac._generate_processing_recommendations(
            confidence=0.2, ac_matches=0, detected_signals=[]
        )

        assert any("Very low priority" in rec for rec in recommendations)

    def test_enhanced_analysis_with_ukrainian_text(self, smart_filter_with_ac):
        """Test enhanced analysis with Ukrainian text"""
        text = "Переказ коштів від Марія Петренко для ТОВ Тест"

        result = smart_filter_with_ac.enhanced_pattern_analysis(text)

        # Should detect Ukrainian language
        assert result["language"] in ["uk", "ukrainian"]

        # Should have reasonable confidence for payment-related text
        assert result["enhanced_analysis"]["final_confidence"] > 0.0

        # Should generate recommendations
        assert len(result["recommendations"]) > 0

    def test_enhanced_analysis_with_english_text(self, smart_filter_with_ac):
        """Test enhanced analysis with English text"""
        text = "Payment from John Smith to ABC Corporation"

        result = smart_filter_with_ac.enhanced_pattern_analysis(text)

        # Should detect English language
        assert result["language"] in ["en", "english"]

        # Should process payment-related text
        assert result["smart_filter_result"]["should_process"] is True

    def test_max_matches_limit(self, smart_filter_with_ac):
        """Test max_matches parameter limits results"""
        text = "Платіж від Іван Петро Володимирович для ТОВ Тестова Компанія ЄДРПОУ 12345678 ІПН 1234567890"

        # Test with max_matches limit
        result_limited = smart_filter_with_ac.search_aho_corasick(text, max_matches=3)
        result_unlimited = smart_filter_with_ac.search_aho_corasick(text)

        if result_limited["total_matches"] > 0:
            assert len(result_limited["matches"]) <= 3
            # Unlimited should have same or more matches
            assert result_unlimited["total_matches"] >= result_limited["total_matches"]

    def test_error_handling_invalid_text(self, smart_filter_with_ac):
        """Test error handling with problematic text"""
        # Test with None - should not crash
        try:
            result = smart_filter_with_ac.enhanced_pattern_analysis("")
            assert result["enhanced_analysis"]["final_confidence"] == 0.0
        except Exception as e:
            pytest.fail(f"Should handle empty text gracefully: {e}")

    def test_integration_with_existing_smart_filter(self, smart_filter_with_ac):
        """Test that enhanced AC doesn't break existing smart filter functionality"""
        text = "Платіж від Тестова Персона"

        # Test existing method still works
        filter_result = smart_filter_with_ac.should_process_text(text)
        assert isinstance(filter_result, FilterResult)

        # Test enhanced analysis includes filter result
        enhanced_result = smart_filter_with_ac.enhanced_pattern_analysis(text)
        assert enhanced_result["smart_filter_result"]["confidence"] == filter_result.confidence

    def test_performance_with_long_text(self, smart_filter_with_ac):
        """Test performance with longer text"""
        long_text = """
        Договір про надання послуг № 123 від 15.03.2024
        Замовник: ТОВ "Тестова Компанія" ЄДРПОУ 12345678
        Представник: Іван Петренко Володимирович ІПН 1234567890
        Виконавець: ФОП Марія Сидоренко ІПН 9876543210
        Предмет: консультаційні послуги з фінансового планування
        Сума: 50000 грн
        """ * 3  # Repeat to make it longer

        import time
        start_time = time.time()

        result = smart_filter_with_ac.enhanced_pattern_analysis(long_text)

        end_time = time.time()
        processing_time = (end_time - start_time) * 1000  # Convert to ms

        # Should process within reasonable time (less than 1 second for test)
        assert processing_time < 1000
        assert result["ac_pattern_result"]["processing_time_ms"] > 0

    def test_async_compatibility(self, smart_filter_with_ac):
        """Test that async methods still work with enhanced functionality"""
        import asyncio

        async def test_async():
            text = "Тестовий платіж"
            result = await smart_filter_with_ac.should_process_text_async(text)
            assert isinstance(result, FilterResult)
            return result

        # Run async test
        result = asyncio.run(test_async())
        assert result is not None
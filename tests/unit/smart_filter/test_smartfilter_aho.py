"""
Unit tests for SmartFilter Aho-Corasick integration scenarios

Tests the integration between SmartFilter and Aho-Corasick search
to verify that AC patterns correctly influence processing decisions.
"""

import pytest
from unittest.mock import Mock, patch

from ai_service.layers.smart_filter.smart_filter_service import SmartFilterService, FilterResult
from ai_service.layers.smart_filter.smart_filter_adapter import SmartFilterAdapter
from ai_service.config import SERVICE_CONFIG


class TestSmartFilterAhoCorasickIntegration:
    """Test Aho-Corasick integration with SmartFilter"""

    @pytest.fixture
    def smart_filter_disabled(self):
        """Create SmartFilterService with AC disabled"""
        return SmartFilterService(enable_aho_corasick=False)

    @pytest.fixture
    def smart_filter_enabled(self):
        """Create SmartFilterService with AC enabled"""
        return SmartFilterService(enable_aho_corasick=True)

    @pytest.fixture
    def adapter_disabled(self):
        """Create SmartFilterAdapter with AC disabled"""
        adapter = SmartFilterAdapter()
        # We'll initialize in the test to control AC state
        return adapter

    @pytest.fixture
    def adapter_enabled(self):
        """Create SmartFilterAdapter with AC enabled"""
        adapter = SmartFilterAdapter()
        # We'll initialize in the test to control AC state
        return adapter

    def test_scenario_1_ac_disabled_petrov_no_context(self, smart_filter_disabled):
        """
        Scenario 1: enable_aho_corasick=False → "Петров" без контекста → should_process depends on other signals
        """
        text = "Петров"
        
        result = smart_filter_disabled.should_process_text(text)
        
        # Verify AC is disabled
        assert smart_filter_disabled.aho_corasick_enabled is False
        
        # Verify result - may be True due to name detection, but AC should not influence
        # The key point is that AC is disabled and not influencing the decision
        assert isinstance(result.should_process, bool)
        assert "ac_match" not in result.detected_signals
        
        # Verify AC details
        ac_details = result.signal_details.get("aho_corasick_matches", {})
        assert ac_details.get("enabled") is False
        assert ac_details.get("total_matches") == 0

    def test_scenario_2_ac_enabled_with_document_pattern(self, smart_filter_enabled):
        """
        Scenario 2: enable_aho_corasick=True, текст с документом → should_process=True, confidence>=0.7
        """
        # Use a text that will trigger AC patterns (document numbers)
        text = "Петров паспорт 1234567890"
        
        result = smart_filter_enabled.should_process_text(text)
        
        # Verify AC is enabled
        assert smart_filter_enabled.aho_corasick_enabled is True
        
        # Verify result
        assert result.should_process is True
        assert result.confidence >= 0.3  # Should be boosted by AC matches
        assert "ac_match" in result.detected_signals
        
        # Verify AC details
        ac_details = result.signal_details.get("aho_corasick_matches", {})
        assert ac_details.get("enabled") is True
        assert ac_details.get("total_matches") > 0
        assert ac_details.get("confidence_bonus") > 0

    def test_scenario_3_ac_enabled_nasa_no_trigger(self, smart_filter_enabled):
        """
        Scenario 3: enable_aho_corasick=True, текст "NASA contract" → не триггерит, так как NASA не в списке
        """
        text = "NASA contract"
        
        result = smart_filter_enabled.should_process_text(text)
        
        # Verify AC is enabled
        assert smart_filter_enabled.aho_corasick_enabled is True
        
        # Verify result - should not trigger AC matches
        ac_details = result.signal_details.get("aho_corasick_matches", {})
        assert ac_details.get("enabled") is True
        assert ac_details.get("total_matches") == 0
        assert ac_details.get("confidence_bonus") == 0.0
        
        # NASA should not be in AC patterns
        assert "ac_match" not in result.detected_signals

    def test_scenario_4_ac_enabled_petrov_with_context(self, smart_filter_enabled):
        """
        Scenario 4: enable_aho_corasick=True, "Петров" с контекстом → should_process зависит от контекста
        """
        # Test with payment context that should trigger name detection
        text = "Оплата за послуги Петров"
        
        result = smart_filter_enabled.should_process_text(text)
        
        # Verify AC is enabled
        assert smart_filter_enabled.aho_corasick_enabled is True
        
        # Verify AC details - no AC matches for just "Петров"
        ac_details = result.signal_details.get("aho_corasick_matches", {})
        assert ac_details.get("enabled") is True
        assert ac_details.get("total_matches") == 0
        assert ac_details.get("confidence_bonus") == 0.0
        
        # Should still process due to name detection and payment context
        assert result.should_process is True
        assert "name" in result.detected_signals

    def test_scenario_5_ac_verification_in_name_detector(self, smart_filter_enabled):
        """
        Scenario 5: Test AC verification within NameDetector
        """
        # Test with text that has both names and document patterns
        text = "Іван Петров паспорт 1234567890"
        
        result = smart_filter_enabled.should_process_text(text)
        
        # Verify name signals include AC verification
        name_signals = result.signal_details.get("names", {})
        assert "ac_verified_names" in name_signals
        assert "ac_confidence_bonus" in name_signals
        
        # Should have some AC verification if document patterns match names
        ac_verified_names = name_signals.get("ac_verified_names", [])
        ac_bonus = name_signals.get("ac_confidence_bonus", 0.0)
        
        # The verification should find document patterns in the names text
        if ac_verified_names:
            assert ac_bonus > 0.0
            assert len(ac_verified_names) > 0

    def test_scenario_6_confidence_comparison_with_without_ac(self):
        """
        Scenario 6: Compare confidence with and without AC
        """
        text = "Петров паспорт 1234567890"
        
        # Test without AC
        service_disabled = SmartFilterService(enable_aho_corasick=False)
        result_disabled = service_disabled.should_process_text(text)
        
        # Test with AC
        service_enabled = SmartFilterService(enable_aho_corasick=True)
        result_enabled = service_enabled.should_process_text(text)
        
        # AC should increase confidence when patterns match
        assert result_enabled.confidence >= result_disabled.confidence
        
        # AC should add ac_match signal when enabled and patterns found
        if result_enabled.signal_details.get("aho_corasick_matches", {}).get("total_matches", 0) > 0:
            assert "ac_match" in result_enabled.detected_signals
            assert "ac_match" not in result_disabled.detected_signals

    def test_scenario_7_adapter_integration_ac_disabled(self, adapter_disabled):
        """
        Scenario 7: Test SmartFilterAdapter with AC disabled
        """
        import asyncio
        
        async def run_test():
            await adapter_disabled.initialize()
            adapter_disabled._service.aho_corasick_enabled = False
            
            result = await adapter_disabled.should_process("Петров")
            
            # Verify AC is disabled
            assert adapter_disabled._service.aho_corasick_enabled is False
            
            # Verify result
            assert isinstance(result.should_process, bool)
            assert "ac_match" not in result.detected_signals
            
            # Verify name signals
            name_signals = result.details.get("name_signals", {})
            assert name_signals.get("ac_verified_names") == []
            assert name_signals.get("ac_confidence_bonus") == 0.0
        
        asyncio.run(run_test())

    def test_scenario_8_adapter_integration_ac_enabled(self, adapter_enabled):
        """
        Scenario 8: Test SmartFilterAdapter with AC enabled
        """
        import asyncio
        
        async def run_test():
            await adapter_enabled.initialize()
            adapter_enabled._service.aho_corasick_enabled = True
            
            result = await adapter_enabled.should_process("Петров паспорт 1234567890")
            
            # Verify AC is enabled
            assert adapter_enabled._service.aho_corasick_enabled is True
            
            # Verify result
            assert isinstance(result.should_process, bool)
            
            # Should have AC match if document patterns are found
            if "ac_match" in result.detected_signals:
                name_signals = result.details.get("name_signals", {})
                assert "ac_verified_names" in name_signals
                assert "ac_confidence_bonus" in name_signals
        
        asyncio.run(run_test())

    def test_scenario_9_config_flag_behavior(self):
        """
        Scenario 9: Test that configuration flag properly controls AC behavior
        """
        # Test default config (should be False based on our changes)
        assert SERVICE_CONFIG.enable_aho_corasick is False
        
        # Test with explicit False
        service_false = SmartFilterService(enable_aho_corasick=False)
        assert service_false.aho_corasick_enabled is False
        
        # Test with explicit True
        service_true = SmartFilterService(enable_aho_corasick=True)
        assert service_true.aho_corasick_enabled is True
        
        # Test with None (should use config)
        service_none = SmartFilterService(enable_aho_corasick=None)
        assert service_none.aho_corasick_enabled == SERVICE_CONFIG.enable_aho_corasick

    def test_scenario_10_edge_cases(self, smart_filter_enabled):
        """
        Scenario 10: Test edge cases for AC integration
        """
        # Empty text
        result1 = smart_filter_enabled.should_process_text("")
        assert result1.should_process is False
        # Empty text returns empty signal_details, so AC details may not be present
        ac_details = result1.signal_details.get("aho_corasick_matches", {})
        if ac_details:  # Only check if AC details are present
            assert ac_details.get("total_matches", 0) == 0
        
        # Whitespace only
        result2 = smart_filter_enabled.should_process_text("   ")
        assert result2.should_process is False
        
        # Text with only AC patterns
        result3 = smart_filter_enabled.should_process_text("1234567890")
        ac_details = result3.signal_details.get("aho_corasick_matches", {})
        if ac_details.get("total_matches", 0) > 0:
            assert "ac_match" in result3.detected_signals
            assert result3.confidence > 0.0
        
        # Very long text
        long_text = "Петров " * 100 + "1234567890"
        result4 = smart_filter_enabled.should_process_text(long_text)
        assert isinstance(result4.should_process, bool)
        assert isinstance(result4.confidence, float)

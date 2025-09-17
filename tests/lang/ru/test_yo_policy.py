#!/usr/bin/env python3
"""
Tests for Russian 'ё' policy (preserve/fold).

Tests that the 'ё' strategy correctly handles 'ё' characters
with proper tracing and conversion.
"""

import pytest
from src.ai_service.layers.normalization.morphology_adapter import MorphologyAdapter


class TestRussianYoPolicy:
    """Test Russian 'ё' policy implementation."""
    
    @pytest.fixture
    def morphology_adapter(self):
        """Create MorphologyAdapter instance."""
        return MorphologyAdapter()
    
    def test_preserve_strategy(self, morphology_adapter):
        """Test that 'preserve' strategy keeps 'ё' characters."""
        token = "Семён"
        processed, traces = morphology_adapter.apply_yo_strategy(token, "preserve")
        
        assert processed == "Семён"
        assert len(traces) == 1
        assert traces[0]["type"] == "yo"
        assert traces[0]["action"] == "preserve"
        assert traces[0]["from"] == "Семён"
        assert traces[0]["to"] == "Семён"
    
    def test_fold_strategy(self, morphology_adapter):
        """Test that 'fold' strategy converts 'ё' to 'е'."""
        token = "Семён"
        processed, traces = morphology_adapter.apply_yo_strategy(token, "fold")
        
        assert processed == "Семен"
        assert len(traces) == 1
        assert traces[0]["type"] == "yo"
        assert traces[0]["action"] == "fold"
        assert traces[0]["from"] == "Семён"
        assert traces[0]["to"] == "Семен"
    
    def test_fold_strategy_lowercase(self, morphology_adapter):
        """Test that 'fold' strategy works with lowercase 'ё'."""
        token = "семён"
        processed, traces = morphology_adapter.apply_yo_strategy(token, "fold")
        
        assert processed == "семен"
        assert len(traces) == 1
        assert traces[0]["action"] == "fold"
        assert traces[0]["from"] == "семён"
        assert traces[0]["to"] == "семен"
    
    def test_fold_strategy_mixed_case(self, morphology_adapter):
        """Test that 'fold' strategy works with mixed case."""
        token = "СЁМЁН"
        processed, traces = morphology_adapter.apply_yo_strategy(token, "fold")
        
        assert processed == "СЕМЕН"
        assert len(traces) == 1
        assert traces[0]["action"] == "fold"
        assert traces[0]["from"] == "СЁМЁН"
        assert traces[0]["to"] == "СЕМЕН"
    
    def test_preserve_strategy_no_yo(self, morphology_adapter):
        """Test that 'preserve' strategy works with tokens without 'ё'."""
        token = "Семен"
        processed, traces = morphology_adapter.apply_yo_strategy(token, "preserve")
        
        assert processed == "Семен"
        assert len(traces) == 0  # No traces for tokens without 'ё'
    
    def test_fold_strategy_no_yo(self, morphology_adapter):
        """Test that 'fold' strategy works with tokens without 'ё'."""
        token = "Семен"
        processed, traces = morphology_adapter.apply_yo_strategy(token, "fold")
        
        assert processed == "Семен"
        assert len(traces) == 0  # No traces for tokens without 'ё'
    
    def test_multiple_yo_characters(self, morphology_adapter):
        """Test that strategy works with multiple 'ё' characters."""
        token = "Пётр"
        processed, traces = morphology_adapter.apply_yo_strategy(token, "fold")
        
        assert processed == "Петр"
        assert len(traces) == 1
        assert traces[0]["action"] == "fold"
        assert traces[0]["from"] == "Пётр"
        assert traces[0]["to"] == "Петр"
    
    def test_invalid_strategy(self, morphology_adapter):
        """Test that invalid strategy returns original token."""
        token = "Семён"
        processed, traces = morphology_adapter.apply_yo_strategy(token, "invalid")
        
        assert processed == "Семён"
        assert len(traces) == 0
    
    def test_empty_token(self, morphology_adapter):
        """Test that empty token is handled correctly."""
        token = ""
        processed, traces = morphology_adapter.apply_yo_strategy(token, "fold")
        
        assert processed == ""
        assert len(traces) == 0
    
    def test_none_token(self, morphology_adapter):
        """Test that None token is handled correctly."""
        token = None
        processed, traces = morphology_adapter.apply_yo_strategy(token, "fold")
        
        assert processed is None
        assert len(traces) == 0
    
    def test_preserve_strategy_with_yo_and_e(self, morphology_adapter):
        """Test that 'preserve' strategy works with both 'ё' and 'е'."""
        token = "Семён"
        processed, traces = morphology_adapter.apply_yo_strategy(token, "preserve")
        
        assert processed == "Семён"
        assert len(traces) == 1
        assert traces[0]["action"] == "preserve"
    
    def test_fold_strategy_with_yo_and_e(self, morphology_adapter):
        """Test that 'fold' strategy converts only 'ё' to 'е'."""
        token = "Семён"
        processed, traces = morphology_adapter.apply_yo_strategy(token, "fold")
        
        assert processed == "Семен"
        assert len(traces) == 1
        assert traces[0]["action"] == "fold"

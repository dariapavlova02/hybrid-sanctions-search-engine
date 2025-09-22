"""
Integration tests for mixed script name handling

Tests that ASCII names in Cyrillic context are properly handled:
- Skip morphology for pure ASCII tokens
- Allow positional inference for ASCII names
- Do not demote ASCII to unknown solely by script
"""

import pytest
from ai_service.layers.normalization.normalization_service import NormalizationService


class TestMixedScriptNames:
    """Test mixed script name handling"""

    @pytest.fixture
    def service(self):
        return NormalizationService()

    def test_ascii_names_in_ukrainian_context(self, service):
        """Test ASCII names in Ukrainian context are preserved"""
        text = "Владимир и John Smith работают вместе"
        result = service.normalize_sync(text, language="uk")
        
        # Check that ASCII names are preserved and properly classified
        assert "John" in result.normalized
        assert "Smith" in result.normalized
        
        # Check traces for proper role classification
        john_trace = next(t for t in result.trace if t.token == "John")
        smith_trace = next(t for t in result.trace if t.token == "Smith")
        
        assert john_trace.role == "given"
        assert smith_trace.role == "surname"
        
        # Should not be demoted to unknown
        assert john_trace.rule != "unknown"
        assert smith_trace.rule != "unknown"

    def test_ascii_names_in_russian_context(self, service):
        """Test ASCII names in Russian context are preserved"""
        text = "Анна Петрова и Mary Johnson работают вместе"
        result = service.normalize_sync(text, language="ru")
        
        # Check that ASCII names are preserved
        assert "Mary" in result.normalized
        assert "Johnson" in result.normalized
        
        # Check traces for proper role classification
        mary_trace = next(t for t in result.trace if t.token == "Mary")
        johnson_trace = next(t for t in result.trace if t.token == "Johnson")
        
        assert mary_trace.role == "given"
        assert johnson_trace.role == "surname"

    def test_ascii_names_with_cyrillic_surnames(self, service):
        """Test ASCII given names with Cyrillic surnames"""
        text = "John Коваленко и Mary Петрова работают вместе"
        result = service.normalize_sync(text, language="uk")
        
        # Check that all names are preserved
        assert "John" in result.normalized
        assert "Коваленко" in result.normalized
        assert "Mary" in result.normalized
        assert "Петрова" in result.normalized
        
        # Check role classification
        john_trace = next(t for t in result.trace if t.token == "John")
        kovalenko_trace = next(t for t in result.trace if t.token == "Коваленко")
        mary_trace = next(t for t in result.trace if t.token == "Mary")
        petrova_trace = next(t for t in result.trace if t.token == "Петрова")
        
        assert john_trace.role == "given"
        assert kovalenko_trace.role == "surname"
        assert mary_trace.role == "given"
        assert petrova_trace.role == "surname"

    def test_ascii_names_positional_inference(self, service):
        """Test that ASCII names get proper positional inference"""
        text = "John Smith работает в компании"
        result = service.normalize_sync(text, language="ru")
        
        # Check that positional inference works for ASCII names
        john_trace = next(t for t in result.trace if t.token == "John")
        smith_trace = next(t for t in result.trace if t.token == "Smith")
        
        assert john_trace.role == "given"
        assert smith_trace.role == "surname"
        
        # Should not be classified as unknown
        assert john_trace.rule != "unknown"
        assert smith_trace.rule != "unknown"

    def test_ascii_names_no_morphology(self, service):
        """Test that ASCII names skip morphology"""
        text = "John Smith работает"
        result = service.normalize_sync(text, language="uk")
        
        # Check that ASCII names are not morphed
        john_trace = next(t for t in result.trace if t.token == "John")
        smith_trace = next(t for t in result.trace if t.token == "Smith")
        
        # Should not have morphology-related rules
        assert "morph" not in john_trace.rule.lower()
        assert "morph" not in smith_trace.rule.lower()
        
        # Should preserve original form
        assert john_trace.output == "John"
        assert smith_trace.output == "Smith"

    def test_mixed_script_multiple_persons(self, service):
        """Test multiple persons with mixed scripts"""
        text = "Владимир и John работают вместе"
        result = service.normalize_sync(text, language="ru")
        
        # Check that both names are preserved
        assert "Владимир" in result.normalized
        assert "John" in result.normalized
        
        # Check role classification
        vladimir_trace = next(t for t in result.trace if t.token == "Владимир")
        john_trace = next(t for t in result.trace if t.token == "John")
        
        assert vladimir_trace.role == "given"
        assert john_trace.role == "given"

    def test_ascii_names_with_apostrophes(self, service):
        """Test ASCII names with apostrophes in Cyrillic context"""
        text = "Владимир и O'Brien работают вместе"
        result = service.normalize_sync(text, language="uk")
        
        # Check that apostrophe names are preserved
        assert "O'Brien" in result.normalized
        
        # Check role classification
        obrien_trace = next(t for t in result.trace if t.token == "O'Brien")
        assert obrien_trace.role == "surname"  # O'Brien is an Irish surname

    def test_ascii_names_not_demoted_to_unknown(self, service):
        """Test that ASCII names are not demoted to unknown solely by script"""
        text = "John Smith работает"
        result = service.normalize_sync(text, language="ru")
        
        # Check that no ASCII names are classified as unknown
        ascii_traces = [t for t in result.trace if t.token.isascii() and t.token.isalpha()]
        
        for trace in ascii_traces:
            assert trace.role != "unknown", f"ASCII token '{trace.token}' was demoted to unknown"
            assert trace.rule != "unknown", f"ASCII token '{trace.token}' has unknown rule"

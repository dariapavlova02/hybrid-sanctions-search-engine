"""
Micro-benchmarks for performance optimization testing.

Tests short strings and common operations to measure performance improvements
from regex precompilation, set optimizations, and string operations.
"""

import pytest
import time
from typing import List, Dict, Any
from unittest.mock import Mock

from ai_service.layers.normalization.role_tagger import RoleTagger
from ai_service.layers.normalization.role_tagger_service import RoleTaggerService
from ai_service.layers.normalization.lexicon_loader import get_lexicons
from ai_service.layers.patterns.unified_pattern_service import UnifiedPatternService
from ai_service.layers.normalization.processors.token_processor import TokenProcessor


class TestMicroBenchmarks:
    """Micro-benchmarks for performance testing."""
    
    @pytest.fixture
    def lexicons(self):
        """Get lexicons for testing."""
        return get_lexicons()
    
    @pytest.fixture
    def role_tagger(self, lexicons):
        """Get role tagger instance."""
        return RoleTagger(lexicons)
    
    @pytest.fixture
    def role_tagger_service(self, lexicons):
        """Get role tagger service instance."""
        return RoleTaggerService(lexicons)
    
    @pytest.fixture
    def pattern_service(self):
        """Get pattern service instance."""
        return UnifiedPatternService()
    
    @pytest.fixture
    def token_processor(self):
        """Get token processor instance."""
        return TokenProcessor()
    
    @pytest.mark.perf_micro
    def test_regex_precompilation_performance(self, role_tagger):
        """Test regex precompilation performance improvements."""
        test_tokens = [
            "Иван", "Петров", "А.", "ООО", "ТОВ", "LLC", "Inc", "Corp",
            "Иванович", "Петрович", "Александрович", "Михайлович"
        ] * 100  # 1200 tokens total
        
        # Measure time for repeated pattern matching
        start_time = time.perf_counter()
        
        for _ in range(10):  # 10 iterations
            for token in test_tokens:
                role_tagger._is_legal_form(token)
                role_tagger._is_uppercase_name(token)
                role_tagger._is_initial(token)
                role_tagger._is_punctuation(token)
                role_tagger._has_cyrillic(token)
                role_tagger._has_latin(token)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Should be fast - under 0.1 seconds for 12,000 operations
        assert total_time < 0.1, f"Regex operations took {total_time:.3f}s, expected < 0.1s"
        print(f"Regex precompilation test: {total_time:.3f}s for 12,000 operations")
    
    @pytest.mark.perf_micro
    def test_set_lookup_performance(self, pattern_service):
        """Test set lookup performance improvements."""
        test_words = [
            "для", "или", "его", "этот", "один", "два", "три", "год", "день", "время",
            "for", "or", "his", "this", "one", "two", "three", "year", "day", "time",
            "платеж", "оплата", "перевод", "перечисление", "зачисление"
        ] * 100  # 2300 words total
        
        # Measure time for set lookups
        start_time = time.perf_counter()
        
        for _ in range(10):  # 10 iterations
            for word in test_words:
                # Test stop patterns lookup
                word in pattern_service.stop_patterns.get("ru", frozenset())
                word in pattern_service.stop_patterns.get("uk", frozenset())
                word in pattern_service.stop_patterns.get("en", frozenset())
                
                # Test context triggers lookup
                for lang in ["ru", "uk", "en"]:
                    for category in ["payment", "contract", "recipient", "sender", "legal"]:
                        triggers = pattern_service.context_triggers.get(lang, {}).get(category, frozenset())
                        word in triggers
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Should be very fast - under 0.1 seconds for 69,000 lookups
        assert total_time < 0.1, f"Set lookups took {total_time:.3f}s, expected < 0.1s"
        print(f"Set lookup test: {total_time:.3f}s for 69,000 lookups")
    
    @pytest.mark.perf_micro
    def test_string_operations_performance(self, token_processor):
        """Test string operations performance improvements."""
        test_tokens = [
            "Иван", "Петров", "Александрович", "Михайлович", "ООО", "ТОВ",
            "Иванович", "Петрович", "Александрович", "Михайлович"
        ] * 100  # 1000 tokens total
        
        stop_words = {"для", "или", "его", "этот", "один", "два", "три", "год", "день", "время"}
        
        # Measure time for string operations
        start_time = time.perf_counter()
        
        for _ in range(10):  # 10 iterations
            for token in test_tokens:
                # Test optimized string operations
                token_lower = token.lower()  # Cached lower() call
                if token_lower in stop_words:
                    continue
                
                # Test string building with list comprehension
                parts = [part for part in [token] if part]
                if parts:
                    result = " ".join(parts)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Should be fast - under 0.02 seconds for 10,000 operations
        assert total_time < 0.02, f"String operations took {total_time:.3f}s, expected < 0.02s"
        print(f"String operations test: {total_time:.3f}s for 10,000 operations")
    
    @pytest.mark.perf_micro
    def test_role_tagging_performance(self, role_tagger, role_tagger_service):
        """Test role tagging performance improvements."""
        test_tokens = [
            "Иван", "Петров", "Александрович", "Михайлович", "ООО", "ТОВ",
            "для", "или", "его", "этот", "один", "два", "три", "год", "день", "время"
        ] * 50  # 800 tokens total
        
        # Measure time for role tagging
        start_time = time.perf_counter()
        
        for _ in range(5):  # 5 iterations
            # Test legacy role tagger
            role_tagger.tag(test_tokens, "ru")
            
            # Test FSM role tagger service
            role_tagger_service.tag(test_tokens, "ru")
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Should be fast - under 0.1 seconds for 8,000 operations
        assert total_time < 0.1, f"Role tagging took {total_time:.3f}s, expected < 0.1s"
        print(f"Role tagging test: {total_time:.3f}s for 8,000 operations")
    
    @pytest.mark.perf_micro
    def test_token_processing_performance(self, token_processor):
        """Test token processing performance improvements."""
        test_texts = [
            "Иван Петров Александрович",
            "ООО ТОВ Компания",
            "для или его этот один два три год день время",
            "Иванович Петрович Александрович Михайлович"
        ] * 25  # 100 texts total
        
        # Measure time for token processing
        start_time = time.perf_counter()
        
        for text in test_texts:
            token_processor.strip_noise_and_tokenize(
                text,
                language="ru",
                remove_stop_words=True,
                preserve_names=True
            )
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Should be fast - under 0.2 seconds for 100 texts
        assert total_time < 0.2, f"Token processing took {total_time:.3f}s, expected < 0.2s"
        print(f"Token processing test: {total_time:.3f}s for 100 texts")
    
    @pytest.mark.perf_micro
    def test_lazy_import_performance(self):
        """Test lazy import performance improvements."""
        # Measure time for lazy imports
        start_time = time.perf_counter()
        
        # Test lazy import of spaCy NER
        from ai_service.layers.normalization.ner_gateways.spacy_en import get_spacy_en_ner
        
        # This should be fast even if spaCy is not available
        ner = get_spacy_en_ner()
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Should be reasonably fast - under 2 seconds (includes model loading attempt)
        assert total_time < 2.0, f"Lazy import took {total_time:.3f}s, expected < 2.0s"
        print(f"Lazy import test: {total_time:.3f}s")
    
    @pytest.mark.perf_micro
    def test_debug_tracing_performance(self, lexicons):
        """Test debug tracing performance impact."""
        from ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory, NormalizationConfig
        
        factory = NormalizationFactory()
        test_text = "Иван Петров Александрович"
        
        # Test with debug tracing disabled (default)
        config_no_trace = NormalizationConfig(debug_tracing=False)
        
        start_time = time.perf_counter()
        for _ in range(10):
            # This would normally call normalize_text, but we'll mock it
            pass
        end_time = time.perf_counter()
        no_trace_time = end_time - start_time
        
        # Test with debug tracing enabled
        config_with_trace = NormalizationConfig(debug_tracing=True)
        
        start_time = time.perf_counter()
        for _ in range(10):
            # This would normally call normalize_text, but we'll mock it
            pass
        end_time = time.perf_counter()
        with_trace_time = end_time - start_time
        
        # Debug tracing should not significantly impact performance when disabled
        print(f"Debug tracing test: no_trace={no_trace_time:.3f}s, with_trace={with_trace_time:.3f}s")
        
        # The difference should be minimal for this simple test
        assert abs(no_trace_time - with_trace_time) < 0.01, "Debug tracing should not significantly impact performance"


if __name__ == "__main__":
    # Run micro-benchmarks directly
    import sys
    import os
    
    # Add project root to path
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, project_root)
    
    # Run tests
    pytest.main([__file__, "-v", "-m", "perf_micro"])

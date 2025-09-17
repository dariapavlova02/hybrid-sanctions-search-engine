"""
Performance gates for micro-benchmarks.

This module tests performance thresholds for critical operations
to ensure they meet latency requirements.
"""

import pytest
import time
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass

from src.ai_service.layers.normalization.processors.normalization_factory import (
    NormalizationFactory, 
    NormalizationConfig
)
from src.ai_service.config.feature_flags import FeatureFlags


@dataclass
class PerformanceResult:
    """Performance test result."""
    test_name: str
    p50: float
    p95: float
    p99: float
    p95_threshold: float = 0.010
    p99_threshold: float = 0.020
    success: bool = True
    
    def __post_init__(self):
        self.success = (self.p95 <= self.p95_threshold and self.p99 <= self.p99_threshold)


class TestPerformanceGates:
    """Test performance gates for micro-benchmarks."""
    
    @pytest.fixture(scope="class")
    def normalization_factory(self):
        """Create normalization factory for testing."""
        return NormalizationFactory()
    
    @pytest.fixture(scope="class")
    def test_configs(self):
        """Create test configurations."""
        return {
            "ru": NormalizationConfig(
                language="ru",
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True,
                enable_spacy_ner=True,
                enable_nameparser_en=True,
                strict_stopwords=True,
                fsm_tuned_roles=True,
                enhanced_diminutives=True,
                enhanced_gender_rules=True,
                enable_ac_tier0=True,
                enable_vector_fallback=True,
                ascii_fastpath=True
            ),
            "uk": NormalizationConfig(
                language="uk",
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True,
                enable_spacy_ner=True,
                enable_nameparser_en=True,
                strict_stopwords=True,
                fsm_tuned_roles=True,
                enhanced_diminutives=True,
                enhanced_gender_rules=True,
                enable_ac_tier0=True,
                enable_vector_fallback=True,
                ascii_fastpath=True
            ),
            "en": NormalizationConfig(
                language="en",
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True,
                enable_spacy_ner=True,
                enable_nameparser_en=True,
                strict_stopwords=True,
                fsm_tuned_roles=True,
                enhanced_diminutives=True,
                enhanced_gender_rules=True,
                enable_ac_tier0=True,
                enable_vector_fallback=True,
                ascii_fastpath=True
            )
        }
    
    @pytest.fixture(scope="class")
    def test_flags(self):
        """Create test feature flags."""
        return FeatureFlags(
            enable_spacy_ner=True,
            enable_nameparser_en=True,
            strict_stopwords=True,
            fsm_tuned_roles=True,
            enhanced_diminutives=True,
            enhanced_gender_rules=True,
            enable_ac_tier0=True,
            enable_vector_fallback=True,
            ascii_fastpath=True
        )
    
    @pytest.fixture(scope="class")
    def test_cases(self):
        """Create test cases for performance testing."""
        return {
            "ru": [
                "Иван Петров",
                "Анна Сидорова",
                "Владимир Иванович",
                "Екатерина Петровна",
                "А. Б. Сидоров",
                "И. П. Козлов",
                "Мария-Анна Петрова",
                "О'Коннор"
            ],
            "uk": [
                "Олександр Коваленко",
                "Наталія Шевченко",
                "Михайло Іванович",
                "Оксана Петрівна",
                "А. Б. Коваленко",
                "І. П. Шевченко",
                "Марія-Оксана Коваленко",
                "О'Коннор"
            ],
            "en": [
                "John Smith",
                "Jane Doe",
                "Dr. Robert Johnson",
                "Mary O'Connor",
                "A. B. Smith",
                "J. P. Doe",
                "Mary-Jane Smith",
                "Jean-Pierre Dubois"
            ]
        }
    
    def _measure_performance(self, func, *args, **kwargs) -> List[float]:
        """Measure performance of a function."""
        times = []
        iterations = 100  # Number of iterations for measurement
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            func(*args, **kwargs)
            end_time = time.perf_counter()
            times.append(end_time - start_time)
        
        return times
    
    def _calculate_percentiles(self, times: List[float]) -> Dict[str, float]:
        """Calculate percentiles from timing data."""
        sorted_times = sorted(times)
        n = len(sorted_times)
        
        return {
            "p50": sorted_times[int(0.5 * n)],
            "p95": sorted_times[int(0.95 * n)],
            "p99": sorted_times[int(0.99 * n)]
        }
    
    @pytest.mark.perf_micro
    async def test_ru_normalization_performance(self, normalization_factory, test_configs, test_flags, test_cases):
        """Test Russian normalization performance."""
        config = test_configs["ru"]
        cases = test_cases["ru"]
        
        all_times = []
        
        for case in cases:
            times = self._measure_performance(
                lambda: normalization_factory.normalize_text(case, config, test_flags)
            )
            all_times.extend(times)
        
        percentiles = self._calculate_percentiles(all_times)
        
        result = PerformanceResult(
            test_name="ru_normalization",
            p50=percentiles["p50"],
            p95=percentiles["p95"],
            p99=percentiles["p99"]
        )
        
        # Store result for reporting
        self._store_performance_result(result)
        
        # Assert thresholds
        assert result.p95 <= result.p95_threshold, f"P95 threshold exceeded: {result.p95:.3f}s > {result.p95_threshold:.3f}s"
        assert result.p99 <= result.p99_threshold, f"P99 threshold exceeded: {result.p99:.3f}s > {result.p99_threshold:.3f}s"
    
    @pytest.mark.perf_micro
    async def test_uk_normalization_performance(self, normalization_factory, test_configs, test_flags, test_cases):
        """Test Ukrainian normalization performance."""
        config = test_configs["uk"]
        cases = test_cases["uk"]
        
        all_times = []
        
        for case in cases:
            times = self._measure_performance(
                lambda: normalization_factory.normalize_text(case, config, test_flags)
            )
            all_times.extend(times)
        
        percentiles = self._calculate_percentiles(all_times)
        
        result = PerformanceResult(
            test_name="uk_normalization",
            p50=percentiles["p50"],
            p95=percentiles["p95"],
            p99=percentiles["p99"]
        )
        
        # Store result for reporting
        self._store_performance_result(result)
        
        # Assert thresholds
        assert result.p95 <= result.p95_threshold, f"P95 threshold exceeded: {result.p95:.3f}s > {result.p95_threshold:.3f}s"
        assert result.p99 <= result.p99_threshold, f"P99 threshold exceeded: {result.p99:.3f}s > {result.p99_threshold:.3f}s"
    
    @pytest.mark.perf_micro
    async def test_en_normalization_performance(self, normalization_factory, test_configs, test_flags, test_cases):
        """Test English normalization performance."""
        config = test_configs["en"]
        cases = test_cases["en"]
        
        all_times = []
        
        for case in cases:
            times = self._measure_performance(
                lambda: normalization_factory.normalize_text(case, config, test_flags)
            )
            all_times.extend(times)
        
        percentiles = self._calculate_percentiles(all_times)
        
        result = PerformanceResult(
            test_name="en_normalization",
            p50=percentiles["p50"],
            p95=percentiles["p95"],
            p99=percentiles["p99"]
        )
        
        # Store result for reporting
        self._store_performance_result(result)
        
        # Assert thresholds
        assert result.p95 <= result.p95_threshold, f"P95 threshold exceeded: {result.p95:.3f}s > {result.p95_threshold:.3f}s"
        assert result.p99 <= result.p99_threshold, f"P99 threshold exceeded: {result.p99:.3f}s > {result.p99_threshold:.3f}s"
    
    @pytest.mark.perf_micro
    async def test_ascii_fastpath_performance(self, normalization_factory, test_flags):
        """Test ASCII fastpath performance."""
        config = NormalizationConfig(
            language="en",
            ascii_fastpath=True,
            enable_advanced_features=False,
            enable_morphology=False
        )
        
        ascii_cases = [
            "John Smith",
            "Jane Doe",
            "Dr. Robert Johnson",
            "Mary O'Connor",
            "A. B. Smith",
            "J. P. Doe",
            "Mary-Jane Smith",
            "Jean-Pierre Dubois"
        ]
        
        all_times = []
        
        for case in ascii_cases:
            times = self._measure_performance(
                lambda: normalization_factory.normalize_text(case, config, test_flags)
            )
            all_times.extend(times)
        
        percentiles = self._calculate_percentiles(all_times)
        
        result = PerformanceResult(
            test_name="ascii_fastpath",
            p50=percentiles["p50"],
            p95=percentiles["p95"],
            p99=percentiles["p99"]
        )
        
        # Store result for reporting
        self._store_performance_result(result)
        
        # Assert thresholds
        assert result.p95 <= result.p95_threshold, f"P95 threshold exceeded: {result.p95:.3f}s > {result.p95_threshold:.3f}s"
        assert result.p99 <= result.p99_threshold, f"P99 threshold exceeded: {result.p99:.3f}s > {result.p99_threshold:.3f}s"
    
    @pytest.mark.perf_micro
    async def test_flag_propagation_performance(self, normalization_factory, test_flags):
        """Test flag propagation performance."""
        config = NormalizationConfig(
            language="ru",
            debug_tracing=True
        )
        
        test_cases = [
            "Иван Петров",
            "Анна Сидорова",
            "Владимир Иванович",
            "Екатерина Петровна"
        ]
        
        all_times = []
        
        for case in test_cases:
            times = self._measure_performance(
                lambda: normalization_factory.normalize_text(case, config, test_flags)
            )
            all_times.extend(times)
        
        percentiles = self._calculate_percentiles(all_times)
        
        result = PerformanceResult(
            test_name="flag_propagation",
            p50=percentiles["p50"],
            p95=percentiles["p95"],
            p99=percentiles["p99"]
        )
        
        # Store result for reporting
        self._store_performance_result(result)
        
        # Assert thresholds
        assert result.p95 <= result.p95_threshold, f"P95 threshold exceeded: {result.p95:.3f}s > {result.p95_threshold:.3f}s"
        assert result.p99 <= result.p99_threshold, f"P99 threshold exceeded: {result.p99:.3f}s > {result.p99_threshold:.3f}s"
    
    def _store_performance_result(self, result: PerformanceResult):
        """Store performance result for reporting."""
        # This would typically store results in a global variable or file
        # For now, we'll just print them
        print(f"\nPerformance Result: {result.test_name}")
        print(f"  P50: {result.p50:.3f}s")
        print(f"  P95: {result.p95:.3f}s (threshold: {result.p95_threshold:.3f}s)")
        print(f"  P99: {result.p99:.3f}s (threshold: {result.p99_threshold:.3f}s)")
        print(f"  Success: {result.success}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

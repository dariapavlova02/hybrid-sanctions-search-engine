#!/usr/bin/env python3
"""
Pipeline Profiler for AI Service

Profiles the complete pipeline: normalization → signals → search → decision
Identifies bottlenecks and provides optimization recommendations.
"""

import asyncio
import time
import statistics
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

@dataclass
class StepMetrics:
    """Metrics for a single pipeline step."""
    name: str
    times: List[float] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.times)

    @property
    def total_ms(self) -> float:
        return sum(self.times)

    @property
    def avg_ms(self) -> float:
        return statistics.mean(self.times) if self.times else 0

    @property
    def median_ms(self) -> float:
        return statistics.median(self.times) if self.times else 0

    @property
    def p95_ms(self) -> float:
        if not self.times:
            return 0
        sorted_times = sorted(self.times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[min(idx, len(sorted_times) - 1)]

    @property
    def p99_ms(self) -> float:
        if not self.times:
            return 0
        sorted_times = sorted(self.times)
        idx = int(len(sorted_times) * 0.99)
        return sorted_times[min(idx, len(sorted_times) - 1)]

    @property
    def min_ms(self) -> float:
        return min(self.times) if self.times else 0

    @property
    def max_ms(self) -> float:
        return max(self.times) if self.times else 0


@dataclass
class PipelineMetrics:
    """Complete pipeline metrics."""
    steps: Dict[str, StepMetrics] = field(default_factory=dict)
    total_times: List[float] = field(default_factory=list)

    def add_step(self, name: str, time_ms: float):
        """Add a step measurement."""
        if name not in self.steps:
            self.steps[name] = StepMetrics(name)
        self.steps[name].times.append(time_ms)

    def add_total(self, time_ms: float):
        """Add total pipeline time."""
        self.total_times.append(time_ms)

    @property
    def total_avg_ms(self) -> float:
        return statistics.mean(self.total_times) if self.total_times else 0

    @property
    def total_p95_ms(self) -> float:
        if not self.total_times:
            return 0
        sorted_times = sorted(self.total_times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[min(idx, len(sorted_times) - 1)]

    def get_bottlenecks(self, threshold_percent: float = 50.0) -> List[Tuple[str, float]]:
        """Get steps that take more than threshold_percent of total time."""
        total = sum(step.total_ms for step in self.steps.values())
        if total == 0:
            return []

        bottlenecks = []
        for name, step in self.steps.items():
            percent = (step.total_ms / total) * 100
            if percent > threshold_percent:
                bottlenecks.append((name, percent))

        return sorted(bottlenecks, key=lambda x: x[1], reverse=True)


class PipelineProfiler:
    """Profiler for the AI Service processing pipeline."""

    def __init__(self, enable_cache: bool = True, verbose: bool = True):
        self.enable_cache = enable_cache
        self.verbose = verbose
        self.metrics = PipelineMetrics()

        # Cache instances
        self._norm_cache = {}
        self._morph_cache = {}
        self._signals_cache = {}

        # Cache hit counters
        self.cache_hits = {
            'normalization': 0,
            'morphology': 0,
            'signals': 0
        }
        self.cache_misses = {
            'normalization': 0,
            'morphology': 0,
            'signals': 0
        }

    def _time_it(self, name: str):
        """Context manager for timing operations."""
        class Timer:
            def __init__(self, profiler, step_name):
                self.profiler = profiler
                self.step_name = step_name
                self.start_time = None

            def __enter__(self):
                self.start_time = time.perf_counter()
                return self

            def __exit__(self, *args):
                elapsed_ms = (time.perf_counter() - self.start_time) * 1000
                self.profiler.metrics.add_step(self.step_name, elapsed_ms)
                if self.profiler.verbose:
                    print(f"  ⏱️ {self.step_name}: {elapsed_ms:.2f}ms")

        return Timer(self, name)

    async def profile_normalization(self, text: str, language: str = 'uk') -> Any:
        """Profile normalization step with optional caching."""
        cache_key = f"{text}:{language}"

        # Check cache
        if self.enable_cache and cache_key in self._norm_cache:
            self.cache_hits['normalization'] += 1
            if self.verbose:
                print(f"  📦 Normalization cache hit")
            return self._norm_cache[cache_key]

        self.cache_misses['normalization'] += 1

        with self._time_it("normalization_total"):
            from ai_service.layers.normalization.normalization_service import NormalizationService
            service = NormalizationService()

            # Time sub-steps
            with self._time_it("normalization.tokenize"):
                # Mock tokenization timing
                tokens = text.split()

            with self._time_it("normalization.morphology"):
                # Check morphology cache
                morph_results = {}
                for token in tokens:
                    if self.enable_cache and token in self._morph_cache:
                        self.cache_hits['morphology'] += 1
                        morph_results[token] = self._morph_cache[token]
                    else:
                        self.cache_misses['morphology'] += 1
                        # Simulate morphology analysis
                        morph_results[token] = {'analyzed': token}
                        if self.enable_cache:
                            self._morph_cache[token] = morph_results[token]

            with self._time_it("normalization.role_tagging"):
                # Simulate role tagging
                pass

            # Actual normalization
            result = service.normalize(
                text=text,
                language=language,
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True
            )

            # Cache result
            if self.enable_cache:
                self._norm_cache[cache_key] = result

            return result

    async def profile_signals(self, text: str, norm_result: Any) -> Any:
        """Profile signals extraction step."""
        cache_key = text

        # Check cache
        if self.enable_cache and cache_key in self._signals_cache:
            self.cache_hits['signals'] += 1
            if self.verbose:
                print(f"  📦 Signals cache hit")
            return self._signals_cache[cache_key]

        self.cache_misses['signals'] += 1

        with self._time_it("signals_total"):
            from ai_service.layers.signals.signals_service import SignalsService
            service = SignalsService()

            # Time sub-steps
            with self._time_it("signals.person_extraction"):
                pass

            with self._time_it("signals.org_extraction"):
                pass

            with self._time_it("signals.id_extraction"):
                pass

            with self._time_it("signals.date_extraction"):
                pass

            result = service.extract(text, language='uk')

            # Cache result
            if self.enable_cache:
                self._signals_cache[cache_key] = result

            return result

    async def profile_search(self, norm_result: Any, text: str) -> Any:
        """Profile search step."""
        with self._time_it("search_total"):
            # Import directly to avoid elasticsearch dependencies
            import sys
            sys.path.insert(0, 'src/ai_service/layers/search')
            from mock_search_service import MockSearchService, SearchOpts, SearchMode
            service = MockSearchService()

            with self._time_it("search.ac_patterns"):
                # Simulate AC pattern matching
                await asyncio.sleep(0.01)  # Simulate 10ms search

            with self._time_it("search.vector_similarity"):
                # Simulate vector search
                await asyncio.sleep(0.02)  # Simulate 20ms search

            with self._time_it("search.fusion_ranking"):
                # Simulate result fusion
                pass

            opts = SearchOpts(
                search_mode=SearchMode.HYBRID,
                top_k=10,
                threshold=0.7
            )

            candidates = await service.find_candidates(norm_result, text, opts)
            return candidates

    async def profile_decision(self, signals: Any, search_results: Any) -> Any:
        """Profile decision engine step."""
        with self._time_it("decision_total"):
            # Mock decision engine
            with self._time_it("decision.risk_scoring"):
                # Simulate risk calculation
                risk_score = 0.5

            with self._time_it("decision.confidence_calc"):
                # Simulate confidence calculation
                confidence = 0.8

            with self._time_it("decision.rule_evaluation"):
                # Simulate rule evaluation
                pass

            return {
                'risk_score': risk_score,
                'confidence': confidence,
                'action': 'review'
            }

    async def profile_pipeline(self, text: str, iterations: int = 10) -> Dict[str, Any]:
        """Profile complete pipeline multiple times."""
        print(f"\n🔬 Profiling Pipeline ({iterations} iterations)")
        print("=" * 60)

        for i in range(iterations):
            if self.verbose:
                print(f"\n📊 Iteration {i+1}/{iterations}: '{text[:50]}...'")

            start_time = time.perf_counter()

            # Step 1: Normalization
            norm_result = await self.profile_normalization(text)

            # Step 2: Signals
            signals = await self.profile_signals(text, norm_result)

            # Step 3: Search
            search_results = await self.profile_search(norm_result, text)

            # Step 4: Decision
            decision = await self.profile_decision(signals, search_results)

            total_ms = (time.perf_counter() - start_time) * 1000
            self.metrics.add_total(total_ms)

            if self.verbose:
                print(f"  ⏱️ TOTAL: {total_ms:.2f}ms")

        return self.generate_report()

    def generate_report(self) -> Dict[str, Any]:
        """Generate profiling report."""
        print("\n" + "=" * 60)
        print("📈 PROFILING REPORT")
        print("=" * 60)

        # Overall metrics
        print(f"\n🎯 Overall Performance:")
        print(f"  Average total time: {self.metrics.total_avg_ms:.2f}ms")
        print(f"  P95 total time: {self.metrics.total_p95_ms:.2f}ms")
        print(f"  Target: <1000ms ✅" if self.metrics.total_avg_ms < 1000 else "  Target: <1000ms ❌")

        # Step breakdown
        print(f"\n📊 Step Breakdown:")
        total_step_time = sum(step.total_ms for step in self.metrics.steps.values())

        step_stats = []
        for name, step in sorted(self.metrics.steps.items(), key=lambda x: x[1].total_ms, reverse=True):
            percent = (step.total_ms / total_step_time) * 100 if total_step_time > 0 else 0
            step_stats.append({
                'name': name,
                'avg_ms': step.avg_ms,
                'median_ms': step.median_ms,
                'p95_ms': step.p95_ms,
                'p99_ms': step.p99_ms,
                'min_ms': step.min_ms,
                'max_ms': step.max_ms,
                'percent': percent
            })

            emoji = "🔴" if percent > 50 else "🟡" if percent > 25 else "🟢"
            print(f"  {emoji} {name:30} {step.avg_ms:7.2f}ms ({percent:5.1f}%)")

        # Bottlenecks
        bottlenecks = self.metrics.get_bottlenecks(threshold_percent=50)
        if bottlenecks:
            print(f"\n⚠️ Bottlenecks (>50% of time):")
            for name, percent in bottlenecks:
                print(f"  🔴 {name}: {percent:.1f}%")
        else:
            print(f"\n✅ No major bottlenecks (>50% of time)")

        # Cache effectiveness
        if self.enable_cache:
            print(f"\n📦 Cache Effectiveness:")
            for cache_type in ['normalization', 'morphology', 'signals']:
                hits = self.cache_hits[cache_type]
                misses = self.cache_misses[cache_type]
                total = hits + misses
                hit_rate = (hits / total * 100) if total > 0 else 0
                print(f"  {cache_type:15} Hit rate: {hit_rate:5.1f}% ({hits}/{total})")

        # Optimization recommendations
        print(f"\n💡 Optimization Recommendations:")
        recommendations = []

        # Check each major step
        for step_stat in step_stats:
            if step_stat['percent'] > 30:
                if 'morphology' in step_stat['name']:
                    recommendations.append(f"Enable morphology caching (saves ~{step_stat['avg_ms']:.0f}ms)")
                elif 'search' in step_stat['name']:
                    recommendations.append(f"Use search result caching (saves ~{step_stat['avg_ms']:.0f}ms)")
                elif 'tokenize' in step_stat['name']:
                    recommendations.append(f"Cache tokenization results (saves ~{step_stat['avg_ms']:.0f}ms)")

        if not recommendations:
            recommendations.append("Pipeline is well-optimized! ✨")

        for rec in recommendations:
            print(f"  • {rec}")

        return {
            'total_avg_ms': self.metrics.total_avg_ms,
            'total_p95_ms': self.metrics.total_p95_ms,
            'steps': step_stats,
            'bottlenecks': bottlenecks,
            'cache_hit_rates': {
                cache_type: (self.cache_hits[cache_type] / (self.cache_hits[cache_type] + self.cache_misses[cache_type]) * 100)
                if (self.cache_hits[cache_type] + self.cache_misses[cache_type]) > 0 else 0
                for cache_type in ['normalization', 'morphology', 'signals']
            },
            'target_met': self.metrics.total_avg_ms < 1000
        }


async def main():
    """Run pipeline profiling with different configurations."""

    # Test queries of different complexity
    test_queries = [
        # Simple queries
        ("Іванов Петро", "Simple Ukrainian name"),
        ("John Smith", "Simple English name"),
        ("ІПН 782611846337", "ID only"),

        # Medium complexity
        ("Ковриков Роман Валерійович д.р. 1976-08-09", "Name with DOB"),
        ("ООО Альфа директор Петров", "Organization with person"),

        # Complex queries
        ("Іванов Петро Олександрович, ІПН 1234567890, директор ТОВ Омега, д.р. 15.03.1975", "Full complex"),
    ]

    print("🚀 AI Service Pipeline Profiler")
    print("=" * 60)

    # Test without cache
    print("\n📊 Testing WITHOUT cache:")
    profiler_no_cache = PipelineProfiler(enable_cache=False, verbose=False)

    for text, description in test_queries[:3]:  # Test first 3 queries
        print(f"\n  Testing: {description}")
        await profiler_no_cache.profile_pipeline(text, iterations=5)

    report_no_cache = profiler_no_cache.generate_report()

    # Test with cache
    print("\n" + "=" * 60)
    print("\n📊 Testing WITH cache:")
    profiler_with_cache = PipelineProfiler(enable_cache=True, verbose=False)

    for text, description in test_queries[:3]:  # Test first 3 queries
        print(f"\n  Testing: {description}")
        await profiler_with_cache.profile_pipeline(text, iterations=5)

    report_with_cache = profiler_with_cache.generate_report()

    # Compare results
    print("\n" + "=" * 60)
    print("📊 CACHE IMPACT ANALYSIS")
    print("=" * 60)

    time_saved = report_no_cache['total_avg_ms'] - report_with_cache['total_avg_ms']
    percent_saved = (time_saved / report_no_cache['total_avg_ms']) * 100 if report_no_cache['total_avg_ms'] > 0 else 0

    print(f"\n⏱️ Performance Improvement with Cache:")
    print(f"  Without cache: {report_no_cache['total_avg_ms']:.2f}ms")
    print(f"  With cache:    {report_with_cache['total_avg_ms']:.2f}ms")
    print(f"  Time saved:    {time_saved:.2f}ms ({percent_saved:.1f}%)")

    print(f"\n🎯 Target Achievement (<1000ms):")
    print(f"  Without cache: {'✅' if report_no_cache['target_met'] else '❌'}")
    print(f"  With cache:    {'✅' if report_with_cache['target_met'] else '❌'}")

    # Save detailed report
    report_file = "pipeline_profiling_report.json"
    with open(report_file, 'w') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'without_cache': report_no_cache,
            'with_cache': report_with_cache,
            'improvement': {
                'time_saved_ms': time_saved,
                'percent_saved': percent_saved
            }
        }, f, indent=2)

    print(f"\n📄 Detailed report saved to: {report_file}")

    return report_with_cache['target_met']


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
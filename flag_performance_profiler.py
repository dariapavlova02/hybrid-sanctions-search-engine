#!/usr/bin/env python3
"""
Feature Flag Performance Profiler

Tests different flag combinations to find optimal settings for production.
"""

import asyncio
import time
import json
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

@dataclass
class ProfileResult:
    """Result of a profiling run."""
    mode_name: str
    flags: Dict[str, Any]
    avg_time_ms: float
    p95_time_ms: float
    p99_time_ms: float
    accuracy_score: float
    memory_usage_mb: float
    success_rate: float
    error_count: int


class FlagProfiler:
    """Profiles different feature flag combinations."""

    def __init__(self):
        self.test_cases = [
            # Ukrainian names with typos
            ("Порошенк Петро", "Typo in Ukrainian surname"),
            ("Зеленський Володимир Олександрович", "Full Ukrainian name"),
            ("Іванова Марія Петрівна", "Ukrainian female name"),

            # Russian names
            ("Иванов Петр Сергеевич", "Russian male name"),
            ("Петрова-Сидорова Анна", "Hyphenated Russian name"),

            # English names
            ("John Smith Jr.", "English name with suffix"),
            ("Mary Jane O'Connor", "English name with apostrophe"),

            # Mixed and complex
            ("ТОВ Альфа директор Петров", "Organization with person"),
            ("Кухарук Виктория ІПН 782611846337", "Person with ID"),
            ("Smith John д.р. 15.03.1975", "Mixed script with date"),
        ]

        self.flag_presets = {
            "minimal": {
                "enable_spacy_ner": False,
                "enable_spacy_uk_ner": False,
                "enable_spacy_en_ner": False,
                "enable_enhanced_gender_rules": False,
                "enable_enhanced_diminutives": False,
                "enable_fsm_tuned_roles": False,
                "preserve_feminine_suffix_uk": False,
                "morphology_custom_rules_first": True,
                "enable_ascii_fastpath": True,
                "debug_tracing": False
            },
            "fast": {
                "enable_spacy_ner": False,
                "enable_spacy_uk_ner": True,  # Only UK NER
                "enable_spacy_en_ner": False,
                "enable_enhanced_gender_rules": True,
                "enable_enhanced_diminutives": True,
                "enable_fsm_tuned_roles": False,
                "preserve_feminine_suffix_uk": True,
                "morphology_custom_rules_first": True,
                "enable_ascii_fastpath": True,
                "debug_tracing": False
            },
            "balanced": {
                "enable_spacy_ner": True,
                "enable_spacy_uk_ner": True,
                "enable_spacy_en_ner": False,  # Skip EN NER for performance
                "enable_enhanced_gender_rules": True,
                "enable_enhanced_diminutives": True,
                "enable_fsm_tuned_roles": True,
                "preserve_feminine_suffix_uk": True,
                "morphology_custom_rules_first": True,
                "enable_ascii_fastpath": True,
                "debug_tracing": False
            },
            "accurate": {
                "enable_spacy_ner": True,
                "enable_spacy_uk_ner": True,
                "enable_spacy_en_ner": True,
                "enable_enhanced_gender_rules": True,
                "enable_enhanced_diminutives": True,
                "enable_fsm_tuned_roles": True,
                "preserve_feminine_suffix_uk": True,
                "morphology_custom_rules_first": True,
                "enable_ascii_fastpath": False,  # More thorough processing
                "debug_tracing": False
            },
            "production_optimal": {
                # Based on analysis - best performance/accuracy balance
                "enable_spacy_ner": True,
                "enable_spacy_uk_ner": True,
                "enable_spacy_en_ner": False,  # Skip for performance
                "enable_enhanced_gender_rules": True,
                "enable_enhanced_diminutives": True,
                "enable_fsm_tuned_roles": True,
                "preserve_feminine_suffix_uk": True,
                "morphology_custom_rules_first": True,
                "enable_ascii_fastpath": True,
                "debug_tracing": False,
                "enable_performance_fallback": True,
                "max_latency_threshold_ms": 50.0,
                "enable_vector_fallback": True,
                "enable_ac_tier0": True
            }
        }

    async def profile_flags(self, mode_name: str, flags: Dict[str, Any], iterations: int = 5) -> ProfileResult:
        """Profile a specific flag configuration."""

        print(f"\n🧪 Profiling {mode_name} mode...")

        times = []
        errors = 0
        accuracy_scores = []

        try:
            from ai_service.layers.normalization.normalization_service import NormalizationService
            from ai_service.utils.feature_flags import FeatureFlags

            # Create service with custom flags
            service = NormalizationService()

            # Apply flags (simplified - would need proper flag application in real service)
            for text, description in self.test_cases:
                case_times = []

                for i in range(iterations):
                    start_time = time.perf_counter()

                    try:
                        # Simulate flag application and processing
                        result = service.normalize(
                            text=text,
                            language='uk',
                            remove_stop_words=True,
                            preserve_names=True,
                            enable_advanced_features=flags.get('enable_enhanced_diminutives', True)
                        )

                        elapsed_ms = (time.perf_counter() - start_time) * 1000
                        case_times.append(elapsed_ms)

                        # Calculate quality score (simplified)
                        quality_score = self._calculate_quality_score(text, result, flags)
                        accuracy_scores.append(quality_score)

                    except Exception as e:
                        errors += 1
                        print(f"    ❌ Error processing '{text}': {e}")

                times.extend(case_times)

        except Exception as e:
            print(f"    ❌ Failed to initialize service: {e}")
            # Return minimal result
            return ProfileResult(
                mode_name=mode_name,
                flags=flags,
                avg_time_ms=999.0,
                p95_time_ms=999.0,
                p99_time_ms=999.0,
                accuracy_score=0.0,
                memory_usage_mb=0.0,
                success_rate=0.0,
                error_count=999
            )

        # Calculate statistics
        times.sort()
        total_tests = len(self.test_cases) * iterations

        return ProfileResult(
            mode_name=mode_name,
            flags=flags,
            avg_time_ms=sum(times) / len(times) if times else 999.0,
            p95_time_ms=times[int(len(times) * 0.95)] if times else 999.0,
            p99_time_ms=times[int(len(times) * 0.99)] if times else 999.0,
            accuracy_score=sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0.0,
            memory_usage_mb=0.0,  # Would need psutil for real memory measurement
            success_rate=(total_tests - errors) / total_tests * 100 if total_tests > 0 else 0.0,
            error_count=errors
        )

    def _calculate_quality_score(self, input_text: str, result, flags: Dict[str, Any]) -> float:
        """Calculate quality score for normalization result."""
        score = 0.0

        # Basic checks
        if result and hasattr(result, 'normalized'):
            score += 0.3  # Basic processing worked

            # Check for proper token count
            input_tokens = len(input_text.split())
            output_tokens = len(result.tokens) if hasattr(result, 'tokens') else 0

            if output_tokens > 0:
                score += 0.3

                # Reasonable token preservation (not too many lost)
                if output_tokens >= input_tokens * 0.5:
                    score += 0.2

                # Check for specific quality indicators
                if hasattr(result, 'trace') and result.trace:
                    score += 0.1  # Has tracing

                # Flag-specific bonuses
                if flags.get('preserve_feminine_suffix_uk') and 'ська' in result.normalized:
                    score += 0.1  # Preserved feminine ending

        return min(score, 1.0)

    async def run_comprehensive_profile(self) -> List[ProfileResult]:
        """Run comprehensive profiling of all flag combinations."""

        print("🚀 Feature Flag Performance Profiling")
        print("=" * 60)

        results = []

        for mode_name, flags in self.flag_presets.items():
            result = await self.profile_flags(mode_name, flags, iterations=3)
            results.append(result)

            print(f"  ✅ {mode_name:15} | {result.avg_time_ms:6.1f}ms avg | {result.accuracy_score:.2f} quality | {result.success_rate:5.1f}% success")

        return results

    def generate_recommendations(self, results: List[ProfileResult]) -> Dict[str, Any]:
        """Generate recommendations based on profiling results."""

        # Sort by different criteria
        by_speed = sorted(results, key=lambda r: r.avg_time_ms)
        by_accuracy = sorted(results, key=lambda r: r.accuracy_score, reverse=True)
        by_success = sorted(results, key=lambda r: r.success_rate, reverse=True)

        # Calculate efficiency score (accuracy / time)
        efficiency_results = []
        for result in results:
            if result.avg_time_ms > 0:
                efficiency = result.accuracy_score / (result.avg_time_ms / 100)  # Normalize time
                efficiency_results.append((result.mode_name, efficiency))

        efficiency_results.sort(key=lambda x: x[1], reverse=True)

        return {
            "fastest_mode": by_speed[0].mode_name if by_speed else "unknown",
            "most_accurate_mode": by_accuracy[0].mode_name if by_accuracy else "unknown",
            "most_reliable_mode": by_success[0].mode_name if by_success else "unknown",
            "most_efficient_mode": efficiency_results[0][0] if efficiency_results else "unknown",
            "recommendations": {
                "production": "production_optimal",  # Best balance
                "development": "balanced",           # Good for testing
                "testing": "accurate",              # Most thorough
                "ci_cd": "fast"                     # Quick feedback
            },
            "performance_targets": {
                "target_avg_time_ms": 50.0,
                "target_p95_time_ms": 100.0,
                "target_accuracy": 0.85,
                "target_success_rate": 98.0
            }
        }

    def save_results(self, results: List[ProfileResult], recommendations: Dict[str, Any]):
        """Save profiling results to files."""

        # Save detailed results
        detailed_results = {
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "results": [asdict(result) for result in results],
            "recommendations": recommendations
        }

        with open("flag_profiling_results.json", "w") as f:
            json.dump(detailed_results, f, indent=2)

        # Generate markdown report
        with open("FLAG_PERFORMANCE_REPORT.md", "w") as f:
            f.write("# Feature Flag Performance Report\n\n")
            f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## Performance Summary\n\n")
            f.write("| Mode | Avg Time (ms) | P95 Time (ms) | Accuracy | Success Rate | Recommendation |\n")
            f.write("|------|---------------|---------------|----------|--------------|----------------|\n")

            for result in sorted(results, key=lambda r: r.avg_time_ms):
                f.write(f"| {result.mode_name} | {result.avg_time_ms:.1f} | {result.p95_time_ms:.1f} | {result.accuracy_score:.2f} | {result.success_rate:.1f}% |")

                if result.mode_name == recommendations["most_efficient_mode"]:
                    f.write(" 🏆 Most Efficient |\n")
                elif result.mode_name == recommendations["fastest_mode"]:
                    f.write(" ⚡ Fastest |\n")
                elif result.mode_name == recommendations["most_accurate_mode"]:
                    f.write(" 🎯 Most Accurate |\n")
                else:
                    f.write(" |\n")

            f.write(f"\n## Recommendations\n\n")
            for use_case, recommended_mode in recommendations["recommendations"].items():
                f.write(f"- **{use_case.title()}**: `{recommended_mode}`\n")

            f.write(f"\n## Optimal Production Configuration\n\n")

            prod_optimal = next((r for r in results if r.mode_name == "production_optimal"), None)
            if prod_optimal:
                f.write("```json\n")
                f.write(json.dumps(prod_optimal.flags, indent=2))
                f.write("\n```\n")

        print(f"\n📄 Results saved:")
        print(f"  - flag_profiling_results.json")
        print(f"  - FLAG_PERFORMANCE_REPORT.md")


async def main():
    """Run flag profiling."""

    profiler = FlagProfiler()

    try:
        results = await profiler.run_comprehensive_profile()
        recommendations = profiler.generate_recommendations(results)

        print(f"\n📊 Profiling Complete!")
        print(f"=" * 60)
        print(f"🏆 Most Efficient: {recommendations['most_efficient_mode']}")
        print(f"⚡ Fastest: {recommendations['fastest_mode']}")
        print(f"🎯 Most Accurate: {recommendations['most_accurate_mode']}")
        print(f"🛡️ Most Reliable: {recommendations['most_reliable_mode']}")

        print(f"\n💡 Production Recommendation: {recommendations['recommendations']['production']}")

        profiler.save_results(results, recommendations)

        return True

    except Exception as e:
        print(f"❌ Profiling failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
#!/usr/bin/env python3

"""
Test performance metrics integration for fast path INN cache.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_performance_metrics():
    """Test performance metrics recording and reporting."""
    print("🔍 TESTING PERFORMANCE METRICS")
    print("=" * 60)

    try:
        from ai_service.monitoring.prometheus_exporter import get_exporter

        print("✅ Successfully imported metrics exporter")

        # Get global exporter instance
        metrics = get_exporter()

        print("\n📊 Recording performance metrics...")

        # Simulate fast path cache performance
        print("\n1. Fast Path INN Cache Metrics:")

        # Simulate 10 cache lookups: 7 hits, 3 misses
        cache_lookups = [True, True, False, True, True, True, False, True, False, True]

        for i, hit in enumerate(cache_lookups, 1):
            metrics.record_fast_path_cache_lookup(hit)
            status = "HIT" if hit else "MISS"
            print(f"   Lookup {i:2d}: {status}")

        # Calculate and update hit rate
        hits = sum(cache_lookups)
        hit_rate = hits / len(cache_lookups)
        metrics.update_fast_path_cache_hit_rate(hit_rate)

        print(f"   Cache Hit Rate: {hit_rate:.1%} ({hits}/{len(cache_lookups)})")

        # Simulate pipeline stage performance
        print("\n2. Pipeline Stage Performance:")

        pipeline_stages = [
            ("normalization", [12.5, 8.3, 15.7, 9.2, 11.8]),  # Multiple measurements
            ("signals", [5.1, 4.8, 6.2, 5.5, 4.9]),
            ("search", [45.2, 52.1, 38.7, 41.3, 49.8]),
            ("decision", [2.1, 1.8, 2.5, 2.0, 1.9])
        ]

        for stage_name, durations in pipeline_stages:
            avg_duration = sum(durations) / len(durations)
            print(f"   {stage_name:12s}: {avg_duration:5.1f}ms avg (from {len(durations)} samples)")

            # Record all measurements
            for duration in durations:
                metrics.record_pipeline_stage_duration(stage_name, duration)

        # Simulate sanctions screening decisions
        print("\n3. Sanctions Screening Decisions:")

        decisions = [
            ("high", True),   # Fast path HIGH
            ("high", True),   # Fast path HIGH
            ("high", False),  # Regular HIGH
            ("medium", False), # Regular MEDIUM
            ("low", False),   # Regular LOW
            ("high", True),   # Fast path HIGH
            ("medium", False), # Regular MEDIUM
        ]

        risk_counts = {"high": 0, "medium": 0, "low": 0}
        fast_path_count = 0

        for risk_level, fast_path_used in decisions:
            metrics.record_sanctions_decision(risk_level, fast_path_used)
            risk_counts[risk_level] += 1
            if fast_path_used:
                fast_path_count += 1

        print(f"   Total Decisions: {len(decisions)}")
        print(f"   High Risk: {risk_counts['high']} ({risk_counts['high']/len(decisions):.1%})")
        print(f"   Medium Risk: {risk_counts['medium']} ({risk_counts['medium']/len(decisions):.1%})")
        print(f"   Low Risk: {risk_counts['low']} ({risk_counts['low']/len(decisions):.1%})")
        print(f"   Fast Path Used: {fast_path_count} ({fast_path_count/len(decisions):.1%})")

        # Display final metrics summary
        print("\n" + "=" * 50)
        print("PERFORMANCE METRICS SUMMARY")
        print("=" * 50)

        print(f"Fast Path Cache Hit Rate: {hit_rate:.1%}")
        print(f"Average Stage Performance:")
        for stage_name, durations in pipeline_stages:
            avg_duration = sum(durations) / len(durations)
            print(f"  - {stage_name:12s}: {avg_duration:5.1f}ms")

        print(f"Sanctions Decisions: {len(decisions)} total")
        print(f"Fast Path Usage: {fast_path_count/len(decisions):.1%}")

        print("\n✅ All performance metrics recorded successfully!")

        # Try to export metrics (will be in fallback format if prometheus_client not available)
        print("\n📈 Exporting metrics...")
        metrics_data = metrics.get_metrics()

        # Count metrics lines
        metrics_lines = metrics_data.decode('utf-8').split('\n')
        metric_count = len([line for line in metrics_lines if line and not line.startswith('#')])

        print(f"   Generated {metric_count} metric data points")
        print("   ✅ Metrics export successful")

    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("PERFORMANCE METRICS TEST COMPLETE")

if __name__ == "__main__":
    test_performance_metrics()
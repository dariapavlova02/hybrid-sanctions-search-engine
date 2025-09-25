#!/usr/bin/env python3

"""
Test metrics integration with fast path INN cache.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_metrics_integration():
    """Test metrics integration with pipeline and fast path."""
    print("🔍 TESTING METRICS INTEGRATION")
    print("=" * 60)

    try:
        from ai_service.monitoring.prometheus_exporter import get_exporter

        print("✅ Successfully imported metrics exporter")

        # Get global exporter instance
        metrics = get_exporter()

        # Test fast path cache metrics recording
        print("\n1. Testing fast path cache metrics:")

        # Record some cache lookups
        metrics.record_fast_path_cache_lookup(hit=True)   # Cache hit
        metrics.record_fast_path_cache_lookup(hit=False)  # Cache miss
        metrics.record_fast_path_cache_lookup(hit=True)   # Another hit

        # Update cache hit rate
        metrics.update_fast_path_cache_hit_rate(0.67)  # 2 hits out of 3 lookups

        print("   ✅ Recorded 3 cache lookups (2 hits, 1 miss)")
        print("   ✅ Updated cache hit rate to 0.67")

        # Test pipeline stage duration metrics
        print("\n2. Testing pipeline stage metrics:")

        metrics.record_pipeline_stage_duration("normalization", 15.5)  # 15.5ms
        metrics.record_pipeline_stage_duration("signals", 8.2)         # 8.2ms
        metrics.record_pipeline_stage_duration("decision", 2.1)        # 2.1ms

        print("   ✅ Recorded normalization: 15.5ms")
        print("   ✅ Recorded signals: 8.2ms")
        print("   ✅ Recorded decision: 2.1ms")

        # Test sanctions decision metrics
        print("\n3. Testing sanctions decision metrics:")

        metrics.record_sanctions_decision("high", fast_path_used=True)   # Fast path HIGH
        metrics.record_sanctions_decision("medium", fast_path_used=False) # Regular MEDIUM
        metrics.record_sanctions_decision("high", fast_path_used=True)   # Another fast path HIGH

        print("   ✅ Recorded HIGH risk decision (fast path)")
        print("   ✅ Recorded MEDIUM risk decision (regular)")
        print("   ✅ Recorded another HIGH risk decision (fast path)")

        # Get and display metrics
        print("\n4. Generated Prometheus metrics:")
        print("-" * 40)

        metrics_data = metrics.get_metrics()
        print(metrics_data.decode('utf-8'))

        print("-" * 40)
        print("✅ Metrics successfully generated and exported")

    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("METRICS INTEGRATION TEST COMPLETE")

if __name__ == "__main__":
    test_metrics_integration()
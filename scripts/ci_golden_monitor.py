#!/usr/bin/env python3
"""
CI Golden Test Monitor - checks parity % and p95 latency for build gate.
"""

import asyncio
import json
import sys
import time
import statistics
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.ai_service.layers.normalization.normalization_service_legacy import NormalizationService as LegacyService
from src.ai_service.layers.normalization.normalization_service import NormalizationService as FactoryService

# Import configuration loader
try:
    from scripts.ci_config_loader import get_ci_thresholds, check_critical_conditions, send_alert
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

@dataclass
class CIThresholds:
    """CI build thresholds."""
    min_parity_rate: float = 0.8  # 80% minimum parity
    max_p95_latency_ms: float = 50.0  # 50ms p95 latency limit
    max_avg_latency_ms: float = 20.0  # 20ms average latency limit
    min_success_rate: float = 0.95  # 95% success rate

@dataclass
class TestResult:
    """Individual test result."""
    case_id: str
    input_text: str
    language: str
    expected: str
    legacy_output: str
    factory_output: str
    legacy_time: float
    factory_time: float
    legacy_success: bool
    factory_success: bool
    parity_match: bool
    legacy_accuracy: bool
    factory_accuracy: bool

@dataclass
class CIMetrics:
    """Aggregated CI metrics."""
    total_cases: int
    parity_rate: float
    legacy_accuracy: float
    factory_accuracy: float
    legacy_success_rate: float
    factory_success_rate: float
    legacy_avg_latency_ms: float
    factory_avg_latency_ms: float
    legacy_p95_latency_ms: float
    factory_p95_latency_ms: float
    passes_thresholds: bool
    failed_checks: List[str]

def load_golden_cases() -> List[Dict]:
    """Load golden cases from JSON."""
    golden_path = Path(__file__).parent.parent / "tests" / "golden_cases" / "golden_cases.json"
    return json.loads(golden_path.read_text())

def extract_expected_normalized(case: Dict) -> str:
    """Extract expected normalized string."""
    personas = case.get("expected_personas", [])
    if not personas:
        return ""
    return " | ".join(persona["normalized"] for persona in personas)

async def run_single_test(case: Dict, legacy_service: LegacyService, factory_service: FactoryService) -> TestResult:
    """Run single golden test case."""
    expected = extract_expected_normalized(case)

    # Test legacy
    start_time = time.perf_counter()
    try:
        legacy_result = legacy_service.normalize(
            case["input"],
            language=case["language"],
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True,
        )
        legacy_output = legacy_result.normalized
        legacy_success = legacy_result.success
    except Exception:
        legacy_output = ""
        legacy_success = False
    legacy_time = time.perf_counter() - start_time

    # Test factory
    start_time = time.perf_counter()
    try:
        factory_result = await factory_service.normalize_async(
            case["input"],
            language=case["language"],
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True,
        )
        factory_output = factory_result.normalized
        factory_success = factory_result.success
    except Exception:
        factory_output = ""
        factory_success = False
    factory_time = time.perf_counter() - start_time

    return TestResult(
        case_id=case["id"],
        input_text=case["input"],
        language=case["language"],
        expected=expected,
        legacy_output=legacy_output,
        factory_output=factory_output,
        legacy_time=legacy_time,
        factory_time=factory_time,
        legacy_success=legacy_success,
        factory_success=factory_success,
        parity_match=legacy_output == factory_output,
        legacy_accuracy=legacy_output == expected,
        factory_accuracy=factory_output == expected,
    )

async def run_golden_tests() -> List[TestResult]:
    """Run all golden tests."""
    cases = load_golden_cases()
    legacy_service = LegacyService()
    factory_service = FactoryService()

    results = []
    for case in cases:
        result = await run_single_test(case, legacy_service, factory_service)
        results.append(result)

    return results

def calculate_ci_metrics(results: List[TestResult], thresholds: CIThresholds) -> CIMetrics:
    """Calculate CI metrics and check thresholds."""
    total = len(results)

    # Basic rates
    parity_matches = sum(1 for r in results if r.parity_match)
    legacy_accurate = sum(1 for r in results if r.legacy_accuracy)
    factory_accurate = sum(1 for r in results if r.factory_accuracy)
    legacy_successes = sum(1 for r in results if r.legacy_success)
    factory_successes = sum(1 for r in results if r.factory_success)

    parity_rate = parity_matches / total
    legacy_accuracy = legacy_accurate / total
    factory_accuracy = factory_accurate / total
    legacy_success_rate = legacy_successes / total
    factory_success_rate = factory_successes / total

    # Latency metrics
    legacy_times_ms = [r.legacy_time * 1000 for r in results]
    factory_times_ms = [r.factory_time * 1000 for r in results]

    legacy_avg_latency = statistics.mean(legacy_times_ms)
    factory_avg_latency = statistics.mean(factory_times_ms)

    legacy_p95_latency = statistics.quantiles(legacy_times_ms, n=20)[18]  # 95th percentile
    factory_p95_latency = statistics.quantiles(factory_times_ms, n=20)[18]

    # Check thresholds
    failed_checks = []

    if parity_rate < thresholds.min_parity_rate:
        failed_checks.append(f"Parity rate {parity_rate:.1%} below threshold {thresholds.min_parity_rate:.1%}")

    if factory_p95_latency > thresholds.max_p95_latency_ms:
        failed_checks.append(f"Factory p95 latency {factory_p95_latency:.1f}ms above threshold {thresholds.max_p95_latency_ms}ms")

    if factory_avg_latency > thresholds.max_avg_latency_ms:
        failed_checks.append(f"Factory avg latency {factory_avg_latency:.1f}ms above threshold {thresholds.max_avg_latency_ms}ms")

    if factory_success_rate < thresholds.min_success_rate:
        failed_checks.append(f"Factory success rate {factory_success_rate:.1%} below threshold {thresholds.min_success_rate:.1%}")

    return CIMetrics(
        total_cases=total,
        parity_rate=parity_rate,
        legacy_accuracy=legacy_accuracy,
        factory_accuracy=factory_accuracy,
        legacy_success_rate=legacy_success_rate,
        factory_success_rate=factory_success_rate,
        legacy_avg_latency_ms=legacy_avg_latency,
        factory_avg_latency_ms=factory_avg_latency,
        legacy_p95_latency_ms=legacy_p95_latency,
        factory_p95_latency_ms=factory_p95_latency,
        passes_thresholds=len(failed_checks) == 0,
        failed_checks=failed_checks,
    )

def print_ci_report(metrics: CIMetrics, thresholds: CIThresholds):
    """Print CI report."""
    print("=" * 80)
    print("🔍 GOLDEN TEST CI MONITOR REPORT")
    print("=" * 80)

    status = "✅ PASS" if metrics.passes_thresholds else "❌ FAIL"
    print(f"Build Status: {status}")

    print(f"\n📊 Metrics Summary:")
    print(f"  Total test cases: {metrics.total_cases}")
    print(f"  Parity rate: {metrics.parity_rate:.1%} (threshold: {thresholds.min_parity_rate:.1%})")
    print(f"  Factory accuracy: {metrics.factory_accuracy:.1%}")
    print(f"  Factory success rate: {metrics.factory_success_rate:.1%} (threshold: {thresholds.min_success_rate:.1%})")

    print(f"\n⏱️  Performance Metrics:")
    print(f"  Factory avg latency: {metrics.factory_avg_latency_ms:.1f}ms (threshold: {thresholds.max_avg_latency_ms}ms)")
    print(f"  Factory p95 latency: {metrics.factory_p95_latency_ms:.1f}ms (threshold: {thresholds.max_p95_latency_ms}ms)")
    print(f"  Legacy avg latency: {metrics.legacy_avg_latency_ms:.1f}ms")
    print(f"  Legacy p95 latency: {metrics.legacy_p95_latency_ms:.1f}ms")

    if metrics.failed_checks:
        print(f"\n❌ Failed Checks:")
        for check in metrics.failed_checks:
            print(f"  - {check}")
    else:
        print(f"\n✅ All checks passed!")

    print(f"\nCI Thresholds:")
    print(f"  Min parity rate: {thresholds.min_parity_rate:.1%}")
    print(f"  Max p95 latency: {thresholds.max_p95_latency_ms}ms")
    print(f"  Max avg latency: {thresholds.max_avg_latency_ms}ms")
    print(f"  Min success rate: {thresholds.min_success_rate:.1%}")

def save_ci_metrics(metrics: CIMetrics, output_file: str):
    """Save CI metrics for monitoring."""
    data = {
        "timestamp": time.time(),
        "build_status": "pass" if metrics.passes_thresholds else "fail",
        "metrics": {
            "total_cases": metrics.total_cases,
            "parity_rate": metrics.parity_rate,
            "factory_accuracy": metrics.factory_accuracy,
            "factory_success_rate": metrics.factory_success_rate,
            "factory_avg_latency_ms": metrics.factory_avg_latency_ms,
            "factory_p95_latency_ms": metrics.factory_p95_latency_ms,
        },
        "failed_checks": metrics.failed_checks,
    }

    Path(output_file).write_text(json.dumps(data, indent=2))

async def main():
    """Main CI monitoring function."""
    # Parse command line arguments for custom thresholds
    import argparse
    import os

    parser = argparse.ArgumentParser(description="CI Golden Test Monitor")
    parser.add_argument("--min-parity", type=float, help="Minimum parity rate")
    parser.add_argument("--max-p95-latency", type=float, help="Maximum p95 latency in ms")
    parser.add_argument("--max-avg-latency", type=float, help="Maximum average latency in ms")
    parser.add_argument("--min-success-rate", type=float, help="Minimum success rate")
    parser.add_argument("--output", type=str, default="ci_metrics.json", help="Output file for metrics")
    parser.add_argument("--strict", action="store_true", help="Strict mode: fail on any threshold violation")
    parser.add_argument("--environment", type=str, help="CI environment (development, staging, production)")
    parser.add_argument("--enable-alerts", action="store_true", help="Enable alert notifications")

    args = parser.parse_args()

    # Load thresholds from configuration if available
    if CONFIG_AVAILABLE and not all([args.min_parity, args.max_p95_latency, args.max_avg_latency, args.min_success_rate]):
        environment = args.environment or os.getenv("CI_ENVIRONMENT", "development")
        config_thresholds = get_ci_thresholds(environment=environment)

        thresholds = CIThresholds(
            min_parity_rate=args.min_parity or config_thresholds.min_parity_rate,
            max_p95_latency_ms=args.max_p95_latency or config_thresholds.max_p95_latency_ms,
            max_avg_latency_ms=args.max_avg_latency or config_thresholds.max_avg_latency_ms,
            min_success_rate=args.min_success_rate or config_thresholds.min_success_rate,
        )
        print(f"📋 Using {environment} environment thresholds")
    else:
        # Fallback to command line arguments or defaults
        thresholds = CIThresholds(
            min_parity_rate=args.min_parity or 0.8,
            max_p95_latency_ms=args.max_p95_latency or 50.0,
            max_avg_latency_ms=args.max_avg_latency or 20.0,
            min_success_rate=args.min_success_rate or 0.95,
        )
        print("📋 Using command line or default thresholds")

    print("🚀 Starting Golden Test CI Monitor...")

    try:
        results = await run_golden_tests()
        metrics = calculate_ci_metrics(results, thresholds)

        print_ci_report(metrics, thresholds)
        save_ci_metrics(metrics, args.output)

        # Check critical conditions and send alerts if enabled
        if args.enable_alerts and CONFIG_AVAILABLE:
            metrics_dict = {
                "parity_rate": metrics.parity_rate,
                "factory_success_rate": metrics.factory_success_rate,
                "factory_p95_latency_ms": metrics.factory_p95_latency_ms
            }

            critical_conditions = check_critical_conditions(metrics_dict)
            if critical_conditions:
                alert_message = f"🚨 CRITICAL: Golden Test Monitor Alert\n\n"
                alert_message += f"Environment: {args.environment or 'development'}\n"
                alert_message += f"Parity Rate: {metrics.parity_rate:.1%}\n"
                alert_message += f"Success Rate: {metrics.factory_success_rate:.1%}\n"
                alert_message += f"P95 Latency: {metrics.factory_p95_latency_ms:.1f}ms\n\n"
                alert_message += f"Triggered conditions:\n"
                for condition in critical_conditions:
                    alert_message += f"- {condition}\n"

                send_alert(alert_message)
                print(f"\n🚨 Critical conditions triggered - alerts sent!")

        # Exit with appropriate code for CI
        if not metrics.passes_thresholds:
            print(f"\n💥 Build failed due to threshold violations!")
            sys.exit(1)
        else:
            print(f"\n🎉 Build passed all quality gates!")
            sys.exit(0)

    except Exception as e:
        print(f"❌ CI Monitor failed with error: {e}")

        # Send failure alert if enabled
        if args.enable_alerts and CONFIG_AVAILABLE:
            failure_message = f"💥 CI Monitor Failure\n\nError: {str(e)}\nEnvironment: {args.environment or 'development'}"
            send_alert(failure_message)

        sys.exit(2)

if __name__ == "__main__":
    asyncio.run(main())
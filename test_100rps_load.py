#!/usr/bin/env python3
"""
Load test script for 100 RPS payment processing capacity.
Tests realistic payment scenarios with concurrent requests.
"""

import asyncio
import aiohttp
import time
import json
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class PaymentTestCase:
    """Represents a payment processing test case."""
    text: str
    expected_language: str
    description: str

# Realistic payment test cases
PAYMENT_TEST_CASES = [
    PaymentTestCase("Иванов Иван Иванович", "ru", "Simple Russian name"),
    PaymentTestCase("ООО Рога и Копыта", "ru", "Russian company"),
    PaymentTestCase("Smith John", "en", "English name"),
    PaymentTestCase("Перевод на карту Петрову А.А.", "ru", "Card transfer"),
    PaymentTestCase("ИП Сидоров Петр Васильевич", "ru", "Individual entrepreneur"),
    PaymentTestCase("Петренко Олександр Іванович", "uk", "Ukrainian name"),
    PaymentTestCase("ТОВ Будівельна компанія", "uk", "Ukrainian company"),
    PaymentTestCase("Payment to Johnson & Co LLC", "en", "English company"),
    PaymentTestCase("За услуги по договору №123", "ru", "Service payment"),
    PaymentTestCase("Возврат средств клиенту", "ru", "Refund payment"),
]

@dataclass
class TestResult:
    """Test result statistics."""
    success: bool
    response_time_ms: float
    status_code: int
    error: str = ""

class LoadTester:
    """Load tester for payment processing."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[TestResult] = []

    async def send_payment_request(self, session: aiohttp.ClientSession, payment: PaymentTestCase) -> TestResult:
        """Send a single payment processing request."""
        start_time = time.time()

        try:
            payload = {
                "text": payment.text,
                "generate_variants": False,
                "generate_embeddings": False
            }

            async with session.post(
                f"{self.base_url}/process",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5.0)
            ) as response:
                end_time = time.time()
                response_time_ms = (end_time - start_time) * 1000

                if response.status == 200:
                    data = await response.json()
                    return TestResult(
                        success=data.get("success", False),
                        response_time_ms=response_time_ms,
                        status_code=response.status
                    )
                else:
                    return TestResult(
                        success=False,
                        response_time_ms=response_time_ms,
                        status_code=response.status,
                        error=f"HTTP {response.status}"
                    )

        except Exception as e:
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            return TestResult(
                success=False,
                response_time_ms=response_time_ms,
                status_code=0,
                error=str(e)
            )

    async def run_concurrent_batch(self, rps: int, duration_seconds: int) -> List[TestResult]:
        """Run concurrent requests at specified RPS for given duration."""
        total_requests = rps * duration_seconds
        interval = 1.0 / rps  # Time between requests to maintain RPS

        print(f"Starting load test: {rps} RPS for {duration_seconds} seconds")
        print(f"Total requests: {total_requests}")
        print(f"Request interval: {interval:.3f} seconds")

        connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=50,  # Per-host connection limit
            ttl_dns_cache=300,
            use_dns_cache=True,
        )

        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            start_time = time.time()

            for i in range(total_requests):
                # Select payment case cyclically
                payment = PAYMENT_TEST_CASES[i % len(PAYMENT_TEST_CASES)]

                # Schedule the request
                task = asyncio.create_task(self.send_payment_request(session, payment))
                tasks.append(task)

                # Wait to maintain RPS (except for last request)
                if i < total_requests - 1:
                    elapsed = time.time() - start_time
                    expected_time = (i + 1) * interval
                    sleep_time = max(0, expected_time - elapsed)
                    if sleep_time > 0:
                        await asyncio.sleep(sleep_time)

            # Wait for all requests to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out exceptions and convert to TestResult
            valid_results = []
            for result in results:
                if isinstance(result, TestResult):
                    valid_results.append(result)
                else:
                    # Handle exceptions
                    valid_results.append(TestResult(
                        success=False,
                        response_time_ms=0,
                        status_code=0,
                        error=str(result)
                    ))

            return valid_results

    def analyze_results(self, results: List[TestResult]) -> Dict[str, Any]:
        """Analyze test results and return statistics."""
        if not results:
            return {"error": "No results to analyze"}

        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        response_times = [r.response_time_ms for r in results]
        successful_times = [r.response_time_ms for r in successful]

        stats = {
            "total_requests": len(results),
            "successful_requests": len(successful),
            "failed_requests": len(failed),
            "success_rate": len(successful) / len(results) * 100,
            "response_times": {
                "min_ms": min(response_times) if response_times else 0,
                "max_ms": max(response_times) if response_times else 0,
                "mean_ms": statistics.mean(response_times) if response_times else 0,
                "median_ms": statistics.median(response_times) if response_times else 0,
                "p95_ms": statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else 0,
                "p99_ms": statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else 0,
            },
            "successful_response_times": {
                "mean_ms": statistics.mean(successful_times) if successful_times else 0,
                "p95_ms": statistics.quantiles(successful_times, n=20)[18] if len(successful_times) >= 20 else 0,
            },
            "error_breakdown": {}
        }

        # Error breakdown
        error_counts = {}
        for result in failed:
            error_key = result.error or f"HTTP_{result.status_code}"
            error_counts[error_key] = error_counts.get(error_key, 0) + 1
        stats["error_breakdown"] = error_counts

        return stats

async def main():
    """Main load testing function."""
    tester = LoadTester()

    # Test scenarios
    test_scenarios = [
        (50, 10),   # 50 RPS for 10 seconds
        (75, 10),   # 75 RPS for 10 seconds
        (100, 10),  # 100 RPS for 10 seconds
        (125, 10),  # 125 RPS for 10 seconds (overload test)
    ]

    print("🧪 Payment Processing Load Test")
    print("=" * 50)

    # Check if service is available
    try:
        connector = aiohttp.TCPConnector()
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get("http://localhost:8000/health") as response:
                if response.status != 200:
                    print("❌ Service is not available. Start the service first.")
                    return
                print("✅ Service is available")
    except Exception as e:
        print(f"❌ Cannot connect to service: {e}")
        print("Start the service with: python -m uvicorn src.ai_service.main:app --host 0.0.0.0 --port 8000")
        return

    overall_results = {}

    for rps, duration in test_scenarios:
        print(f"\n🚀 Testing {rps} RPS for {duration} seconds...")

        results = await tester.run_concurrent_batch(rps, duration)
        stats = tester.analyze_results(results)
        overall_results[f"{rps}_rps"] = stats

        print(f"📊 Results for {rps} RPS:")
        print(f"   Total requests: {stats['total_requests']}")
        print(f"   Success rate: {stats['success_rate']:.1f}%")
        print(f"   Failed requests: {stats['failed_requests']}")
        print(f"   Response times:")
        print(f"     Mean: {stats['response_times']['mean_ms']:.1f}ms")
        print(f"     P95: {stats['response_times']['p95_ms']:.1f}ms")
        print(f"     P99: {stats['response_times']['p99_ms']:.1f}ms")

        if stats['error_breakdown']:
            print(f"   Errors: {stats['error_breakdown']}")

        # Verdict for this RPS level
        if stats['success_rate'] >= 99.0 and stats['response_times']['p95_ms'] <= 100:
            print(f"   ✅ {rps} RPS: EXCELLENT")
        elif stats['success_rate'] >= 95.0 and stats['response_times']['p95_ms'] <= 200:
            print(f"   🟢 {rps} RPS: GOOD")
        elif stats['success_rate'] >= 90.0:
            print(f"   🟡 {rps} RPS: ACCEPTABLE")
        else:
            print(f"   🔴 {rps} RPS: POOR")

        # Brief pause between tests
        await asyncio.sleep(2)

    print(f"\n🎯 FINAL VERDICT:")
    print("=" * 50)

    # Check 100 RPS specifically
    if "100_rps" in overall_results:
        rps100_stats = overall_results["100_rps"]
        if rps100_stats['success_rate'] >= 99.0 and rps100_stats['response_times']['p95_ms'] <= 100:
            print("✅ 100 RPS PAYMENT PROCESSING: READY FOR PRODUCTION!")
            print(f"   Success rate: {rps100_stats['success_rate']:.1f}%")
            print(f"   P95 latency: {rps100_stats['response_times']['p95_ms']:.1f}ms")
        else:
            print("❌ 100 RPS PAYMENT PROCESSING: NEEDS OPTIMIZATION")
            print(f"   Success rate: {rps100_stats['success_rate']:.1f}% (target: >99%)")
            print(f"   P95 latency: {rps100_stats['response_times']['p95_ms']:.1f}ms (target: <100ms)")

    # Save detailed results
    with open("load_test_results.json", "w") as f:
        json.dump(overall_results, f, indent=2)

    print(f"\n📝 Detailed results saved to: load_test_results.json")

if __name__ == "__main__":
    asyncio.run(main())
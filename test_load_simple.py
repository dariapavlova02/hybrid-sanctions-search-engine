#!/usr/bin/env python3
"""
Simple load testing script for AI Service - 50 requests per second using threads
"""

import requests
import time
import json
import threading
import queue
from typing import List, Dict, Any
from dataclasses import dataclass
from collections import defaultdict
import random
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

@dataclass
class TestResult:
    """Result of a single test request"""
    request_id: int
    start_time: float
    end_time: float
    status_code: int
    response_time: float
    success: bool
    error: str = None


class LoadTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        self.results_lock = threading.Lock()
        self.test_data = self._generate_test_data()

    def _generate_test_data(self) -> List[str]:
        """Generate varied test data for more realistic testing"""
        return [
            # Ukrainian names
            "Петро Порошенко",
            "Володимир Зеленський",
            "Юлія Тимошенко",
            "Віталій Кличко",
            "Ігор Коломойський",

            # Complex cases with context
            "Платеж от Петра Порошенко",
            "Сплата по договору від Булат Максим Євгенович",
            "Абон плата за телекомунікаційні послуги, Шевченко",

            # With IDs
            "Павлова Дарія ІПН 782611846337",
            "Петренко Петро ЄДРПОУ 12345678",

            # Misspelled names (for vector search)
            "Порошенк Петро",
            "Зеленскй Владимир",

            # Organizations
            "ТОВ Приватбанк",
            "ООО Газпром",

            # Edge cases
            "Іван",
            "А.Б.",
        ]

    def send_request(self, request_id: int, text: str) -> TestResult:
        """Send a single request to the API"""
        start_time = time.time()

        payload = {
            "text": text,
            "language": "auto",
            "enable_search": True,
            "enable_variants": False,
            "enable_embeddings": False
        }

        try:
            response = requests.post(
                f"{self.base_url}/process",
                json=payload,
                timeout=30
            )
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to ms

            return TestResult(
                request_id=request_id,
                start_time=start_time,
                end_time=end_time,
                status_code=response.status_code,
                response_time=response_time,
                success=response.status_code == 200,
                error=None if response.status_code == 200 else f"HTTP {response.status_code}"
            )

        except requests.exceptions.Timeout:
            end_time = time.time()
            return TestResult(
                request_id=request_id,
                start_time=start_time,
                end_time=end_time,
                status_code=0,
                response_time=(end_time - start_time) * 1000,
                success=False,
                error="Timeout"
            )

        except Exception as e:
            end_time = time.time()
            return TestResult(
                request_id=request_id,
                start_time=start_time,
                end_time=end_time,
                status_code=0,
                response_time=(end_time - start_time) * 1000,
                success=False,
                error=str(e)
            )

    def worker(self, request_id: int, text: str):
        """Worker function for thread pool"""
        result = self.send_request(request_id, text)
        with self.results_lock:
            self.results.append(result)
        return result

    def run_load_test(self, target_rps: int = 50, duration_seconds: int = 10):
        """Run the load test at target RPS for specified duration"""
        print(f"🚀 Starting load test: {target_rps} RPS for {duration_seconds} seconds")
        print(f"📊 Total requests to send: {target_rps * duration_seconds}")
        print("-" * 60)

        # Warm up
        print("🔥 Warming up...")
        self.send_request(0, "warm up request")

        print(f"📈 Starting main test at {target_rps} RPS...")
        start_time = time.time()

        # Use ThreadPoolExecutor for concurrent requests
        with ThreadPoolExecutor(max_workers=target_rps * 2) as executor:
            futures = []
            request_id = 0

            for second in range(duration_seconds):
                batch_start = time.time()

                # Submit target_rps requests
                batch_futures = []
                for _ in range(target_rps):
                    text = random.choice(self.test_data)
                    future = executor.submit(self.worker, request_id, text)
                    futures.append(future)
                    batch_futures.append(future)
                    request_id += 1

                # Wait for the second to complete
                elapsed = time.time() - batch_start
                if elapsed < 1.0:
                    time.sleep(1.0 - elapsed)

                # Progress update
                completed = len([f for f in futures if f.done()])
                print(f"  Second {second + 1}/{duration_seconds}: "
                      f"{request_id} requests sent, {completed} completed")

            # Wait for all requests to complete
            print("\n⏳ Waiting for all requests to complete...")
            for future in as_completed(futures):
                pass

        total_duration = time.time() - start_time
        actual_rps = len(self.results) / total_duration

        print("-" * 60)
        print(f"✅ Load test completed!")
        print(f"⏱️  Total duration: {total_duration:.2f} seconds")
        print(f"📊 Actual RPS: {actual_rps:.2f}")

        self.print_statistics()

    def print_statistics(self):
        """Print detailed statistics of the test results"""
        if not self.results:
            print("❌ No results to analyze")
            return

        # Calculate statistics
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]

        response_times = [r.response_time for r in successful]

        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)

        print(f"\n✅ Success Rate: {len(successful)}/{len(self.results)} "
              f"({len(successful)/len(self.results)*100:.1f}%)")
        print(f"❌ Failed: {len(failed)}")

        if response_times:
            print(f"\n⏱️  Response Time Statistics (successful requests):")
            print(f"   Min:     {min(response_times):.2f} ms")
            print(f"   Max:     {max(response_times):.2f} ms")
            print(f"   Mean:    {statistics.mean(response_times):.2f} ms")
            print(f"   Median:  {statistics.median(response_times):.2f} ms")
            if len(response_times) > 1:
                print(f"   StdDev:  {statistics.stdev(response_times):.2f} ms")

            # Calculate percentiles
            sorted_times = sorted(response_times)
            p50_idx = min(len(sorted_times) * 50 // 100, len(sorted_times) - 1)
            p90_idx = min(len(sorted_times) * 90 // 100, len(sorted_times) - 1)
            p95_idx = min(len(sorted_times) * 95 // 100, len(sorted_times) - 1)
            p99_idx = min(len(sorted_times) * 99 // 100, len(sorted_times) - 1)

            print(f"\n📈 Percentiles:")
            print(f"   50th (p50): {sorted_times[p50_idx]:.2f} ms")
            print(f"   90th (p90): {sorted_times[p90_idx]:.2f} ms")
            print(f"   95th (p95): {sorted_times[p95_idx]:.2f} ms")
            print(f"   99th (p99): {sorted_times[p99_idx]:.2f} ms")

        # Error analysis
        if failed:
            print(f"\n❌ Error Analysis:")
            error_counts = defaultdict(int)
            for r in failed:
                error_counts[r.error] += 1

            for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"   {error}: {count}")

        # Response time distribution
        if response_times:
            print(f"\n📊 Response Time Distribution:")
            buckets = [(0, 50), (50, 100), (100, 200), (200, 500),
                      (500, 1000), (1000, 2000), (2000, 5000), (5000, float('inf'))]

            for low, high in buckets:
                count = sum(1 for rt in response_times if low <= rt < high)
                if count > 0:
                    percentage = count / len(response_times) * 100
                    bar = '█' * int(percentage / 2)
                    label = f"{low}-{high}ms" if high != float('inf') else f">{low}ms"
                    print(f"   {label:>12}: {bar} {count} ({percentage:.1f}%)")


def main():
    """Main function to run the load test"""
    tester = LoadTester()

    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/health/detailed", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"✅ Server is running ({health.get('version', 'unknown')})")
            print(f"   Status: {health.get('status', 'unknown')}\n")
        else:
            print(f"⚠️  Server returned status {response.status_code}\n")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("Please make sure the server is running on http://localhost:8000")
        return

    # Run load test at 50 RPS for 10 seconds
    tester.run_load_test(target_rps=50, duration_seconds=10)

    print("\n" + "=" * 60)
    print("💡 RECOMMENDATIONS:")
    print("=" * 60)

    # Analyze and provide recommendations
    if tester.results:
        successful = [r for r in tester.results if r.success]
        success_rate = len(successful) / len(tester.results) if tester.results else 0

        if success_rate < 0.95:
            print("⚠️  Success rate is below 95%. Consider:")
            print("   • Increasing server resources (CPU/Memory)")
            print("   • Optimizing database queries")
            print("   • Implementing caching")
            print("   • Scaling horizontally (more instances)")

        response_times = [r.response_time for r in successful] if successful else []
        if response_times and statistics.mean(response_times) > 1000:
            print("⚠️  Average response time exceeds 1 second. Consider:")
            print("   • Profiling the application to find bottlenecks")
            print("   • Optimizing normalization algorithms")
            print("   • Using connection pooling")
            print("   • Enabling async processing")

        if success_rate >= 0.95 and response_times and statistics.mean(response_times) < 500:
            print("✅ Server is handling 50 RPS well!")
            print("   • Consider increasing RPS to find the limit")
            print("   • Monitor resource usage during peak loads")
            print("   • Set up alerts for performance degradation")


if __name__ == "__main__":
    print("🔧 AI Service Load Testing Tool")
    print("================================")
    main()
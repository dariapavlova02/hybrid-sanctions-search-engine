#!/usr/bin/env python3
"""
Load testing script for AI Service - 50 requests per second
"""

import asyncio
import aiohttp
import time
import json
from typing import List, Dict, Any
from dataclasses import dataclass
from collections import defaultdict
import random
import statistics

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
    response_data: dict = None


class LoadTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[TestResult] = []
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
            "Рінат Ахметов",
            "Павло Фукс",
            "Вадим Новинський",
            "Дмитро Фірташ",
            "Сергій Тігіпко",

            # Russian names
            "Владимир Путин",
            "Сергей Лавров",
            "Михаил Мишустин",
            "Дмитрий Медведев",
            "Алексей Навальный",

            # Complex cases with context
            "Платеж от Петра Порошенко",
            "Оплата услуг Иванов Иван Иванович",
            "Перевод от ООО Рога и Копыта для Петрова",
            "Сплата по договору від Булат Максим Євгенович",
            "Абон плата за телекомунікаційні послуги, Шевченко",

            # With IDs
            "Павлова Дарія ІПН 782611846337",
            "Іванов Іван ІПН 1234567890",
            "Петренко Петро ЄДРПОУ 12345678",

            # Misspelled names (for vector search)
            "Порошенк Петро",
            "Зеленскй Владимир",
            "Тимошенк Юлия",

            # English names
            "John Smith",
            "Mary Johnson",
            "Robert Williams Jr.",

            # Mixed scripts
            "Sergey Лавров",
            "Vladimir Путін",
            "Oleksandr Smith",

            # Organizations
            "ТОВ Приватбанк",
            "ООО Газпром",
            "LLC Microsoft Ukraine",
            "АТ Укрнафта",

            # Edge cases
            ".",
            "123",
            "   ",
            "Іван",
            "А.Б.",
            "фон дер Ляйен",
            "д'Артаньян",
            "О'Брайен",
            "Мак-Дональд",

            # Long texts
            "Платіж за комунальні послуги від Іванова Івана Івановича за листопад 2024 року згідно договору №123456",
            "Payment from John Smith for consulting services according to invoice INV-2024-001 dated November 15, 2024",

            # Multiple persons
            "Петро Порошенко та Юлія Тимошенко",
            "Іванов, Петров і Сидоров",
            "От Марії та Івана Петренків",
        ]

    async def send_request(self, session: aiohttp.ClientSession, request_id: int, text: str) -> TestResult:
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
            async with session.post(
                f"{self.base_url}/api/v1/process",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to ms

                response_data = await response.json()

                return TestResult(
                    request_id=request_id,
                    start_time=start_time,
                    end_time=end_time,
                    status_code=response.status,
                    response_time=response_time,
                    success=response.status == 200,
                    response_data=response_data
                )

        except asyncio.TimeoutError:
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

    async def run_batch(self, session: aiohttp.ClientSession, batch_size: int, batch_id: int) -> List[TestResult]:
        """Run a batch of requests concurrently"""
        tasks = []
        for i in range(batch_size):
            request_id = batch_id * batch_size + i
            text = random.choice(self.test_data)
            tasks.append(self.send_request(session, request_id, text))

        return await asyncio.gather(*tasks)

    async def run_load_test(self, target_rps: int = 50, duration_seconds: int = 10):
        """Run the load test at target RPS for specified duration"""
        print(f"🚀 Starting load test: {target_rps} RPS for {duration_seconds} seconds")
        print(f"📊 Total requests to send: {target_rps * duration_seconds}")
        print("-" * 60)

        connector = aiohttp.TCPConnector(
            limit=100,  # Connection pool size
            limit_per_host=100
        )

        async with aiohttp.ClientSession(connector=connector) as session:
            # Warm up with a single request
            print("🔥 Warming up...")
            await self.send_request(session, 0, "warm up request")

            print(f"📈 Starting main test at {target_rps} RPS...")
            start_time = time.time()

            # Calculate batch parameters
            batch_size = target_rps  # Send target_rps requests each second
            total_batches = duration_seconds

            for batch_id in range(total_batches):
                batch_start = time.time()

                # Send batch
                batch_results = await self.run_batch(session, batch_size, batch_id)
                self.results.extend(batch_results)

                # Calculate how long to wait to maintain RPS
                batch_duration = time.time() - batch_start
                wait_time = max(0, 1.0 - batch_duration)  # Wait remainder of the second

                # Progress update
                completed = (batch_id + 1) * batch_size
                print(f"  Batch {batch_id + 1}/{total_batches}: {completed} requests sent, "
                      f"batch took {batch_duration:.2f}s, waiting {wait_time:.2f}s")

                if wait_time > 0:
                    await asyncio.sleep(wait_time)

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
            p50 = sorted_times[len(sorted_times) * 50 // 100]
            p90 = sorted_times[len(sorted_times) * 90 // 100]
            p95 = sorted_times[len(sorted_times) * 95 // 100]
            p99 = sorted_times[len(sorted_times) * 99 // 100] if len(sorted_times) > 100 else sorted_times[-1]

            print(f"\n📈 Percentiles:")
            print(f"   50th (p50): {p50:.2f} ms")
            print(f"   90th (p90): {p90:.2f} ms")
            print(f"   95th (p95): {p95:.2f} ms")
            print(f"   99th (p99): {p99:.2f} ms")

        # Error analysis
        if failed:
            print(f"\n❌ Error Analysis:")
            error_counts = defaultdict(int)
            for r in failed:
                error_counts[r.error or f"HTTP {r.status_code}"] += 1

            for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"   {error}: {count}")

        # Status code distribution
        print(f"\n🔢 Status Code Distribution:")
        status_counts = defaultdict(int)
        for r in self.results:
            status_counts[r.status_code] += 1

        for status, count in sorted(status_counts.items()):
            print(f"   {status}: {count}")

        # Response time distribution
        if response_times:
            print(f"\n📊 Response Time Distribution:")
            buckets = [0, 10, 25, 50, 100, 200, 500, 1000, 2000, 5000, float('inf')]
            bucket_counts = defaultdict(int)

            for rt in response_times:
                for i in range(len(buckets) - 1):
                    if buckets[i] <= rt < buckets[i + 1]:
                        bucket_counts[f"{buckets[i]}-{buckets[i+1]}ms"] += 1
                        break

            for bucket, count in sorted(bucket_counts.items(), key=lambda x: float(x[0].split('-')[0])):
                percentage = count / len(response_times) * 100
                bar = '█' * int(percentage / 2)
                print(f"   {bucket:>15}: {bar} {count} ({percentage:.1f}%)")


async def main():
    """Main function to run the load test"""
    tester = LoadTester()

    # Run load test at 50 RPS for 10 seconds
    await tester.run_load_test(target_rps=50, duration_seconds=10)

    print("\n" + "=" * 60)
    print("💡 RECOMMENDATIONS:")
    print("=" * 60)

    # Analyze and provide recommendations
    if tester.results:
        successful = [r for r in tester.results if r.success]
        success_rate = len(successful) / len(tester.results)

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
            print("   • Implementing async processing where possible")
            print("   • Using connection pooling")

        if success_rate >= 0.95 and response_times and statistics.mean(response_times) < 500:
            print("✅ Server is handling 50 RPS well!")
            print("   • Consider increasing RPS to find the limit")
            print("   • Monitor resource usage during peak loads")
            print("   • Set up alerts for performance degradation")


if __name__ == "__main__":
    print("🔧 AI Service Load Testing Tool")
    print("================================")
    asyncio.run(main())
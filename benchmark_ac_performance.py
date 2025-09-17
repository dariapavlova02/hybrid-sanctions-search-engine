"""
Benchmark script to compare Aho-Corasick vs basic pattern matching performance.
"""

import time
import statistics
from typing import List

# Import the role tagger classes
from src.ai_service.layers.normalization.role_tagger import RoleTagger


def benchmark_role_tagger(tokens_list: List[List[str]], language: str = "ru", iterations: int = 100):
    """Benchmark role tagger with and without AC acceleration."""

    # Initialize both versions
    ac_tagger = RoleTagger(window=3, enable_ac=True)
    basic_tagger = RoleTagger(window=3, enable_ac=False)

    print(f"Benchmarking role tagger with {len(tokens_list)} token sets, {iterations} iterations each")
    print(f"Language: {language}")
    print(f"AC enabled: {ac_tagger.enable_ac}, automaton built: {ac_tagger._ac_automaton is not None}")
    print(f"Basic enabled: {basic_tagger.enable_ac}")

    # Benchmark AC-enabled version
    ac_times = []
    for _ in range(iterations):
        start_time = time.perf_counter()
        for tokens in tokens_list:
            _ = ac_tagger.tag(tokens, language)
        end_time = time.perf_counter()
        ac_times.append((end_time - start_time) * 1000)  # Convert to milliseconds

    # Benchmark basic version
    basic_times = []
    for _ in range(iterations):
        start_time = time.perf_counter()
        for tokens in tokens_list:
            _ = basic_tagger.tag(tokens, language)
        end_time = time.perf_counter()
        basic_times.append((end_time - start_time) * 1000)  # Convert to milliseconds

    # Calculate statistics
    ac_mean = statistics.mean(ac_times)
    ac_median = statistics.median(ac_times)
    ac_p95 = sorted(ac_times)[int(0.95 * len(ac_times))]

    basic_mean = statistics.mean(basic_times)
    basic_median = statistics.median(basic_times)
    basic_p95 = sorted(basic_times)[int(0.95 * len(basic_times))]

    # Print results
    print("\n=== BENCHMARK RESULTS ===")
    print(f"AC Tagger    - Mean: {ac_mean:.2f}ms, Median: {ac_median:.2f}ms, P95: {ac_p95:.2f}ms")
    print(f"Basic Tagger - Mean: {basic_mean:.2f}ms, Median: {basic_median:.2f}ms, P95: {basic_p95:.2f}ms")

    # Calculate improvement
    mean_improvement = ((basic_mean - ac_mean) / basic_mean) * 100
    p95_improvement = ((basic_p95 - ac_p95) / basic_p95) * 100

    print(f"\nImprovement with AC:")
    print(f"Mean: {mean_improvement:+.1f}% ({'faster' if mean_improvement > 0 else 'slower'})")
    print(f"P95:  {p95_improvement:+.1f}% ({'faster' if p95_improvement > 0 else 'slower'})")

    # Test result consistency
    ac_sample = ac_tagger.tag(tokens_list[0], language)
    basic_sample = basic_tagger.tag(tokens_list[0], language)

    print(f"\nResult consistency check:")
    print(f"AC result:    {[(tag.token, tag.role.value) for tag in ac_sample]}")
    print(f"Basic result: {[(tag.token, tag.role.value) for tag in basic_sample]}")
    print(f"Results match: {len(ac_sample) == len(basic_sample) and all(a.role == b.role for a, b in zip(ac_sample, basic_sample))}")


def create_large_test_case(size: int = 100) -> List[str]:
    """Create a large test case with many tokens."""
    import random

    # Base patterns to repeat
    patterns = [
        ["ООО", "КОМПАНИЯ", "РАЗРАБОТКА", "платеж", "за", "услуги", "согласно", "договор"],
        ["ТОВ", "ПРОГРЕС", "оплата", "в", "пользу", "клиент", "банк"],
        ["LLC", "TECHNOLOGY", "SOLUTIONS", "payment", "for", "services", "invoice"],
        ["платеж", "транзакция", "перевод", "депозит", "снятие", "комиссия"],
        ["ТОВАРИСТВО", "ОБМЕЖЕНОЮ", "ВІДПОВІДАЛЬНІСТЮ", "платіж", "користь"],
        ["invoice", "payment", "transfer", "deposit", "withdrawal", "commission", "fee"]
    ]

    result = []
    for _ in range(size):
        pattern = random.choice(patterns)
        result.extend(pattern)

    return result


def main():
    """Run benchmark with various test cases."""

    print("Starting Aho-Corasick Role Tagger Performance Benchmark")
    print("=" * 60)

    # Test with different data sizes
    test_sizes = [
        ("Small (5 tokens)", [
            ["Іван", "Петрович", "Іваненко"],
            ["ООО", "КОМПАНИЯ"],
            ["платеж", "услуги", "договор"]
        ]),
        ("Medium (50 tokens)", [create_large_test_case(10) for _ in range(5)]),
        ("Large (500 tokens)", [create_large_test_case(100) for _ in range(5)]),
        ("XLarge (1000 tokens)", [create_large_test_case(200) for _ in range(5)])
    ]

    for test_name, test_cases in test_sizes:
        print(f"\n{test_name} test:")
        print("-" * 40)
        try:
            benchmark_role_tagger(test_cases, language="ru", iterations=20)
        except Exception as e:
            print(f"Benchmark failed for {test_name}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
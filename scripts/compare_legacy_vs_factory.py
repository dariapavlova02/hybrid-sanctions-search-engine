#!/usr/bin/env python3
"""
Compare legacy vs factory normalization outputs using golden cases.
"""

import json
import asyncio
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass

# Import legacy service
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.ai_service.layers.normalization.normalization_service_legacy import NormalizationService as LegacyService
from src.ai_service.layers.normalization.normalization_service import NormalizationService as FactoryService

@dataclass
class ComparisonResult:
    case_id: str
    input_text: str
    language: str
    expected: str
    legacy_output: str
    factory_output: str
    legacy_success: bool
    factory_success: bool
    legacy_time: float
    factory_time: float
    match: bool
    legacy_match: bool
    factory_match: bool

def load_golden_cases() -> List[Dict]:
    """Load golden cases from JSON file."""
    golden_path = Path(__file__).parent.parent / "tests" / "golden_cases" / "golden_cases.json"
    return json.loads(golden_path.read_text())

def extract_expected_normalized(case: Dict) -> str:
    """Extract expected normalized string from case."""
    personas = case.get("expected_personas", [])
    if not personas:
        return ""
    return " | ".join(persona["normalized"] for persona in personas)

async def compare_case(case: Dict, legacy_service: LegacyService, factory_service: FactoryService) -> ComparisonResult:
    """Compare legacy vs factory for a single case."""
    expected = extract_expected_normalized(case)

    # Test legacy
    start_time = time.time()
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
        legacy_time = time.time() - start_time
    except Exception as e:
        legacy_output = f"ERROR: {e}"
        legacy_success = False
        legacy_time = time.time() - start_time

    # Test factory
    start_time = time.time()
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
        factory_time = time.time() - start_time
    except Exception as e:
        factory_output = f"ERROR: {e}"
        factory_success = False
        factory_time = time.time() - start_time

    return ComparisonResult(
        case_id=case["id"],
        input_text=case["input"],
        language=case["language"],
        expected=expected,
        legacy_output=legacy_output,
        factory_output=factory_output,
        legacy_success=legacy_success,
        factory_success=factory_success,
        legacy_time=legacy_time,
        factory_time=factory_time,
        match=legacy_output == factory_output,
        legacy_match=legacy_output == expected,
        factory_match=factory_output == expected,
    )

async def run_comparison() -> List[ComparisonResult]:
    """Run full comparison of all golden cases."""
    print("Loading golden cases...")
    cases = load_golden_cases()
    print(f"Found {len(cases)} golden cases")

    print("Initializing services...")
    legacy_service = LegacyService()
    factory_service = FactoryService()

    print("Running comparisons...")
    results = []
    for i, case in enumerate(cases):
        print(f"Processing case {i+1}/{len(cases)}: {case['id']}")
        result = await compare_case(case, legacy_service, factory_service)
        results.append(result)

    return results

def analyze_results(results: List[ComparisonResult]) -> Dict[str, Any]:
    """Analyze comparison results and generate statistics."""
    total = len(results)

    # Basic counts
    legacy_vs_factory_matches = sum(1 for r in results if r.match)
    legacy_vs_expected_matches = sum(1 for r in results if r.legacy_match)
    factory_vs_expected_matches = sum(1 for r in results if r.factory_match)

    # Success rates
    legacy_success_rate = sum(1 for r in results if r.legacy_success) / total
    factory_success_rate = sum(1 for r in results if r.factory_success) / total

    # Performance
    legacy_avg_time = sum(r.legacy_time for r in results) / total
    factory_avg_time = sum(r.factory_time for r in results) / total

    # Divergent cases
    divergent_cases = [r for r in results if not r.match]

    # Cases where factory is better than legacy
    factory_better = [r for r in results if r.factory_match and not r.legacy_match]

    # Cases where legacy is better than factory
    legacy_better = [r for r in results if r.legacy_match and not r.factory_match]

    return {
        "total_cases": total,
        "legacy_vs_factory_matches": legacy_vs_factory_matches,
        "legacy_vs_expected_matches": legacy_vs_expected_matches,
        "factory_vs_expected_matches": factory_vs_expected_matches,
        "parity_rate": legacy_vs_factory_matches / total,
        "legacy_accuracy": legacy_vs_expected_matches / total,
        "factory_accuracy": factory_vs_expected_matches / total,
        "legacy_success_rate": legacy_success_rate,
        "factory_success_rate": factory_success_rate,
        "legacy_avg_time": legacy_avg_time,
        "factory_avg_time": factory_avg_time,
        "divergent_cases": len(divergent_cases),
        "factory_better_cases": len(factory_better),
        "legacy_better_cases": len(legacy_better),
        "results": results,
    }

def print_summary(analysis: Dict[str, Any]):
    """Print analysis summary."""
    print("\n" + "="*80)
    print("LEGACY VS FACTORY COMPARISON SUMMARY")
    print("="*80)

    print(f"Total cases: {analysis['total_cases']}")
    print(f"Legacy vs Factory parity rate: {analysis['parity_rate']:.1%} ({analysis['legacy_vs_factory_matches']}/{analysis['total_cases']})")
    print(f"Legacy accuracy (vs expected): {analysis['legacy_accuracy']:.1%} ({analysis['legacy_vs_expected_matches']}/{analysis['total_cases']})")
    print(f"Factory accuracy (vs expected): {analysis['factory_accuracy']:.1%} ({analysis['factory_vs_expected_matches']}/{analysis['total_cases']})")

    print(f"\nSuccess rates:")
    print(f"Legacy: {analysis['legacy_success_rate']:.1%}")
    print(f"Factory: {analysis['factory_success_rate']:.1%}")

    print(f"\nPerformance:")
    print(f"Legacy avg time: {analysis['legacy_avg_time']*1000:.1f}ms")
    print(f"Factory avg time: {analysis['factory_avg_time']*1000:.1f}ms")

    print(f"\nDivergence analysis:")
    print(f"Divergent cases: {analysis['divergent_cases']}")
    print(f"Factory better than legacy: {analysis['factory_better_cases']}")
    print(f"Legacy better than factory: {analysis['legacy_better_cases']}")

def print_detailed_results(analysis: Dict[str, Any]):
    """Print detailed results for each case."""
    print("\n" + "="*80)
    print("DETAILED CASE-BY-CASE RESULTS")
    print("="*80)

    for result in analysis['results']:
        status_legacy = "✓" if result.legacy_match else "✗"
        status_factory = "✓" if result.factory_match else "✗"
        parity = "✓" if result.match else "✗"

        print(f"\nCase: {result.case_id}")
        print(f"Input: {result.input_text}")
        print(f"Expected: {result.expected}")
        print(f"Legacy {status_legacy}: {result.legacy_output}")
        print(f"Factory {status_factory}: {result.factory_output}")
        print(f"Parity: {parity}")

        if not result.match:
            print("⚠️  DIVERGENCE DETECTED")

def save_results(analysis: Dict[str, Any], output_file: str):
    """Save results to JSON file."""
    # Convert ComparisonResult objects to dicts for JSON serialization
    serializable_results = []
    for result in analysis['results']:
        serializable_results.append({
            'case_id': result.case_id,
            'input_text': result.input_text,
            'language': result.language,
            'expected': result.expected,
            'legacy_output': result.legacy_output,
            'factory_output': result.factory_output,
            'legacy_success': result.legacy_success,
            'factory_success': result.factory_success,
            'legacy_time': result.legacy_time,
            'factory_time': result.factory_time,
            'match': result.match,
            'legacy_match': result.legacy_match,
            'factory_match': result.factory_match,
        })

    output_data = dict(analysis)
    output_data['results'] = serializable_results

    Path(output_file).write_text(json.dumps(output_data, indent=2, ensure_ascii=False))
    print(f"\nResults saved to: {output_file}")

async def main():
    """Main comparison function."""
    print("Starting Legacy vs Factory Comparison")
    print("="*50)

    results = await run_comparison()
    analysis = analyze_results(results)

    print_summary(analysis)
    print_detailed_results(analysis)

    # Save results
    output_file = f"comparison_results_{int(time.time())}.json"
    save_results(analysis, output_file)

if __name__ == "__main__":
    asyncio.run(main())
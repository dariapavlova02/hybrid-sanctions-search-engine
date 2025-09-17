#!/usr/bin/env python3
"""
Golden Test Runner with CSV Report Generation.
Compares legacy vs factory normalization outputs and generates detailed CSV report.
"""

import asyncio
import csv
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.ai_service.layers.normalization.normalization_service_legacy import NormalizationService as LegacyService
from src.ai_service.layers.normalization.normalization_service import NormalizationService as FactoryService

@dataclass
class GoldenTestResult:
    """Result of a single golden test case."""
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
    diff: str
    legacy_trace: Optional[List[str]] = None
    factory_trace: Optional[List[str]] = None
    legacy_accuracy: bool = False
    factory_accuracy: bool = False
    parity_match: bool = False

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

def extract_trace_rules(trace: Optional[List]) -> List[str]:
    """Extract last 5 rules from trace."""
    if not trace:
        return []
    
    # Extract rules from TokenTrace objects
    rules = []
    for trace_item in trace:
        if hasattr(trace_item, 'rule') and trace_item.rule:
            rules.append(trace_item.rule)
        elif isinstance(trace_item, dict) and 'rule' in trace_item:
            rules.append(trace_item['rule'])
    
    return rules[-5:] if len(rules) > 5 else rules

def calculate_diff(legacy: str, factory: str) -> str:
    """Calculate a short diff description between legacy and factory outputs."""
    if legacy == factory:
        return "MATCH"
    
    # Simple diff: show first difference
    if len(legacy) != len(factory):
        return f"LEN_DIFF: {len(legacy)} vs {len(factory)}"
    
    # Find first character difference
    for i, (l, f) in enumerate(zip(legacy, factory)):
        if l != f:
            return f"CHAR_DIFF@{i}: '{l}' vs '{f}'"
    
    return "UNKNOWN_DIFF"

async def run_single_golden_test(case: Dict, legacy_service: LegacyService, factory_service: FactoryService) -> GoldenTestResult:
    """Run a single golden test case and return detailed result."""
    expected = extract_expected_normalized(case)
    
    # Test legacy service
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
        legacy_trace = getattr(legacy_result, 'trace', [])
    except Exception as e:
        legacy_output = f"ERROR: {e}"
        legacy_success = False
        legacy_trace = None
    legacy_time = time.perf_counter() - start_time
    
    # Test factory service
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
        factory_trace = getattr(factory_result, 'trace', [])
    except Exception as e:
        factory_output = f"ERROR: {e}"
        factory_success = False
        factory_trace = None
    factory_time = time.perf_counter() - start_time
    
    # Extract trace rules
    legacy_trace_rules = extract_trace_rules(legacy_trace)
    factory_trace_rules = extract_trace_rules(factory_trace)
    
    # Calculate metrics
    diff = calculate_diff(legacy_output, factory_output)
    legacy_accuracy = legacy_output == expected
    factory_accuracy = factory_output == expected
    parity_match = legacy_output == factory_output
    
    return GoldenTestResult(
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
        diff=diff,
        legacy_trace=legacy_trace_rules,
        factory_trace=factory_trace_rules,
        legacy_accuracy=legacy_accuracy,
        factory_accuracy=factory_accuracy,
        parity_match=parity_match,
    )

async def run_golden_tests() -> List[GoldenTestResult]:
    """Run all golden tests and return results."""
    print("Loading golden cases...")
    cases = load_golden_cases()
    print(f"Found {len(cases)} golden cases")
    
    print("Initializing services...")
    legacy_service = LegacyService()
    factory_service = FactoryService()
    
    print("Running golden tests...")
    results = []
    for i, case in enumerate(cases):
        print(f"Processing case {i+1}/{len(cases)}: {case['id']}")
        result = await run_single_golden_test(case, legacy_service, factory_service)
        results.append(result)
    
    return results

def save_csv_report(results: List[GoldenTestResult], output_file: str):
    """Save results to CSV file with detailed trace information."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'case_id',
            'input_text',
            'language',
            'expected',
            'legacy_output',
            'factory_output',
            'diff',
            'legacy_accuracy',
            'factory_accuracy',
            'parity_match',
            'legacy_success',
            'factory_success',
            'legacy_time_ms',
            'factory_time_ms',
            'legacy_trace_rules',
            'factory_trace_rules',
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            writer.writerow({
                'case_id': result.case_id,
                'input_text': result.input_text,
                'language': result.language,
                'expected': result.expected,
                'legacy_output': result.legacy_output,
                'factory_output': result.factory_output,
                'diff': result.diff,
                'legacy_accuracy': result.legacy_accuracy,
                'factory_accuracy': result.factory_accuracy,
                'parity_match': result.parity_match,
                'legacy_success': result.legacy_success,
                'factory_success': result.factory_success,
                'legacy_time_ms': round(result.legacy_time * 1000, 2),
                'factory_time_ms': round(result.factory_time * 1000, 2),
                'legacy_trace_rules': '; '.join(result.legacy_trace or []),
                'factory_trace_rules': '; '.join(result.factory_trace or []),
            })
    
    print(f"CSV report saved to: {output_path}")

def print_summary(results: List[GoldenTestResult]):
    """Print summary statistics."""
    total = len(results)
    
    # Basic metrics
    parity_matches = sum(1 for r in results if r.parity_match)
    legacy_accurate = sum(1 for r in results if r.legacy_accuracy)
    factory_accurate = sum(1 for r in results if r.factory_accuracy)
    legacy_successes = sum(1 for r in results if r.legacy_success)
    factory_successes = sum(1 for r in results if r.factory_success)
    
    # Performance metrics
    legacy_avg_time = sum(r.legacy_time for r in results) / total
    factory_avg_time = sum(r.factory_time for r in results) / total
    
    # Divergent cases
    divergent_cases = [r for r in results if not r.parity_match]
    
    print("\n" + "="*80)
    print("GOLDEN TEST RUNNER SUMMARY")
    print("="*80)
    
    print(f"Total cases: {total}")
    print(f"Parity rate: {parity_matches/total:.1%} ({parity_matches}/{total})")
    print(f"Legacy accuracy: {legacy_accurate/total:.1%} ({legacy_accurate}/{total})")
    print(f"Factory accuracy: {factory_accurate/total:.1%} ({factory_accurate}/{total})")
    
    print(f"\nSuccess rates:")
    print(f"Legacy: {legacy_successes/total:.1%} ({legacy_successes}/{total})")
    print(f"Factory: {factory_successes/total:.1%} ({factory_successes}/{total})")
    
    print(f"\nPerformance:")
    print(f"Legacy avg time: {legacy_avg_time*1000:.1f}ms")
    print(f"Factory avg time: {factory_avg_time*1000:.1f}ms")
    
    print(f"\nDivergence analysis:")
    print(f"Divergent cases: {len(divergent_cases)}")
    
    # Show top divergent cases
    if divergent_cases:
        print(f"\nTop 10 divergent cases:")
        for i, result in enumerate(divergent_cases[:10]):
            print(f"  {i+1}. {result.case_id}: {result.diff}")
            print(f"     Input: {result.input_text}")
            print(f"     Legacy: {result.legacy_output}")
            print(f"     Factory: {result.factory_output}")
            print(f"     Legacy trace: {'; '.join(result.legacy_trace or [])}")
            print(f"     Factory trace: {'; '.join(result.factory_trace or [])}")
            print()

def print_top_deltas(results: List[GoldenTestResult], top_n: int = 20):
    """Print top deltas with trace context."""
    divergent_cases = [r for r in results if not r.parity_match]
    
    if not divergent_cases:
        print("No divergent cases found!")
        return
    
    print(f"\n" + "="*80)
    print(f"TOP {min(top_n, len(divergent_cases))} DELTAS WITH TRACE CONTEXT")
    print("="*80)
    
    for i, result in enumerate(divergent_cases[:top_n]):
        print(f"\n{i+1}. Case ID: {result.case_id}")
        print(f"   Language: {result.language}")
        print(f"   Input: {result.input_text}")
        print(f"   Expected: {result.expected}")
        print(f"   Legacy: {result.legacy_output}")
        print(f"   Factory: {result.factory_output}")
        print(f"   Diff: {result.diff}")
        print(f"   Legacy Success: {result.legacy_success}")
        print(f"   Factory Success: {result.factory_success}")
        print(f"   Legacy Accuracy: {result.legacy_accuracy}")
        print(f"   Factory Accuracy: {result.factory_accuracy}")
        print(f"   Legacy Trace (last 5 rules): {'; '.join(result.legacy_trace or [])}")
        print(f"   Factory Trace (last 5 rules): {'; '.join(result.factory_trace or [])}")
        print(f"   Legacy Time: {result.legacy_time*1000:.2f}ms")
        print(f"   Factory Time: {result.factory_time*1000:.2f}ms")
        print("-" * 80)

async def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Golden Test Runner with CSV Report")
    parser.add_argument("--report", type=str, default="out/golden_diff.csv", 
                       help="Output CSV file path")
    parser.add_argument("--top-deltas", type=int, default=20,
                       help="Number of top deltas to show")
    parser.add_argument("--verbose", action="store_true",
                       help="Show verbose output")
    
    args = parser.parse_args()
    
    print("🚀 Starting Golden Test Runner...")
    print(f"Report will be saved to: {args.report}")
    
    try:
        results = await run_golden_tests()
        
        # Save CSV report
        save_csv_report(results, args.report)
        
        # Print summary
        print_summary(results)
        
        # Print top deltas with trace context
        print_top_deltas(results, args.top_deltas)
        
        print(f"\n✅ Golden test runner completed successfully!")
        print(f"📊 CSV report saved to: {args.report}")
        
    except Exception as e:
        print(f"❌ Golden test runner failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

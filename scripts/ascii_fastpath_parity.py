#!/usr/bin/env python3
"""
ASCII Fastpath Parity Job

Runs shadow-mode validation comparing ASCII fastpath vs full pipeline
using golden test cases to ensure 100% semantic compatibility.
"""

import json
import asyncio
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

from src.ai_service.layers.normalization.processors.normalization_factory import (
    NormalizationFactory, 
    NormalizationConfig
)
from src.ai_service.utils.ascii_utils import is_ascii_name


@dataclass
class ParityResult:
    """Result of parity comparison."""
    case_id: str
    input_text: str
    language: str
    is_ascii: bool
    fastpath_eligible: bool
    fastpath_success: bool
    full_success: bool
    results_match: bool
    fastpath_time: float
    full_time: float
    performance_improvement: float
    fastpath_result: Dict[str, Any]
    full_result: Dict[str, Any]
    error_message: str = ""


@dataclass
class ParitySummary:
    """Summary of parity job results."""
    total_cases: int
    ascii_cases: int
    fastpath_eligible_cases: int
    fastpath_successes: int
    full_successes: int
    parity_matches: int
    avg_performance_improvement: float
    failed_cases: List[str]
    error_cases: List[str]


class AsciiFastpathParityJob:
    """ASCII fastpath parity validation job."""
    
    def __init__(self):
        self.factory = NormalizationFactory()
        self.results: List[ParityResult] = []
    
    def load_golden_cases(self) -> List[Dict[str, Any]]:
        """Load golden test cases."""
        golden_path = Path(__file__).parent.parent / "tests" / "golden_cases" / "golden_cases.json"
        return json.loads(golden_path.read_text())
    
    def is_ascii_case(self, case: Dict[str, Any]) -> bool:
        """Check if case is ASCII and suitable for fastpath."""
        input_text = case.get("input", "")
        language = case.get("language", "")
        
        # Check if it's English and ASCII
        if language != "en":
            return False
        
        return is_ascii_name(input_text)
    
    def is_fastpath_eligible(self, case: Dict[str, Any]) -> bool:
        """Check if case is eligible for ASCII fastpath."""
        if not self.is_ascii_case(case):
            return False
        
        # Additional eligibility checks
        input_text = case.get("input", "")
        
        # Skip cases with complex processing requirements
        if any(keyword in input_text.lower() for keyword in ["dr.", "jr.", "sr.", "mr.", "mrs.", "ms."]):
            return False
        
        # Skip cases with multiple personas (complex parsing)
        expected_personas = case.get("expected_personas", [])
        if len(expected_personas) > 1:
            return False
        
        return True
    
    def create_configs(self, language: str) -> Tuple[NormalizationConfig, NormalizationConfig]:
        """Create fastpath and full pipeline configs."""
        fastpath_config = NormalizationConfig(
            language=language,
            ascii_fastpath=True,
            enable_advanced_features=False,
            enable_morphology=False
        )
        
        full_config = NormalizationConfig(
            language=language,
            ascii_fastpath=False,
            enable_advanced_features=True,
            enable_morphology=True
        )
        
        return fastpath_config, full_config
    
    def normalize_result(self, result) -> Dict[str, Any]:
        """Normalize result for comparison."""
        return {
            "normalized": result.normalized,
            "tokens": result.tokens,
            "language": result.language,
            "success": result.success,
            "confidence": result.confidence,
            "token_count": result.token_count,
            "errors": result.errors or []
        }
    
    def results_equivalent(self, fastpath_result: Dict[str, Any], full_result: Dict[str, Any]) -> bool:
        """Check if results are equivalent."""
        # Check basic fields
        if fastpath_result["success"] != full_result["success"]:
            return False
        
        if fastpath_result["language"] != full_result["language"]:
            return False
        
        if fastpath_result["token_count"] != full_result["token_count"]:
            return False
        
        # Check normalized text (case-insensitive)
        if fastpath_result["normalized"].lower() != full_result["normalized"].lower():
            return False
        
        # Check tokens (case-insensitive)
        if len(fastpath_result["tokens"]) != len(full_result["tokens"]):
            return False
        
        for fp_token, full_token in zip(fastpath_result["tokens"], full_result["tokens"]):
            if fp_token.lower() != full_token.lower():
                return False
        
        return True
    
    async def process_case(self, case: Dict[str, Any]) -> ParityResult:
        """Process a single golden test case."""
        case_id = case.get("id", "unknown")
        input_text = case.get("input", "")
        language = case.get("language", "en")
        
        is_ascii = self.is_ascii_case(case)
        fastpath_eligible = self.is_fastpath_eligible(case)
        
        result = ParityResult(
            case_id=case_id,
            input_text=input_text,
            language=language,
            is_ascii=is_ascii,
            fastpath_eligible=fastpath_eligible,
            fastpath_success=False,
            full_success=False,
            results_match=False,
            fastpath_time=0.0,
            full_time=0.0,
            performance_improvement=0.0,
            fastpath_result={},
            full_result={}
        )
        
        try:
            # Create configs
            fastpath_config, full_config = self.create_configs(language)
            
            # Run fastpath if eligible
            if fastpath_eligible:
                start_time = time.perf_counter()
                fastpath_result = await self.factory.normalize_text(input_text, fastpath_config)
                result.fastpath_time = time.perf_counter() - start_time
                result.fastpath_success = fastpath_result.success
                result.fastpath_result = self.normalize_result(fastpath_result)
            
            # Run full pipeline
            start_time = time.perf_counter()
            full_result = await self.factory.normalize_text(input_text, full_config)
            result.full_time = time.perf_counter() - start_time
            result.full_success = full_result.success
            result.full_result = self.normalize_result(full_result)
            
            # Compare results if both succeeded
            if result.fastpath_success and result.full_success:
                result.results_match = self.results_equivalent(result.fastpath_result, result.full_result)
                
                # Calculate performance improvement
                if result.full_time > 0:
                    result.performance_improvement = (result.full_time - result.fastpath_time) / result.full_time * 100
            
        except Exception as e:
            result.error_message = str(e)
        
        return result
    
    async def run_parity_job(self) -> ParitySummary:
        """Run the complete parity job."""
        print("🔍 Loading golden test cases...")
        cases = self.load_golden_cases()
        print(f"📊 Loaded {len(cases)} golden test cases")
        
        print("🚀 Running parity validation...")
        for i, case in enumerate(cases, 1):
            print(f"  Processing case {i}/{len(cases)}: {case.get('id', 'unknown')}")
            result = await self.process_case(case)
            self.results.append(result)
        
        # Calculate summary
        total_cases = len(self.results)
        ascii_cases = sum(1 for r in self.results if r.is_ascii)
        fastpath_eligible_cases = sum(1 for r in self.results if r.fastpath_eligible)
        fastpath_successes = sum(1 for r in self.results if r.fastpath_success)
        full_successes = sum(1 for r in self.results if r.full_success)
        parity_matches = sum(1 for r in self.results if r.results_match)
        
        # Calculate average performance improvement
        improvements = [r.performance_improvement for r in self.results if r.performance_improvement > 0]
        avg_performance_improvement = sum(improvements) / len(improvements) if improvements else 0.0
        
        # Find failed and error cases
        failed_cases = [r.case_id for r in self.results if r.fastpath_eligible and not r.results_match]
        error_cases = [r.case_id for r in self.results if r.error_message]
        
        summary = ParitySummary(
            total_cases=total_cases,
            ascii_cases=ascii_cases,
            fastpath_eligible_cases=fastpath_eligible_cases,
            fastpath_successes=fastpath_successes,
            full_successes=full_successes,
            parity_matches=parity_matches,
            avg_performance_improvement=avg_performance_improvement,
            failed_cases=failed_cases,
            error_cases=error_cases
        )
        
        return summary
    
    def print_summary(self, summary: ParitySummary):
        """Print parity job summary."""
        print("\n" + "="*60)
        print("📈 ASCII FASTPATH PARITY JOB SUMMARY")
        print("="*60)
        
        print(f"📊 Total cases processed: {summary.total_cases}")
        print(f"🔤 ASCII cases: {summary.ascii_cases}")
        print(f"⚡ Fastpath eligible cases: {summary.fastpath_eligible_cases}")
        print(f"✅ Fastpath successes: {summary.fastpath_successes}")
        print(f"✅ Full pipeline successes: {summary.full_successes}")
        print(f"🎯 Parity matches: {summary.parity_matches}")
        print(f"📈 Average performance improvement: {summary.avg_performance_improvement:.1f}%")
        
        if summary.failed_cases:
            print(f"\n❌ Failed parity cases ({len(summary.failed_cases)}):")
            for case_id in summary.failed_cases:
                print(f"  - {case_id}")
        
        if summary.error_cases:
            print(f"\n💥 Error cases ({len(summary.error_cases)}):")
            for case_id in summary.error_cases:
                print(f"  - {case_id}")
        
        # Calculate success rates
        if summary.fastpath_eligible_cases > 0:
            fastpath_success_rate = summary.fastpath_successes / summary.fastpath_eligible_cases * 100
            print(f"\n🎯 Fastpath success rate: {fastpath_success_rate:.1f}%")
        
        if summary.fastpath_eligible_cases > 0:
            parity_rate = summary.parity_matches / summary.fastpath_eligible_cases * 100
            print(f"🎯 Parity match rate: {parity_rate:.1f}%")
        
        print("\n" + "="*60)
        
        # Determine overall success
        if summary.failed_cases or summary.error_cases:
            print("❌ PARITY JOB FAILED")
            return False
        else:
            print("✅ PARITY JOB PASSED")
            return True
    
    def save_detailed_results(self, output_file: str = "ascii_fastpath_parity_results.json"):
        """Save detailed results to JSON file."""
        results_data = []
        for result in self.results:
            results_data.append({
                "case_id": result.case_id,
                "input_text": result.input_text,
                "language": result.language,
                "is_ascii": result.is_ascii,
                "fastpath_eligible": result.fastpath_eligible,
                "fastpath_success": result.fastpath_success,
                "full_success": result.full_success,
                "results_match": result.results_match,
                "fastpath_time": result.fastpath_time,
                "full_time": result.full_time,
                "performance_improvement": result.performance_improvement,
                "error_message": result.error_message
            })
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Detailed results saved to: {output_file}")


async def main():
    """Main entry point."""
    print("🚀 Starting ASCII Fastpath Parity Job...")
    
    job = AsciiFastpathParityJob()
    summary = await job.run_parity_job()
    
    success = job.print_summary(summary)
    job.save_detailed_results()
    
    if not success:
        exit(1)
    
    print("✅ ASCII Fastpath Parity Job completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())

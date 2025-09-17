#!/usr/bin/env python3
"""
Shadow mode validation script for feature-gated functional improvements.

This script runs comprehensive validation of all feature improvements
in shadow mode to measure their effectiveness without affecting production.
"""

import asyncio
import json
import time
from typing import Dict, List, Any
from pathlib import Path

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_service.validation.shadow_mode_validator import (
    ShadowModeValidator,
    ValidationResult,
    validate_all_test_cases
)


class ShadowModeValidationRunner:
    """Runs shadow mode validation and generates reports."""
    
    def __init__(self):
        self.validator = ShadowModeValidator()
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    async def run_validation(self) -> Dict[str, Any]:
        """Run comprehensive shadow mode validation."""
        print("🚀 Starting Shadow Mode Validation")
        print("=" * 50)
        
        self.start_time = time.time()
        
        # Run validation for all test cases
        print("📊 Running validation for all test cases...")
        test_results = await validate_all_test_cases()
        
        # Calculate aggregate statistics
        print("📈 Calculating aggregate statistics...")
        aggregate_stats = self._calculate_aggregate_stats(test_results)
        
        # Generate improvement summary
        print("📋 Generating improvement summary...")
        improvement_summary = self._generate_improvement_summary(aggregate_stats)
        
        # Generate detailed report
        print("📝 Generating detailed report...")
        detailed_report = self._generate_detailed_report(test_results, aggregate_stats)
        
        self.end_time = time.time()
        total_time = self.end_time - self.start_time
        
        # Compile final results
        self.results = {
            "validation_summary": {
                "total_test_cases": len(test_results),
                "total_improvements_tested": 8,
                "validation_time_seconds": total_time,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "aggregate_statistics": aggregate_stats,
            "improvement_summary": improvement_summary,
            "detailed_results": test_results,
            "detailed_report": detailed_report
        }
        
        return self.results
    
    def _calculate_aggregate_stats(self, test_results: Dict[str, List[ValidationResult]]) -> Dict[str, Any]:
        """Calculate aggregate statistics from test results."""
        stats = {}
        
        # Initialize stats for each improvement
        improvements = [
            "enable_spacy_ner",
            "enable_nameparser_en", 
            "strict_stopwords",
            "fsm_tuned_roles",
            "enhanced_diminutives",
            "enhanced_gender_rules",
            "enable_ac_tier0",
            "enable_vector_fallback"
        ]
        
        for improvement in improvements:
            stats[improvement] = {
                "accuracy_improvements": [],
                "confidence_improvements": [],
                "performance_impacts": [],
                "error_rate_reductions": [],
                "coverage_improvements": [],
                "success_count": 0,
                "total_count": 0
            }
        
        # Collect data from all test cases
        for test_case, results in test_results.items():
            for result in results:
                if result.flag_name in stats:
                    stats[result.flag_name]["accuracy_improvements"].append(result.accuracy_improvement)
                    stats[result.flag_name]["confidence_improvements"].append(result.confidence_improvement)
                    stats[result.flag_name]["performance_impacts"].append(result.performance_impact_ms)
                    stats[result.flag_name]["error_rate_reductions"].append(result.error_rate_reduction)
                    stats[result.flag_name]["coverage_improvements"].append(result.coverage_improvement)
                    stats[result.flag_name]["total_count"] += 1
                    if result.success:
                        stats[result.flag_name]["success_count"] += 1
        
        # Calculate averages and other metrics
        for improvement, data in stats.items():
            if data["total_count"] > 0:
                data["avg_accuracy_improvement"] = sum(data["accuracy_improvements"]) / len(data["accuracy_improvements"])
                data["avg_confidence_improvement"] = sum(data["confidence_improvements"]) / len(data["confidence_improvements"])
                data["avg_performance_impact_ms"] = sum(data["performance_impacts"]) / len(data["performance_impacts"])
                data["avg_error_rate_reduction"] = sum(data["error_rate_reductions"]) / len(data["error_rate_reductions"])
                data["avg_coverage_improvement"] = sum(data["coverage_improvements"]) / len(data["coverage_improvements"])
                data["success_rate"] = data["success_count"] / data["total_count"]
                
                # Calculate max improvements
                data["max_accuracy_improvement"] = max(data["accuracy_improvements"]) if data["accuracy_improvements"] else 0
                data["max_confidence_improvement"] = max(data["confidence_improvements"]) if data["confidence_improvements"] else 0
                data["max_error_rate_reduction"] = max(data["error_rate_reductions"]) if data["error_rate_reductions"] else 0
                data["max_coverage_improvement"] = max(data["coverage_improvements"]) if data["coverage_improvements"] else 0
            else:
                data["avg_accuracy_improvement"] = 0.0
                data["avg_confidence_improvement"] = 0.0
                data["avg_performance_impact_ms"] = 0.0
                data["avg_error_rate_reduction"] = 0.0
                data["avg_coverage_improvement"] = 0.0
                data["success_rate"] = 0.0
                data["max_accuracy_improvement"] = 0.0
                data["max_confidence_improvement"] = 0.0
                data["max_error_rate_reduction"] = 0.0
                data["max_coverage_improvement"] = 0.0
        
        return stats
    
    def _generate_improvement_summary(self, aggregate_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Generate improvement summary."""
        summary = {
            "top_improvements": [],
            "overall_metrics": {
                "avg_accuracy_improvement": 0.0,
                "avg_confidence_improvement": 0.0,
                "avg_performance_impact_ms": 0.0,
                "avg_error_rate_reduction": 0.0,
                "avg_coverage_improvement": 0.0
            }
        }
        
        # Calculate overall averages
        total_accuracy = 0.0
        total_confidence = 0.0
        total_performance = 0.0
        total_error_reduction = 0.0
        total_coverage = 0.0
        count = 0
        
        for improvement, data in aggregate_stats.items():
            if data["total_count"] > 0:
                total_accuracy += data["avg_accuracy_improvement"]
                total_confidence += data["avg_confidence_improvement"]
                total_performance += data["avg_performance_impact_ms"]
                total_error_reduction += data["avg_error_rate_reduction"]
                total_coverage += data["avg_coverage_improvement"]
                count += 1
                
                # Add to top improvements
                summary["top_improvements"].append({
                    "improvement": improvement,
                    "accuracy_improvement": data["avg_accuracy_improvement"],
                    "confidence_improvement": data["avg_confidence_improvement"],
                    "error_rate_reduction": data["avg_error_rate_reduction"],
                    "coverage_improvement": data["avg_coverage_improvement"],
                    "success_rate": data["success_rate"]
                })
        
        if count > 0:
            summary["overall_metrics"]["avg_accuracy_improvement"] = total_accuracy / count
            summary["overall_metrics"]["avg_confidence_improvement"] = total_confidence / count
            summary["overall_metrics"]["avg_performance_impact_ms"] = total_performance / count
            summary["overall_metrics"]["avg_error_rate_reduction"] = total_error_reduction / count
            summary["overall_metrics"]["avg_coverage_improvement"] = total_coverage / count
        
        # Sort top improvements by accuracy improvement
        summary["top_improvements"].sort(key=lambda x: x["accuracy_improvement"], reverse=True)
        
        return summary
    
    def _generate_detailed_report(self, test_results: Dict[str, List[ValidationResult]], aggregate_stats: Dict[str, Any]) -> str:
        """Generate detailed text report."""
        report = []
        report.append("SHADOW MODE VALIDATION REPORT")
        report.append("=" * 50)
        report.append("")
        
        # Summary
        report.append("SUMMARY")
        report.append("-" * 20)
        report.append(f"Total test cases: {len(test_results)}")
        report.append(f"Total improvements tested: 8")
        report.append(f"Validation time: {self.end_time - self.start_time:.2f} seconds")
        report.append("")
        
        # Overall metrics
        overall = aggregate_stats.get("overall_metrics", {})
        report.append("OVERALL METRICS")
        report.append("-" * 20)
        report.append(f"Average accuracy improvement: {overall.get('avg_accuracy_improvement', 0.0):.2f}%")
        report.append(f"Average confidence improvement: {overall.get('avg_confidence_improvement', 0.0):.2f}%")
        report.append(f"Average performance impact: {overall.get('avg_performance_impact_ms', 0.0):.2f}ms")
        report.append(f"Average error rate reduction: {overall.get('avg_error_rate_reduction', 0.0):.2f}%")
        report.append(f"Average coverage improvement: {overall.get('avg_coverage_improvement', 0.0):.2f}%")
        report.append("")
        
        # Individual improvement results
        report.append("INDIVIDUAL IMPROVEMENT RESULTS")
        report.append("-" * 40)
        
        for improvement, data in aggregate_stats.items():
            if improvement == "overall_metrics":
                continue
                
            report.append(f"\n{improvement.upper()}:")
            report.append(f"  Accuracy improvement: {data['avg_accuracy_improvement']:.2f}%")
            report.append(f"  Confidence improvement: {data['avg_confidence_improvement']:.2f}%")
            report.append(f"  Performance impact: {data['avg_performance_impact_ms']:.2f}ms")
            report.append(f"  Error rate reduction: {data['avg_error_rate_reduction']:.2f}%")
            report.append(f"  Coverage improvement: {data['avg_coverage_improvement']:.2f}%")
            report.append(f"  Success rate: {data['success_rate']:.2f}%")
            report.append(f"  Max accuracy improvement: {data['max_accuracy_improvement']:.2f}%")
            report.append(f"  Max confidence improvement: {data['max_confidence_improvement']:.2f}%")
        
        # Test case results
        report.append("\n\nTEST CASE RESULTS")
        report.append("-" * 20)
        
        for test_case, results in test_results.items():
            report.append(f"\nTest case: '{test_case}'")
            for result in results:
                report.append(f"  {result.flag_name}:")
                report.append(f"    Accuracy: {result.accuracy_improvement:.2f}%")
                report.append(f"    Confidence: {result.confidence_improvement:.2f}%")
                report.append(f"    Performance: {result.performance_impact_ms:.2f}ms")
                report.append(f"    Error reduction: {result.error_rate_reduction:.2f}%")
                report.append(f"    Coverage: {result.coverage_improvement:.2f}%")
                report.append(f"    Success: {result.success}")
                if result.errors:
                    report.append(f"    Errors: {', '.join(result.errors)}")
        
        return "\n".join(report)
    
    def save_results(self, output_dir: str = "reports"):
        """Save validation results to files."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Save JSON results
        json_file = output_path / "shadow_mode_validation_results.json"
        with open(json_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        # Save detailed report
        report_file = output_path / "shadow_mode_validation_report.txt"
        with open(report_file, 'w') as f:
            f.write(self.results["detailed_report"])
        
        print(f"📁 Results saved to {output_path}")
        print(f"   JSON: {json_file}")
        print(f"   Report: {report_file}")
    
    def print_summary(self):
        """Print validation summary to console."""
        if not self.results:
            print("❌ No validation results available")
            return
        
        print("\n🎯 SHADOW MODE VALIDATION SUMMARY")
        print("=" * 50)
        
        # Overall metrics
        overall = self.results["aggregate_statistics"].get("overall_metrics", {})
        print(f"📊 Overall Metrics:")
        print(f"   Accuracy improvement: {overall.get('avg_accuracy_improvement', 0.0):.2f}%")
        print(f"   Confidence improvement: {overall.get('avg_confidence_improvement', 0.0):.2f}%")
        print(f"   Performance impact: {overall.get('avg_performance_impact_ms', 0.0):.2f}ms")
        print(f"   Error rate reduction: {overall.get('avg_error_rate_reduction', 0.0):.2f}%")
        print(f"   Coverage improvement: {overall.get('avg_coverage_improvement', 0.0):.2f}%")
        
        # Top improvements
        print(f"\n🏆 Top Improvements:")
        for i, improvement in enumerate(self.results["improvement_summary"]["top_improvements"][:5], 1):
            print(f"   {i}. {improvement['improvement']}: {improvement['accuracy_improvement']:.2f}% accuracy improvement")
        
        # Validation info
        summary = self.results["validation_summary"]
        print(f"\n⏱️  Validation Info:")
        print(f"   Test cases: {summary['total_test_cases']}")
        print(f"   Improvements tested: {summary['total_improvements_tested']}")
        print(f"   Time: {summary['validation_time_seconds']:.2f}s")


async def main():
    """Main function to run shadow mode validation."""
    print("🚀 Shadow Mode Validation Runner")
    print("=" * 50)
    
    # Create runner
    runner = ShadowModeValidationRunner()
    
    try:
        # Run validation
        results = await runner.run_validation()
        
        # Print summary
        runner.print_summary()
        
        # Save results
        runner.save_results()
        
        print("\n✅ Shadow mode validation completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Shadow mode validation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

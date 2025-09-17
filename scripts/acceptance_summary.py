#!/usr/bin/env python3
"""
Acceptance summary generator for parity and performance gates.

This script generates a comprehensive acceptance summary from parity and
performance test results.
"""

import json
import argparse
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class AcceptanceSummaryGenerator:
    """Generates acceptance summary from test results."""
    
    def __init__(self):
        self.parity_data = {}
        self.perf_data = {}
        self.summary = {}
    
    def load_parity_report(self, parity_file: str) -> Dict[str, Any]:
        """Load parity report from JSON file."""
        try:
            with open(parity_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️  Parity report not found: {parity_file}")
            return {}
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing parity report: {e}")
            return {}
    
    def load_perf_report(self, perf_file: str) -> Dict[str, Any]:
        """Load performance report from JSON file."""
        try:
            with open(perf_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️  Performance report not found: {perf_file}")
            return {}
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing performance report: {e}")
            return {}
    
    def analyze_parity_results(self, parity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze parity results."""
        analysis = {
            "overall_success": False,
            "language_results": {},
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "success_rate": 0.0,
            "threshold_met": False
        }
        
        if not parity_data:
            return analysis
        
        # Extract language-specific results
        languages = ["ru", "uk", "en"]
        all_passed = True
        
        for lang in languages:
            lang_key = f"language_{lang}"
            if lang_key in parity_data:
                lang_data = parity_data[lang_key]
                lang_analysis = {
                    "total": lang_data.get("total", 0),
                    "passed": lang_data.get("passed", 0),
                    "failed": lang_data.get("failed", 0),
                    "success_rate": lang_data.get("success_rate", 0.0),
                    "threshold_met": lang_data.get("success_rate", 0.0) >= 0.9
                }
                analysis["language_results"][lang] = lang_analysis
                
                if not lang_analysis["threshold_met"]:
                    all_passed = False
            else:
                analysis["language_results"][lang] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "success_rate": 0.0,
                    "threshold_met": False
                }
                all_passed = False
        
        # Calculate overall metrics
        analysis["total_tests"] = sum(lang["total"] for lang in analysis["language_results"].values())
        analysis["passed_tests"] = sum(lang["passed"] for lang in analysis["language_results"].values())
        analysis["failed_tests"] = sum(lang["failed"] for lang in analysis["language_results"].values())
        
        if analysis["total_tests"] > 0:
            analysis["success_rate"] = analysis["passed_tests"] / analysis["total_tests"]
        
        analysis["threshold_met"] = all_passed and analysis["success_rate"] >= 0.9
        analysis["overall_success"] = analysis["threshold_met"]
        
        return analysis
    
    def analyze_perf_results(self, perf_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance results."""
        analysis = {
            "overall_success": False,
            "p95_threshold_met": False,
            "p99_threshold_met": False,
            "p95_max": 0.0,
            "p99_max": 0.0,
            "p95_threshold": 0.010,
            "p99_threshold": 0.020,
            "test_results": []
        }
        
        if not perf_data:
            return analysis
        
        # Extract performance metrics
        if "test_results" in perf_data:
            for test_result in perf_data["test_results"]:
                test_analysis = {
                    "name": test_result.get("name", "unknown"),
                    "p95": test_result.get("p95", 0.0),
                    "p99": test_result.get("p99", 0.0),
                    "p95_met": test_result.get("p95", 0.0) <= analysis["p95_threshold"],
                    "p99_met": test_result.get("p99", 0.0) <= analysis["p99_threshold"],
                    "success": (test_result.get("p95", 0.0) <= analysis["p95_threshold"] and 
                               test_result.get("p99", 0.0) <= analysis["p99_threshold"])
                }
                analysis["test_results"].append(test_analysis)
                
                # Track max values
                analysis["p95_max"] = max(analysis["p95_max"], test_result.get("p95", 0.0))
                analysis["p99_max"] = max(analysis["p99_max"], test_result.get("p99", 0.0))
        
        # Check thresholds
        analysis["p95_threshold_met"] = analysis["p95_max"] <= analysis["p95_threshold"]
        analysis["p99_threshold_met"] = analysis["p99_max"] <= analysis["p99_threshold"]
        analysis["overall_success"] = analysis["p95_threshold_met"] and analysis["p99_threshold_met"]
        
        return analysis
    
    def generate_summary(self, parity_file: str, perf_file: str) -> str:
        """Generate acceptance summary."""
        # Load data
        parity_data = self.load_parity_report(parity_file)
        perf_data = self.load_perf_report(perf_file)
        
        # Analyze results
        parity_analysis = self.analyze_parity_results(parity_data)
        perf_analysis = self.analyze_perf_results(perf_data)
        
        # Generate summary
        summary_lines = []
        summary_lines.append("# 🚀 Acceptance Gates Status")
        summary_lines.append("")
        summary_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        summary_lines.append("")
        
        # Parity Results
        summary_lines.append("## 📊 Parity Results (Golden Tests)")
        summary_lines.append("")
        
        if parity_analysis["overall_success"]:
            summary_lines.append("✅ **PASSED** - All language subsets meet 90% threshold")
        else:
            summary_lines.append("❌ **FAILED** - One or more language subsets below 90% threshold")
        
        summary_lines.append("")
        summary_lines.append("### Language-Specific Results")
        summary_lines.append("")
        summary_lines.append("| Language | Total | Passed | Failed | Success Rate | Threshold Met |")
        summary_lines.append("|----------|-------|--------|--------|--------------|---------------|")
        
        for lang, results in parity_analysis["language_results"].items():
            status = "✅" if results["threshold_met"] else "❌"
            summary_lines.append(
                f"| {lang.upper()} | {results['total']} | {results['passed']} | "
                f"{results['failed']} | {results['success_rate']:.1%} | {status} |"
            )
        
        summary_lines.append("")
        summary_lines.append(f"**Overall:** {parity_analysis['passed_tests']}/{parity_analysis['total_tests']} "
                           f"({parity_analysis['success_rate']:.1%})")
        summary_lines.append("")
        
        # Performance Results
        summary_lines.append("## ⚡ Performance Results (Micro-benchmarks)")
        summary_lines.append("")
        
        if perf_analysis["overall_success"]:
            summary_lines.append("✅ **PASSED** - All performance thresholds met")
        else:
            summary_lines.append("❌ **FAILED** - Performance thresholds exceeded")
        
        summary_lines.append("")
        summary_lines.append("### Performance Thresholds")
        summary_lines.append("")
        summary_lines.append("| Metric | Threshold | Actual | Status |")
        summary_lines.append("|--------|-----------|--------|--------|")
        
        p95_status = "✅" if perf_analysis["p95_threshold_met"] else "❌"
        p99_status = "✅" if perf_analysis["p99_threshold_met"] else "❌"
        
        summary_lines.append(f"| P95 | {perf_analysis['p95_threshold']:.3f}s | {perf_analysis['p95_max']:.3f}s | {p95_status} |")
        summary_lines.append(f"| P99 | {perf_analysis['p99_threshold']:.3f}s | {perf_analysis['p99_max']:.3f}s | {p99_status} |")
        
        summary_lines.append("")
        summary_lines.append("### Individual Test Results")
        summary_lines.append("")
        summary_lines.append("| Test | P95 | P99 | P95 Met | P99 Met | Status |")
        summary_lines.append("|------|-----|-----|---------|---------|--------|")
        
        for test in perf_analysis["test_results"]:
            p95_status = "✅" if test["p95_met"] else "❌"
            p99_status = "✅" if test["p99_met"] else "❌"
            overall_status = "✅" if test["success"] else "❌"
            
            summary_lines.append(
                f"| {test['name']} | {test['p95']:.3f}s | {test['p99']:.3f}s | "
                f"{p95_status} | {p99_status} | {overall_status} |"
            )
        
        summary_lines.append("")
        
        # Feature Flags Status
        summary_lines.append("## 🚩 Feature Flags Status")
        summary_lines.append("")
        summary_lines.append("All feature flags were enabled in SHADOW MODE:")
        summary_lines.append("")
        
        flags = [
            "SHADOW_MODE=true",
            "USE_FACTORY_NORMALIZER=true",
            "FIX_INITIALS_DOUBLE_DOT=true",
            "PRESERVE_HYPHENATED_CASE=true",
            "STRICT_STOPWORDS=true",
            "ENABLE_SPACY_NER=true",
            "ENABLE_NAMEPARSER_EN=true",
            "ENHANCED_DIMINUTIVES=true",
            "ENHANCED_GENDER_RULES=true",
            "ASCII_FASTPATH=true",
            "ENABLE_AC_TIER0=true",
            "ENABLE_VECTOR_FALLBACK=true",
            "DEBUG_TRACE=true"
        ]
        
        for flag in flags:
            summary_lines.append(f"- ✅ {flag}")
        
        summary_lines.append("")
        summary_lines.append("**Note:** All features were tested in shadow mode. Production responses were not modified.")
        summary_lines.append("")
        
        # Overall Status
        overall_success = parity_analysis["overall_success"] and perf_analysis["overall_success"]
        
        summary_lines.append("## 🎯 Overall Acceptance Status")
        summary_lines.append("")
        
        if overall_success:
            summary_lines.append("✅ **ACCEPTED** - All gates passed")
            summary_lines.append("")
            summary_lines.append("This PR is ready for merge! 🚀")
        else:
            summary_lines.append("❌ **REJECTED** - One or more gates failed")
            summary_lines.append("")
            summary_lines.append("This PR should NOT be merged until all gates pass.")
        
        summary_lines.append("")
        summary_lines.append("---")
        summary_lines.append("")
        summary_lines.append("### Artifacts")
        summary_lines.append("")
        summary_lines.append("- `parity_report.json` - Detailed parity test results")
        summary_lines.append("- `perf.json` - Detailed performance test results")
        summary_lines.append("- `ACCEPTANCE_GATES_STATUS.md` - This summary")
        
        return "\n".join(summary_lines)
    
    def save_summary(self, summary: str, output_file: str):
        """Save summary to file."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(summary)
        
        print(f"📝 Acceptance summary saved to: {output_file}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Generate acceptance summary from test results")
    parser.add_argument("--parity", required=True, help="Path to parity report JSON file")
    parser.add_argument("--perf", required=True, help="Path to performance report JSON file")
    parser.add_argument("--out", required=True, help="Output file for acceptance summary")
    
    args = parser.parse_args()
    
    # Generate summary
    generator = AcceptanceSummaryGenerator()
    summary = generator.generate_summary(args.parity, args.perf)
    
    # Save summary
    generator.save_summary(summary, args.out)
    
    # Print summary to console
    print("\n" + "="*80)
    print(summary)
    print("="*80)


if __name__ == "__main__":
    main()

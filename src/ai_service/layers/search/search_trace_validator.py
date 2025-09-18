"""Search trace validation with deterministic ordering and comprehensive analysis."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import time

from ...contracts.trace_models import SearchTrace
from ...utils.logging_config import get_logger


class TraceStepType(Enum):
    """Types of search trace steps."""
    AC_SEARCH = "AC_SEARCH"
    VECTOR_SEARCH = "VECTOR_SEARCH"
    HYBRID_MERGE = "HYBRID_MERGE"
    RESULT_FILTER = "RESULT_FILTER"
    SCORE_CALCULATION = "SCORE_CALCULATION"
    FALLBACK_TRIGGERED = "FALLBACK_TRIGGERED"


class ValidationSeverity(Enum):
    """Validation issue severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Single validation issue found in search trace."""
    severity: ValidationSeverity
    category: str
    message: str
    step_index: Optional[int] = None
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "severity": self.severity.value,
            "category": self.category,
            "message": self.message,
            "step_index": self.step_index,
            "expected": self.expected,
            "actual": self.actual,
            "details": self.details
        }


@dataclass
class ValidationReport:
    """Comprehensive validation report for search trace."""
    is_valid: bool
    total_steps: int
    deterministic_hash: str
    issues: List[ValidationIssue] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    timing_analysis: Dict[str, Any] = field(default_factory=dict)
    coverage_analysis: Dict[str, Any] = field(default_factory=dict)

    def has_errors(self) -> bool:
        """Check if report contains any errors."""
        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)

    def has_warnings(self) -> bool:
        """Check if report contains any warnings."""
        return any(issue.severity == ValidationSeverity.WARNING for issue in self.issues)

    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get all issues of specific severity."""
        return [issue for issue in self.issues if issue.severity == severity]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_valid": self.is_valid,
            "total_steps": self.total_steps,
            "deterministic_hash": self.deterministic_hash,
            "issues": [issue.to_dict() for issue in self.issues],
            "statistics": self.statistics,
            "timing_analysis": self.timing_analysis,
            "coverage_analysis": self.coverage_analysis,
            "summary": {
                "errors": len(self.get_issues_by_severity(ValidationSeverity.ERROR)),
                "warnings": len(self.get_issues_by_severity(ValidationSeverity.WARNING)),
                "info": len(self.get_issues_by_severity(ValidationSeverity.INFO))
            }
        }


class SearchTraceValidator:
    """Validator for search traces with deterministic ordering and analysis."""

    def __init__(self, strict_mode: bool = False):
        self.logger = get_logger(__name__)
        self.strict_mode = strict_mode

        # Expected step patterns for different search strategies
        self.expected_patterns = {
            "ac_only": [TraceStepType.AC_SEARCH],
            "vector_only": [TraceStepType.VECTOR_SEARCH],
            "hybrid": [
                TraceStepType.AC_SEARCH,
                TraceStepType.VECTOR_SEARCH,
                TraceStepType.HYBRID_MERGE
            ],
            "fallback": [
                TraceStepType.AC_SEARCH,
                TraceStepType.FALLBACK_TRIGGERED,
                TraceStepType.VECTOR_SEARCH
            ]
        }

    def validate_trace(self, search_trace: SearchTrace) -> ValidationReport:
        """Comprehensive validation of search trace."""
        start_time = time.time()

        report = ValidationReport(
            is_valid=True,
            total_steps=len(search_trace.notes),
            deterministic_hash=""
        )

        try:
            # Generate deterministic hash
            report.deterministic_hash = self._generate_deterministic_hash(search_trace)

            # Parse and analyze trace steps
            parsed_steps = self._parse_trace_steps(search_trace)

            # Run validation checks
            self._validate_step_ordering(parsed_steps, report)
            self._validate_timing_consistency(parsed_steps, report)
            self._validate_data_integrity(parsed_steps, report)
            self._validate_coverage_requirements(parsed_steps, report)
            self._validate_performance_thresholds(parsed_steps, report)

            # Generate statistics
            report.statistics = self._generate_statistics(parsed_steps)
            report.timing_analysis = self._analyze_timing(parsed_steps)
            report.coverage_analysis = self._analyze_coverage(parsed_steps)

            # Determine final validity
            report.is_valid = not report.has_errors()

            validation_time = time.time() - start_time
            self.logger.debug(f"Trace validation completed in {validation_time:.3f}s: {len(report.issues)} issues found")

        except Exception as e:
            self.logger.error(f"Trace validation failed: {e}")
            report.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="validation_error",
                message=f"Validation process failed: {str(e)}"
            ))
            report.is_valid = False

        return report

    def _generate_deterministic_hash(self, search_trace: SearchTrace) -> str:
        """Generate deterministic hash for trace comparison."""
        # Create normalized representation for hashing
        normalized = {
            "enabled": search_trace.enabled,
            "total_time_ms": search_trace.total_time_ms,
            "total_hits": search_trace.total_hits,
            "notes": sorted(search_trace.notes),  # Deterministic ordering
        }

        # Convert to JSON string with sorted keys
        json_str = json.dumps(normalized, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()[:16]

    def _parse_trace_steps(self, search_trace: SearchTrace) -> List[Dict[str, Any]]:
        """Parse trace notes into structured steps."""
        steps = []

        for i, note in enumerate(search_trace.notes):
            step = {
                "index": i,
                "raw_note": note,
                "timestamp": None,
                "step_type": None,
                "duration_ms": None,
                "result_count": None,
                "metadata": {}
            }

            # Parse different step types
            if "AC search" in note:
                step["step_type"] = TraceStepType.AC_SEARCH
                # Extract metadata like "AC search completed with 3 results in 15ms"
                if "completed with" in note and "results" in note:
                    import re
                    match = re.search(r'completed with (\d+) results', note)
                    if match:
                        step["result_count"] = int(match.group(1))

                    match = re.search(r'in (\d+)ms', note)
                    if match:
                        step["duration_ms"] = int(match.group(1))

            elif "Vector" in note or "SEMANTIC" in note:
                step["step_type"] = TraceStepType.VECTOR_SEARCH
                # Parse vector search metadata
                if "fallback" in note.lower():
                    step["metadata"]["is_fallback"] = True

            elif "HYBRID" in note or "merge" in note.lower():
                step["step_type"] = TraceStepType.HYBRID_MERGE

            elif "fallback" in note.lower():
                step["step_type"] = TraceStepType.FALLBACK_TRIGGERED

            elif "filter" in note.lower():
                step["step_type"] = TraceStepType.RESULT_FILTER

            elif "score" in note.lower():
                step["step_type"] = TraceStepType.SCORE_CALCULATION

            steps.append(step)

        return steps

    def _validate_step_ordering(self, steps: List[Dict[str, Any]], report: ValidationReport) -> None:
        """Validate logical ordering of search steps."""
        if not steps:
            report.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="ordering",
                message="No search steps found in trace"
            ))
            return

        # Check for valid patterns
        step_types = [step.get("step_type") for step in steps if step.get("step_type")]

        # Identify search strategy based on steps
        strategy = "unknown"
        if TraceStepType.AC_SEARCH in step_types and TraceStepType.VECTOR_SEARCH in step_types:
            if TraceStepType.HYBRID_MERGE in step_types:
                strategy = "hybrid"
            elif TraceStepType.FALLBACK_TRIGGERED in step_types:
                strategy = "fallback"
        elif TraceStepType.AC_SEARCH in step_types:
            strategy = "ac_only"
        elif TraceStepType.VECTOR_SEARCH in step_types:
            strategy = "vector_only"

        # Validate against expected pattern
        if strategy in self.expected_patterns:
            expected = self.expected_patterns[strategy]
            for expected_type in expected:
                if expected_type not in step_types:
                    report.issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="ordering",
                        message=f"Missing expected step type for {strategy} strategy: {expected_type.value}",
                        expected=expected_type.value,
                        actual=None
                    ))

        # Check for logical inconsistencies
        ac_index = next((i for i, step in enumerate(steps) if step.get("step_type") == TraceStepType.AC_SEARCH), -1)
        vector_index = next((i for i, step in enumerate(steps) if step.get("step_type") == TraceStepType.VECTOR_SEARCH), -1)
        hybrid_index = next((i for i, step in enumerate(steps) if step.get("step_type") == TraceStepType.HYBRID_MERGE), -1)

        if hybrid_index != -1:
            if ac_index == -1 or vector_index == -1:
                report.issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="ordering",
                    message="Hybrid merge step found without both AC and vector search steps",
                    step_index=hybrid_index
                ))
            elif ac_index > hybrid_index or vector_index > hybrid_index:
                report.issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="ordering",
                    message="Hybrid merge step must come after AC and vector search steps",
                    step_index=hybrid_index
                ))

    def _validate_timing_consistency(self, steps: List[Dict[str, Any]], report: ValidationReport) -> None:
        """Validate timing information consistency."""
        total_step_time = 0
        timing_steps = []

        for step in steps:
            if step.get("duration_ms") is not None:
                duration = step["duration_ms"]
                timing_steps.append((step["index"], duration))
                total_step_time += duration

                # Check for unreasonable durations
                if duration < 0:
                    report.issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="timing",
                        message=f"Negative duration found: {duration}ms",
                        step_index=step["index"]
                    ))
                elif duration > 10000:  # 10 seconds
                    report.issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="timing",
                        message=f"Unusually long duration: {duration}ms",
                        step_index=step["index"],
                        details={"duration_ms": duration}
                    ))

        # Compare with total trace time if available
        # This would need to be enhanced based on actual SearchTrace implementation

    def _validate_data_integrity(self, steps: List[Dict[str, Any]], report: ValidationReport) -> None:
        """Validate data integrity across steps."""
        # Check result count consistency
        result_counts = [(step["index"], step["result_count"])
                        for step in steps if step.get("result_count") is not None]

        # Validate result count progression
        for i, (step_index, count) in enumerate(result_counts):
            if count < 0:
                report.issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="data_integrity",
                    message=f"Negative result count: {count}",
                    step_index=step_index
                ))

            # Check for dramatic result count changes that might indicate issues
            if i > 0:
                prev_count = result_counts[i-1][1]
                if abs(count - prev_count) > prev_count * 2:  # More than 2x change
                    report.issues.append(ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        category="data_integrity",
                        message=f"Large result count change: {prev_count} -> {count}",
                        step_index=step_index,
                        details={"previous_count": prev_count, "current_count": count}
                    ))

    def _validate_coverage_requirements(self, steps: List[Dict[str, Any]], report: ValidationReport) -> None:
        """Validate coverage of required search components."""
        step_types = set(step.get("step_type") for step in steps if step.get("step_type"))

        # Check for minimum coverage requirements
        requirements = {
            "search_execution": [TraceStepType.AC_SEARCH, TraceStepType.VECTOR_SEARCH],
            "result_processing": [TraceStepType.HYBRID_MERGE, TraceStepType.RESULT_FILTER, TraceStepType.SCORE_CALCULATION]
        }

        for requirement_name, required_types in requirements.items():
            if not any(req_type in step_types for req_type in required_types):
                severity = ValidationSeverity.ERROR if self.strict_mode else ValidationSeverity.WARNING
                report.issues.append(ValidationIssue(
                    severity=severity,
                    category="coverage",
                    message=f"Missing coverage for {requirement_name}",
                    expected=f"One of: {[t.value for t in required_types]}",
                    actual=list(step_types)
                ))

    def _validate_performance_thresholds(self, steps: List[Dict[str, Any]], report: ValidationReport) -> None:
        """Validate performance against defined thresholds."""
        # Performance thresholds
        thresholds = {
            TraceStepType.AC_SEARCH: {"max_duration_ms": 50, "max_results": 1000},
            TraceStepType.VECTOR_SEARCH: {"max_duration_ms": 200, "max_results": 100},
            TraceStepType.HYBRID_MERGE: {"max_duration_ms": 20, "max_results": 50}
        }

        for step in steps:
            step_type = step.get("step_type")
            if step_type and step_type in thresholds:
                threshold = thresholds[step_type]

                # Check duration threshold
                if step.get("duration_ms") is not None:
                    duration = step["duration_ms"]
                    if duration > threshold["max_duration_ms"]:
                        report.issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            category="performance",
                            message=f"{step_type.value} exceeded duration threshold",
                            step_index=step["index"],
                            expected=f"<= {threshold['max_duration_ms']}ms",
                            actual=f"{duration}ms"
                        ))

                # Check result count threshold
                if step.get("result_count") is not None:
                    count = step["result_count"]
                    if count > threshold["max_results"]:
                        report.issues.append(ValidationIssue(
                            severity=ValidationSeverity.INFO,
                            category="performance",
                            message=f"{step_type.value} returned many results",
                            step_index=step["index"],
                            details={"result_count": count, "threshold": threshold["max_results"]}
                        ))

    def _generate_statistics(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive statistics for trace steps."""
        step_types = [step.get("step_type") for step in steps if step.get("step_type")]
        durations = [step.get("duration_ms") for step in steps if step.get("duration_ms") is not None]
        result_counts = [step.get("result_count") for step in steps if step.get("result_count") is not None]

        stats = {
            "total_steps": len(steps),
            "typed_steps": len([s for s in step_types if s is not None]),
            "step_type_distribution": {
                step_type.value: step_types.count(step_type)
                for step_type in TraceStepType
                if step_type in step_types
            },
            "timing": {
                "steps_with_timing": len(durations),
                "total_duration_ms": sum(durations) if durations else 0,
                "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
                "max_duration_ms": max(durations) if durations else 0,
                "min_duration_ms": min(durations) if durations else 0
            },
            "results": {
                "steps_with_results": len(result_counts),
                "total_results": sum(result_counts) if result_counts else 0,
                "avg_results": sum(result_counts) / len(result_counts) if result_counts else 0,
                "max_results": max(result_counts) if result_counts else 0,
                "min_results": min(result_counts) if result_counts else 0
            }
        }

        return stats

    def _analyze_timing(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze timing patterns in trace."""
        timing_analysis = {
            "bottlenecks": [],
            "performance_distribution": {},
            "timing_consistency": "unknown"
        }

        # Find bottlenecks
        durations_with_index = [(step["index"], step["duration_ms"])
                               for step in steps if step.get("duration_ms") is not None]

        if durations_with_index:
            durations_with_index.sort(key=lambda x: x[1], reverse=True)
            # Top 3 slowest steps
            timing_analysis["bottlenecks"] = durations_with_index[:3]

            # Performance distribution by step type
            for step in steps:
                if step.get("step_type") and step.get("duration_ms") is not None:
                    step_type = step["step_type"].value
                    if step_type not in timing_analysis["performance_distribution"]:
                        timing_analysis["performance_distribution"][step_type] = {
                            "count": 0,
                            "total_ms": 0,
                            "avg_ms": 0,
                            "max_ms": 0
                        }

                    perf = timing_analysis["performance_distribution"][step_type]
                    perf["count"] += 1
                    perf["total_ms"] += step["duration_ms"]
                    perf["avg_ms"] = perf["total_ms"] / perf["count"]
                    perf["max_ms"] = max(perf["max_ms"], step["duration_ms"])

        return timing_analysis

    def _analyze_coverage(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze coverage of search trace."""
        step_types = set(step.get("step_type") for step in steps if step.get("step_type"))

        all_possible_types = set(TraceStepType)
        covered_types = step_types & all_possible_types
        missing_types = all_possible_types - covered_types

        coverage_percentage = len(covered_types) / len(all_possible_types) * 100 if all_possible_types else 0

        return {
            "coverage_percentage": round(coverage_percentage, 1),
            "covered_step_types": [t.value for t in covered_types],
            "missing_step_types": [t.value for t in missing_types],
            "search_strategy_identified": self._identify_search_strategy(step_types),
            "completeness_score": self._calculate_completeness_score(step_types)
        }

    def _identify_search_strategy(self, step_types: Set[TraceStepType]) -> str:
        """Identify the search strategy used based on step types."""
        if TraceStepType.AC_SEARCH in step_types and TraceStepType.VECTOR_SEARCH in step_types:
            if TraceStepType.HYBRID_MERGE in step_types:
                return "hybrid"
            elif TraceStepType.FALLBACK_TRIGGERED in step_types:
                return "fallback"
            else:
                return "parallel"
        elif TraceStepType.AC_SEARCH in step_types:
            return "ac_only"
        elif TraceStepType.VECTOR_SEARCH in step_types:
            return "vector_only"
        else:
            return "unknown"

    def _calculate_completeness_score(self, step_types: Set[TraceStepType]) -> float:
        """Calculate completeness score (0-1) based on expected steps."""
        # Weight different step types by importance
        weights = {
            TraceStepType.AC_SEARCH: 0.3,
            TraceStepType.VECTOR_SEARCH: 0.3,
            TraceStepType.HYBRID_MERGE: 0.2,
            TraceStepType.RESULT_FILTER: 0.1,
            TraceStepType.SCORE_CALCULATION: 0.05,
            TraceStepType.FALLBACK_TRIGGERED: 0.05
        }

        score = sum(weights.get(step_type, 0) for step_type in step_types)
        return min(score, 1.0)  # Cap at 1.0


def create_deterministic_trace_snapshot(search_trace: SearchTrace, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create deterministic snapshot of search trace for comparison."""
    validator = SearchTraceValidator()
    report = validator.validate_trace(search_trace)

    snapshot = {
        "trace_hash": report.deterministic_hash,
        "enabled": search_trace.enabled,
        "total_time_ms": search_trace.total_time_ms,
        "total_hits": search_trace.total_hits,
        "notes": sorted(search_trace.notes),  # Deterministic ordering
        "validation": {
            "is_valid": report.is_valid,
            "issues_count": len(report.issues),
            "errors_count": len(report.get_issues_by_severity(ValidationSeverity.ERROR)),
            "warnings_count": len(report.get_issues_by_severity(ValidationSeverity.WARNING))
        },
        "statistics": report.statistics,
        "coverage": report.coverage_analysis,
        "metadata": metadata or {},
        "snapshot_timestamp": time.time()
    }

    return snapshot
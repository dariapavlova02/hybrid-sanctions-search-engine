"""
Result building utilities for constructing NormalizationResult objects.
"""

import time
from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass

from .config import NormalizationConfig
from .person_extraction import PersonCandidate
from ....contracts.base_contracts import NormalizationResult, TokenTrace


@dataclass
class ProcessingMetrics:
    """Metrics for normalization processing."""
    start_time: float
    end_time: Optional[float] = None
    token_count: int = 0
    original_length: int = 0
    normalized_length: int = 0
    persons_detected: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    @property
    def processing_time(self) -> float:
        """Calculate processing time in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time


class ResultBuilder:
    """Builds normalized results from processed tokens and metadata."""

    def __init__(self):
        """Initialize the result builder."""
        pass

    def build_normalization_result(
        self,
        original_text: str,
        normalized_tokens: List[str],
        token_traces: List[TokenTrace],
        persons: List[PersonCandidate],
        language: str,
        config: NormalizationConfig,
        metrics: ProcessingMetrics,
        organizations_core: Optional[List[str]] = None,
        errors: Optional[List[str]] = None
    ) -> NormalizationResult:
        """Build a complete NormalizationResult from processed components."""
        # Finalize metrics
        metrics.end_time = time.time()
        metrics.token_count = len(normalized_tokens)
        metrics.original_length = len(original_text)

        # Build normalized text
        normalized_text = self._reconstruct_normalized_text(normalized_tokens)
        metrics.normalized_length = len(normalized_text)
        metrics.persons_detected = len(persons)

        # Build person structures
        persons_core = self._build_persons_core(persons)

        # Collect all errors
        all_errors = []
        if errors:
            all_errors.extend(errors)
        if metrics.errors:
            all_errors.extend(metrics.errors)

        # Calculate confidence
        confidence = self._calculate_confidence(
            normalized_tokens,
            token_traces,
            persons,
            language
        )

        return NormalizationResult(
            normalized=normalized_text,
            tokens=normalized_tokens,
            trace=token_traces,
            errors=all_errors,
            language=language,
            confidence=confidence,
            original_length=metrics.original_length,
            normalized_length=metrics.normalized_length,
            token_count=metrics.token_count,
            processing_time=metrics.processing_time,
            success=len(all_errors) == 0,
            persons_core=persons_core,
            organizations_core=organizations_core or []
        )

    def create_token_trace(
        self,
        original_token: str,
        normalized_token: str,
        role: str,
        rule: str,
        morphology_lang: Optional[str] = None,
        normal_form: Optional[str] = None,
        fallback: bool = False,
        notes: Optional[str] = None
    ) -> TokenTrace:
        """Create a token trace for debugging and explanation."""
        return TokenTrace(
            token=original_token,
            role=role,
            rule=rule,
            morphology_lang=morphology_lang,
            normal_form=normal_form,
            output=normalized_token,
            fallback=fallback,
            notes=notes
        )

    def merge_traces(
        self,
        traces1: List[TokenTrace],
        traces2: List[TokenTrace]
    ) -> List[TokenTrace]:
        """Merge two lists of traces, avoiding duplicates."""
        seen_tokens = set()
        merged = []

        for trace in traces1 + traces2:
            trace_key = (trace.token, trace.role, trace.output)
            if trace_key not in seen_tokens:
                seen_tokens.add(trace_key)
                merged.append(trace)

        return merged

    def validate_result(
        self,
        result: NormalizationResult,
        config: NormalizationConfig
    ) -> List[str]:
        """Validate a normalization result and return any validation errors."""
        errors = []

        # Check basic structure
        if not result.normalized and result.tokens:
            errors.append("Normalized text is empty but tokens exist")

        if len(result.tokens) != len(result.trace):
            errors.append(f"Token count ({len(result.tokens)}) doesn't match trace count ({len(result.trace)})")

        # Check language consistency
        if not result.language:
            errors.append("Language not detected")

        # Check processing time reasonableness
        if result.processing_time > 10.0:  # 10 seconds is very long
            errors.append(f"Processing time too long: {result.processing_time:.2f}s")

        # Check confidence bounds
        if result.confidence is not None and (result.confidence < 0.0 or result.confidence > 1.0):
            errors.append(f"Confidence out of bounds: {result.confidence}")

        return errors

    def _reconstruct_normalized_text(self, tokens: List[str]) -> str:
        """Reconstruct normalized text from tokens."""
        if not tokens:
            return ""

        # Join tokens with single spaces
        normalized = " ".join(token for token in tokens if token and token.strip())

        # Clean up multiple spaces
        import re
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized

    def _build_persons_core(self, persons: List[PersonCandidate]) -> List[List[str]]:
        """Build persons_core structure from person candidates."""
        if not persons:
            return []

        persons_core = []
        for person in persons:
            if person.tokens:
                persons_core.append(person.tokens)

        return persons_core

    def _calculate_confidence(
        self,
        tokens: List[str],
        traces: List[TokenTrace],
        persons: List[PersonCandidate],
        language: str
    ) -> Optional[float]:
        """Calculate confidence score for the normalization result."""
        if not tokens:
            return None

        confidence_factors = []

        # Language detection confidence
        if language in ["ru", "uk", "en"]:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.5)

        # Token processing confidence
        processed_tokens = len([t for t in traces if not t.fallback])
        total_tokens = len(traces)
        if total_tokens > 0:
            token_confidence = processed_tokens / total_tokens
            confidence_factors.append(token_confidence)

        # Person structure confidence
        if persons:
            person_confidences = [p.confidence for p in persons if p.confidence is not None]
            if person_confidences:
                avg_person_confidence = sum(person_confidences) / len(person_confidences)
                confidence_factors.append(avg_person_confidence)

        # Calculate weighted average
        if confidence_factors:
            return sum(confidence_factors) / len(confidence_factors)

        return None

    def create_processing_metrics(self, original_text: str) -> ProcessingMetrics:
        """Create initial processing metrics."""
        return ProcessingMetrics(
            start_time=time.time(),
            original_length=len(original_text)
        )

    def add_error_to_metrics(self, metrics: ProcessingMetrics, error: str):
        """Add an error to processing metrics."""
        if metrics.errors is None:
            metrics.errors = []
        metrics.errors.append(error)

    def build_minimal_result(
        self,
        original_text: str,
        error_message: str,
        language: str = "unknown"
    ) -> NormalizationResult:
        """Build a minimal result for error cases."""
        return NormalizationResult(
            normalized="",
            tokens=[],
            trace=[],
            errors=[error_message],
            language=language,
            confidence=None,
            original_length=len(original_text),
            normalized_length=0,
            token_count=0,
            processing_time=0.0,
            success=False,
            persons_core=[],
            organizations_core=[]
        )

    def extract_organizations_core(
        self,
        original_text: str,
        traces: List[TokenTrace]
    ) -> List[str]:
        """Extract organization core names from traces and original text."""
        organizations = []

        # Look for quoted segments that might be organization names
        import re
        quote_pattern = r'"([^"]+)"|\'([^\']+)\'|«([^»]+)»'

        for match in re.finditer(quote_pattern, original_text):
            # Get the first non-None group
            quoted_text = None
            for group in match.groups():
                if group is not None:
                    quoted_text = group.strip()
                    break

            if quoted_text and len(quoted_text) > 2:
                organizations.append(quoted_text)

        # Look for organization-like tokens in traces
        org_indicators = {
            "ооо", "зао", "оао", "пао", "ао", "тов", "тдв", "ват", "пат", "ат",
            "llc", "ltd", "inc", "corp", "co", "plc", "gmbh", "ag", "bank"
        }

        for trace in traces:
            if trace.token.lower() in org_indicators:
                # This suggests the presence of an organization
                # Look for nearby capitalized words that might be the core name
                pass  # Implementation would depend on more context

        return organizations
"""
Result processing utilities including deduplication, reranking, and filtering.
"""

import re
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

from ..contracts import Candidate, SearchOpts
from ....utils.logging_config import get_logger


class ResultProcessor:
    """Processes and enhances search results."""

    def __init__(self):
        """Initialize result processor."""
        self.logger = get_logger(__name__)

        # Default processing configuration
        self.config = {
            "enable_rapidfuzz_reranking": True,
            "enable_anchor_boost": True,
            "enable_deduplication": True,
            "similarity_threshold": 0.8,
            "anchor_boost_factor": 1.2,
            "max_results": 100
        }

    def process_results(
        self,
        candidates: List[Candidate],
        query: str,
        opts: SearchOpts
    ) -> List[Candidate]:
        """Process search results with full pipeline."""
        if not candidates:
            return []

        self.logger.info(f"Processing {len(candidates)} candidates")

        # Step 1: Deduplication
        if self.config["enable_deduplication"]:
            candidates = self.deduplicate_candidates(candidates)
            self.logger.debug(f"After deduplication: {len(candidates)} candidates")

        # Step 2: Apply rapidfuzz reranking
        if self.config["enable_rapidfuzz_reranking"]:
            candidates = self.apply_rapidfuzz_reranking(candidates, query)
            self.logger.debug(f"After rapidfuzz reranking: {len(candidates)} candidates")

        # Step 3: Apply anchor boost
        if self.config["enable_anchor_boost"]:
            candidates = self.apply_anchor_boost(candidates, query)
            self.logger.debug(f"After anchor boost: {len(candidates)} candidates")

        # Step 4: Apply metadata filters
        candidates = self.apply_metadata_filters(candidates, opts)
        self.logger.debug(f"After metadata filters: {len(candidates)} candidates")

        # Step 5: Apply result limits
        candidates = candidates[:opts.limit]

        # Step 6: Final validation
        candidates = self.validate_results(candidates)

        self.logger.info(f"Final processed results: {len(candidates)} candidates")
        return candidates

    def deduplicate_candidates(self, candidates: List[Candidate]) -> List[Candidate]:
        """Remove duplicate candidates based on text similarity."""
        if not candidates:
            return []

        seen_texts: Set[str] = set()
        deduplicated = []

        for candidate in candidates:
            # Normalize text for comparison
            normalized_text = self._normalize_for_dedup(candidate.text)

            if normalized_text not in seen_texts:
                seen_texts.add(normalized_text)
                deduplicated.append(candidate)
            else:
                # If we've seen this text, check if current candidate has better score
                existing_idx = next(
                    (i for i, c in enumerate(deduplicated)
                     if self._normalize_for_dedup(c.text) == normalized_text),
                    -1
                )

                if existing_idx >= 0:
                    existing = deduplicated[existing_idx]
                    if (candidate.score or 0) > (existing.score or 0):
                        # Replace with better scoring candidate
                        deduplicated[existing_idx] = candidate

        return deduplicated

    def apply_rapidfuzz_reranking(
        self,
        candidates: List[Candidate],
        query: str
    ) -> List[Candidate]:
        """Apply rapidfuzz string similarity reranking."""
        if not candidates or not query:
            return candidates

        try:
            # Try to import rapidfuzz for fuzzy string matching
            try:
                from rapidfuzz import fuzz
                rapidfuzz_available = True
            except ImportError:
                self.logger.warning("rapidfuzz not available, using basic similarity")
                rapidfuzz_available = False

            # Calculate new scores combining original and fuzzy similarity
            for candidate in candidates:
                if rapidfuzz_available:
                    # Use rapidfuzz for better similarity calculation
                    fuzzy_score = fuzz.ratio(query.lower(), candidate.text.lower()) / 100.0
                else:
                    # Fallback to simple similarity
                    fuzzy_score = self._simple_similarity(query, candidate.text)

                # Combine original score with fuzzy score
                original_score = candidate.score or 0.0
                combined_score = (original_score * 0.7) + (fuzzy_score * 0.3)
                candidate.score = combined_score

            # Re-sort by combined score
            candidates.sort(key=lambda c: c.score or 0, reverse=True)

        except Exception as e:
            self.logger.warning(f"Rapidfuzz reranking failed: {e}")

        return candidates

    def apply_anchor_boost(
        self,
        candidates: List[Candidate],
        query: str
    ) -> List[Candidate]:
        """Apply boost to candidates that contain exact query terms."""
        if not candidates or not query:
            return candidates

        query_terms = set(query.lower().split())

        for candidate in candidates:
            candidate_terms = set(candidate.text.lower().split())

            # Calculate term overlap
            overlap = len(query_terms.intersection(candidate_terms))
            total_query_terms = len(query_terms)

            if overlap > 0 and total_query_terms > 0:
                overlap_ratio = overlap / total_query_terms

                # Apply boost based on overlap
                boost_factor = 1.0 + (overlap_ratio * (self.config["anchor_boost_factor"] - 1.0))
                candidate.score = (candidate.score or 0.0) * boost_factor

        # Re-sort after boosting
        candidates.sort(key=lambda c: c.score or 0, reverse=True)
        return candidates

    def apply_metadata_filters(
        self,
        candidates: List[Candidate],
        opts: SearchOpts
    ) -> List[Candidate]:
        """Apply metadata-based filtering."""
        if not hasattr(opts, 'metadata_filters') or not opts.metadata_filters:
            return candidates

        filtered = []
        for candidate in candidates:
            if self._matches_metadata_filters(candidate, opts.metadata_filters):
                filtered.append(candidate)

        return filtered

    def validate_results(self, candidates: List[Candidate]) -> List[Candidate]:
        """Validate and clean up final results."""
        validated = []

        for candidate in candidates:
            # Basic validation
            if not candidate.text or not candidate.text.strip():
                continue

            # Score validation
            if candidate.score is not None and candidate.score < 0:
                candidate.score = 0.0

            # Text length validation
            if len(candidate.text.strip()) < 2:
                continue

            validated.append(candidate)

        return validated

    def combine_result_sets(
        self,
        *result_sets: List[Candidate],
        weights: Optional[List[float]] = None
    ) -> List[Candidate]:
        """Combine multiple result sets with optional weighting."""
        if not result_sets:
            return []

        # Default equal weights
        if weights is None:
            weights = [1.0] * len(result_sets)

        if len(weights) != len(result_sets):
            raise ValueError("Number of weights must match number of result sets")

        # Combine all candidates with weighted scores
        all_candidates = []
        for result_set, weight in zip(result_sets, weights):
            for candidate in result_set:
                # Create new candidate with weighted score
                weighted_candidate = Candidate(
                    text=candidate.text,
                    score=(candidate.score or 0.0) * weight,
                    metadata=candidate.metadata,
                    source=getattr(candidate, 'source', 'unknown')
                )
                all_candidates.append(weighted_candidate)

        # Deduplicate and merge scores for same candidates
        return self.deduplicate_candidates(all_candidates)

    def group_by_similarity(
        self,
        candidates: List[Candidate],
        threshold: float = 0.8
    ) -> List[List[Candidate]]:
        """Group candidates by text similarity."""
        if not candidates:
            return []

        groups = []
        ungrouped = candidates.copy()

        while ungrouped:
            # Start new group with first ungrouped candidate
            current = ungrouped.pop(0)
            current_group = [current]

            # Find similar candidates
            remaining = []
            for candidate in ungrouped:
                similarity = self._simple_similarity(current.text, candidate.text)
                if similarity >= threshold:
                    current_group.append(candidate)
                else:
                    remaining.append(candidate)

            groups.append(current_group)
            ungrouped = remaining

        return groups

    def _normalize_for_dedup(self, text: str) -> str:
        """Normalize text for deduplication comparison."""
        if not text:
            return ""

        # Convert to lowercase
        normalized = text.lower().strip()

        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)

        # Remove common punctuation
        normalized = re.sub(r'[^\w\s]', '', normalized)

        return normalized

    def _simple_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple character-based similarity between two texts."""
        if not text1 or not text2:
            return 0.0

        # Convert to lowercase for comparison
        t1 = text1.lower()
        t2 = text2.lower()

        if t1 == t2:
            return 1.0

        # Calculate character overlap
        set1 = set(t1)
        set2 = set(t2)

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        if union == 0:
            return 0.0

        return intersection / union

    def _matches_metadata_filters(
        self,
        candidate: Candidate,
        filters: Dict[str, Any]
    ) -> bool:
        """Check if candidate matches metadata filters."""
        if not candidate.metadata:
            return not filters  # No metadata means no filtering

        for key, expected_value in filters.items():
            if key not in candidate.metadata:
                return False

            actual_value = candidate.metadata[key]

            # Handle different filter types
            if isinstance(expected_value, list):
                # IN filter
                if actual_value not in expected_value:
                    return False
            elif isinstance(expected_value, dict):
                # Range or complex filters
                if "min" in expected_value and actual_value < expected_value["min"]:
                    return False
                if "max" in expected_value and actual_value > expected_value["max"]:
                    return False
            else:
                # Exact match
                if actual_value != expected_value:
                    return False

        return True

    def update_config(self, **kwargs) -> None:
        """Update processing configuration."""
        self.config.update(kwargs)

    def get_config(self) -> Dict[str, Any]:
        """Get current processing configuration."""
        return self.config.copy()
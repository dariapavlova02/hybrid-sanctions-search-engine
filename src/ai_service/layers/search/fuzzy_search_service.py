"""
Fuzzy search service for handling typos and misspellings.
Uses rapidfuzz for high-performance fuzzy string matching.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict

try:
    import rapidfuzz
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False

from ...utils.logging_config import get_logger
from ...utils.profiling import profile_function
from ...contracts.search_contracts import Candidate, SearchResult


@dataclass
class FuzzyMatchResult:
    """Result of fuzzy matching operation."""
    original_query: str
    matched_text: str
    score: float
    algorithm: str  # 'ratio', 'partial_ratio', 'token_sort_ratio', 'token_set_ratio'
    doc_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class FuzzyConfig:
    """Configuration for fuzzy matching."""
    # Score thresholds
    min_score_threshold: float = 0.6  # Minimum score to consider a match
    high_confidence_threshold: float = 0.85  # High confidence matches
    partial_match_threshold: float = 0.75  # For partial matches
    token_match_threshold: float = 0.8  # For token-based matches

    # Algorithm weights
    ratio_weight: float = 0.3
    partial_ratio_weight: float = 0.25
    token_sort_ratio_weight: float = 0.25
    token_set_ratio_weight: float = 0.2

    # Performance settings
    max_candidates: int = 1000  # Maximum candidates to consider
    max_results: int = 50  # Maximum results to return
    enable_preprocessing: bool = True  # Enable query preprocessing

    # Specific use cases
    enable_name_fuzzy: bool = True  # Special handling for person names
    enable_org_fuzzy: bool = True   # Special handling for organization names
    name_boost_factor: float = 1.2  # Boost factor for name matches

    # Performance optimization
    use_scorer_cache: bool = True
    cache_size: int = 10000


class FuzzySearchService:
    """High-performance fuzzy search service for typo tolerance."""

    def __init__(self, config: Optional[FuzzyConfig] = None):
        self.logger = get_logger(__name__)
        self.config = config or FuzzyConfig()

        if not RAPIDFUZZ_AVAILABLE:
            self.logger.warning("rapidfuzz not available - fuzzy search will be disabled")
            self.enabled = False
            return

        self.enabled = True
        self._scorer_cache = {} if self.config.use_scorer_cache else None

        # Pre-compiled patterns for optimization
        self._name_patterns = self._compile_name_patterns()

        self.logger.info(f"FuzzySearchService initialized (enabled: {self.enabled})")

    def _compile_name_patterns(self) -> Dict[str, Any]:
        """Compile patterns for name recognition."""
        return {
            'person_suffixes': {'ович', 'евич', 'івна', 'ївна', 'енко', 'ук', 'юк'},
            'org_patterns': {'ооо', 'тов', 'llc', 'ltd', 'inc', 'corp', 'gmbh'}
        }

    @profile_function("fuzzy_search.search")
    async def search_async(
        self,
        query: str,
        candidates: List[str],
        doc_mapping: Optional[Dict[str, str]] = None,
        metadata_mapping: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[FuzzyMatchResult]:
        """
        Perform fuzzy search against candidates.

        Args:
            query: Search query (potentially with typos)
            candidates: List of candidate strings to match against
            doc_mapping: Optional mapping from candidate string to doc_id
            metadata_mapping: Optional mapping from candidate string to metadata

        Returns:
            List of fuzzy match results sorted by score
        """
        if not self.enabled:
            return []

        if not query or not candidates:
            return []

        start_time = time.time()

        try:
            # Preprocess query
            processed_query = self._preprocess_query(query) if self.config.enable_preprocessing else query

            # Limit candidates for performance
            candidate_subset = candidates[:self.config.max_candidates]

            # Perform fuzzy matching with multiple algorithms
            matches = self._fuzzy_match_multi_algorithm(processed_query, candidate_subset)

            # Convert to FuzzyMatchResult objects
            results = []
            for candidate, score, algorithm in matches:
                doc_id = doc_mapping.get(candidate) if doc_mapping else None
                metadata = metadata_mapping.get(candidate) if metadata_mapping else None

                result = FuzzyMatchResult(
                    original_query=query,
                    matched_text=candidate,
                    score=score,
                    algorithm=algorithm,
                    doc_id=doc_id,
                    metadata=metadata
                )
                results.append(result)

            # Sort by score (descending) and limit results
            results.sort(key=lambda x: x.score, reverse=True)
            results = results[:self.config.max_results]

            processing_time = (time.time() - start_time) * 1000
            self.logger.debug(f"Fuzzy search completed: {len(results)} results in {processing_time:.2f}ms")

            return results

        except Exception as e:
            self.logger.error(f"Fuzzy search failed: {e}")
            return []

    def _preprocess_query(self, query: str) -> str:
        """Preprocess query for better matching."""
        # Basic normalization
        processed = query.strip().lower()

        # Remove extra whitespace
        processed = ' '.join(processed.split())

        # TODO: Add more sophisticated preprocessing if needed
        # - Remove diacritics
        # - Handle common abbreviations
        # - Normalize punctuation

        return processed

    def _fuzzy_match_multi_algorithm(
        self,
        query: str,
        candidates: List[str]
    ) -> List[Tuple[str, float, str]]:
        """
        Use multiple fuzzy matching algorithms and combine results.

        Returns:
            List of (candidate, score, algorithm) tuples
        """
        all_matches = []

        # Algorithm 1: Simple ratio (Levenshtein-based)
        try:
            ratio_matches = process.extract(
                query,
                candidates,
                scorer=fuzz.ratio,
                limit=self.config.max_results * 2,
                score_cutoff=self.config.min_score_threshold * 100  # rapidfuzz uses 0-100
            )
            for candidate, score, _ in ratio_matches:
                normalized_score = score / 100.0
                if normalized_score >= self.config.min_score_threshold:
                    all_matches.append((candidate, normalized_score, 'ratio'))
        except Exception as e:
            self.logger.warning(f"Ratio matching failed: {e}")

        # Algorithm 2: Partial ratio (good for substring matches)
        try:
            partial_matches = process.extract(
                query,
                candidates,
                scorer=fuzz.partial_ratio,
                limit=self.config.max_results * 2,
                score_cutoff=self.config.partial_match_threshold * 100
            )
            for candidate, score, _ in partial_matches:
                normalized_score = score / 100.0
                if normalized_score >= self.config.partial_match_threshold:
                    all_matches.append((candidate, normalized_score, 'partial_ratio'))
        except Exception as e:
            self.logger.warning(f"Partial ratio matching failed: {e}")

        # Algorithm 3: Token sort ratio (good for word order differences)
        try:
            token_sort_matches = process.extract(
                query,
                candidates,
                scorer=fuzz.token_sort_ratio,
                limit=self.config.max_results * 2,
                score_cutoff=self.config.token_match_threshold * 100
            )
            for candidate, score, _ in token_sort_matches:
                normalized_score = score / 100.0
                if normalized_score >= self.config.token_match_threshold:
                    all_matches.append((candidate, normalized_score, 'token_sort_ratio'))
        except Exception as e:
            self.logger.warning(f"Token sort matching failed: {e}")

        # Algorithm 4: Token set ratio (good for different word sets)
        try:
            token_set_matches = process.extract(
                query,
                candidates,
                scorer=fuzz.token_set_ratio,
                limit=self.config.max_results * 2,
                score_cutoff=self.config.token_match_threshold * 100
            )
            for candidate, score, _ in token_set_matches:
                normalized_score = score / 100.0
                if normalized_score >= self.config.token_match_threshold:
                    all_matches.append((candidate, normalized_score, 'token_set_ratio'))
        except Exception as e:
            self.logger.warning(f"Token set matching failed: {e}")

        # Combine and deduplicate results
        return self._combine_fuzzy_results(all_matches)

    def _combine_fuzzy_results(
        self,
        matches: List[Tuple[str, float, str]]
    ) -> List[Tuple[str, float, str]]:
        """
        Combine results from multiple algorithms and deduplicate.

        For each candidate, we take the best score across all algorithms,
        but apply weighted scoring based on algorithm reliability.
        """
        candidate_scores = defaultdict(list)

        # Group by candidate
        for candidate, score, algorithm in matches:
            candidate_scores[candidate].append((score, algorithm))

        # Calculate final scores
        final_results = []
        for candidate, score_list in candidate_scores.items():

            # Get best score for each algorithm
            algo_scores = {}
            for score, algorithm in score_list:
                if algorithm not in algo_scores or score > algo_scores[algorithm]:
                    algo_scores[algorithm] = score

            # Calculate weighted final score
            final_score = 0.0
            total_weight = 0.0

            weights = {
                'ratio': self.config.ratio_weight,
                'partial_ratio': self.config.partial_ratio_weight,
                'token_sort_ratio': self.config.token_sort_ratio_weight,
                'token_set_ratio': self.config.token_set_ratio_weight
            }

            for algorithm, score in algo_scores.items():
                weight = weights.get(algorithm, 0.25)  # Default weight
                final_score += score * weight
                total_weight += weight

            if total_weight > 0:
                final_score /= total_weight

                # Apply name boost if applicable
                if self._is_person_name(candidate) and self.config.enable_name_fuzzy:
                    final_score *= self.config.name_boost_factor
                    final_score = min(final_score, 1.0)  # Cap at 1.0

                # Determine best algorithm for this candidate
                best_algorithm = max(algo_scores.keys(), key=lambda k: algo_scores[k])

                final_results.append((candidate, final_score, best_algorithm))

        return final_results

    def _is_person_name(self, text: str) -> bool:
        """Check if text looks like a person name."""
        text_lower = text.lower()

        # Check for patronymic/surname patterns
        for suffix in self._name_patterns['person_suffixes']:
            if suffix in text_lower:
                return True

        # Check for capitalization pattern (Title Case)
        words = text.split()
        if len(words) >= 2:
            capitalized_words = sum(1 for word in words if word and word[0].isupper())
            if capitalized_words >= 2:  # Multiple capitalized words suggest names
                return True

        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get fuzzy search statistics."""
        return {
            'enabled': self.enabled,
            'cache_size': len(self._scorer_cache) if self._scorer_cache else 0,
            'config': {
                'min_score_threshold': self.config.min_score_threshold,
                'high_confidence_threshold': self.config.high_confidence_threshold,
                'max_candidates': self.config.max_candidates,
                'max_results': self.config.max_results
            }
        }


# Convenience function for quick fuzzy matching
def fuzzy_match_names(
    query: str,
    names: List[str],
    threshold: float = 0.6,
    limit: int = 10
) -> List[Tuple[str, float]]:
    """
    Quick fuzzy matching function for names.

    Args:
        query: Query string
        names: List of names to match against
        threshold: Minimum score threshold
        limit: Maximum number of results

    Returns:
        List of (name, score) tuples
    """
    if not RAPIDFUZZ_AVAILABLE:
        return []

    try:
        matches = process.extract(
            query,
            names,
            scorer=fuzz.token_sort_ratio,  # Good for names
            limit=limit,
            score_cutoff=threshold * 100
        )
        return [(name, score / 100.0) for name, score in matches]
    except Exception:
        return []
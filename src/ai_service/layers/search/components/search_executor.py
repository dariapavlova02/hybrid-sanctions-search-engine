"""
Search execution logic for AC, vector, and hybrid search modes.
"""

import asyncio
import math
from typing import Any, Dict, List, Optional, Tuple

from ..contracts import Candidate, SearchOpts, SearchMode
from ..elasticsearch_adapters import ElasticsearchACAdapter, ElasticsearchVectorAdapter
from ....contracts.base_contracts import NormalizationResult
from ....utils.logging_config import get_logger


class SearchExecutor:
    """Handles execution of different search modes."""

    def __init__(
        self,
        ac_adapter: Optional[ElasticsearchACAdapter] = None,
        vector_adapter: Optional[ElasticsearchVectorAdapter] = None
    ):
        """Initialize search executor with adapters."""
        self.logger = get_logger(__name__)
        self.ac_adapter = ac_adapter
        self.vector_adapter = vector_adapter

        # Escalation thresholds
        self.escalation_config = {
            "min_ac_score": 0.7,
            "min_ac_results": 2,
            "max_score_variance": 0.3
        }

    async def execute_ac_search(
        self,
        query_text: str,
        normalized: NormalizationResult,
        opts: SearchOpts
    ) -> List[Candidate]:
        """Execute AC (Aho-Corasick) exact match search."""
        if not self.ac_adapter:
            self.logger.warning("AC adapter not available")
            return []

        try:
            # Prepare AC search parameters
            ac_params = self._prepare_ac_params(query_text, normalized, opts)

            # Execute AC search
            candidates = await self.ac_adapter.search(ac_params)

            # Filter and process results
            filtered_candidates = self._filter_ac_results(candidates, opts)

            self.logger.info(f"AC search returned {len(filtered_candidates)} candidates")
            return filtered_candidates

        except Exception as e:
            self.logger.error(f"AC search failed: {e}", exc_info=True)
            return []

    async def execute_vector_search(
        self,
        query_vector: List[float],
        normalized: NormalizationResult,
        opts: SearchOpts
    ) -> List[Candidate]:
        """Execute vector similarity search."""
        if not self.vector_adapter:
            self.logger.warning("Vector adapter not available")
            return []

        try:
            # Prepare vector search parameters
            vector_params = self._prepare_vector_params(query_vector, normalized, opts)

            # Execute vector search
            candidates = await self.vector_adapter.search(vector_params)

            # Filter and process results
            filtered_candidates = self._filter_vector_results(candidates, opts)

            self.logger.info(f"Vector search returned {len(filtered_candidates)} candidates")
            return filtered_candidates

        except Exception as e:
            self.logger.error(f"Vector search failed: {e}", exc_info=True)
            return []

    async def execute_hybrid_search(
        self,
        query_text: str,
        query_vector: List[float],
        normalized: NormalizationResult,
        opts: SearchOpts
    ) -> List[Candidate]:
        """Execute hybrid search combining AC and vector results."""
        try:
            # Execute both searches concurrently
            ac_task = self.execute_ac_search(query_text, normalized, opts)
            vector_task = self.execute_vector_search(query_vector, normalized, opts)

            ac_candidates, vector_candidates = await asyncio.gather(
                ac_task, vector_task, return_exceptions=True
            )

            # Handle exceptions
            if isinstance(ac_candidates, Exception):
                self.logger.error(f"AC search in hybrid failed: {ac_candidates}")
                ac_candidates = []

            if isinstance(vector_candidates, Exception):
                self.logger.error(f"Vector search in hybrid failed: {vector_candidates}")
                vector_candidates = []

            # Combine and fuse results
            combined_candidates = self._fuse_hybrid_results(
                ac_candidates, vector_candidates, opts
            )

            self.logger.info(
                f"Hybrid search: AC={len(ac_candidates)}, Vector={len(vector_candidates)}, "
                f"Combined={len(combined_candidates)}"
            )

            return combined_candidates

        except Exception as e:
            self.logger.error(f"Hybrid search failed: {e}", exc_info=True)
            return []

    def should_escalate_to_vector(
        self,
        ac_candidates: List[Candidate],
        opts: SearchOpts
    ) -> bool:
        """Determine if vector search escalation is needed."""
        if not ac_candidates:
            return True

        # Check minimum number of results
        if len(ac_candidates) < self.escalation_config["min_ac_results"]:
            return True

        # Check score quality
        scores = [c.score for c in ac_candidates if c.score is not None]
        if not scores:
            return True

        max_score = max(scores)
        if max_score < self.escalation_config["min_ac_score"]:
            return True

        # Check score variance (if results are too scattered)
        if len(scores) > 1:
            avg_score = sum(scores) / len(scores)
            variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
            if variance > self.escalation_config["max_score_variance"]:
                return True

        return False

    def should_use_vector_fallback(
        self,
        ac_candidates: List[Candidate],
        vector_candidates: List[Candidate],
        opts: SearchOpts
    ) -> bool:
        """Determine if vector fallback should be used."""
        # Use vector fallback if AC failed completely
        if not ac_candidates and vector_candidates:
            return True

        # Use vector fallback if AC results are significantly worse
        if ac_candidates and vector_candidates:
            ac_max_score = max((c.score or 0) for c in ac_candidates)
            vector_max_score = max((c.score or 0) for c in vector_candidates)

            if vector_max_score > ac_max_score * 1.2:  # 20% better
                return True

        return False

    def _prepare_ac_params(
        self,
        query_text: str,
        normalized: NormalizationResult,
        opts: SearchOpts
    ) -> Dict[str, Any]:
        """Prepare parameters for AC search."""
        params = {
            "query": query_text,
            "normalized_query": normalized.normalized,
            "tokens": normalized.tokens,
            "limit": opts.limit,
            "offset": opts.offset
        }

        # Add metadata filters if present
        if hasattr(opts, 'metadata_filters') and opts.metadata_filters:
            params["filters"] = opts.metadata_filters

        # Add language information
        if normalized.language:
            params["language"] = normalized.language

        return params

    def _prepare_vector_params(
        self,
        query_vector: List[float],
        normalized: NormalizationResult,
        opts: SearchOpts
    ) -> Dict[str, Any]:
        """Prepare parameters for vector search."""
        params = {
            "vector": query_vector,
            "limit": opts.limit,
            "offset": opts.offset,
            "min_score": 0.5  # Minimum similarity threshold
        }

        # Add metadata filters if present
        if hasattr(opts, 'metadata_filters') and opts.metadata_filters:
            params["filters"] = opts.metadata_filters

        # Add language information
        if normalized.language:
            params["language"] = normalized.language

        return params

    def _filter_ac_results(
        self,
        candidates: List[Candidate],
        opts: SearchOpts
    ) -> List[Candidate]:
        """Filter and validate AC search results."""
        filtered = []

        for candidate in candidates:
            # Basic validation
            if not candidate.text or not candidate.text.strip():
                continue

            # Score threshold
            if candidate.score is not None and candidate.score < 0.1:
                continue

            # Length validation
            if len(candidate.text) < 2:
                continue

            filtered.append(candidate)

        # Sort by score descending
        filtered.sort(key=lambda c: c.score or 0, reverse=True)

        return filtered[:opts.limit]

    def _filter_vector_results(
        self,
        candidates: List[Candidate],
        opts: SearchOpts
    ) -> List[Candidate]:
        """Filter and validate vector search results."""
        filtered = []

        for candidate in candidates:
            # Basic validation
            if not candidate.text or not candidate.text.strip():
                continue

            # Score threshold for vector similarity
            if candidate.score is not None and candidate.score < 0.3:
                continue

            # Length validation
            if len(candidate.text) < 2:
                continue

            filtered.append(candidate)

        # Sort by score descending
        filtered.sort(key=lambda c: c.score or 0, reverse=True)

        return filtered[:opts.limit]

    def _fuse_hybrid_results(
        self,
        ac_candidates: List[Candidate],
        vector_candidates: List[Candidate],
        opts: SearchOpts
    ) -> List[Candidate]:
        """Fuse AC and vector results using weighted scoring."""
        # Weights for fusion
        ac_weight = 0.7  # AC results get higher weight for exact matches
        vector_weight = 0.3

        # Create a map to track combined candidates
        candidate_map: Dict[str, Candidate] = {}

        # Process AC candidates
        for candidate in ac_candidates:
            key = self._get_candidate_key(candidate)
            if key not in candidate_map:
                # Create new candidate with weighted score
                new_candidate = Candidate(
                    text=candidate.text,
                    score=(candidate.score or 0) * ac_weight,
                    metadata=candidate.metadata,
                    source="ac"
                )
                candidate_map[key] = new_candidate
            else:
                # Update existing candidate
                existing = candidate_map[key]
                existing.score = (existing.score or 0) + (candidate.score or 0) * ac_weight
                existing.source = "hybrid"

        # Process vector candidates
        for candidate in vector_candidates:
            key = self._get_candidate_key(candidate)
            if key not in candidate_map:
                # Create new candidate with weighted score
                new_candidate = Candidate(
                    text=candidate.text,
                    score=(candidate.score or 0) * vector_weight,
                    metadata=candidate.metadata,
                    source="vector"
                )
                candidate_map[key] = new_candidate
            else:
                # Update existing candidate
                existing = candidate_map[key]
                existing.score = (existing.score or 0) + (candidate.score or 0) * vector_weight
                existing.source = "hybrid"

        # Convert to list and sort
        fused_candidates = list(candidate_map.values())
        fused_candidates.sort(key=lambda c: c.score or 0, reverse=True)

        return fused_candidates[:opts.limit]

    def _get_candidate_key(self, candidate: Candidate) -> str:
        """Generate a key for deduplication."""
        # Use normalized text for deduplication
        normalized_text = candidate.text.lower().strip()
        # Add metadata ID if available
        if candidate.metadata and "id" in candidate.metadata:
            return f"{normalized_text}:{candidate.metadata['id']}"
        return normalized_text

    def update_escalation_config(self, **kwargs) -> None:
        """Update escalation configuration."""
        self.escalation_config.update(kwargs)

    def get_escalation_config(self) -> Dict[str, Any]:
        """Get current escalation configuration."""
        return self.escalation_config.copy()
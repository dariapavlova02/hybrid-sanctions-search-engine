"""
Mock Search Service for testing when elasticsearch is not available.
"""

from typing import Any, Dict, List, Optional

# Try to import contracts, fallback to simple classes if dependencies are not available
try:
    from .contracts import SearchService, Candidate, SearchOpts, SearchMetrics, SearchMode
    from ...contracts.base_contracts import NormalizationResult
except ImportError:
    # Fallback minimal implementations for testing without elasticsearch
    from enum import Enum
    from dataclasses import dataclass

    class SearchMode(Enum):
        AC = "ac"
        VECTOR = "vector"
        HYBRID = "hybrid"

    @dataclass
    class Candidate:
        doc_id: str
        score: float
        text: str
        entity_type: str
        metadata: Dict[str, Any]
        search_mode: SearchMode
        match_fields: List[str]
        confidence: float

    @dataclass
    class SearchOpts:
        search_mode: SearchMode = SearchMode.AC
        top_k: int = 10
        threshold: float = 0.7
        enable_escalation: bool = False

    @dataclass
    class SearchMetrics:
        pass

    @dataclass
    class NormalizationResult:
        normalized: str
        tokens: List[str]
        trace: List[Any]
        language: str
        confidence: float
        original_length: int
        normalized_length: int
        token_count: int
        processing_time: float
        success: bool

    class SearchService:
        """Base search service interface"""
        def initialize(self): pass
        async def health_check(self): pass
        async def find_candidates(self, normalized, text, opts): pass
        def get_metrics(self): pass
        def reset_metrics(self): pass


class MockSearchService(SearchService):
    """Mock search service that provides fallback test records when elasticsearch is unavailable."""

    def __init__(self, config=None):
        self.config = config
        self._test_persons = self._create_test_persons()

    def _create_test_persons(self) -> List[Candidate]:
        """Create test person records based on actual sanctions data structure."""
        return [
            Candidate(
                doc_id="mock_person_1",
                score=0.95,
                text="Ковриков Роман Валерійович",
                entity_type="person",
                metadata={
                    "name": "Ковриков Роман Валерійович",
                    "name_en": "Kovrykov Roman Valeriiovych",
                    "birthdate": "1976-08-09",
                    "dob": "1976-08-09",
                    "itn": "782611846337",
                    "person_id": 32450,
                    "status": 1
                },
                search_mode=SearchMode.AC,
                match_fields=["name", "name_en"],
                confidence=0.95
            ),
            Candidate(
                doc_id="mock_person_2",
                score=0.90,
                text="Гаркушев Євген Миколайович",
                entity_type="person",
                metadata={
                    "name": "Гаркушев Євген Миколайович",
                    "name_en": "Harkushev Yevhen Mykolaiovych",
                    "birthdate": "1972-04-18",
                    "dob": "1972-04-18",
                    "itn": "614401250400",
                    "person_id": 32449,
                    "status": 1
                },
                search_mode=SearchMode.AC,
                match_fields=["name", "name_en"],
                confidence=0.90
            ),
            # Add Poroshenko for testing vector search escalation
            Candidate(
                doc_id="mock_person_poroshenko",
                score=0.85,
                text="Порошенко Петро Олексійович",
                entity_type="person",
                metadata={
                    "name": "Порошенко Петро Олексійович",
                    "name_en": "Poroshenko Petro Oleksiyovych",
                    "birthdate": "1965-09-26",
                    "dob": "1965-09-26",
                    "itn": "2847003745",
                    "person_id": 10001,
                    "status": 1
                },
                search_mode=SearchMode.VECTOR,  # Found via vector search
                match_fields=["name", "name_en"],
                confidence=0.85
            )
        ]

    def initialize(self):
        """Mock initialization."""
        pass

    async def health_check(self) -> Dict[str, Any]:
        """Mock health check."""
        return {
            "status": "mock",
            "message": "Mock search service - elasticsearch not available",
            "test_records": len(self._test_persons)
        }

    async def search(
        self,
        query: str,
        *,
        limit: int = 10,
        opts: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Mock search that returns test results for matching queries."""
        # Simple name matching for mock
        query_lower = query.lower()
        results = []

        for person in self._test_persons:
            if (query_lower in person.text.lower() or
                query_lower in person.metadata.get("name_en", "").lower() or
                query_lower in person.metadata.get("itn", "")):
                results.append({
                    "doc_id": person.doc_id,
                    "score": person.score,
                    "text": person.text,
                    "metadata": person.metadata
                })

        return {
            "query": query,
            "results": results[:limit],
            "total_hits": len(results),
            "search_type": "mock",
            "processing_time_ms": 1,
            "warnings": ["Search service not available - using mock with test records"],
        }

    async def find_candidates(
        self,
        normalized: NormalizationResult,
        text: str,
        opts: SearchOpts
    ) -> List[Candidate]:
        """Find search candidates (mock implementation with test records and fuzzy matching)."""
        query_lower = text.lower()
        candidates = []

        for person in self._test_persons:
            score = 0.0
            matched = False

            # Exact substring matching
            if (query_lower in person.text.lower() or
                query_lower in person.metadata.get("name_en", "").lower() or
                query_lower in person.metadata.get("itn", "")):
                matched = True
                score = person.score

            # Fuzzy matching for typos (e.g., "Порошенк" matches "Порошенко")
            elif opts.search_mode in [SearchMode.VECTOR, SearchMode.HYBRID]:
                person_lower = person.text.lower()
                query_tokens = query_lower.split()
                person_tokens = person_lower.split()

                # Check if query tokens are partial matches or have similar prefixes
                matching_tokens = 0
                for q_token in query_tokens:
                    for p_token in person_tokens:
                        # Prefix matching (e.g., "Порошенк" matches "Порошенко")
                        if len(q_token) >= 3 and (p_token.startswith(q_token) or q_token.startswith(p_token)):
                            matching_tokens += 1
                            break
                        # Exact token match
                        elif q_token == p_token:
                            matching_tokens += 1
                            break

                # Calculate fuzzy match score
                if matching_tokens > 0:
                    match_ratio = matching_tokens / max(len(query_tokens), len(person_tokens))
                    if match_ratio >= 0.5:  # At least 50% tokens match
                        matched = True
                        # Reduce score for fuzzy matches
                        score = person.score * match_ratio * 0.8  # 80% of original score for fuzzy

            if matched:
                # Create a copy with updated score and search mode
                candidate = Candidate(
                    doc_id=person.doc_id,
                    score=score,
                    text=person.text,
                    entity_type=person.entity_type,
                    metadata=person.metadata,
                    search_mode=opts.search_mode,
                    match_fields=person.match_fields,
                    confidence=score
                )
                candidates.append(candidate)

        # Sort by score
        candidates.sort(key=lambda c: c.score, reverse=True)

        # Apply threshold filtering
        threshold = getattr(opts, 'threshold', 0.7)
        candidates = [c for c in candidates if c.score >= threshold]

        # Limit results
        limit = getattr(opts, 'top_k', 10)
        return candidates[:limit]

    async def search_similar(
        self,
        normalized_text: str,
        *,
        limit: int = 10,
        threshold: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Mock similarity search."""
        return {
            "query": normalized_text,
            "results": [],
            "total_hits": 0,
            "threshold": threshold,
            "search_type": "similarity_mock",
            "processing_time_ms": 1,
            "warnings": ["Similarity search not available - using mock"],
        }

    def get_metrics(self) -> SearchMetrics:
        """Get mock search metrics."""
        return SearchMetrics()

    def reset_metrics(self) -> None:
        """Reset mock search metrics."""
        pass
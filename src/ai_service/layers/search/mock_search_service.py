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
        """Load real sanctions data instead of hardcoded test records."""
        try:
            import json
            from pathlib import Path

            # Get path to data directory
            data_dir = Path(__file__).parent.parent.parent / "data"
            candidates = []

            # Load sanctioned persons
            persons_file = data_dir / "sanctioned_persons.json"
            if persons_file.exists():
                with open(persons_file, 'r', encoding='utf-8') as f:
                    persons_data = json.load(f)

                # Take first 500 persons for mock search (enough for testing, not too many)
                for i, person in enumerate(persons_data[:500]):
                    name = person.get('name', '').strip()
                    name_en = person.get('name_en', '').strip()

                    if name:  # Only add persons with valid names
                        candidate = Candidate(
                            doc_id=f"mock_person_{person.get('person_id', i)}",
                            score=0.95,  # High score for exact matches
                            text=name,
                            entity_type="person",
                            metadata={
                                "name": name,
                                "name_en": name_en,
                                "birthdate": person.get('birthdate', ''),
                                "dob": person.get('birthdate', ''),
                                "itn": person.get('itn', person.get('inn', '')),
                                "person_id": person.get('person_id', i),
                                "status": person.get('status', 1)
                            },
                            search_mode=SearchMode.AC,
                            match_fields=["name", "name_en"],
                            confidence=0.95
                        )
                        candidates.append(candidate)

            # Load sanctioned companies
            companies_file = data_dir / "sanctioned_companies.json"
            if companies_file.exists():
                with open(companies_file, 'r', encoding='utf-8') as f:
                    companies_data = json.load(f)

                # Take first 200 companies
                for i, company in enumerate(companies_data[:200]):
                    name = company.get('name', '').strip()
                    name_en = company.get('name_en', '').strip()

                    if name:  # Only add companies with valid names
                        candidate = Candidate(
                            doc_id=f"mock_company_{company.get('org_id', i)}",
                            score=0.90,  # Slightly lower score for companies
                            text=name,
                            entity_type="organization",
                            metadata={
                                "name": name,
                                "name_en": name_en,
                                "tax_number": company.get('tax_number', ''),
                                "edrpou": company.get('edrpou', ''),
                                "org_id": company.get('org_id', i),
                                "status": company.get('status', 1)
                            },
                            search_mode=SearchMode.AC,
                            match_fields=["name", "name_en"],
                            confidence=0.90
                        )
                        candidates.append(candidate)

            print(f"[OK] MockSearchService loaded {len(candidates)} real sanctions records")
            return candidates

        except Exception as e:
            print(f"[WARN] Failed to load real sanctions data: {e}, falling back to minimal hardcoded records")
            # Fallback to minimal hardcoded data
            return [
                Candidate(
                    doc_id="fallback_person_1",
                    score=0.95,
                    text="Ковриков Роман Валерійович",
                    entity_type="person",
                    metadata={
                        "name": "Ковриков Роман Валерійович",
                        "name_en": "Kovrykov Roman Valeriiovych",
                        "birthdate": "1976-08-09",
                        "itn": "782611846337",
                        "person_id": 32450,
                        "status": 1
                    },
                    search_mode=SearchMode.AC,
                    match_fields=["name", "name_en"],
                    confidence=0.95
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
                query_lower in (person.metadata.get("name_en") or "").lower() or
                query_lower in (person.metadata.get("itn") or "")):
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

        print(f"[CHECK] MockSearchService.find_candidates: query='{text}', mode={opts.search_mode}, threshold={opts.threshold}")

        for person in self._test_persons:
            score = 0.0
            matched = False

            print(f"  Checking person: {person.text}")

            # Exact substring matching
            exact_match = (query_lower in person.text.lower() or
                          query_lower in (person.metadata.get("name_en") or "").lower() or
                          query_lower in (person.metadata.get("itn") or ""))

            if exact_match:
                matched = True
                score = person.score
                print(f"    [OK] EXACT MATCH! Score: {score:.3f}")

            # Fuzzy matching for typos (e.g., "Порошенк" matches "Порошенко")
            else:
                mode_str = opts.search_mode.value if hasattr(opts.search_mode, 'value') else str(opts.search_mode)
                # Support both enum objects and string values for compatibility
                mode_matches = (opts.search_mode in [SearchMode.AC, SearchMode.VECTOR, SearchMode.HYBRID] or
                              mode_str in ["ac", "vector", "hybrid"])

                if mode_matches:
                    print(f"  Fuzzy matching for '{person.text}'")
                    person_lower = person.text.lower()
                    query_tokens = query_lower.split()
                    person_tokens = person_lower.split()

                    # Check if query tokens are partial matches or have similar prefixes
                    matching_tokens = 0
                    for q_token in query_tokens:
                        for p_token in person_tokens:
                            # Enhanced fuzzy matching (prefix, suffix, or significant overlap)
                            if len(q_token) >= 3 and len(p_token) >= 3:
                                # Prefix matching (e.g., "Порошенк" matches "Порошенко")
                                if p_token.startswith(q_token) or q_token.startswith(p_token):
                                    matching_tokens += 1
                                    break
                                # Common prefix matching (e.g., "Коврико" matches "Ковриков" - both start with "Коврик")
                                elif len(q_token) >= 5 and len(p_token) >= 5:
                                    common_prefix = 0
                                    for i in range(min(len(q_token), len(p_token))):
                                        if q_token[i] == p_token[i]:
                                            common_prefix += 1
                                        else:
                                            break
                                    if common_prefix >= 4:  # At least 4 matching characters from start
                                        matching_tokens += 1
                                        break
                            elif len(q_token) >= 3 and (p_token.startswith(q_token) or q_token.startswith(p_token)):
                                matching_tokens += 1
                                break
                            # Exact token match
                            elif q_token == p_token:
                                matching_tokens += 1
                                break

                    # Calculate fuzzy match score
                    if matching_tokens > 0:
                        match_ratio = matching_tokens / max(len(query_tokens), len(person_tokens))
                        print(f"    Tokens: {matching_tokens}/{max(len(query_tokens), len(person_tokens))}, ratio: {match_ratio:.3f}")
                        if match_ratio >= 0.5:  # At least 50% tokens match
                            matched = True
                            # Minimal penalty for fuzzy matches to ensure good matches pass threshold
                            score = person.score * match_ratio * 1.05  # 105% of original score for fuzzy (boost good matches)
                            print(f"    [OK] FUZZY MATCH! Score: {person.score} * {match_ratio:.3f} * 1.05 = {score:.3f}")

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
        print(f"  Pre-threshold: {len(candidates)} candidates")
        candidates = [c for c in candidates if c.score >= threshold]
        print(f"  Post-threshold ({threshold}): {len(candidates)} candidates")

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
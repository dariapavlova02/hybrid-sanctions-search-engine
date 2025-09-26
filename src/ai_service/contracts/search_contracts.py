"""
Search Contracts - Data models and interfaces for search layer integration.

Defines contracts for integrating HybridSearchService into the existing pipeline
without breaking existing layer contracts.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, TypedDict
from enum import Enum

from .base_contracts import NormalizationResult


class SearchCandidate(TypedDict):
    """Search candidate data structure"""
    id: str
    name: str
    tier: int
    score: float
    meta: Dict[str, Any]


class SearchMode(str, Enum):
    """Search modes for hybrid search"""
    AC = "ac"
    VECTOR = "vector"
    HYBRID = "hybrid"
    FALLBACK_AC = "fallback_ac"
    FALLBACK_VECTOR = "fallback_vector"


class SearchType(str, Enum):
    """Types of search results"""
    EXACT = "exact"
    PHRASE = "phrase"
    NGRAM = "ngram"
    WEAK = "weak"
    VECTOR = "vector"
    FUSION = "fusion"


@dataclass
class SearchOpts:
    """Options for search operations"""
    top_k: int = 50
    threshold: float = 0.7
    search_mode: SearchMode = SearchMode.HYBRID
    enable_escalation: bool = True
    entity_type: Optional[str] = None
    country_filter: Optional[str] = None
    meta_filters: Optional[Dict[str, Any]] = None


@dataclass
class ACScore:
    """AC search result with type and score"""
    entity_id: str
    entity_type: str
    normalized_name: str
    aliases: List[str]
    country: str
    dob: Optional[str]
    meta: Dict[str, Any]
    ac_score: float
    ac_type: SearchType
    matched_field: str
    matched_text: Optional[str] = None


@dataclass
class VectorHit:
    """Vector search result"""
    entity_id: str
    entity_type: str
    normalized_name: str
    aliases: List[str]
    country: str
    dob: Optional[str]
    meta: Dict[str, Any]
    vector_score: float
    matched_field: str = "name_vector"


@dataclass
class Candidate:
    """Final candidate with fusion score"""
    entity_id: str
    entity_type: str
    normalized_name: str
    aliases: List[str]
    country: str
    dob: Optional[str]
    meta: Dict[str, Any]
    final_score: float
    ac_score: float
    vector_score: float
    features: Dict[str, Any]
    search_type: SearchType


@dataclass
class SearchResult:
    """Complete search result"""
    candidates: List[Candidate]
    ac_results: List[ACScore]
    vector_results: List[VectorHit]
    search_metadata: Dict[str, Any]
    processing_time: float
    success: bool
    errors: List[str] = field(default_factory=list)


@dataclass
class SearchInfo:
    """Search information for Decision layer"""
    has_exact_matches: bool = False
    has_phrase_matches: bool = False
    has_ngram_matches: bool = False
    has_vector_matches: bool = False
    
    exact_confidence: float = 0.0
    phrase_confidence: float = 0.0
    ngram_confidence: float = 0.0
    vector_confidence: float = 0.0
    
    total_matches: int = 0
    high_confidence_matches: int = 0
    search_time: float = 0.0
    
    # Detailed results for debugging
    ac_results: List[ACScore] = field(default_factory=list)
    vector_results: List[VectorHit] = field(default_factory=list)
    fusion_candidates: List[Candidate] = field(default_factory=list)


@dataclass
class SearchMetrics:
    """Metrics for search operations"""
    ac_attempts: int = 0
    vector_attempts: int = 0
    ac_success: int = 0
    vector_success: int = 0
    ac_latency_p95: float = 0.0
    vector_latency_p95: float = 0.0
    hit_rate: float = 0.0
    escalation_rate: float = 0.0


class SearchServiceInterface:
    """Interface for search services"""
    
    async def find_candidates(
        self,
        normalized: NormalizationResult,
        text: str,
        opts: SearchOpts
    ) -> List[Candidate]:
        """
        Find candidates using hybrid search
        
        Args:
            normalized: Normalization result
            text: Original text
            opts: Search options
            
        Returns:
            List of candidates with fusion scores
            
        Raises:
            SearchServiceError: On search errors
            ElasticsearchConnectionError: On ES connection issues
            TimeoutError: On timeout
        """
        pass
    
    async def search_ac(
        self,
        candidates: List[str],
        entity_type: str,
        opts: SearchOpts
    ) -> List[ACScore]:
        """
        AC search in Elasticsearch
        
        Args:
            candidates: Candidate strings for search
            entity_type: Entity type (person/org)
            opts: Search options
            
        Returns:
            List of AC results with types and scores
        """
        pass
    
    async def search_vector(
        self,
        query_vector: List[float],
        entity_type: str,
        opts: SearchOpts
    ) -> List[VectorHit]:
        """
        Vector search in Elasticsearch
        
        Args:
            query_vector: 384-dimensional query vector
            entity_type: Entity type (person/org)
            opts: Search options
            
        Returns:
            List of Vector results with similarity scores
        """
        pass
    
    def get_metrics(self) -> SearchMetrics:
        """Get search metrics"""
        pass


class ElasticsearchACAdapterInterface:
    """Interface for Elasticsearch AC adapter"""
    
    async def search(
        self,
        candidates: List[str],
        entity_type: str,
        opts: SearchOpts
    ) -> List[ACScore]:
        """Search using AC methods in Elasticsearch"""
        pass


class ElasticsearchVectorAdapterInterface:
    """Interface for Elasticsearch Vector adapter"""
    
    async def search(
        self,
        query_vector: List[float],
        entity_type: str,
        opts: SearchOpts
    ) -> List[VectorHit]:
        """Search using kNN in Elasticsearch"""
        pass


# Utility functions for integration

def _get(obj, key, default=None):
    """
    Safely get attribute from object or dict

    Args:
        obj: Object or dict to get value from
        key: Key/attribute name
        default: Default value if key not found

    Returns:
        Value or default
    """
    if isinstance(obj, dict):
        return obj.get(key, default)
    else:
        return getattr(obj, key, default)


def extract_search_candidates(signals_result: Any) -> List[SearchCandidate]:
    """
    Extract candidate objects from Signals result
    
    Args:
        signals_result: Result from Signals layer
        
    Returns:
        List of SearchCandidate objects for search
    """
    candidates = []
    
    # Extract from persons
    persons = _get(signals_result, 'persons')
    if persons:
        for person in persons:
            normalized_name = _get(person, 'normalized_name')
            if normalized_name:
                candidates.append(SearchCandidate(
                    id=_get(person, 'id', ''),
                    name=normalized_name,
                    tier=_get(person, 'tier', 0),
                    score=_get(person, 'score', 0.0),
                    meta=_get(person, 'metadata', {})
                ))
            aliases = _get(person, 'aliases')
            if aliases:
                for alias in aliases:
                    candidates.append(SearchCandidate(
                        id=_get(person, 'id', ''),
                        name=alias,
                        tier=_get(person, 'tier', 0),
                        score=_get(person, 'score', 0.0),
                        meta=_get(person, 'metadata', {})
                    ))

    # Extract from organizations
    organizations = _get(signals_result, 'organizations')
    if organizations:
        for org in organizations:
            normalized_name = _get(org, 'normalized_name')
            if normalized_name:
                candidates.append(SearchCandidate(
                    id=_get(org, 'id', ''),
                    name=normalized_name,
                    tier=_get(org, 'tier', 0),
                    score=_get(org, 'score', 0.0),
                    meta=_get(org, 'metadata', {})
                ))
            aliases = _get(org, 'aliases')
            if aliases:
                for alias in aliases:
                    candidates.append(SearchCandidate(
                        id=_get(org, 'id', ''),
                        name=alias,
                        tier=_get(org, 'tier', 0),
                        score=_get(org, 'score', 0.0),
                        meta=_get(org, 'metadata', {})
                    ))
    
    # Remove duplicates based on id+name combination
    seen = set()
    unique_candidates = []
    for candidate in candidates:
        key = (candidate['id'], candidate['name'])
        if key not in seen:
            seen.add(key)
            unique_candidates.append(candidate)
    
    return unique_candidates


def create_search_info(search_result: SearchResult) -> SearchInfo:
    """
    Create SearchInfo from SearchResult for Decision layer

    Args:
        search_result: Complete search result

    Returns:
        SearchInfo for Decision layer
    """
    # If we have separate AC/vector results, use them
    if search_result.ac_results or search_result.vector_results:
        # Analyze AC results
        exact_matches = [r for r in search_result.ac_results if r.ac_type == SearchType.EXACT]
        phrase_matches = [r for r in search_result.ac_results if r.ac_type == SearchType.PHRASE]
        ngram_matches = [r for r in search_result.ac_results if r.ac_type == SearchType.NGRAM]

        # Calculate confidences
        exact_confidence = max([r.ac_score for r in exact_matches], default=0.0)
        phrase_confidence = max([r.ac_score for r in phrase_matches], default=0.0)
        ngram_confidence = max([r.ac_score for r in ngram_matches], default=0.0)
        vector_confidence = max([r.vector_score for r in search_result.vector_results], default=0.0)

        has_exact = len(exact_matches) > 0
        has_phrase = len(phrase_matches) > 0
        has_ngram = len(ngram_matches) > 0
        has_vector = len(search_result.vector_results) > 0

    # Otherwise, analyze candidates directly
    else:
        # Use candidates to determine match types based on search_type and scores
        exact_candidates = [c for c in search_result.candidates if c.search_type == SearchType.EXACT]
        phrase_candidates = [c for c in search_result.candidates if c.search_type == SearchType.PHRASE]
        ngram_candidates = [c for c in search_result.candidates if c.search_type == SearchType.NGRAM]
        vector_candidates = [c for c in search_result.candidates if c.search_type == SearchType.VECTOR]

        # Also check for high AC scores indicating exact matches (fallback heuristic)
        if not exact_candidates:
            exact_candidates = [c for c in search_result.candidates if c.ac_score >= 0.95]

        # Calculate confidences from candidates
        exact_confidence = max([c.ac_score for c in exact_candidates], default=0.0)
        phrase_confidence = max([c.ac_score for c in phrase_candidates], default=0.0)
        ngram_confidence = max([c.ac_score for c in ngram_candidates], default=0.0)
        vector_confidence = max([c.vector_score for c in vector_candidates], default=0.0)

        # If no vector candidates but we have candidates with vector scores, use them
        if not vector_candidates and search_result.candidates:
            vector_confidence = max([c.vector_score for c in search_result.candidates if c.vector_score > 0], default=0.0)

        has_exact = len(exact_candidates) > 0 or exact_confidence >= 0.95
        has_phrase = len(phrase_candidates) > 0 or phrase_confidence >= 0.8
        has_ngram = len(ngram_candidates) > 0 or ngram_confidence >= 0.6
        has_vector = vector_confidence > 0

    # Count high confidence matches - use strict thresholds based on search type
    high_confidence_matches = 0

    # Debug logging
    print(f"🔍 DEBUG: Processing {len(search_result.candidates)} candidates for high_confidence_matches")

    for i, c in enumerate(search_result.candidates):
        # Determine if this is a vector match based on search_mode or search_type
        is_vector_match = False

        # Check if it's a fuzzy result first - fuzzy should never be treated as vector
        is_fuzzy_result = False
        if hasattr(c, 'metadata') and isinstance(c.metadata, dict):
            if c.metadata.get('fuzzy_algorithm') is not None:
                is_fuzzy_result = True

        if is_fuzzy_result:
            is_vector_match = False  # Fuzzy is always non-vector
        elif hasattr(c, 'search_mode') and c.search_mode == 'vector':
            is_vector_match = True
        elif hasattr(c, 'search_type') and c.search_type in ['vector', 'VECTOR']:
            is_vector_match = True
        elif (hasattr(c, 'vector_score') and hasattr(c, 'ac_score') and c.vector_score > c.ac_score):
            is_vector_match = True

        # Use appropriate score
        if hasattr(c, 'final_score'):
            actual_score = c.final_score
        elif hasattr(c, 'score'):
            actual_score = getattr(c, 'score', 0.0)
        else:
            actual_score = 0.0

        # Debug candidate details
        print(f"   Candidate {i}: score={actual_score:.3f}, is_vector={is_vector_match}")
        if hasattr(c, 'search_mode'):
            print(f"      search_mode={c.search_mode}")
        if hasattr(c, 'search_type'):
            print(f"      search_type={c.search_type}")

        # Apply strict thresholds
        if is_vector_match:
            # Vector match - very high threshold to prevent false positives
            threshold = 0.90
            passes = actual_score >= threshold
            print(f"      Vector threshold: {actual_score:.3f} >= {threshold} = {passes}")
            if passes:
                high_confidence_matches += 1
        else:
            # AC/fuzzy/exact match - use appropriate threshold
            if is_fuzzy_result:
                threshold = 0.65  # Lower threshold for fuzzy matches
            else:
                threshold = 0.80  # Higher threshold for AC/exact matches
            passes = actual_score >= threshold
            print(f"      AC/Fuzzy threshold: {actual_score:.3f} >= {threshold} = {passes}")
            if passes:
                high_confidence_matches += 1

    print(f"🎯 FINAL: high_confidence_matches = {high_confidence_matches}")

    return SearchInfo(
        has_exact_matches=has_exact,
        has_phrase_matches=has_phrase,
        has_ngram_matches=has_ngram,
        has_vector_matches=has_vector,

        exact_confidence=exact_confidence,
        phrase_confidence=phrase_confidence,
        ngram_confidence=ngram_confidence,
        vector_confidence=vector_confidence,

        total_matches=len(search_result.candidates),
        high_confidence_matches=high_confidence_matches,
        search_time=search_result.processing_time,

        ac_results=search_result.ac_results,
        vector_results=search_result.vector_results,
        fusion_candidates=search_result.candidates
    )


# Search Tracing Support

@dataclass
class SearchTraceStep:
    """
    Detailed trace step for search operations.

    This provides comprehensive tracing for search integration,
    supporting both Aho-Corasick tier matching and fallback strategies.
    """
    stage: str = "search"
    rule: str = ""  # One of: ac_tier0, ac_tier1, ac_tier2, ac_tier3, knn_fallback, hybrid_rerank
    query: str = ""
    hits: List[Dict[str, Any]] = field(default_factory=list)
    took_ms: float = 0.0

    # Additional search-specific fields
    tier: Optional[str] = None  # T0, T1, T2, T3 for AC tiers
    confidence: float = 0.0
    method_fallback: bool = False
    total_results: int = 0
    filtered_results: int = 0

    # Performance metrics
    search_time_ms: float = 0.0
    rerank_time_ms: float = 0.0
    total_time_ms: float = 0.0

    def __post_init__(self):
        # Ensure took_ms is set from total_time_ms if not provided
        if self.took_ms == 0.0 and self.total_time_ms > 0.0:
            self.took_ms = self.total_time_ms

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging and serialization."""
        return {
            'stage': self.stage,
            'rule': self.rule,
            'query': self.query,
            'hits_count': len(self.hits),
            'took_ms': self.took_ms,
            'tier': self.tier,
            'confidence': self.confidence,
            'method_fallback': self.method_fallback,
            'total_results': self.total_results,
            'filtered_results': self.filtered_results,
            'search_time_ms': self.search_time_ms,
            'rerank_time_ms': self.rerank_time_ms,
            'total_time_ms': self.total_time_ms
        }


# Factory functions for common search trace scenarios

def create_ac_tier0_trace(query: str, patterns: List[str], took_ms: float) -> SearchTraceStep:
    """Create trace for AC Tier 0 (exact documents & IDs) match."""
    return SearchTraceStep(
        stage="search",
        rule="ac_tier0",
        query=query,
        hits=[{'pattern': p, 'score': 1.0, 'type': 'exact_document'} for p in patterns],
        took_ms=took_ms,
        tier="T0",
        confidence=0.95,
        total_results=len(patterns),
        filtered_results=len(patterns),
        search_time_ms=took_ms,
        total_time_ms=took_ms
    )


def create_knn_fallback_trace(query: str, results: List[Dict], took_ms: float) -> SearchTraceStep:
    """Create trace for KNN fallback when AC tiers don't match."""
    return SearchTraceStep(
        stage="search",
        rule="knn_fallback",
        query=query,
        hits=results,
        took_ms=took_ms,
        confidence=0.6,
        method_fallback=True,
        total_results=len(results),
        filtered_results=len(results),
        search_time_ms=took_ms,
        total_time_ms=took_ms
    )


def create_hybrid_rerank_trace(query: str, results: List[Dict], search_ms: float, rerank_ms: float) -> SearchTraceStep:
    """Create trace for hybrid search with reranking."""
    return SearchTraceStep(
        stage="search",
        rule="hybrid_rerank",
        query=query,
        hits=results,
        took_ms=search_ms + rerank_ms,
        confidence=0.85,
        total_results=len(results),
        filtered_results=len(results),
        search_time_ms=search_ms,
        rerank_time_ms=rerank_ms,
        total_time_ms=search_ms + rerank_ms
    )

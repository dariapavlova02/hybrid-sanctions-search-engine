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
    # Analyze AC results
    exact_matches = [r for r in search_result.ac_results if r.ac_type == SearchType.EXACT]
    phrase_matches = [r for r in search_result.ac_results if r.ac_type == SearchType.PHRASE]
    ngram_matches = [r for r in search_result.ac_results if r.ac_type == SearchType.NGRAM]
    
    # Calculate confidences
    exact_confidence = max([r.ac_score for r in exact_matches], default=0.0)
    phrase_confidence = max([r.ac_score for r in phrase_matches], default=0.0)
    ngram_confidence = max([r.ac_score for r in ngram_matches], default=0.0)
    vector_confidence = max([r.vector_score for r in search_result.vector_results], default=0.0)
    
    # Count high confidence matches
    high_confidence_matches = sum(1 for c in search_result.candidates if c.final_score >= 0.8)
    
    return SearchInfo(
        has_exact_matches=len(exact_matches) > 0,
        has_phrase_matches=len(phrase_matches) > 0,
        has_ngram_matches=len(ngram_matches) > 0,
        has_vector_matches=len(search_result.vector_results) > 0,
        
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

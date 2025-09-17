"""
Search trace models for tracking search pipeline execution.

This module provides data structures for tracing search operations
across different stages (AC, LEXICAL, SEMANTIC, HYBRID, RERANK, WATCHLIST).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple

# ============================================================================
# Search Stage Types
# ============================================================================

SearchStage = Literal["AC", "LEXICAL", "SEMANTIC", "HYBRID", "RERANK", "WATCHLIST"]

# ============================================================================
# Search Trace Models
# ============================================================================

@dataclass
class SearchTraceHit:
    """Represents a single search hit with metadata."""
    
    doc_id: str
    score: float
    rank: int
    source: SearchStage  # откуда пришёл кандидат
    signals: Dict[str, Any] = field(default_factory=dict)  # dob_match, id_match...


@dataclass
class SearchTraceStep:
    """Represents a single step in the search pipeline."""
    
    stage: SearchStage
    query: str
    topk: int
    took_ms: float
    hits: List[SearchTraceHit] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)  # thresholds, flags
    
    def __post_init__(self):
        """Round took_ms to 0.1ms precision for stable snapshots."""
        self.took_ms = round(self.took_ms, 1)
        # Sort hits deterministically: score desc, doc_id asc
        self.hits = self._sort_hits_deterministically()
    
    def _sort_hits_deterministically(self) -> List[SearchTraceHit]:
        """Sort hits deterministically for stable snapshots."""
        return sorted(self.hits, key=lambda h: (-h.score, h.doc_id))
    
    def limit_hits(self, max_hits: int = 10) -> None:
        """Limit hits to top N for stable snapshots."""
        if len(self.hits) > max_hits:
            self.hits = self.hits[:max_hits]
    
    def clean_meta_for_snapshot(self) -> None:
        """Remove volatile fields from meta data for stable snapshots."""
        volatile_fields = {
            'timestamp', 'created_at', 'updated_at', 'start_time', 'end_time',
            'random_seed', 'session_id', 'request_id', 'trace_id',
            'duration_ms', 'elapsed_time', 'processing_time'
        }
        
        cleaned_meta = {}
        for key, value in self.meta.items():
            if key.lower() not in volatile_fields:
                cleaned_meta[key] = value
        
        self.meta = cleaned_meta


@dataclass
class SearchTrace:
    """Main search trace container for tracking search pipeline execution."""
    
    enabled: bool
    steps: List[SearchTraceStep] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def add_step(self, step: SearchTraceStep) -> None:
        """Add a search step to the trace if enabled."""
        if self.enabled:
            self.steps.append(step)

    def note(self, msg: str) -> None:
        """Add a note to the trace if enabled."""
        if self.enabled:
            self.notes.append(msg)

    def get_stage_steps(self, stage: SearchStage) -> List[SearchTraceStep]:
        """Get all steps for a specific stage."""
        return [step for step in self.steps if step.stage == stage]

    def get_total_time_ms(self) -> float:
        """Get total execution time across all steps."""
        return sum(step.took_ms for step in self.steps)

    def get_hit_count(self) -> int:
        """Get total number of hits across all steps."""
        return sum(len(step.hits) for step in self.steps)
    
    def prepare_for_snapshot(self, max_hits: int = 3) -> None:
        """Prepare trace for stable snapshot comparison."""
        for step in self.steps:
            step.limit_hits(max_hits)
            step.clean_meta_for_snapshot()

    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary for serialization."""
        return {
            "enabled": self.enabled,
            "steps": [
                {
                    "stage": step.stage,
                    "query": step.query,
                    "topk": step.topk,
                    "took_ms": step.took_ms,
                    "hits": [
                        {
                            "doc_id": hit.doc_id,
                            "score": hit.score,
                            "rank": hit.rank,
                            "source": hit.source,
                            "signals": hit.signals
                        }
                        for hit in step.hits
                    ],
                    "meta": step.meta
                }
                for step in self.steps
            ],
            "notes": self.notes,
            "total_time_ms": self.get_total_time_ms(),
            "total_hits": self.get_hit_count()
        }


# ============================================================================
# Search Trace Builder
# ============================================================================

class SearchTraceBuilder:
    """Helper class for building search traces."""
    
    def __init__(self, enabled: bool = True):
        self.trace = SearchTrace(enabled=enabled)
    
    def add_ac_step(self, query: str, topk: int, took_ms: float, 
                   hits: List[SearchTraceHit], meta: Optional[Dict[str, Any]] = None) -> None:
        """Add an AC (Autocomplete) search step."""
        step = SearchTraceStep(
            stage="AC",
            query=query,
            topk=topk,
            took_ms=took_ms,
            hits=hits,
            meta=meta or {}
        )
        self.trace.add_step(step)
    
    def add_lexical_step(self, query: str, topk: int, took_ms: float,
                        hits: List[SearchTraceHit], meta: Optional[Dict[str, Any]] = None) -> None:
        """Add a lexical search step."""
        step = SearchTraceStep(
            stage="LEXICAL",
            query=query,
            topk=topk,
            took_ms=took_ms,
            hits=hits,
            meta=meta or {}
        )
        self.trace.add_step(step)
    
    def add_semantic_step(self, query: str, topk: int, took_ms: float,
                         hits: List[SearchTraceHit], meta: Optional[Dict[str, Any]] = None) -> None:
        """Add a semantic search step."""
        step = SearchTraceStep(
            stage="SEMANTIC",
            query=query,
            topk=topk,
            took_ms=took_ms,
            hits=hits,
            meta=meta or {}
        )
        self.trace.add_step(step)
    
    def add_hybrid_step(self, query: str, topk: int, took_ms: float,
                       hits: List[SearchTraceHit], meta: Optional[Dict[str, Any]] = None) -> None:
        """Add a hybrid search step."""
        step = SearchTraceStep(
            stage="HYBRID",
            query=query,
            topk=topk,
            took_ms=took_ms,
            hits=hits,
            meta=meta or {}
        )
        self.trace.add_step(step)
    
    def add_rerank_step(self, query: str, topk: int, took_ms: float,
                       hits: List[SearchTraceHit], meta: Optional[Dict[str, Any]] = None) -> None:
        """Add a reranking step."""
        step = SearchTraceStep(
            stage="RERANK",
            query=query,
            topk=topk,
            took_ms=took_ms,
            hits=hits,
            meta=meta or {}
        )
        self.trace.add_step(step)
    
    def add_watchlist_step(self, query: str, topk: int, took_ms: float,
                          hits: List[SearchTraceHit], meta: Optional[Dict[str, Any]] = None) -> None:
        """Add a watchlist search step."""
        step = SearchTraceStep(
            stage="WATCHLIST",
            query=query,
            topk=topk,
            took_ms=took_ms,
            hits=hits,
            meta=meta or {}
        )
        self.trace.add_step(step)
    
    def note(self, msg: str) -> None:
        """Add a note to the trace."""
        self.trace.note(msg)
    
    def build(self) -> SearchTrace:
        """Build and return the search trace."""
        return self.trace


# ============================================================================
# Search Hit Factory
# ============================================================================

def create_search_hit(doc_id: str, score: float, rank: int, source: SearchStage,
                     signals: Optional[Dict[str, Any]] = None) -> SearchTraceHit:
    """Factory function to create a SearchTraceHit."""
    return SearchTraceHit(
        doc_id=doc_id,
        score=score,
        rank=rank,
        source=source,
        signals=signals or {}
    )


def create_ac_hit(doc_id: str, score: float, rank: int, 
                 signals: Optional[Dict[str, Any]] = None) -> SearchTraceHit:
    """Create an AC search hit."""
    return create_search_hit(doc_id, score, rank, "AC", signals)


def create_lexical_hit(doc_id: str, score: float, rank: int,
                      signals: Optional[Dict[str, Any]] = None) -> SearchTraceHit:
    """Create a lexical search hit."""
    return create_search_hit(doc_id, score, rank, "LEXICAL", signals)


def create_semantic_hit(doc_id: str, score: float, rank: int,
                       signals: Optional[Dict[str, Any]] = None) -> SearchTraceHit:
    """Create a semantic search hit."""
    return create_search_hit(doc_id, score, rank, "SEMANTIC", signals)


def create_hybrid_hit(doc_id: str, score: float, rank: int,
                     signals: Optional[Dict[str, Any]] = None) -> SearchTraceHit:
    """Create a hybrid search hit."""
    return create_search_hit(doc_id, score, rank, "HYBRID", signals)


def create_rerank_hit(doc_id: str, score: float, rank: int,
                     signals: Optional[Dict[str, Any]] = None) -> SearchTraceHit:
    """Create a rerank search hit."""
    return create_search_hit(doc_id, score, rank, "RERANK", signals)


def create_watchlist_hit(doc_id: str, score: float, rank: int,
                        signals: Optional[Dict[str, Any]] = None) -> SearchTraceHit:
    """Create a watchlist search hit."""
    return create_search_hit(doc_id, score, rank, "WATCHLIST", signals)

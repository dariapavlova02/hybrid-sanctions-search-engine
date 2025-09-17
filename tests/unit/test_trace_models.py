"""
Unit tests for search trace models.
"""

import pytest
from src.ai_service.contracts.trace_models import (
    SearchStage,
    SearchTrace,
    SearchTraceBuilder,
    SearchTraceHit,
    SearchTraceStep,
    create_ac_hit,
    create_hybrid_hit,
    create_lexical_hit,
    create_rerank_hit,
    create_search_hit,
    create_semantic_hit,
    create_watchlist_hit,
)


class TestSearchTraceHit:
    """Test SearchTraceHit functionality."""
    
    def test_create_search_hit(self):
        """Test creating a search hit."""
        hit = create_search_hit(
            doc_id="doc123",
            score=0.95,
            rank=1,
            source="AC",
            signals={"dob_match": True, "id_match": False}
        )
        
        assert hit.doc_id == "doc123"
        assert hit.score == 0.95
        assert hit.rank == 1
        assert hit.source == "AC"
        assert hit.signals == {"dob_match": True, "id_match": False}
    
    def test_create_ac_hit(self):
        """Test creating an AC hit."""
        hit = create_ac_hit("doc456", 0.88, 2, {"name_match": True})
        
        assert hit.doc_id == "doc456"
        assert hit.score == 0.88
        assert hit.rank == 2
        assert hit.source == "AC"
        assert hit.signals == {"name_match": True}
    
    def test_create_lexical_hit(self):
        """Test creating a lexical hit."""
        hit = create_lexical_hit("doc789", 0.92, 1)
        
        assert hit.doc_id == "doc789"
        assert hit.score == 0.92
        assert hit.rank == 1
        assert hit.source == "LEXICAL"
        assert hit.signals == {}
    
    def test_create_semantic_hit(self):
        """Test creating a semantic hit."""
        hit = create_semantic_hit("doc101", 0.87, 3, {"similarity": 0.87})
        
        assert hit.doc_id == "doc101"
        assert hit.score == 0.87
        assert hit.rank == 3
        assert hit.source == "SEMANTIC"
        assert hit.signals == {"similarity": 0.87}
    
    def test_create_hybrid_hit(self):
        """Test creating a hybrid hit."""
        hit = create_hybrid_hit("doc202", 0.91, 1)
        
        assert hit.doc_id == "doc202"
        assert hit.score == 0.91
        assert hit.rank == 1
        assert hit.source == "HYBRID"
        assert hit.signals == {}
    
    def test_create_rerank_hit(self):
        """Test creating a rerank hit."""
        hit = create_rerank_hit("doc303", 0.89, 2)
        
        assert hit.doc_id == "doc303"
        assert hit.score == 0.89
        assert hit.rank == 2
        assert hit.source == "RERANK"
        assert hit.signals == {}
    
    def test_create_watchlist_hit(self):
        """Test creating a watchlist hit."""
        hit = create_watchlist_hit("doc404", 0.93, 1, {"watchlist_match": True})
        
        assert hit.doc_id == "doc404"
        assert hit.score == 0.93
        assert hit.rank == 1
        assert hit.source == "WATCHLIST"
        assert hit.signals == {"watchlist_match": True}


class TestSearchTraceStep:
    """Test SearchTraceStep functionality."""
    
    def test_create_search_trace_step(self):
        """Test creating a search trace step."""
        hits = [
            create_ac_hit("doc1", 0.95, 1),
            create_ac_hit("doc2", 0.88, 2)
        ]
        
        step = SearchTraceStep(
            stage="AC",
            query="test query",
            topk=10,
            took_ms=15.5,
            hits=hits,
            meta={"threshold": 0.8, "flags": ["debug"]}
        )
        
        assert step.stage == "AC"
        assert step.query == "test query"
        assert step.topk == 10
        assert step.took_ms == 15.5
        assert len(step.hits) == 2
        assert step.meta == {"threshold": 0.8, "flags": ["debug"]}


class TestSearchTrace:
    """Test SearchTrace functionality."""
    
    def test_create_enabled_trace(self):
        """Test creating an enabled trace."""
        trace = SearchTrace(enabled=True)
        
        assert trace.enabled is True
        assert trace.steps == []
        assert trace.notes == []
    
    def test_create_disabled_trace(self):
        """Test creating a disabled trace."""
        trace = SearchTrace(enabled=False)
        
        assert trace.enabled is False
        assert trace.steps == []
        assert trace.notes == []
    
    def test_add_step_enabled(self):
        """Test adding a step when trace is enabled."""
        trace = SearchTrace(enabled=True)
        step = SearchTraceStep(
            stage="AC",
            query="test",
            topk=5,
            took_ms=10.0
        )
        
        trace.add_step(step)
        
        assert len(trace.steps) == 1
        assert trace.steps[0] == step
    
    def test_add_step_disabled(self):
        """Test adding a step when trace is disabled."""
        trace = SearchTrace(enabled=False)
        step = SearchTraceStep(
            stage="AC",
            query="test",
            topk=5,
            took_ms=10.0
        )
        
        trace.add_step(step)
        
        assert len(trace.steps) == 0
    
    def test_note_enabled(self):
        """Test adding a note when trace is enabled."""
        trace = SearchTrace(enabled=True)
        
        trace.note("Test note")
        
        assert len(trace.notes) == 1
        assert trace.notes[0] == "Test note"
    
    def test_note_disabled(self):
        """Test adding a note when trace is disabled."""
        trace = SearchTrace(enabled=False)
        
        trace.note("Test note")
        
        assert len(trace.notes) == 0
    
    def test_get_stage_steps(self):
        """Test getting steps for a specific stage."""
        trace = SearchTrace(enabled=True)
        
        ac_step = SearchTraceStep("AC", "query1", 5, 10.0)
        lexical_step = SearchTraceStep("LEXICAL", "query2", 5, 15.0)
        ac_step2 = SearchTraceStep("AC", "query3", 5, 12.0)
        
        trace.add_step(ac_step)
        trace.add_step(lexical_step)
        trace.add_step(ac_step2)
        
        ac_steps = trace.get_stage_steps("AC")
        lexical_steps = trace.get_stage_steps("LEXICAL")
        
        assert len(ac_steps) == 2
        assert len(lexical_steps) == 1
        assert ac_steps[0] == ac_step
        assert ac_steps[1] == ac_step2
        assert lexical_steps[0] == lexical_step
    
    def test_get_total_time_ms(self):
        """Test getting total execution time."""
        trace = SearchTrace(enabled=True)
        
        trace.add_step(SearchTraceStep("AC", "query1", 5, 10.0))
        trace.add_step(SearchTraceStep("LEXICAL", "query2", 5, 15.0))
        trace.add_step(SearchTraceStep("SEMANTIC", "query3", 5, 12.0))
        
        assert trace.get_total_time_ms() == 37.0
    
    def test_get_hit_count(self):
        """Test getting total hit count."""
        trace = SearchTrace(enabled=True)
        
        step1 = SearchTraceStep("AC", "query1", 5, 10.0)
        step1.hits = [create_ac_hit("doc1", 0.9, 1), create_ac_hit("doc2", 0.8, 2)]
        
        step2 = SearchTraceStep("LEXICAL", "query2", 5, 15.0)
        step2.hits = [create_lexical_hit("doc3", 0.85, 1)]
        
        trace.add_step(step1)
        trace.add_step(step2)
        
        assert trace.get_hit_count() == 3
    
    def test_to_dict(self):
        """Test converting trace to dictionary."""
        trace = SearchTrace(enabled=True)
        
        step = SearchTraceStep(
            stage="AC",
            query="test query",
            topk=5,
            took_ms=10.0,
            hits=[create_ac_hit("doc1", 0.9, 1, {"match": True})],
            meta={"threshold": 0.8}
        )
        
        trace.add_step(step)
        trace.note("Test note")
        
        result = trace.to_dict()
        
        assert result["enabled"] is True
        assert len(result["steps"]) == 1
        assert result["steps"][0]["stage"] == "AC"
        assert result["steps"][0]["query"] == "test query"
        assert result["steps"][0]["topk"] == 5
        assert result["steps"][0]["took_ms"] == 10.0
        assert len(result["steps"][0]["hits"]) == 1
        assert result["steps"][0]["hits"][0]["doc_id"] == "doc1"
        assert result["steps"][0]["hits"][0]["score"] == 0.9
        assert result["steps"][0]["hits"][0]["rank"] == 1
        assert result["steps"][0]["hits"][0]["source"] == "AC"
        assert result["steps"][0]["hits"][0]["signals"] == {"match": True}
        assert result["steps"][0]["meta"] == {"threshold": 0.8}
        assert result["notes"] == ["Test note"]
        assert result["total_time_ms"] == 10.0
        assert result["total_hits"] == 1


class TestSearchTraceBuilder:
    """Test SearchTraceBuilder functionality."""
    
    def test_create_builder(self):
        """Test creating a trace builder."""
        builder = SearchTraceBuilder(enabled=True)
        
        assert builder.trace.enabled is True
        assert len(builder.trace.steps) == 0
        assert len(builder.trace.notes) == 0
    
    def test_add_ac_step(self):
        """Test adding an AC step."""
        builder = SearchTraceBuilder(enabled=True)
        hits = [create_ac_hit("doc1", 0.9, 1)]
        
        builder.add_ac_step("test query", 5, 10.0, hits, {"threshold": 0.8})
        
        assert len(builder.trace.steps) == 1
        step = builder.trace.steps[0]
        assert step.stage == "AC"
        assert step.query == "test query"
        assert step.topk == 5
        assert step.took_ms == 10.0
        assert len(step.hits) == 1
        assert step.meta == {"threshold": 0.8}
    
    def test_add_lexical_step(self):
        """Test adding a lexical step."""
        builder = SearchTraceBuilder(enabled=True)
        hits = [create_lexical_hit("doc1", 0.85, 1)]
        
        builder.add_lexical_step("test query", 10, 15.0, hits)
        
        assert len(builder.trace.steps) == 1
        step = builder.trace.steps[0]
        assert step.stage == "LEXICAL"
        assert step.query == "test query"
        assert step.topk == 10
        assert step.took_ms == 15.0
        assert len(step.hits) == 1
        assert step.meta == {}
    
    def test_add_semantic_step(self):
        """Test adding a semantic step."""
        builder = SearchTraceBuilder(enabled=True)
        hits = [create_semantic_hit("doc1", 0.88, 1)]
        
        builder.add_semantic_step("test query", 8, 12.0, hits)
        
        assert len(builder.trace.steps) == 1
        step = builder.trace.steps[0]
        assert step.stage == "SEMANTIC"
        assert step.query == "test query"
        assert step.topk == 8
        assert step.took_ms == 12.0
        assert len(step.hits) == 1
    
    def test_add_hybrid_step(self):
        """Test adding a hybrid step."""
        builder = SearchTraceBuilder(enabled=True)
        hits = [create_hybrid_hit("doc1", 0.92, 1)]
        
        builder.add_hybrid_step("test query", 6, 18.0, hits)
        
        assert len(builder.trace.steps) == 1
        step = builder.trace.steps[0]
        assert step.stage == "HYBRID"
        assert step.query == "test query"
        assert step.topk == 6
        assert step.took_ms == 18.0
        assert len(step.hits) == 1
    
    def test_add_rerank_step(self):
        """Test adding a rerank step."""
        builder = SearchTraceBuilder(enabled=True)
        hits = [create_rerank_hit("doc1", 0.87, 1)]
        
        builder.add_rerank_step("test query", 4, 8.0, hits)
        
        assert len(builder.trace.steps) == 1
        step = builder.trace.steps[0]
        assert step.stage == "RERANK"
        assert step.query == "test query"
        assert step.topk == 4
        assert step.took_ms == 8.0
        assert len(step.hits) == 1
    
    def test_add_watchlist_step(self):
        """Test adding a watchlist step."""
        builder = SearchTraceBuilder(enabled=True)
        hits = [create_watchlist_hit("doc1", 0.94, 1)]
        
        builder.add_watchlist_step("test query", 3, 20.0, hits)
        
        assert len(builder.trace.steps) == 1
        step = builder.trace.steps[0]
        assert step.stage == "WATCHLIST"
        assert step.query == "test query"
        assert step.topk == 3
        assert step.took_ms == 20.0
        assert len(step.hits) == 1
    
    def test_note(self):
        """Test adding a note."""
        builder = SearchTraceBuilder(enabled=True)
        
        builder.note("Test note")
        
        assert len(builder.trace.notes) == 1
        assert builder.trace.notes[0] == "Test note"
    
    def test_build(self):
        """Test building the trace."""
        builder = SearchTraceBuilder(enabled=True)
        hits = [create_ac_hit("doc1", 0.9, 1)]
        
        builder.add_ac_step("test query", 5, 10.0, hits)
        builder.note("Test note")
        
        trace = builder.build()
        
        assert trace.enabled is True
        assert len(trace.steps) == 1
        assert len(trace.notes) == 1
        assert trace.notes[0] == "Test note"
    
    def test_disabled_builder(self):
        """Test builder when disabled."""
        builder = SearchTraceBuilder(enabled=False)
        hits = [create_ac_hit("doc1", 0.9, 1)]
        
        builder.add_ac_step("test query", 5, 10.0, hits)
        builder.note("Test note")
        
        trace = builder.build()
        
        assert trace.enabled is False
        assert len(trace.steps) == 0
        assert len(trace.notes) == 0

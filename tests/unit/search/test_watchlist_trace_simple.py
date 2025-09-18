"""
Simple unit tests for watchlist index service trace integration.
Tests the trace functionality without heavy dependencies.
"""

import pytest
from unittest.mock import Mock, patch
from src.ai_service.contracts.trace_models import SearchTrace, SearchTraceHit, SearchTraceStep


class TestWatchlistTraceSimple:
    """Test SearchTrace functionality for watchlist integration."""
    
    def test_search_trace_hit_creation(self):
        """Test creating SearchTraceHit for watchlist results."""
        hit = SearchTraceHit(
            doc_id="doc123",
            score=0.95,
            rank=1,
            source="LEXICAL",
            signals={"name_match": True, "dob_match": False}
        )
        
        assert hit.doc_id == "doc123"
        assert hit.score == 0.95
        assert hit.rank == 1
        assert hit.source == "LEXICAL"
        assert hit.signals == {"name_match": True, "dob_match": False}
    
    def test_search_trace_step_creation(self):
        """Test creating SearchTraceStep for watchlist search."""
        hits = [
            SearchTraceHit("doc1", 0.9, 1, "LEXICAL"),
            SearchTraceHit("doc2", 0.8, 2, "LEXICAL")
        ]
        
        step = SearchTraceStep(
            stage="LEXICAL",
            query="test query",
            topk=10,
            took_ms=15.5,
            hits=hits,
            meta={
                "overlay_id": "overlay_123",
                "active_id": None,
                "search_type": "overlay"
            }
        )
        
        assert step.stage == "LEXICAL"
        assert step.query == "test query"
        assert step.topk == 10
        assert step.took_ms == 15.5
        assert len(step.hits) == 2
        assert step.meta["overlay_id"] == "overlay_123"
        assert step.meta["search_type"] == "overlay"
    
    def test_search_trace_with_overlay_and_active_steps(self):
        """Test SearchTrace with overlay and active search steps."""
        trace = SearchTrace(enabled=True)
        
        # Add overlay step
        overlay_hits = [SearchTraceHit("doc1", 0.9, 1, "LEXICAL")]
        overlay_step = SearchTraceStep(
            stage="LEXICAL",
            query="test query",
            topk=10,
            took_ms=12.0,
            hits=overlay_hits,
            meta={
                "overlay_id": "overlay_123",
                "active_id": None,
                "search_type": "overlay"
            }
        )
        trace.add_step(overlay_step)
        
        # Add active step
        active_hits = [SearchTraceHit("doc2", 0.8, 1, "LEXICAL")]
        active_step = SearchTraceStep(
            stage="LEXICAL",
            query="test query",
            topk=10,
            took_ms=8.0,
            hits=active_hits,
            meta={
                "overlay_id": None,
                "active_id": "active_456",
                "search_type": "active"
            }
        )
        trace.add_step(active_step)
        
        # Add rerank step
        rerank_hits = [
            SearchTraceHit("doc1", 0.9, 1, "RERANK"),
            SearchTraceHit("doc2", 0.8, 2, "RERANK")
        ]
        rerank_step = SearchTraceStep(
            stage="RERANK",
            query="test query",
            topk=10,
            took_ms=2.0,
            hits=rerank_hits,
            meta={
                "total_candidates": 2,
                "final_results": 2,
                "merge_strategy": "max_score"
            }
        )
        trace.add_step(rerank_step)
        
        # Check trace
        assert len(trace.steps) == 3
        
        # Check overlay step
        assert trace.steps[0].stage == "LEXICAL"
        assert trace.steps[0].meta["search_type"] == "overlay"
        assert trace.steps[0].took_ms == 12.0
        
        # Check active step
        assert trace.steps[1].stage == "LEXICAL"
        assert trace.steps[1].meta["search_type"] == "active"
        assert trace.steps[1].took_ms == 8.0
        
        # Check rerank step
        assert trace.steps[2].stage == "RERANK"
        assert trace.steps[2].meta["merge_strategy"] == "max_score"
        assert trace.steps[2].took_ms == 2.0
        
        # Check total time
        assert trace.get_total_time_ms() == 22.0
        
        # Check hit count
        assert trace.get_hit_count() == 4  # 1 + 1 + 2
    
    def test_search_trace_with_notes(self):
        """Test SearchTrace with notes for edge cases."""
        trace = SearchTrace(enabled=True)
        
        # Add notes for different scenarios
        trace.note("Watchlist index not ready - empty index")
        trace.note("No overlay index available")
        trace.note("Watchlist search completed: 2 results from 3 candidates")
        
        # Check notes
        assert len(trace.notes) == 3
        assert "empty index" in trace.notes[0]
        assert "No overlay index available" in trace.notes[1]
        assert "search completed" in trace.notes[2]
    
    def test_search_trace_disabled(self):
        """Test SearchTrace when disabled."""
        trace = SearchTrace(enabled=False)
        
        # Try to add steps and notes
        hit = SearchTraceHit("doc1", 0.9, 1, "LEXICAL")
        step = SearchTraceStep("LEXICAL", "query", 10, 5.0, [hit])
        trace.add_step(step)
        trace.note("This should not be added")
        
        # Check that nothing was added
        assert len(trace.steps) == 0
        assert len(trace.notes) == 0
    
    def test_search_trace_error_handling(self):
        """Test SearchTrace with error handling."""
        trace = SearchTrace(enabled=True)
        
        # Add error notes
        trace.note("Watchlist search failed: Connection timeout")
        trace.note("Failed to get document doc123: Index not found")
        trace.note("Failed to reload snapshot from /path: Permission denied")
        
        # Check error notes
        assert len(trace.notes) == 3
        assert "search failed" in trace.notes[0]
        assert "Failed to get document" in trace.notes[1]
        assert "Failed to reload snapshot" in trace.notes[2]
    
    def test_search_trace_serialization(self):
        """Test SearchTrace serialization to dictionary."""
        trace = SearchTrace(enabled=True)
        
        # Add a step
        hit = SearchTraceHit("doc1", 0.9, 1, "LEXICAL", {"match": True})
        step = SearchTraceStep(
            stage="LEXICAL",
            query="test query",
            topk=10,
            took_ms=15.0,
            hits=[hit],
            meta={"overlay_id": "overlay_123"}
        )
        trace.add_step(step)
        trace.note("Test note")
        
        # Serialize to dict
        result = trace.to_dict()
        
        # Check structure
        assert result["enabled"] is True
        assert len(result["steps"]) == 1
        assert len(result["notes"]) == 1
        assert result["total_time_ms"] == 15.0
        assert result["total_hits"] == 1
        
        # Check step structure
        step_dict = result["steps"][0]
        assert step_dict["stage"] == "LEXICAL"
        assert step_dict["query"] == "test query"
        assert step_dict["topk"] == 10
        assert step_dict["took_ms"] == 15.0
        assert len(step_dict["hits"]) == 1
        assert step_dict["hits"][0]["doc_id"] == "doc1"
        assert step_dict["hits"][0]["score"] == 0.9
        assert step_dict["hits"][0]["rank"] == 1
        assert step_dict["hits"][0]["source"] == "LEXICAL"
        assert step_dict["hits"][0]["signals"] == {"match": True}
        assert step_dict["meta"]["overlay_id"] == "overlay_123"
        
        # Check notes
        assert result["notes"] == ["Test note"]
    
    def test_watchlist_search_flow_simulation(self):
        """Test simulating the complete watchlist search flow."""
        trace = SearchTrace(enabled=True)
        
        # Simulate overlay search
        overlay_results = [("doc1", 0.9), ("doc2", 0.8)]
        overlay_hits = [
            SearchTraceHit(doc_id, score, rank, "LEXICAL")
            for rank, (doc_id, score) in enumerate(overlay_results, 1)
        ]
        
        trace.add_step(SearchTraceStep(
            stage="LEXICAL",
            query="test query",
            topk=10,
            took_ms=12.0,
            hits=overlay_hits,
            meta={"overlay_id": "overlay_123", "search_type": "overlay"}
        ))
        
        # Simulate active search
        active_results = [("doc2", 0.85), ("doc3", 0.7)]
        active_hits = [
            SearchTraceHit(doc_id, score, rank, "LEXICAL")
            for rank, (doc_id, score) in enumerate(active_results, 1)
        ]
        
        trace.add_step(SearchTraceStep(
            stage="LEXICAL",
            query="test query",
            topk=10,
            took_ms=8.0,
            hits=active_hits,
            meta={"active_id": "active_456", "search_type": "active"}
        ))
        
        # Simulate merge and rerank
        # doc1: 0.9 (overlay only)
        # doc2: max(0.8, 0.85) = 0.85 (both)
        # doc3: 0.7 (active only)
        merged_results = [("doc1", 0.9), ("doc2", 0.85), ("doc3", 0.7)]
        rerank_hits = [
            SearchTraceHit(doc_id, score, rank, "RERANK")
            for rank, (doc_id, score) in enumerate(merged_results, 1)
        ]
        
        trace.add_step(SearchTraceStep(
            stage="RERANK",
            query="test query",
            topk=10,
            took_ms=2.0,
            hits=rerank_hits,
            meta={
                "total_candidates": 3,
                "final_results": 3,
                "merge_strategy": "max_score"
            }
        ))
        
        trace.note("Watchlist search completed: 3 results from 3 candidates")
        
        # Verify the complete flow
        assert len(trace.steps) == 3
        assert trace.get_total_time_ms() == 22.0
        assert trace.get_hit_count() == 7  # 2 + 2 + 3
        assert len(trace.notes) == 1
        
        # Check that doc2 appears in both overlay and active steps
        overlay_doc_ids = [hit.doc_id for hit in trace.steps[0].hits]
        active_doc_ids = [hit.doc_id for hit in trace.steps[1].hits]
        assert "doc2" in overlay_doc_ids
        assert "doc2" in active_doc_ids
        
        # Check that final rerank has all unique docs
        rerank_doc_ids = [hit.doc_id for hit in trace.steps[2].hits]
        assert set(rerank_doc_ids) == {"doc1", "doc2", "doc3"}

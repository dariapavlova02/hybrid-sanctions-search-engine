"""
Unit tests for SearchTrace contracts and behavior.

Tests SearchTrace performance overhead, serialization, and edge cases.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

from src.ai_service.contracts.trace_models import (
    SearchTrace,
    SearchTraceBuilder,
    SearchTraceStep,
    SearchTraceHit,
    SearchStage,
    create_lexical_hit,
    create_semantic_hit,
    create_hybrid_hit,
)
from src.ai_service.contracts.decision_contracts import DecisionOutput, RiskLevel
from src.ai_service.core.decision_engine import DecisionEngine
from src.ai_service.core.unified_orchestrator import UnifiedOrchestrator
from src.ai_service.layers.embeddings.indexing.watchlist_index_service import WatchlistIndexService


class TestSearchTraceContracts:
    """Test SearchTrace contracts and behavior."""

    def test_debug_trace_false_no_overhead(self):
        """Test that debug_trace=False has minimal overhead."""
        # Create disabled trace
        trace = SearchTrace(enabled=False)
        
        # Measure time for operations
        start_time = time.perf_counter()
        
        # Add many steps and notes
        for i in range(1000):
            trace.add_step(SearchTraceStep(
                stage="LEXICAL",
                query=f"test_{i}",
                topk=10,
                took_ms=1.0,
                hits=[create_lexical_hit(f"doc_{i}", 0.9, 1)]
            ))
            trace.note(f"Test note {i}")
        
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        
        # Should be very fast (under 2ms for 1000 operations, accounting for rounding)
        assert elapsed < 0.002, f"Disabled trace operations took {elapsed:.6f}s, expected < 0.002s"
        
        # No steps or notes should be recorded
        assert len(trace.steps) == 0
        assert len(trace.notes) == 0

    def test_debug_trace_true_records_steps(self):
        """Test that debug_trace=True records all steps."""
        # Create enabled trace
        trace = SearchTrace(enabled=True)
        
        # Add steps
        trace.add_step(SearchTraceStep(
            stage="LEXICAL",
            query="test query",
            topk=10,
            took_ms=5.0,
            hits=[create_lexical_hit("doc1", 0.9, 1)]
        ))
        
        trace.add_step(SearchTraceStep(
            stage="SEMANTIC",
            query="test query",
            topk=10,
            took_ms=3.0,
            hits=[create_semantic_hit("doc2", 0.8, 1)]
        ))
        
        trace.note("Test note")
        
        # Verify steps and notes are recorded
        assert len(trace.steps) == 2
        assert len(trace.notes) == 1
        
        # Verify step details
        assert trace.steps[0].stage == "LEXICAL"
        assert trace.steps[0].query == "test query"
        assert trace.steps[0].took_ms == 5.0
        assert len(trace.steps[0].hits) == 1
        assert trace.steps[0].hits[0].doc_id == "doc1"
        assert trace.steps[0].hits[0].source == "LEXICAL"
        
        assert trace.steps[1].stage == "SEMANTIC"
        assert trace.steps[1].hits[0].source == "SEMANTIC"
        
        assert trace.notes[0] == "Test note"

    def test_search_trace_builder(self):
        """Test SearchTraceBuilder functionality."""
        builder = SearchTraceBuilder(enabled=True)
        
        # Add steps using builder methods
        builder.add_lexical_step(
            query="test",
            topk=5,
            took_ms=2.0,
            hits=[create_lexical_hit("doc1", 0.9, 1)]
        )
        
        builder.add_semantic_step(
            query="test",
            topk=5,
            took_ms=1.5,
            hits=[create_semantic_hit("doc2", 0.8, 1)]
        )
        
        builder.add_hybrid_step(
            query="test",
            topk=5,
            took_ms=3.0,
            hits=[create_hybrid_hit("doc3", 0.95, 1)]
        )
        
        builder.note("Builder test note")
        
        # Build trace
        trace = builder.build()
        
        # Verify trace
        assert trace.enabled is True
        assert len(trace.steps) == 3
        assert len(trace.notes) == 1
        
        # Verify step stages
        stages = [step.stage for step in trace.steps]
        assert "LEXICAL" in stages
        assert "SEMANTIC" in stages
        assert "HYBRID" in stages

    def test_serialization_preserves_contract(self):
        """Test that SearchTrace serialization preserves Decision.audit contract."""
        # Create mock decision output
        decision_output = DecisionOutput(
            risk=RiskLevel.LOW,
            score=0.7,
            reasons=["test_reason"],
            details={
                "smartfilter_should_process": True,
                "person_confidence": 0.8,
                "org_confidence": 0.6,
                "similarity_cos_top": 0.9,
                "date_match": True,
                "id_match": False
            }
        )
        
        # Create search trace
        trace = SearchTrace(enabled=True)
        trace.add_step(SearchTraceStep(
            stage="LEXICAL",
            query="test",
            topk=10,
            took_ms=5.0,
            hits=[create_lexical_hit("doc1", 0.9, 1)]
        ))
        trace.note("Test trace note")
        
        # Add search trace to decision details
        decision_output.details["search_trace"] = trace.to_dict()
        
        # Verify original audit keys are preserved
        expected_keys = {
            "smartfilter_should_process",
            "person_confidence", 
            "org_confidence",
            "similarity_cos_top",
            "date_match",
            "id_match",
            "search_trace"  # New key added
        }
        
        actual_keys = set(decision_output.details.keys())
        assert actual_keys == expected_keys
        
        # Verify search_trace structure
        search_trace_data = decision_output.details["search_trace"]
        assert search_trace_data["enabled"] is True
        assert len(search_trace_data["steps"]) == 1
        assert len(search_trace_data["notes"]) == 1
        assert search_trace_data["steps"][0]["stage"] == "LEXICAL"

    def test_empty_index_trace_notes(self):
        """Test that empty index scenarios add trace notes."""
        trace = SearchTrace(enabled=True)
        
        # Simulate empty index scenario
        trace.note("Empty index - no documents found")
        trace.note("Fallback to vector search")
        
        # Verify notes are recorded
        assert len(trace.notes) == 2
        assert "Empty index" in trace.notes[0]
        assert "Fallback to vector search" in trace.notes[1]

    def test_exception_trace_notes(self):
        """Test that exceptions add trace notes."""
        trace = SearchTrace(enabled=True)
        
        # Simulate exception scenarios
        trace.note("Exception in lexical search: Connection timeout")
        trace.note("Exception in semantic search: Model not loaded")
        trace.note("Fallback to cached results")
        
        # Verify exception notes are recorded
        assert len(trace.notes) == 3
        assert "Exception in lexical search" in trace.notes[0]
        assert "Exception in semantic search" in trace.notes[1]
        assert "Fallback to cached results" in trace.notes[2]

    def test_trace_step_metadata(self):
        """Test that trace steps include proper metadata."""
        trace = SearchTrace(enabled=True)
        
        # Add step with metadata
        meta = {
            "overlay_id": "overlay_123",
            "active_id": "active_456",
            "min_sim": 0.7,
            "consensus_boost": 1.2
        }
        
        trace.add_step(SearchTraceStep(
            stage="HYBRID",
            query="test query",
            topk=10,
            took_ms=5.0,
            hits=[create_hybrid_hit("doc1", 0.9, 1)],
            meta=meta
        ))
        
        # Verify metadata is preserved
        assert len(trace.steps) == 1
        step = trace.steps[0]
        assert step.meta == meta
        assert step.meta["overlay_id"] == "overlay_123"
        assert step.meta["active_id"] == "active_456"
        assert step.meta["min_sim"] == 0.7
        assert step.meta["consensus_boost"] == 1.2

    def test_trace_hit_signals(self):
        """Test that trace hits include proper signals."""
        # Create hit with signals
        signals = {
            "tier": "T0",
            "dob_match": True,
            "id_match": False,
            "confidence": 0.95
        }
        
        hit = create_lexical_hit("doc1", 0.9, 1, signals)
        
        trace = SearchTrace(enabled=True)
        trace.add_step(SearchTraceStep(
            stage="AC",
            query="test",
            topk=10,
            took_ms=2.0,
            hits=[hit]
        ))
        
        # Verify signals are preserved
        assert len(trace.steps) == 1
        step = trace.steps[0]
        assert len(step.hits) == 1
        
        hit_data = step.hits[0]
        assert hit_data.signals == signals
        assert hit_data.signals["tier"] == "T0"
        assert hit_data.signals["dob_match"] is True
        assert hit_data.signals["id_match"] is False
        assert hit_data.signals["confidence"] == 0.95

    def test_trace_performance_impact(self):
        """Test that enabled trace has measurable but reasonable performance impact."""
        # Test disabled trace performance
        disabled_trace = SearchTrace(enabled=False)
        
        start_time = time.perf_counter()
        for i in range(100):
            disabled_trace.add_step(SearchTraceStep(
                stage="LEXICAL",
                query=f"test_{i}",
                topk=10,
                took_ms=1.0,
                hits=[create_lexical_hit(f"doc_{i}", 0.9, 1)]
            ))
            disabled_trace.note(f"Note {i}")
        disabled_time = time.perf_counter() - start_time
        
        # Test enabled trace performance
        enabled_trace = SearchTrace(enabled=True)
        
        start_time = time.perf_counter()
        for i in range(100):
            enabled_trace.add_step(SearchTraceStep(
                stage="LEXICAL",
                query=f"test_{i}",
                topk=10,
                took_ms=1.0,
                hits=[create_lexical_hit(f"doc_{i}", 0.9, 1)]
            ))
            enabled_trace.note(f"Note {i}")
        enabled_time = time.perf_counter() - start_time
        
        # Both should be very fast (under 1ms for 100 operations)
        assert disabled_time < 0.001, f"Disabled trace took {disabled_time:.6f}s, expected < 0.001s"
        assert enabled_time < 0.01, f"Enabled trace took {enabled_time:.6f}s, expected < 0.01s"
        
        # Enabled trace should not be dramatically slower (allow for measurement variance)
        if enabled_time > disabled_time:
            assert enabled_time < disabled_time * 50, "Enabled trace should not be 50x slower"
        
        # Verify data is actually recorded
        assert len(enabled_trace.steps) == 100
        assert len(enabled_trace.notes) == 100
        assert len(disabled_trace.steps) == 0
        assert len(disabled_trace.notes) == 0

    def test_trace_to_dict_structure(self):
        """Test that trace.to_dict() produces correct structure."""
        trace = SearchTrace(enabled=True)
        
        # Add sample data
        trace.add_step(SearchTraceStep(
            stage="LEXICAL",
            query="test query",
            topk=5,
            took_ms=3.0,
            hits=[create_lexical_hit("doc1", 0.9, 1)],
            meta={"test_meta": "value"}
        ))
        trace.note("Test note")
        
        # Convert to dict
        trace_dict = trace.to_dict()
        
        # Verify structure
        assert isinstance(trace_dict, dict)
        assert "enabled" in trace_dict
        assert "steps" in trace_dict
        assert "notes" in trace_dict
        
        assert trace_dict["enabled"] is True
        assert len(trace_dict["steps"]) == 1
        assert len(trace_dict["notes"]) == 1
        
        # Verify step structure
        step_dict = trace_dict["steps"][0]
        assert "stage" in step_dict
        assert "query" in step_dict
        assert "topk" in step_dict
        assert "took_ms" in step_dict
        assert "hits" in step_dict
        assert "meta" in step_dict
        
        assert step_dict["stage"] == "LEXICAL"
        assert step_dict["query"] == "test query"
        assert step_dict["topk"] == 5
        assert step_dict["took_ms"] == 3.0
        assert step_dict["meta"]["test_meta"] == "value"
        
        # Verify hit structure
        hit_dict = step_dict["hits"][0]
        assert "doc_id" in hit_dict
        assert "score" in hit_dict
        assert "rank" in hit_dict
        assert "source" in hit_dict
        assert "signals" in hit_dict
        
        assert hit_dict["doc_id"] == "doc1"
        assert hit_dict["score"] == 0.9
        assert hit_dict["rank"] == 1
        assert hit_dict["source"] == "LEXICAL"

    def test_trace_edge_cases(self):
        """Test edge cases for SearchTrace."""
        # Test with None values
        trace = SearchTrace(enabled=True)
        trace.add_step(SearchTraceStep(
            stage="LEXICAL",
            query="",
            topk=0,
            took_ms=0.0,
            hits=[],
            meta={}
        ))
        trace.note("")
        
        # Should handle empty values gracefully
        assert len(trace.steps) == 1
        assert len(trace.notes) == 1
        
        # Test with very large numbers
        trace.add_step(SearchTraceStep(
            stage="SEMANTIC",
            query="x" * 1000,  # Very long query
            topk=10000,  # Very large topk
            took_ms=999999.0,  # Very large time
            hits=[create_semantic_hit("doc", 1.0, 1)],
            meta={"large_key": "x" * 1000}
        ))
        
        # Should handle large values
        assert len(trace.steps) == 2
        step = trace.steps[1]
        assert len(step.query) == 1000
        assert step.topk == 10000
        assert step.took_ms == 999999.0
        assert len(step.meta["large_key"]) == 1000

    def test_trace_builder_edge_cases(self):
        """Test SearchTraceBuilder edge cases."""
        # Test with disabled builder
        disabled_builder = SearchTraceBuilder(enabled=False)
        disabled_builder.add_lexical_step("test", 10, 1.0, [])
        disabled_builder.note("test note")
        
        disabled_trace = disabled_builder.build()
        assert disabled_trace.enabled is False
        assert len(disabled_trace.steps) == 0
        assert len(disabled_trace.notes) == 0
        
        # Test with enabled builder
        enabled_builder = SearchTraceBuilder(enabled=True)
        enabled_builder.add_lexical_step("test", 10, 1.0, [])
        enabled_builder.note("test note")
        
        enabled_trace = enabled_builder.build()
        assert enabled_trace.enabled is True
        assert len(enabled_trace.steps) == 1
        assert len(enabled_trace.notes) == 1

    def test_trace_serialization_edge_cases(self):
        """Test serialization edge cases."""
        # Test with disabled trace
        disabled_trace = SearchTrace(enabled=False)
        disabled_dict = disabled_trace.to_dict()
        
        assert disabled_dict["enabled"] is False
        assert len(disabled_dict["steps"]) == 0
        assert len(disabled_dict["notes"]) == 0
        
        # Test with empty trace
        empty_trace = SearchTrace(enabled=True)
        empty_dict = empty_trace.to_dict()
        
        assert empty_dict["enabled"] is True
        assert len(empty_dict["steps"]) == 0
        assert len(empty_dict["notes"]) == 0
        
        # Test with complex data
        complex_trace = SearchTrace(enabled=True)
        complex_trace.add_step(SearchTraceStep(
            stage="HYBRID",
            query="complex query with special chars: !@#$%^&*()",
            topk=100,
            took_ms=123.456,
            hits=[
                create_hybrid_hit("doc1", 0.999, 1, {"tier": "T0", "special": "value"}),
                create_hybrid_hit("doc2", 0.888, 2, {"tier": "T1", "special": "value2"})
            ],
            meta={"complex_meta": {"nested": {"value": 123}}}
        ))
        complex_trace.note("Complex note with special chars: !@#$%^&*()")
        
        complex_dict = complex_trace.to_dict()
        
        # Should serialize complex data correctly
        assert complex_dict["enabled"] is True
        assert len(complex_dict["steps"]) == 1
        assert len(complex_dict["notes"]) == 1
        
        step_dict = complex_dict["steps"][0]
        assert step_dict["stage"] == "HYBRID"
        assert step_dict["query"] == "complex query with special chars: !@#$%^&*()"
        assert step_dict["topk"] == 100
        assert step_dict["took_ms"] == 123.5  # Rounded to 0.1ms precision
        assert len(step_dict["hits"]) == 2
        assert step_dict["meta"]["complex_meta"]["nested"]["value"] == 123
        
        assert complex_dict["notes"][0] == "Complex note with special chars: !@#$%^&*()"

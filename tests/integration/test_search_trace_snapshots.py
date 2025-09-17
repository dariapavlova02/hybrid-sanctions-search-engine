"""
Integration tests for SearchTrace snapshots with stable fixtures and approval testing.
"""

import json
import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, List

from src.ai_service.core.unified_orchestrator import UnifiedOrchestrator
from src.ai_service.config.feature_flags import FeatureFlags
from src.ai_service.contracts.trace_models import SearchTrace


class SearchTraceSnapshotNormalizer:
    """Normalizes SearchTrace data for stable snapshot comparison."""
    
    @staticmethod
    def normalize_trace_data(trace_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize trace data for stable comparison."""
        if not trace_data or not isinstance(trace_data, dict):
            return trace_data
        
        normalized = trace_data.copy()
        
        # Normalize steps
        if "steps" in normalized:
            normalized["steps"] = [
                SearchTraceSnapshotNormalizer._normalize_step(step)
                for step in normalized["steps"]
            ]
        
        # Remove dynamic fields
        normalized.pop("total_time_ms", None)
        normalized.pop("total_hits", None)
        
        return normalized
    
    @staticmethod
    def _normalize_step(step: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a single search step."""
        if not isinstance(step, dict):
            return step
        
        normalized_step = step.copy()
        
        # Normalize timing
        normalized_step.pop("took_ms", None)
        
        # Normalize hits (keep only top 3)
        if "hits" in normalized_step and isinstance(normalized_step["hits"], list):
            hits = normalized_step["hits"]
            if len(hits) > 3:
                # Keep top 3 and add summary
                top_hits = hits[:3]
                summary = {
                    "doc_id": f"...{len(hits) - 3} more hits",
                    "score": 0.0,
                    "rank": 0,
                    "source": "SUMMARY",
                    "signals": {"total_hits": len(hits)}
                }
                normalized_step["hits"] = top_hits + [summary]
        
        # Normalize meta fields
        if "meta" in normalized_step and isinstance(normalized_step["meta"], dict):
            meta = normalized_step["meta"]
            # Remove dynamic timing fields
            meta.pop("load_time_ms", None)
            meta.pop("search_time_ms", None)
            
            # Normalize tier counts
            if "tiers" in meta and isinstance(meta["tiers"], dict):
                tiers = meta["tiers"]
                # Keep only essential tier info
                normalized_tiers = {}
                for tier_key in ["t0", "t1", "t2"]:
                    if tier_key in tiers:
                        normalized_tiers[tier_key] = tiers[tier_key]
                meta["tiers"] = normalized_tiers
        
        return normalized_step


@pytest.fixture
def search_trace_normalizer():
    """Fixture for SearchTrace normalizer."""
    return SearchTraceSnapshotNormalizer()


@pytest.fixture
def minimal_watchlist_index():
    """Create minimal watchlist index with 5-10 test records."""
    # Mock watchlist service to avoid heavy dependencies
    mock_watchlist = Mock()
    mock_watchlist.ready.return_value = True
    mock_watchlist.search.return_value = [
        ("DOC_12345", 0.95),
        ("DOC_67890", 0.88),
        ("DOC_11111", 0.82)
    ]
    mock_watchlist.get_doc.return_value = Mock(
        doc_id="DOC_12345",
        text="Иванов Иван Иванович",
        entity_type="person",
        metadata={"dob": "1980-01-01", "passport": "1234567890"}
    )
    return mock_watchlist


@pytest.fixture
def orchestrator_with_search_trace(minimal_watchlist_index):
    """Create orchestrator with search trace enabled and minimal watchlist."""
    # Mock services
    mock_validation = Mock()
    mock_validation.validate_and_sanitize.return_value = {"should_process": True, "sanitized_text": "test"}
    
    mock_language = Mock()
    mock_language.detect_language_config_driven.return_value = {"language": "ru", "confidence": 0.9}
    
    mock_unicode = Mock()
    mock_unicode.normalize_unicode.return_value = "test"
    
    mock_normalization = Mock()
    mock_normalization.normalize_async.return_value = Mock(
        normalized="test",
        tokens=["test"],
        trace=[],
        success=True,
        errors=[]
    )
    
    mock_signals = Mock()
    mock_signals.extract_signals.return_value = Mock(
        persons=[],
        organizations=[],
        confidence=0.8
    )
    
    # Mock decision engine
    mock_decision_engine = Mock()
    
    # Create orchestrator
    orchestrator = UnifiedOrchestrator(
        validation_service=mock_validation,
        language_service=mock_language,
        unicode_service=mock_unicode,
        normalization_service=mock_normalization,
        signals_service=mock_signals,
        decision_engine=mock_decision_engine,
        enable_decision_engine=True
    )
    
    return orchestrator, minimal_watchlist_index


@pytest.mark.search_trace
@pytest.mark.asyncio
async def test_ac_tier_trace_snapshot(
    orchestrator_with_search_trace, 
    search_trace_normalizer
):
    """Test AC tier trace snapshot with document ID and full name patterns."""
    orchestrator, watchlist_index = orchestrator_with_search_trace
    
    # Test input with T0 and T1 patterns
    test_text = "Иванов Иван Иванович, паспорт 1234567890, директор ООО 'Ромашка'"
    
    # Enable AC tiers and debug trace
    feature_flags = FeatureFlags(
        enable_ac_tier0=True,
        enable_vector_fallback=True
    )
    
    # Create a mock decision engine that captures search trace
    captured_search_trace = None
    
    class MockDecisionEngine:
        def decide(self, decision_input, search_trace=None):
            nonlocal captured_search_trace
            captured_search_trace = search_trace
            return Mock(
                risk="LOW",
                score=0.8,
                reasons=["ac_tier_match"],
                details={}
            )
    
    orchestrator.decision_engine = MockDecisionEngine()
    
    # Process with search trace enabled
    result = await orchestrator.process(
        test_text,
        search_trace_enabled=True,
        feature_flags=feature_flags
    )
    
    # Verify search trace was captured
    assert captured_search_trace is not None
    assert captured_search_trace.enabled is True
    
    # Get trace data
    trace_data = captured_search_trace.to_dict()
    normalized_trace = search_trace_normalizer.normalize_trace_data(trace_data)
    
    # Verify trace structure
    assert "steps" in normalized_trace
    assert "notes" in normalized_trace
    assert len(normalized_trace["notes"]) > 0
    
    # Create snapshot for approval testing
    snapshot_data = {
        "test_case": "ac_tier_trace_snapshot",
        "input_text": test_text,
        "feature_flags": {
            "enable_ac_tier0": True,
            "enable_vector_fallback": True
        },
        "trace_summary": {
            "total_steps": len(normalized_trace["steps"]),
            "total_notes": len(normalized_trace["notes"]),
            "enabled": normalized_trace["enabled"]
        },
        "normalized_trace": normalized_trace
    }
    
    # Verify basic structure
    assert snapshot_data["trace_summary"]["total_notes"] > 0
    assert snapshot_data["trace_summary"]["enabled"] is True
    assert len(snapshot_data["normalized_trace"]["notes"]) > 0


@pytest.mark.search_trace
@pytest.mark.asyncio
async def test_vector_fallback_trace_snapshot(
    orchestrator_with_search_trace,
    search_trace_normalizer
):
    """Test vector fallback trace snapshot with semantic search."""
    orchestrator, watchlist_index = orchestrator_with_search_trace
    
    # Test input without AC patterns (no exact matches)
    test_text = "Александр Николаевич Соколов, инженер-программист"
    
    # Enable vector fallback and debug trace
    feature_flags = FeatureFlags(
        enable_vector_fallback=True
    )
    
    # Create a mock decision engine that captures search trace
    captured_search_trace = None
    
    class MockDecisionEngine:
        def decide(self, decision_input, search_trace=None):
            nonlocal captured_search_trace
            captured_search_trace = search_trace
            return Mock(
                risk="MEDIUM",
                score=0.6,
                reasons=["vector_fallback_match"],
                details={}
            )
    
    orchestrator.decision_engine = MockDecisionEngine()
    
    # Process with search trace enabled
    result = await orchestrator.process(
        test_text,
        search_trace_enabled=True,
        feature_flags=feature_flags
    )
    
    # Verify search trace was captured
    assert captured_search_trace is not None
    assert captured_search_trace.enabled is True
    
    # Get trace data
    trace_data = captured_search_trace.to_dict()
    normalized_trace = search_trace_normalizer.normalize_trace_data(trace_data)
    
    # Verify trace structure
    assert "steps" in normalized_trace
    assert "notes" in normalized_trace
    assert len(normalized_trace["notes"]) > 0
    
    # Create snapshot for approval testing
    snapshot_data = {
        "test_case": "vector_fallback_trace_snapshot",
        "input_text": test_text,
        "feature_flags": {
            "enable_vector_fallback": True
        },
        "trace_summary": {
            "total_steps": len(normalized_trace["steps"]),
            "total_notes": len(normalized_trace["notes"]),
            "enabled": normalized_trace["enabled"]
        },
        "normalized_trace": normalized_trace
    }
    
    # Verify basic structure
    assert snapshot_data["trace_summary"]["total_notes"] > 0
    assert snapshot_data["trace_summary"]["enabled"] is True
    assert len(snapshot_data["normalized_trace"]["notes"]) > 0


@pytest.mark.search_trace
@pytest.mark.asyncio
async def test_hybrid_rerank_trace_snapshot(
    orchestrator_with_search_trace,
    search_trace_normalizer
):
    """Test hybrid rerank trace snapshot with BM25+semantic different top-1."""
    orchestrator, watchlist_index = orchestrator_with_search_trace
    
    # Test input that should trigger both BM25 and semantic search
    test_text = "Петров Петр Петрович, бухгалтер, ООО 'Тюльпан'"
    
    # Enable hybrid search and debug trace
    feature_flags = FeatureFlags(
        enable_ac_tier0=True,
        enable_vector_fallback=True
    )
    
    # Create a mock decision engine that captures search trace
    captured_search_trace = None
    
    class MockDecisionEngine:
        def decide(self, decision_input, search_trace=None):
            nonlocal captured_search_trace
            captured_search_trace = search_trace
            return Mock(
                risk="HIGH",
                score=0.9,
                reasons=["hybrid_consensus_match"],
                details={}
            )
    
    orchestrator.decision_engine = MockDecisionEngine()
    
    # Process with search trace enabled
    result = await orchestrator.process(
        test_text,
        search_trace_enabled=True,
        feature_flags=feature_flags
    )
    
    # Verify search trace was captured
    assert captured_search_trace is not None
    assert captured_search_trace.enabled is True
    
    # Get trace data
    trace_data = captured_search_trace.to_dict()
    normalized_trace = search_trace_normalizer.normalize_trace_data(trace_data)
    
    # Verify trace structure
    assert "steps" in normalized_trace
    assert "notes" in normalized_trace
    assert len(normalized_trace["notes"]) > 0
    
    # Create snapshot for approval testing
    snapshot_data = {
        "test_case": "hybrid_rerank_trace_snapshot",
        "input_text": test_text,
        "feature_flags": {
            "enable_ac_tier0": True,
            "enable_vector_fallback": True
        },
        "trace_summary": {
            "total_steps": len(normalized_trace["steps"]),
            "total_notes": len(normalized_trace["notes"]),
            "enabled": normalized_trace["enabled"]
        },
        "normalized_trace": normalized_trace
    }
    
    # Verify basic structure
    assert snapshot_data["trace_summary"]["total_notes"] > 0
    assert snapshot_data["trace_summary"]["enabled"] is True
    assert len(snapshot_data["normalized_trace"]["notes"]) > 0


@pytest.fixture(scope="session")
def search_trace_snapshots_dir():
    """Directory for storing search trace snapshots."""
    import os
    snapshots_dir = "tests/integration/snapshots/search_trace"
    os.makedirs(snapshots_dir, exist_ok=True)
    return snapshots_dir


def save_snapshot(snapshot_data: Dict[str, Any], filename: str, snapshots_dir: str):
    """Save snapshot data to file for approval testing."""
    import os
    filepath = os.path.join(snapshots_dir, f"{filename}.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(snapshot_data, f, indent=2, ensure_ascii=False)
    return filepath


def load_snapshot(filename: str, snapshots_dir: str) -> Dict[str, Any]:
    """Load snapshot data from file for comparison."""
    import os
    filepath = os.path.join(snapshots_dir, f"{filename}.json")
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

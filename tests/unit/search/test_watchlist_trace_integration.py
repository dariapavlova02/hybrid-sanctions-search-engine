"""
Unit tests for watchlist index service trace integration.
"""

import pytest
from unittest.mock import Mock, patch
from src.ai_service.layers.embeddings.indexing.watchlist_index_service import (
    WatchlistIndexService,
    WatchlistDoc
)
from src.ai_service.contracts.trace_models import SearchTrace, SearchTraceBuilder


class TestWatchlistTraceIntegration:
    """Test SearchTrace integration in WatchlistIndexService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = WatchlistIndexService()
        self.trace = SearchTrace(enabled=True)
    
    def test_search_with_trace_enabled(self):
        """Test search method with trace enabled."""
        # Mock the service to have some data
        self.service._docs = {
            "doc1": WatchlistDoc("doc1", "test text", "person", {}),
            "doc2": WatchlistDoc("doc2", "another text", "person", {})
        }
        self.service._active_id = "test_active"
        
        # Mock the active index search
        with patch.object(self.service._active, 'search', return_value=[("doc1", 0.9), ("doc2", 0.8)]):
            results = self.service.search("test query", top_k=10, trace=self.trace)
        
        # Check results
        assert len(results) == 2
        assert results[0] == ("doc1", 0.9)
        assert results[1] == ("doc2", 0.8)
        
        # Check trace steps
        assert len(self.trace.steps) == 2  # Active search + Rerank
        
        # Check active search step
        active_step = self.trace.steps[0]
        assert active_step.stage == "LEXICAL"
        assert active_step.query == "test query"
        assert active_step.topk == 10
        assert len(active_step.hits) == 2
        assert active_step.hits[0].doc_id == "doc1"
        assert active_step.hits[0].score == 0.9
        assert active_step.hits[0].source == "LEXICAL"
        assert active_step.meta["active_id"] == "test_active"
        assert active_step.meta["search_type"] == "active"
        
        # Check rerank step
        rerank_step = self.trace.steps[1]
        assert rerank_step.stage == "RERANK"
        assert rerank_step.query == "test query"
        assert rerank_step.topk == 10
        assert len(rerank_step.hits) == 2
        assert rerank_step.hits[0].doc_id == "doc1"
        assert rerank_step.hits[0].score == 0.9
        assert rerank_step.hits[0].source == "RERANK"
        assert rerank_step.meta["merge_strategy"] == "max_score"
    
    def test_search_with_overlay_and_active(self):
        """Test search with both overlay and active indexes."""
        # Mock the service to have overlay and active data
        self.service._docs = {"doc1": WatchlistDoc("doc1", "active text", "person", {})}
        self.service._overlay_docs = {"doc2": WatchlistDoc("doc2", "overlay text", "person", {})}
        self.service._active_id = "test_active"
        self.service._overlay_id = "test_overlay"
        
        # Mock the index searches
        with patch.object(self.service._active, 'search', return_value=[("doc1", 0.9)]), \
             patch.object(self.service._overlay, 'search', return_value=[("doc2", 0.8)]):
            results = self.service.search("test query", top_k=10, trace=self.trace)
        
        # Check results
        assert len(results) == 2
        
        # Check trace steps
        assert len(self.trace.steps) == 3  # Overlay + Active + Rerank
        
        # Check overlay step
        overlay_step = self.trace.steps[0]
        assert overlay_step.stage == "LEXICAL"
        assert overlay_step.meta["overlay_id"] == "test_overlay"
        assert overlay_step.meta["search_type"] == "overlay"
        
        # Check active step
        active_step = self.trace.steps[1]
        assert active_step.stage == "LEXICAL"
        assert active_step.meta["active_id"] == "test_active"
        assert active_step.meta["search_type"] == "active"
        
        # Check rerank step
        rerank_step = self.trace.steps[2]
        assert rerank_step.stage == "RERANK"
        assert rerank_step.meta["total_candidates"] == 2
    
    def test_search_with_empty_index(self):
        """Test search with empty index."""
        # Service has no data
        self.service._docs = {}
        
        results = self.service.search("test query", top_k=10, trace=self.trace)
        
        # Check results
        assert len(results) == 0
        
        # Check trace notes
        assert len(self.trace.notes) == 1
        assert "Watchlist index not ready - empty index" in self.trace.notes[0]
    
    def test_search_with_trace_disabled(self):
        """Test search with trace disabled."""
        trace = SearchTrace(enabled=False)
        self.service._docs = {"doc1": WatchlistDoc("doc1", "test text", "person", {})}
        
        with patch.object(self.service._active, 'search', return_value=[("doc1", 0.9)]):
            results = self.service.search("test query", top_k=10, trace=trace)
        
        # Check results
        assert len(results) == 1
        
        # Check trace is empty (disabled)
        assert len(trace.steps) == 0
        assert len(trace.notes) == 0
    
    def test_search_with_no_trace(self):
        """Test search without trace parameter."""
        self.service._docs = {"doc1": WatchlistDoc("doc1", "test text", "person", {})}
        
        with patch.object(self.service._active, 'search', return_value=[("doc1", 0.9)]):
            results = self.service.search("test query", top_k=10)
        
        # Check results
        assert len(results) == 1
        assert results[0] == ("doc1", 0.9)
    
    def test_search_with_exception(self):
        """Test search with exception handling."""
        self.service._docs = {"doc1": WatchlistDoc("doc1", "test text", "person", {})}
        
        # Mock search to raise exception
        with patch.object(self.service._active, 'search', side_effect=Exception("Search failed")):
            results = self.service.search("test query", top_k=10, trace=self.trace)
        
        # Check results
        assert len(results) == 0
        
        # Check trace notes
        assert len(self.trace.notes) == 1
        assert "Watchlist search failed: Search failed" in self.trace.notes[0]
    
    def test_get_doc_with_trace_enabled(self):
        """Test get_doc method with trace enabled."""
        # Mock the service to have some data
        self.service._docs = {"doc1": WatchlistDoc("doc1", "test text", "person", {})}
        self.service._overlay_docs = {"doc2": WatchlistDoc("doc2", "overlay text", "person", {})}
        
        # Test getting doc from overlay
        doc = self.service.get_doc("doc2", trace=self.trace)
        assert doc is not None
        assert doc.doc_id == "doc2"
        assert doc.text == "overlay text"
        
        # Check trace notes
        assert len(self.trace.notes) == 1
        assert "Document doc2 found in overlay index" in self.trace.notes[0]
        
        # Test getting doc from active
        doc = self.service.get_doc("doc1", trace=self.trace)
        assert doc is not None
        assert doc.doc_id == "doc1"
        assert doc.text == "test text"
        
        # Check trace notes
        assert len(self.trace.notes) == 2
        assert "Document doc1 found in active index" in self.trace.notes[1]
        
        # Test getting non-existent doc
        doc = self.service.get_doc("doc3", trace=self.trace)
        assert doc is None
        
        # Check trace notes
        assert len(self.trace.notes) == 3
        assert "Document doc3 not found in any index" in self.trace.notes[2]
    
    def test_get_doc_with_exception(self):
        """Test get_doc with exception handling."""
        # Mock to raise exception
        with patch.object(self.service, '_overlay_docs', side_effect=Exception("Access failed")):
            doc = self.service.get_doc("doc1", trace=self.trace)
        
        # Check results
        assert doc is None
        
        # Check trace notes
        assert len(self.trace.notes) == 1
        assert "Failed to get document doc1: Access failed" in self.trace.notes[0]
    
    def test_reload_snapshot_with_trace_enabled(self):
        """Test reload_snapshot method with trace enabled."""
        # Mock file operations
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open()), \
             patch('json.load', return_value={"doc1": {"text": "test", "entity_type": "person", "metadata": {}}}), \
             patch.object(self.service, '_load_char_index', return_value=Mock()):
            
            result = self.service.reload_snapshot("/test/path", as_overlay=False, trace=self.trace)
        
        # Check result
        assert "active_loaded" in result
        assert result["active_count"] == 1
        assert "load_time_ms" in result
        
        # Check trace notes
        assert len(self.trace.notes) >= 2
        assert any("Index loaded from /test/path" in note for note in self.trace.notes)
        assert any("Active snapshot loaded: 1 documents" in note for note in self.trace.notes)
    
    def test_reload_snapshot_with_missing_directory(self):
        """Test reload_snapshot with missing directory."""
        with patch('os.path.exists', return_value=False):
            result = self.service.reload_snapshot("/missing/path", trace=self.trace)
        
        # Check result
        assert "error" in result
        assert "Snapshot directory not found" in result["error"]
        
        # Check trace notes
        assert len(self.trace.notes) == 1
        assert "Snapshot directory not found: /missing/path" in self.trace.notes[0]
    
    def test_reload_snapshot_with_exception(self):
        """Test reload_snapshot with exception handling."""
        with patch('os.path.exists', return_value=True), \
             patch.object(self.service, '_load_char_index', side_effect=Exception("Load failed")):
            
            result = self.service.reload_snapshot("/test/path", trace=self.trace)
        
        # Check result
        assert "error" in result
        assert "Failed to reload snapshot" in result["error"]
        
        # Check trace notes
        assert len(self.trace.notes) == 1
        assert "Failed to reload snapshot from /test/path: Load failed" in self.trace.notes[0]


def mock_open():
    """Mock open function for file operations."""
    from unittest.mock import mock_open as _mock_open
    return _mock_open(read_data='{"doc1": {"text": "test", "entity_type": "person", "metadata": {}}}')

"""
Unit tests for search contracts and data transformations.
"""

import pytest
from src.ai_service.contracts.search_contracts import (
    SearchOpts, SearchMode, SearchType, ACScore, VectorHit, Candidate,
    SearchInfo, SearchResult, SearchMetrics, extract_search_candidates,
    create_search_info
)


class TestSearchOpts:
    """Test SearchOpts configuration."""
    
    def test_default_values(self):
        """Test default SearchOpts values."""
        opts = SearchOpts()
        
        assert opts.top_k == 50
        assert opts.threshold == 0.7
        assert opts.search_mode == SearchMode.HYBRID
        assert opts.enable_escalation is True
        assert opts.entity_type is None
        assert opts.country_filter is None
        assert opts.meta_filters is None
    
    def test_custom_values(self):
        """Test custom SearchOpts values."""
        opts = SearchOpts(
            top_k=100,
            threshold=0.8,
            search_mode=SearchMode.AC,
            enable_escalation=False,
            entity_type="person",
            country_filter="RU",
            meta_filters={"source": "test"}
        )
        
        assert opts.top_k == 100
        assert opts.threshold == 0.8
        assert opts.search_mode == SearchMode.AC
        assert opts.enable_escalation is False
        assert opts.entity_type == "person"
        assert opts.country_filter == "RU"
        assert opts.meta_filters == {"source": "test"}


class TestACScore:
    """Test ACScore data model."""
    
    def test_ac_score_creation(self):
        """Test ACScore creation."""
        ac_score = ACScore(
            entity_id="person_001",
            entity_type="person",
            normalized_name="иван петров",
            aliases=["и. петров"],
            country="RU",
            dob="1980-05-15",
            meta={"source": "test"},
            ac_score=2.0,
            ac_type=SearchType.EXACT,
            matched_field="normalized_name",
            matched_text="иван петров"
        )
        
        assert ac_score.entity_id == "person_001"
        assert ac_score.entity_type == "person"
        assert ac_score.normalized_name == "иван петров"
        assert ac_score.aliases == ["и. петров"]
        assert ac_score.country == "RU"
        assert ac_score.dob == "1980-05-15"
        assert ac_score.meta == {"source": "test"}
        assert ac_score.ac_score == 2.0
        assert ac_score.ac_type == SearchType.EXACT
        assert ac_score.matched_field == "normalized_name"
        assert ac_score.matched_text == "иван петров"


class TestVectorHit:
    """Test VectorHit data model."""
    
    def test_vector_hit_creation(self):
        """Test VectorHit creation."""
        vector_hit = VectorHit(
            entity_id="person_001",
            entity_type="person",
            normalized_name="иван петров",
            aliases=["и. петров"],
            country="RU",
            dob="1980-05-15",
            meta={"source": "test"},
            vector_score=0.95,
            matched_field="name_vector"
        )
        
        assert vector_hit.entity_id == "person_001"
        assert vector_hit.entity_type == "person"
        assert vector_hit.normalized_name == "иван петров"
        assert vector_hit.aliases == ["и. петров"]
        assert vector_hit.country == "RU"
        assert vector_hit.dob == "1980-05-15"
        assert vector_hit.meta == {"source": "test"}
        assert vector_hit.vector_score == 0.95
        assert vector_hit.matched_field == "name_vector"


class TestCandidate:
    """Test Candidate data model."""
    
    def test_candidate_creation(self):
        """Test Candidate creation."""
        candidate = Candidate(
            entity_id="person_001",
            entity_type="person",
            normalized_name="иван петров",
            aliases=["и. петров"],
            country="RU",
            dob="1980-05-15",
            meta={"source": "test"},
            final_score=1.5,
            ac_score=2.0,
            vector_score=0.8,
            features={"DOB_match": True, "need_context": False},
            search_type=SearchType.FUSION
        )
        
        assert candidate.entity_id == "person_001"
        assert candidate.entity_type == "person"
        assert candidate.normalized_name == "иван петров"
        assert candidate.aliases == ["и. петров"]
        assert candidate.country == "RU"
        assert candidate.dob == "1980-05-15"
        assert candidate.meta == {"source": "test"}
        assert candidate.final_score == 1.5
        assert candidate.ac_score == 2.0
        assert candidate.vector_score == 0.8
        assert candidate.features == {"DOB_match": True, "need_context": False}
        assert candidate.search_type == SearchType.FUSION


class TestSearchInfo:
    """Test SearchInfo data model."""
    
    def test_search_info_creation(self):
        """Test SearchInfo creation."""
        search_info = SearchInfo(
            has_exact_matches=True,
            has_phrase_matches=False,
            has_ngram_matches=True,
            has_vector_matches=True,
            exact_confidence=0.9,
            phrase_confidence=0.0,
            ngram_confidence=0.6,
            vector_confidence=0.8,
            total_matches=3,
            high_confidence_matches=2,
            search_time=0.1
        )
        
        assert search_info.has_exact_matches is True
        assert search_info.has_phrase_matches is False
        assert search_info.has_ngram_matches is True
        assert search_info.has_vector_matches is True
        assert search_info.exact_confidence == 0.9
        assert search_info.phrase_confidence == 0.0
        assert search_info.ngram_confidence == 0.6
        assert search_info.vector_confidence == 0.8
        assert search_info.total_matches == 3
        assert search_info.high_confidence_matches == 2
        assert search_info.search_time == 0.1


class TestSearchMetrics:
    """Test SearchMetrics data model."""
    
    def test_search_metrics_creation(self):
        """Test SearchMetrics creation."""
        metrics = SearchMetrics(
            ac_attempts=10,
            vector_attempts=5,
            ac_success=8,
            vector_success=4,
            ac_latency_p95=50.0,
            vector_latency_p95=100.0,
            hit_rate=0.8,
            escalation_rate=0.2
        )
        
        assert metrics.ac_attempts == 10
        assert metrics.vector_attempts == 5
        assert metrics.ac_success == 8
        assert metrics.vector_success == 4
        assert metrics.ac_latency_p95 == 50.0
        assert metrics.vector_latency_p95 == 100.0
        assert metrics.hit_rate == 0.8
        assert metrics.escalation_rate == 0.2


class TestExtractSearchCandidates:
    """Test extract_search_candidates function."""
    
    def test_extract_from_persons(self):
        """Test extracting candidates from persons."""
        signals_result = {
            "persons": [
                {
                    "normalized_name": "иван петров",
                    "aliases": ["и. петров", "ivan petrov"]
                },
                {
                    "normalized_name": "мария сидорова",
                    "aliases": ["м. сидорова"]
                }
            ],
            "organizations": []
        }
        
        candidates = extract_search_candidates(signals_result)
        
        expected = ["иван петров", "и. петров", "ivan petrov", "мария сидорова", "м. сидорова"]
        assert set(candidates) == set(expected)
    
    def test_extract_from_organizations(self):
        """Test extracting candidates from organizations."""
        signals_result = {
            "persons": [],
            "organizations": [
                {
                    "normalized_name": "ооо приватбанк",
                    "aliases": ["приватбанк", "privatbank"]
                },
                {
                    "normalized_name": "apple inc",
                    "aliases": ["apple"]
                }
            ]
        }
        
        candidates = extract_search_candidates(signals_result)
        
        expected = ["ооо приватбанк", "приватбанк", "privatbank", "apple inc", "apple"]
        assert set(candidates) == set(expected)
    
    def test_extract_mixed_entities(self):
        """Test extracting candidates from mixed entities."""
        signals_result = {
            "persons": [
                {
                    "normalized_name": "иван петров",
                    "aliases": ["и. петров"]
                }
            ],
            "organizations": [
                {
                    "normalized_name": "ооо приватбанк",
                    "aliases": ["приватбанк"]
                }
            ]
        }
        
        candidates = extract_search_candidates(signals_result)
        
        expected = ["иван петров", "и. петров", "ооо приватбанк", "приватбанк"]
        assert set(candidates) == set(expected)
    
    def test_extract_empty_result(self):
        """Test extracting from empty signals result."""
        signals_result = {
            "persons": [],
            "organizations": []
        }
        
        candidates = extract_search_candidates(signals_result)
        assert candidates == []
    
    def test_extract_filters_empty_strings(self):
        """Test that empty strings are filtered out."""
        signals_result = {
            "persons": [
                {
                    "normalized_name": "иван петров",
                    "aliases": ["", "и. петров", None]
                }
            ],
            "organizations": []
        }
        
        candidates = extract_search_candidates(signals_result)
        
        expected = ["иван петров", "и. петров"]
        assert set(candidates) == set(expected)


class TestCreateSearchInfo:
    """Test create_search_info function."""
    
    def test_create_search_info_with_results(self):
        """Test creating SearchInfo from SearchResult with results."""
        from src.ai_service.contracts.search_contracts import SearchResult, ACScore, VectorHit, Candidate
        
        # Create mock search result
        ac_results = [
            ACScore(
                entity_id="person_001",
                entity_type="person",
                normalized_name="иван петров",
                aliases=[],
                country="RU",
                dob=None,
                meta={},
                ac_score=2.0,
                ac_type=SearchType.EXACT,
                matched_field="normalized_name"
            ),
            ACScore(
                entity_id="person_002",
                entity_type="person",
                normalized_name="мария сидорова",
                aliases=[],
                country="UA",
                dob=None,
                meta={},
                ac_score=1.5,
                ac_type=SearchType.PHRASE,
                matched_field="name_text.shingle"
            )
        ]
        
        vector_results = [
            VectorHit(
                entity_id="person_001",
                entity_type="person",
                normalized_name="иван петров",
                aliases=[],
                country="RU",
                dob=None,
                meta={},
                vector_score=0.9,
                matched_field="name_vector"
            )
        ]
        
        candidates = [
            Candidate(
                entity_id="person_001",
                entity_type="person",
                normalized_name="иван петров",
                aliases=[],
                country="RU",
                dob=None,
                meta={},
                final_score=1.8,
                ac_score=2.0,
                vector_score=0.9,
                features={"DOB_match": True, "need_context": False},
                search_type=SearchType.FUSION
            )
        ]
        
        search_result = SearchResult(
            candidates=candidates,
            ac_results=ac_results,
            vector_results=vector_results,
            search_metadata={"test": "data"},
            processing_time=0.1,
            success=True
        )
        
        search_info = create_search_info(search_result)
        
        assert search_info.has_exact_matches is True
        assert search_info.has_phrase_matches is True
        assert search_info.has_ngram_matches is False
        assert search_info.has_vector_matches is True
        assert search_info.exact_confidence == 2.0
        assert search_info.phrase_confidence == 1.5
        assert search_info.ngram_confidence == 0.0
        assert search_info.vector_confidence == 0.9
        assert search_info.total_matches == 1
        assert search_info.high_confidence_matches == 1
        assert search_info.search_time == 0.1
        assert len(search_info.ac_results) == 2
        assert len(search_info.vector_results) == 1
        assert len(search_info.fusion_candidates) == 1
    
    def test_create_search_info_empty_results(self):
        """Test creating SearchInfo from empty SearchResult."""
        from src.ai_service.contracts.search_contracts import SearchResult
        
        search_result = SearchResult(
            candidates=[],
            ac_results=[],
            vector_results=[],
            search_metadata={},
            processing_time=0.0,
            success=True
        )
        
        search_info = create_search_info(search_result)
        
        assert search_info.has_exact_matches is False
        assert search_info.has_phrase_matches is False
        assert search_info.has_ngram_matches is False
        assert search_info.has_vector_matches is False
        assert search_info.exact_confidence == 0.0
        assert search_info.phrase_confidence == 0.0
        assert search_info.ngram_confidence == 0.0
        assert search_info.vector_confidence == 0.0
        assert search_info.total_matches == 0
        assert search_info.high_confidence_matches == 0
        assert search_info.search_time == 0.0
        assert len(search_info.ac_results) == 0
        assert len(search_info.vector_results) == 0
        assert len(search_info.fusion_candidates) == 0

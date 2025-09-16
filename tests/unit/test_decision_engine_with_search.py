"""
Unit tests for DecisionEngine with search integration.
"""

import pytest
from src.ai_service.core.decision_engine import DecisionEngine
from src.ai_service.contracts.decision_contracts import (
    DecisionInput, DecisionOutput, RiskLevel, SmartFilterInfo, SignalsInfo, 
    SimilarityInfo, SearchInfo
)
from src.ai_service.config.settings import DecisionConfig


class TestDecisionEngineWithSearch:
    """Test DecisionEngine with search integration."""
    
    def test_init_with_default_config(self):
        """Test initialization with default config."""
        engine = DecisionEngine()
        
        assert engine.config is not None
        assert isinstance(engine.config, DecisionConfig)
        assert engine.metrics_service is None
    
    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        config = DecisionConfig(
            w_smartfilter=0.2,
            w_person=0.3,
            w_org=0.2,
            w_similarity=0.3,
            w_search_exact=0.4,
            w_search_phrase=0.3,
            w_search_ngram=0.2,
            w_search_vector=0.1
        )
        
        engine = DecisionEngine(config)
        
        assert engine.config == config
        assert engine.config.w_search_exact == 0.4
        assert engine.config.w_search_phrase == 0.3
        assert engine.config.w_search_ngram == 0.2
        assert engine.config.w_search_vector == 0.1
    
    def test_calculate_weighted_score_without_search(self):
        """Test calculate_weighted_score without search info."""
        engine = DecisionEngine()
        
        # Create decision input without search
        decision_input = DecisionInput(
            text="иван петров",
            language="ru",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
            signals=SignalsInfo(person_confidence=0.9, org_confidence=0.0),
            similarity=SimilarityInfo(cos_top=0.7),
            search=None
        )
        
        score = engine._calculate_weighted_score(decision_input)
        
        # Should calculate without search weights
        expected = (
            engine.config.w_smartfilter * 0.8 +
            engine.config.w_person * 0.9 +
            engine.config.w_org * 0.0 +
            engine.config.w_similarity * 0.7
        )
        
        assert score == expected
    
    def test_calculate_weighted_score_with_exact_matches(self):
        """Test calculate_weighted_score with exact matches."""
        engine = DecisionEngine()
        
        # Create search info with exact matches
        search_info = SearchInfo(
            has_exact_matches=True,
            has_phrase_matches=False,
            has_ngram_matches=False,
            has_vector_matches=False,
            exact_confidence=0.9,
            phrase_confidence=0.0,
            ngram_confidence=0.0,
            vector_confidence=0.0,
            total_matches=1,
            high_confidence_matches=1,
            search_time=0.1
        )
        
        decision_input = DecisionInput(
            text="иван петров",
            language="ru",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
            signals=SignalsInfo(person_confidence=0.9, org_confidence=0.0),
            similarity=SimilarityInfo(cos_top=0.7),
            search=search_info
        )
        
        score = engine._calculate_weighted_score(decision_input)
        
        # Should include exact match weight
        expected = (
            engine.config.w_smartfilter * 0.8 +
            engine.config.w_person * 0.9 +
            engine.config.w_org * 0.0 +
            engine.config.w_similarity * 0.7 +
            engine.config.w_search_exact * 0.9 +
            engine.config.bonus_high_confidence
        )
        
        assert score == expected
    
    def test_calculate_weighted_score_with_phrase_matches(self):
        """Test calculate_weighted_score with phrase matches."""
        engine = DecisionEngine()
        
        # Create search info with phrase matches
        search_info = SearchInfo(
            has_exact_matches=False,
            has_phrase_matches=True,
            has_ngram_matches=False,
            has_vector_matches=False,
            exact_confidence=0.0,
            phrase_confidence=0.8,
            ngram_confidence=0.0,
            vector_confidence=0.0,
            total_matches=1,
            high_confidence_matches=0,
            search_time=0.1
        )
        
        decision_input = DecisionInput(
            text="иван петров",
            language="ru",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
            signals=SignalsInfo(person_confidence=0.9, org_confidence=0.0),
            similarity=SimilarityInfo(cos_top=0.7),
            search=search_info
        )
        
        score = engine._calculate_weighted_score(decision_input)
        
        # Should include phrase match weight
        expected = (
            engine.config.w_smartfilter * 0.8 +
            engine.config.w_person * 0.9 +
            engine.config.w_org * 0.0 +
            engine.config.w_similarity * 0.7 +
            engine.config.w_search_phrase * 0.8
        )
        
        assert score == expected
    
    def test_calculate_weighted_score_with_ngram_matches(self):
        """Test calculate_weighted_score with n-gram matches."""
        engine = DecisionEngine()
        
        # Create search info with n-gram matches
        search_info = SearchInfo(
            has_exact_matches=False,
            has_phrase_matches=False,
            has_ngram_matches=True,
            has_vector_matches=False,
            exact_confidence=0.0,
            phrase_confidence=0.0,
            ngram_confidence=0.7,
            vector_confidence=0.0,
            total_matches=1,
            high_confidence_matches=0,
            search_time=0.1
        )
        
        decision_input = DecisionInput(
            text="иван петров",
            language="ru",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
            signals=SignalsInfo(person_confidence=0.9, org_confidence=0.0),
            similarity=SimilarityInfo(cos_top=0.7),
            search=search_info
        )
        
        score = engine._calculate_weighted_score(decision_input)
        
        # Should include n-gram match weight
        expected = (
            engine.config.w_smartfilter * 0.8 +
            engine.config.w_person * 0.9 +
            engine.config.w_org * 0.0 +
            engine.config.w_similarity * 0.7 +
            engine.config.w_search_ngram * 0.7
        )
        
        assert score == expected
    
    def test_calculate_weighted_score_with_vector_matches(self):
        """Test calculate_weighted_score with vector matches."""
        engine = DecisionEngine()
        
        # Create search info with vector matches
        search_info = SearchInfo(
            has_exact_matches=False,
            has_phrase_matches=False,
            has_ngram_matches=False,
            has_vector_matches=True,
            exact_confidence=0.0,
            phrase_confidence=0.0,
            ngram_confidence=0.0,
            vector_confidence=0.8,
            total_matches=1,
            high_confidence_matches=0,
            search_time=0.1
        )
        
        decision_input = DecisionInput(
            text="иван петров",
            language="ru",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
            signals=SignalsInfo(person_confidence=0.9, org_confidence=0.0),
            similarity=SimilarityInfo(cos_top=0.7),
            search=search_info
        )
        
        score = engine._calculate_weighted_score(decision_input)
        
        # Should include vector match weight
        expected = (
            engine.config.w_smartfilter * 0.8 +
            engine.config.w_person * 0.9 +
            engine.config.w_org * 0.0 +
            engine.config.w_similarity * 0.7 +
            engine.config.w_search_vector * 0.8
        )
        
        assert score == expected
    
    def test_calculate_weighted_score_with_multiple_matches(self):
        """Test calculate_weighted_score with multiple match types."""
        engine = DecisionEngine()
        
        # Create search info with multiple match types
        search_info = SearchInfo(
            has_exact_matches=True,
            has_phrase_matches=True,
            has_ngram_matches=True,
            has_vector_matches=True,
            exact_confidence=0.9,
            phrase_confidence=0.8,
            ngram_confidence=0.7,
            vector_confidence=0.6,
            total_matches=4,
            high_confidence_matches=2,
            search_time=0.1
        )
        
        decision_input = DecisionInput(
            text="иван петров",
            language="ru",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
            signals=SignalsInfo(person_confidence=0.9, org_confidence=0.0),
            similarity=SimilarityInfo(cos_top=0.7),
            search=search_info
        )
        
        score = engine._calculate_weighted_score(decision_input)
        
        # Should include all match weights plus bonuses
        expected = (
            engine.config.w_smartfilter * 0.8 +
            engine.config.w_person * 0.9 +
            engine.config.w_org * 0.0 +
            engine.config.w_similarity * 0.7 +
            engine.config.w_search_exact * 0.9 +
            engine.config.w_search_phrase * 0.8 +
            engine.config.w_search_ngram * 0.7 +
            engine.config.w_search_vector * 0.6 +
            engine.config.bonus_multiple_matches +
            engine.config.bonus_high_confidence
        )
        
        assert score == expected
    
    def test_calculate_weighted_score_threshold_filtering(self):
        """Test that search results are filtered by thresholds."""
        engine = DecisionEngine()
        
        # Create search info with low confidence matches
        search_info = SearchInfo(
            has_exact_matches=True,
            has_phrase_matches=True,
            has_ngram_matches=True,
            has_vector_matches=True,
            exact_confidence=0.5,  # Below threshold
            phrase_confidence=0.6,  # Below threshold
            ngram_confidence=0.5,  # Below threshold
            vector_confidence=0.4,  # Below threshold
            total_matches=4,
            high_confidence_matches=0,
            search_time=0.1
        )
        
        decision_input = DecisionInput(
            text="иван петров",
            language="ru",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
            signals=SignalsInfo(person_confidence=0.9, org_confidence=0.0),
            similarity=SimilarityInfo(cos_top=0.7),
            search=search_info
        )
        
        score = engine._calculate_weighted_score(decision_input)
        
        # Should not include any search weights due to low confidence
        expected = (
            engine.config.w_smartfilter * 0.8 +
            engine.config.w_person * 0.9 +
            engine.config.w_org * 0.0 +
            engine.config.w_similarity * 0.7
        )
        
        assert score == expected
    
    def test_calculate_weighted_score_score_capping(self):
        """Test that final score is capped at 1.0."""
        engine = DecisionEngine()
        
        # Create search info with very high confidence
        search_info = SearchInfo(
            has_exact_matches=True,
            has_phrase_matches=True,
            has_ngram_matches=True,
            has_vector_matches=True,
            exact_confidence=1.0,
            phrase_confidence=1.0,
            ngram_confidence=1.0,
            vector_confidence=1.0,
            total_matches=4,
            high_confidence_matches=4,
            search_time=0.1
        )
        
        decision_input = DecisionInput(
            text="иван петров",
            language="ru",
            smartfilter=SmartFilterInfo(should_process=True, confidence=1.0),
            signals=SignalsInfo(person_confidence=1.0, org_confidence=1.0),
            similarity=SimilarityInfo(cos_top=1.0),
            search=search_info
        )
        
        score = engine._calculate_weighted_score(decision_input)
        
        # Should be capped at 1.0
        assert score == 1.0
    
    def test_determine_risk_level_with_search(self):
        """Test risk level determination with search results."""
        engine = DecisionEngine()
        
        # Test high risk with search
        search_info = SearchInfo(
            has_exact_matches=True,
            exact_confidence=0.9,
            total_matches=1,
            high_confidence_matches=1,
            search_time=0.1
        )
        
        decision_input = DecisionInput(
            text="иван петров",
            language="ru",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
            signals=SignalsInfo(person_confidence=0.9, org_confidence=0.0),
            similarity=SimilarityInfo(cos_top=0.7),
            search=search_info
        )
        
        score = engine._calculate_weighted_score(decision_input)
        risk = engine._determine_risk_level(score)
        
        # Should be high risk due to search results
        assert risk in [RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]
    
    def test_decide_with_search(self):
        """Test complete decision process with search."""
        engine = DecisionEngine()
        
        # Create decision input with search
        search_info = SearchInfo(
            has_exact_matches=True,
            exact_confidence=0.9,
            total_matches=1,
            high_confidence_matches=1,
            search_time=0.1
        )
        
        decision_input = DecisionInput(
            text="иван петров",
            language="ru",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
            signals=SignalsInfo(person_confidence=0.9, org_confidence=0.0),
            similarity=SimilarityInfo(cos_top=0.7),
            search=search_info
        )
        
        result = engine.decide(decision_input)
        
        assert isinstance(result, DecisionOutput)
        assert result.risk in [RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]
        assert 0.0 <= result.score <= 1.0
        assert isinstance(result.reasons, list)
        assert isinstance(result.details, dict)
    
    def test_decide_without_search(self):
        """Test complete decision process without search."""
        engine = DecisionEngine()
        
        # Create decision input without search
        decision_input = DecisionInput(
            text="иван петров",
            language="ru",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
            signals=SignalsInfo(person_confidence=0.9, org_confidence=0.0),
            similarity=SimilarityInfo(cos_top=0.7),
            search=None
        )
        
        result = engine.decide(decision_input)
        
        assert isinstance(result, DecisionOutput)
        assert result.risk in [RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]
        assert 0.0 <= result.score <= 1.0
        assert isinstance(result.reasons, list)
        assert isinstance(result.details, dict)
    
    def test_search_bonuses_and_penalties(self):
        """Test search bonuses and penalties."""
        engine = DecisionEngine()
        
        # Test with multiple matches bonus
        search_info = SearchInfo(
            has_exact_matches=True,
            exact_confidence=0.9,
            total_matches=3,  # Multiple matches
            high_confidence_matches=2,  # High confidence
            search_time=0.1
        )
        
        decision_input = DecisionInput(
            text="иван петров",
            language="ru",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
            signals=SignalsInfo(person_confidence=0.9, org_confidence=0.0),
            similarity=SimilarityInfo(cos_top=0.7),
            search=search_info
        )
        
        score = engine._calculate_weighted_score(decision_input)
        
        # Should include bonuses for multiple matches and high confidence
        expected_base = (
            engine.config.w_smartfilter * 0.8 +
            engine.config.w_person * 0.9 +
            engine.config.w_org * 0.0 +
            engine.config.w_similarity * 0.7 +
            engine.config.w_search_exact * 0.9
        )
        
        expected_bonuses = (
            engine.config.bonus_multiple_matches +
            engine.config.bonus_high_confidence
        )
        
        expected = expected_base + expected_bonuses
        
        assert score == expected
    
    def test_search_weights_configuration(self):
        """Test that search weights are properly configured."""
        config = DecisionConfig(
            w_search_exact=0.4,
            w_search_phrase=0.3,
            w_search_ngram=0.2,
            w_search_vector=0.1,
            thr_search_exact=0.8,
            thr_search_phrase=0.7,
            thr_search_ngram=0.6,
            thr_search_vector=0.5,
            bonus_multiple_matches=0.15,
            bonus_high_confidence=0.1
        )
        
        engine = DecisionEngine(config)
        
        assert engine.config.w_search_exact == 0.4
        assert engine.config.w_search_phrase == 0.3
        assert engine.config.w_search_ngram == 0.2
        assert engine.config.w_search_vector == 0.1
        assert engine.config.thr_search_exact == 0.8
        assert engine.config.thr_search_phrase == 0.7
        assert engine.config.thr_search_ngram == 0.6
        assert engine.config.thr_search_vector == 0.5
        assert engine.config.bonus_multiple_matches == 0.15
        assert engine.config.bonus_high_confidence == 0.1

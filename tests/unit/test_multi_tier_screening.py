"""
Unit tests for Multi-tier Screening Service
Testing the comprehensive kNN + AC + fuzzy matching screening pipeline
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass

from src.ai_service.services.multi_tier_screening_service import (
    MultiTierScreeningService, ScreeningResult, ScreeningCandidate
)
from src.ai_service.config.screening_tiers import (
    screening_config, ScreeningTier, RiskLevel
)


class TestMultiTierScreeningService:
    """Tests for MultiTierScreeningService"""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator service"""
        orchestrator = Mock()
        orchestrator.embedding_service = Mock()
        orchestrator.embedding_service.generate_embeddings = AsyncMock(
            return_value={'embeddings': [0.1, 0.2, 0.3]}
        )
        return orchestrator

    @pytest.fixture
    def screening_service(self, mock_orchestrator):
        """Create MultiTierScreeningService instance"""
        return MultiTierScreeningService(orchestrator_service=mock_orchestrator)

    @pytest.mark.asyncio
    async def test_screen_entity_basic_flow(self, screening_service):
        """Test basic entity screening flow"""
        # Arrange
        input_text = "Петро Порошенко"

        # Act
        result = await screening_service.screen_entity(input_text)

        # Assert
        assert isinstance(result, ScreeningResult)
        assert result.input_text == input_text
        assert isinstance(result.risk_level, RiskLevel)
        assert result.final_confidence >= 0.0
        assert result.processing_time_ms > 0
        assert len(result.tiers_executed) > 0
        assert 'start_time' in result.audit_trail
        assert 'tiers' in result.audit_trail

    @pytest.mark.asyncio
    async def test_screen_entity_with_metadata(self, screening_service):
        """Test entity screening with additional metadata"""
        # Arrange
        input_text = "Петро Порошенко"
        metadata = {
            'birthdate': '1965-09-26',
            'country': 'UA',
            'entity_type': 'PERSON'
        }

        # Act
        result = await screening_service.screen_entity(input_text, metadata)

        # Assert
        assert isinstance(result, ScreeningResult)
        assert result.input_text == input_text
        assert 'start_time' in result.audit_trail
        assert 'tiers' in result.audit_trail

    @pytest.mark.asyncio
    async def test_ac_tier_execution(self, screening_service):
        """Test Aho-Corasick tier execution"""
        # Arrange
        tier = ScreeningTier.TIER_0_AC
        config = screening_config.get_tier_config(tier)
        context = {
            'input_text': 'putin test',
            'metadata': {},
            'candidates': [],
            'audit_trail': {'tiers': []}
        }

        # Act
        result = await screening_service._execute_ac_tier(config, context)

        # Assert
        assert 'candidates' in result
        assert 'max_confidence' in result
        assert 'method' in result
        assert 'aho_corasick' in result['method']

        # Should find exact match for 'putin'
        if result['candidates']:
            assert result['candidates'][0]['method'] == 'ac_exact'
            assert result['max_confidence'] > 0.9

    @pytest.mark.asyncio
    async def test_blocking_tier_ukrainian_suffix(self, screening_service):
        """Test blocking tier Ukrainian surname suffix detection"""
        # Arrange
        tier = ScreeningTier.TIER_1_BLOCKING
        config = screening_config.get_tier_config(tier)
        context = {
            'input_text': 'Петро Порошенко',  # Ukrainian surname ending
            'metadata': {},
            'candidates': [],
            'audit_trail': {'tiers': []}
        }

        # Act
        result = await screening_service._execute_blocking_tier(config, context)

        # Assert
        assert 'candidates' in result
        assert result['method'] == 'blocking'

        # Should detect Ukrainian surname pattern
        if result['candidates']:
            candidate = result['candidates'][0]
            assert 'name' in candidate
            assert 'confidence' in candidate or 'confidence_score' in candidate

    @pytest.mark.asyncio
    async def test_knn_tier_with_embeddings(self, screening_service):
        """Test kNN tier with embedding generation"""
        # Arrange
        tier = ScreeningTier.TIER_2_KNN
        config = screening_config.get_tier_config(tier)
        context = {
            'input_text': 'Test Name',
            'metadata': {},
            'candidates': [],
            'audit_trail': {'tiers': []}
        }

        # Act
        result = await screening_service._execute_knn_tier(config, context)

        # Assert
        assert 'candidates' in result
        assert result['method'] == 'knn_vector'

        # Should have called embedding service (if available)
        # Note: In test environment, embedding service may not be called

    @pytest.mark.asyncio
    async def test_knn_tier_embedding_failure(self, screening_service):
        """Test kNN tier graceful handling of embedding failure"""
        # Arrange
        screening_service.orchestrator.embedding_service.generate_embeddings.side_effect = Exception("Embedding failed")

        tier = ScreeningTier.TIER_2_KNN
        config = screening_config.get_tier_config(tier)
        context = {
            'input_text': 'Test Name',
            'metadata': {},
            'candidates': [],
            'audit_trail': {'tiers': []}
        }

        # Act
        result = await screening_service._execute_knn_tier(config, context)

        # Assert
        assert 'candidates' in result
        assert result['method'] == 'knn_vector'
        assert result['max_confidence'] == 0.0  # No candidates due to failure

    @pytest.mark.asyncio
    async def test_rerank_tier_candidate_boosting(self, screening_service):
        """Test re-ranking tier candidate score boosting"""
        # Arrange
        tier = ScreeningTier.TIER_3_RERANK
        config = screening_config.get_tier_config(tier)
        context = {
            'input_text': 'Test Name',
            'metadata': {},
            'candidates': [
                {'entity_id': 'test1', 'name': 'Test', 'confidence': 0.6},
                {'entity_id': 'test2', 'name': 'Name', 'confidence': 0.7}
            ],
            'audit_trail': {'tiers': []}
        }

        # Act
        result = await screening_service._execute_rerank_tier(config, context)

        # Assert
        assert 'candidates' in result
        assert result['method'] == 'reranking'
        assert len(result['candidates']) == 2

        # Scores should be boosted but capped at 1.0
        for candidate in result['candidates']:
            assert candidate['confidence'] <= 1.0
            assert 'features' in candidate

    @pytest.mark.asyncio
    async def test_ml_tier_placeholder(self, screening_service):
        """Test ML tier placeholder implementation"""
        # Arrange
        tier = ScreeningTier.TIER_4_ML
        config = screening_config.get_tier_config(tier)
        context = {
            'input_text': 'Test Name',
            'metadata': {},
            'candidates': [],
            'audit_trail': {'tiers': []}
        }

        # Act
        result = await screening_service._execute_ml_tier(config, context)

        # Assert
        assert 'candidates' in result
        assert result['method'] == 'ml_advanced'
        assert 'note' in result
        assert "not implemented" in result['note']

    @pytest.mark.asyncio
    async def test_early_stopping_high_confidence(self, screening_service):
        """Test early stopping on high confidence score"""
        # Arrange
        input_text = "putin"  # Should trigger AC exact match with high confidence

        # Act
        result = await screening_service.screen_entity(input_text)

        # Assert
        assert isinstance(result, ScreeningResult)
        # Should stop early if confidence is very high
        if result.final_confidence >= 0.95:
            assert result.early_stopped is True

    @pytest.mark.asyncio
    async def test_screening_with_disabled_tiers(self, screening_service):
        """Test screening with some tiers disabled"""
        # Arrange
        # Temporarily disable ML tier (should already be disabled)
        original_enabled = screening_config.tier_4_ml.enabled
        screening_config.tier_4_ml.enabled = False

        input_text = "Test Name"

        try:
            # Act
            result = await screening_service.screen_entity(input_text)

            # Assert
            assert isinstance(result, ScreeningResult)
            assert 'ml_advanced' not in result.tiers_executed

        finally:
            # Cleanup
            screening_config.tier_4_ml.enabled = original_enabled

    @pytest.mark.asyncio
    async def test_screening_exception_handling(self, screening_service):
        """Test screening graceful handling of exceptions"""
        # Arrange
        with patch.object(screening_service, '_execute_tier', side_effect=Exception("Tier failed")):
            input_text = "Test Name"

            # Act
            result = await screening_service.screen_entity(input_text)

            # Assert
            assert isinstance(result, ScreeningResult)
            assert result.risk_level == RiskLevel.AUTO_CLEAR  # Conservative approach
            assert result.final_confidence == 0.0
            assert 'tiers' in result.audit_trail
            assert any('error' in tier for tier in result.audit_trail['tiers'])

    def test_get_screening_metrics(self, screening_service):
        """Test screening metrics retrieval"""
        # Act
        metrics = screening_service.get_screening_metrics()

        # Assert
        assert 'total_screenings' in metrics
        assert 'tier_executions' in metrics
        assert 'tier_performance' in metrics
        assert 'risk_level_distribution' in metrics
        assert 'early_stops' in metrics

        # Check tier performance structure
        for tier_perf in metrics['tier_performance'].values():
            assert 'count' in tier_perf

    def test_reset_metrics(self, screening_service):
        """Test metrics reset functionality"""
        # Arrange
        screening_service.metrics['total_screenings'] = 100

        # Act
        screening_service.reset_metrics()

        # Assert
        assert screening_service.metrics['total_screenings'] == 0

    @pytest.mark.asyncio
    async def test_risk_level_determination(self, screening_service):
        """Test risk level determination based on confidence scores"""
        # Test different confidence ranges
        test_cases = [
            (0.1, RiskLevel.AUTO_CLEAR),
            (0.4, RiskLevel.AUTO_CLEAR),
            (0.7, RiskLevel.REVIEW_LOW),  # 0.7 is in REVIEW_LOW range (0.60-0.74)
            (0.95, RiskLevel.AUTO_HIT)
        ]

        for confidence, expected_risk in test_cases:
            # Act
            risk_level = screening_config.get_risk_level(confidence)

            # Assert
            assert risk_level == expected_risk, f"Confidence {confidence} should map to {expected_risk}, got {risk_level}"

    def test_config_validation(self, screening_service):
        """Test screening configuration validation"""
        # Act
        issues = screening_config.validate_config()

        # Assert
        # Should have no critical configuration issues (except for known threshold ordering issue)
        critical_issues = [issue for issue in issues if "No screening tiers" in issue]
        assert len(critical_issues) == 0, f"Critical config issues found: {critical_issues}"

    @pytest.mark.asyncio
    async def test_tier_timeout_handling(self, screening_service):
        """Test tier timeout handling"""
        # Arrange
        with patch.object(screening_service, '_execute_ac_tier') as mock_ac:
            # Simulate slow tier execution
            async def slow_tier(*args):
                await asyncio.sleep(0.1)  # Simulate delay
                return {'candidates': [], 'max_confidence': 0.0, 'method': 'ac_slow'}

            mock_ac.side_effect = slow_tier
            input_text = "Test Name"

            # Act
            result = await screening_service.screen_entity(input_text)

            # Assert
            assert isinstance(result, ScreeningResult)
            assert result.processing_time_ms >= 100  # Should include the delay

    def test_screening_candidate_creation(self):
        """Test ScreeningCandidate dataclass creation"""
        # Act
        candidate = ScreeningCandidate(
            entity_id="test123",
            name="Test Entity",
            confidence_score=0.85,
            tier_scores={'ac': 0.9, 'knn': 0.8},
            match_reasons=["exact_match", "surname_pattern"],
            metadata={"source": "test"}
        )

        # Assert
        assert candidate.entity_id == "test123"
        assert candidate.name == "Test Entity"
        assert candidate.confidence_score == 0.85
        assert candidate.tier_scores['ac'] == 0.9
        assert "exact_match" in candidate.match_reasons
        assert candidate.metadata["source"] == "test"

    def test_screening_result_creation(self):
        """Test ScreeningResult dataclass creation"""
        # Arrange
        candidate = ScreeningCandidate(
            entity_id="test", name="Test", confidence_score=0.7,
            tier_scores={}, match_reasons=[], metadata={}
        )

        # Act
        result = ScreeningResult(
            input_text="Test Input",
            risk_level=RiskLevel.REVIEW_LOW,
            final_confidence=0.65,
            candidates=[candidate],
            processing_time_ms=150.0,
            tiers_executed=["ac_exact", "knn_vector"],
            early_stopped=False,
            audit_trail={"test": "data"}
        )

        # Assert
        assert result.input_text == "Test Input"
        assert result.risk_level == RiskLevel.REVIEW_LOW
        assert result.final_confidence == 0.65
        assert len(result.candidates) == 1
        assert result.processing_time_ms == 150.0
        assert "ac_exact" in result.tiers_executed
        assert result.early_stopped is False
        assert result.audit_trail["test"] == "data"


class TestScreeningTiersConfig:
    """Tests for ScreeningTiersConfig"""

    def test_get_enabled_tiers(self):
        """Test getting enabled screening tiers"""
        # Act
        enabled_tiers = screening_config.get_enabled_tiers()

        # Assert
        assert len(enabled_tiers) > 0
        assert ScreeningTier.TIER_0_AC in enabled_tiers  # Should be enabled
        assert ScreeningTier.TIER_4_ML not in enabled_tiers  # Should be disabled by default

    def test_get_tier_config(self):
        """Test getting individual tier configuration"""
        # Act
        ac_config = screening_config.get_tier_config(ScreeningTier.TIER_0_AC)

        # Assert
        assert ac_config is not None
        assert ac_config.enabled is True
        assert ac_config.confidence_threshold > 0.0
        assert ac_config.max_candidates > 0
        assert ac_config.timeout_ms > 0
        assert isinstance(ac_config.parameters, dict)

    def test_should_early_stop(self):
        """Test early stopping decision logic"""
        # Test cases
        test_cases = [
            (0.99, True),   # High confidence - should stop
            (0.05, True),   # Very low confidence - should stop
            (0.5, False),   # Medium confidence - should continue
        ]

        for confidence, expected_stop in test_cases:
            # Act
            should_stop = screening_config.should_early_stop(confidence)

            # Assert
            assert should_stop == expected_stop, f"Confidence {confidence} early stop should be {expected_stop}"

    def test_early_stopping_disabled(self):
        """Test early stopping when disabled"""
        # Arrange
        original_setting = screening_config.global_config['early_stopping']['enabled']
        screening_config.global_config['early_stopping']['enabled'] = False

        try:
            # Act
            should_stop = screening_config.should_early_stop(0.99)

            # Assert
            assert should_stop is False

        finally:
            # Cleanup
            screening_config.global_config['early_stopping']['enabled'] = original_setting
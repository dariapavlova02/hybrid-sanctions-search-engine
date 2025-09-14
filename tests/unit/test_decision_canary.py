"""
Canary tests for decision engine stability.

Tests that decision engine produces consistent results for fixed inputs
to detect regressions and ensure decision stability over time.
"""

import pytest
from typing import Dict, List, Tuple

from src.ai_service.core.decision_engine import DecisionEngine
from src.ai_service.contracts.decision_contracts import (
    DecisionInput, SmartFilterInfo, SignalsInfo, SimilarityInfo, RiskLevel
)
from src.ai_service.monitoring.metrics_service import MetricsService


class TestDecisionCanary:
    """Canary tests for decision engine stability"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.engine = DecisionEngine()
        self.metrics_service = MetricsService()
        self.engine_with_metrics = DecisionEngine(metrics_service=self.metrics_service)
    
    def test_low_risk_canary_scenarios(self):
        """Test LOW risk scenarios remain stable"""
        low_risk_scenarios = [
            # Scenario 1: Low confidence across all indicators
            DecisionInput(
                text="Обычный текст без подозрительных элементов",
                language="uk",
                smartfilter=SmartFilterInfo(should_process=True, confidence=0.2),
                signals=SignalsInfo(person_confidence=0.1, org_confidence=0.1),
                similarity=SimilarityInfo(cos_top=0.3)
            ),
            # Scenario 2: Moderate smart filter, low others
            DecisionInput(
                text="Платеж физическому лицу",
                language="uk",
                smartfilter=SmartFilterInfo(should_process=True, confidence=0.4),
                signals=SignalsInfo(person_confidence=0.2, org_confidence=0.1),
                similarity=SimilarityInfo(cos_top=0.2)
            ),
            # Scenario 3: No similarity, low confidence
            DecisionInput(
                text="Документ без подозрительных признаков",
                language="uk",
                smartfilter=SmartFilterInfo(should_process=True, confidence=0.3),
                signals=SignalsInfo(person_confidence=0.15, org_confidence=0.2),
                similarity=SimilarityInfo(cos_top=None)
            )
        ]
        
        for i, scenario in enumerate(low_risk_scenarios):
            result = self.engine.decide(scenario)
            
            # Verify LOW risk
            assert result.risk == RiskLevel.LOW, f"Scenario {i+1} should be LOW risk, got {result.risk}"
            assert result.score < 0.65, f"Scenario {i+1} score {result.score} should be < 0.65"
            
            # Verify score is deterministic (same input = same output)
            result2 = self.engine.decide(scenario)
            assert result.score == result2.score, f"Scenario {i+1} score should be deterministic"
            assert result.risk == result2.risk, f"Scenario {i+1} risk should be deterministic"
    
    def test_medium_risk_canary_scenarios(self):
        """Test MEDIUM risk scenarios remain stable"""
        medium_risk_scenarios = [
            # Scenario 1: Moderate indicators across the board
            DecisionInput(
                text="Платеж в банк с умеренными показателями",
                language="uk",
                smartfilter=SmartFilterInfo(should_process=True, confidence=0.7),
                signals=SignalsInfo(person_confidence=0.7, org_confidence=0.6),
                similarity=SimilarityInfo(cos_top=0.71)
            ),
            # Scenario 2: High person confidence, moderate others
            DecisionInput(
                text="Перевод известному лицу",
                language="uk",
                smartfilter=SmartFilterInfo(should_process=True, confidence=0.7),
                signals=SignalsInfo(person_confidence=0.8, org_confidence=0.6),
                similarity=SimilarityInfo(cos_top=0.7)  # Should reach MEDIUM threshold
            ),
            # Scenario 3: Date match bonus
            DecisionInput(
                text="Платеж с указанием даты рождения",
                language="uk",
                smartfilter=SmartFilterInfo(should_process=True, confidence=0.65),
                signals=SignalsInfo(person_confidence=0.6, org_confidence=0.5, date_match=True),
                similarity=SimilarityInfo(cos_top=0.65)
            )
        ]
        
        for i, scenario in enumerate(medium_risk_scenarios):
            result = self.engine.decide(scenario)
            
            # Verify MEDIUM risk
            assert result.risk == RiskLevel.MEDIUM, f"Scenario {i+1} should be MEDIUM risk, got {result.risk}"
            assert 0.65 <= result.score < 0.85, f"Scenario {i+1} score {result.score} should be in [0.65, 0.85)"
            
            # Verify score is deterministic
            result2 = self.engine.decide(scenario)
            assert result.score == result2.score, f"Scenario {i+1} score should be deterministic"
            assert result.risk == result2.risk, f"Scenario {i+1} risk should be deterministic"
    
    def test_high_risk_canary_scenarios(self):
        """Test HIGH risk scenarios remain stable"""
        high_risk_scenarios = [
            # Scenario 1: High confidence across all indicators
            DecisionInput(
                text="Оплата ТОВ 'ПРИВАТБАНК' Ивану Петрову, 1980-01-01, ИНН 1234567890",
                language="uk",
                smartfilter=SmartFilterInfo(should_process=True, confidence=0.9),
                signals=SignalsInfo(person_confidence=0.9, org_confidence=0.8, date_match=True, id_match=True),
                similarity=SimilarityInfo(cos_top=0.95)
            ),
            # Scenario 2: Very high similarity with moderate others
            DecisionInput(
                text="Высокий риск по сходству",
                language="uk",
                smartfilter=SmartFilterInfo(should_process=True, confidence=0.9),
                signals=SignalsInfo(person_confidence=0.8, org_confidence=0.7, date_match=True),  # Add date bonus
                similarity=SimilarityInfo(cos_top=0.95)
            ),
            # Scenario 3: Multiple strong indicators
            DecisionInput(
                text="Множественные индикаторы высокого риска",
                language="uk",
                smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
                signals=SignalsInfo(person_confidence=0.85, org_confidence=0.75, date_match=True, id_match=True),
                similarity=SimilarityInfo(cos_top=0.9)
            )
        ]
        
        for i, scenario in enumerate(high_risk_scenarios):
            result = self.engine.decide(scenario)
            
            # Verify HIGH risk
            assert result.risk == RiskLevel.HIGH, f"Scenario {i+1} should be HIGH risk, got {result.risk}"
            assert result.score >= 0.85, f"Scenario {i+1} score {result.score} should be >= 0.85"
            
            # Verify score is deterministic
            result2 = self.engine.decide(scenario)
            assert result.score == result2.score, f"Scenario {i+1} score should be deterministic"
            assert result.risk == result2.risk, f"Scenario {i+1} risk should be deterministic"
    
    def test_skip_risk_canary_scenarios(self):
        """Test SKIP risk scenarios remain stable"""
        skip_risk_scenarios = [
            # Scenario 1: Smart filter says skip
            DecisionInput(
                text="Текст для пропуска по умному фильтру",
                language="uk",
                smartfilter=SmartFilterInfo(should_process=False, confidence=0.9),
                signals=SignalsInfo(person_confidence=0.8, org_confidence=0.7),
                similarity=SimilarityInfo(cos_top=0.9)
            ),
            # Scenario 2: Skip with high confidence indicators
            DecisionInput(
                text="Пропуск несмотря на высокие показатели",
                language="uk",
                smartfilter=SmartFilterInfo(should_process=False, confidence=0.95),
                signals=SignalsInfo(person_confidence=0.9, org_confidence=0.8, date_match=True, id_match=True),
                similarity=SimilarityInfo(cos_top=0.95)
            )
        ]
        
        for i, scenario in enumerate(skip_risk_scenarios):
            result = self.engine.decide(scenario)
            
            # Verify SKIP risk
            assert result.risk == RiskLevel.SKIP, f"Scenario {i+1} should be SKIP risk, got {result.risk}"
            assert result.score == 0.0, f"Scenario {i+1} score should be 0.0 for SKIP"
            assert "smartfilter_skip" in result.reasons, f"Scenario {i+1} should have smartfilter_skip reason"
            
            # Verify score is deterministic
            result2 = self.engine.decide(scenario)
            assert result.score == result2.score, f"Scenario {i+1} score should be deterministic"
            assert result.risk == result2.risk, f"Scenario {i+1} risk should be deterministic"
    
    def test_edge_case_canary_scenarios(self):
        """Test edge case scenarios remain stable"""
        edge_case_scenarios = [
            # Scenario 1: All None values
            DecisionInput(
                text="",
                language=None,
                smartfilter=None,
                signals=None,
                similarity=None
            ),
            # Scenario 2: Mixed None and valid values
            DecisionInput(
                text="Смешанные значения",
                language="uk",
                smartfilter=SmartFilterInfo(should_process=True, confidence=0.5),
                signals=SignalsInfo(person_confidence=0.3, org_confidence=None, date_match=None, id_match=True),
                similarity=SimilarityInfo(cos_top=0.4, cos_p95=None)
            ),
            # Scenario 3: Extreme values
            DecisionInput(
                text="Экстремальные значения",
                language="uk",
                smartfilter=SmartFilterInfo(should_process=True, confidence=1.0),
                signals=SignalsInfo(person_confidence=1.0, org_confidence=1.0, date_match=True, id_match=True),
                similarity=SimilarityInfo(cos_top=1.0)
            )
        ]
        
        for i, scenario in enumerate(edge_case_scenarios):
            result = self.engine.decide(scenario)
            
            # Verify valid result (no exceptions)
            assert result.risk in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.SKIP]
            assert 0.0 <= result.score <= 1.0
            assert isinstance(result.reasons, list)
            assert len(result.reasons) > 0
            
            # Verify score is deterministic
            result2 = self.engine.decide(scenario)
            assert result.score == result2.score, f"Edge case {i+1} score should be deterministic"
            assert result.risk == result2.risk, f"Edge case {i+1} risk should be deterministic"
    
    def test_score_calculation_stability(self):
        """Test that score calculation is mathematically stable"""
        # Test with known values for predictable score
        scenario = DecisionInput(
            text="Тест стабильности расчета",
            language="uk",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.5),
            signals=SignalsInfo(person_confidence=0.4, org_confidence=0.3, date_match=True, id_match=False),
            similarity=SimilarityInfo(cos_top=0.6)
        )
        
        # Calculate expected score manually
        expected_score = (
            0.25 * 0.5 +  # smartfilter contribution
            0.3 * 0.4 +   # person contribution
            0.15 * 0.3 +  # org contribution
            0.25 * 0.6 +  # similarity contribution
            0.07          # date bonus
        )
        expected_score = min(expected_score, 1.0)
        
        result = self.engine.decide(scenario)
        
        # Verify score matches expected calculation
        assert abs(result.score - expected_score) < 0.001, f"Score {result.score} should match expected {expected_score}"
        
        # Verify multiple runs produce same result
        for _ in range(10):
            result_repeat = self.engine.decide(scenario)
            assert result.score == result_repeat.score, "Score should be identical across multiple runs"
            assert result.risk == result_repeat.risk, "Risk should be identical across multiple runs"
    
    def test_reasons_stability(self):
        """Test that reasons generation is stable"""
        scenario = DecisionInput(
            text="Тест стабильности причин",
            language="uk",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
            signals=SignalsInfo(person_confidence=0.9, org_confidence=0.7, date_match=True, id_match=True),
            similarity=SimilarityInfo(cos_top=0.95)
        )
        
        result1 = self.engine.decide(scenario)
        result2 = self.engine.decide(scenario)
        
        # Verify reasons are identical
        assert result1.reasons == result2.reasons, "Reasons should be identical across multiple runs"
        
        # Verify expected reasons are present
        reasons_text = " ".join(result1.reasons)
        assert "strong_smartfilter_signal" in reasons_text
        assert "person_evidence_strong" in reasons_text
        assert "id_exact_match" in reasons_text
        assert "dob_match" in reasons_text
        assert "high_vector_similarity" in reasons_text
    
    def test_metrics_recording_stability(self):
        """Test that metrics recording works correctly"""
        scenario = DecisionInput(
            text="Тест метрик",
            language="uk",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.6),
            signals=SignalsInfo(person_confidence=0.7, org_confidence=0.5, date_match=True, id_match=False),
            similarity=SimilarityInfo(cos_top=0.8)
        )
        
        # Record metrics
        result = self.engine_with_metrics.decide(scenario)
        
        # Verify metrics were recorded
        decision_total = self.metrics_service.get_metric_summary("decision_total")
        assert decision_total["count"] > 0, "decision_total should be recorded"
        
        decision_score = self.metrics_service.get_metric_summary("decision_score")
        assert decision_score["count"] > 0, "decision_score should be recorded"
        
        # Verify risk-specific metrics
        decision_total_values = self.metrics_service.get_metric_values("decision_total")
        assert len(decision_total_values) > 0, "Should have decision_total values"
        assert decision_total_values[0].labels["risk"] == result.risk.value, "Risk label should match result"
    
    def test_configuration_stability(self):
        """Test that different configurations produce stable results"""
        from src.ai_service.config.settings import DecisionConfig
        
        # Test with custom configuration
        custom_config = DecisionConfig(
            w_smartfilter=0.3,
            w_person=0.4,
            w_org=0.2,
            w_similarity=0.1,
            thr_high=0.8,
            thr_medium=0.6
        )
        
        custom_engine = DecisionEngine(config=custom_config)
        
        scenario = DecisionInput(
            text="Тест конфигурации",
            language="uk",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.7),
            signals=SignalsInfo(person_confidence=0.6, org_confidence=0.5),
            similarity=SimilarityInfo(cos_top=0.7)
        )
        
        result1 = custom_engine.decide(scenario)
        result2 = custom_engine.decide(scenario)
        
        # Verify results are stable with custom config
        assert result1.score == result2.score, "Score should be stable with custom config"
        assert result1.risk == result2.risk, "Risk should be stable with custom config"
        assert result1.reasons == result2.reasons, "Reasons should be stable with custom config"
    
    def test_batch_consistency(self):
        """Test that batch processing produces consistent results"""
        scenarios = [
            DecisionInput(
                text="Сценарий 1",
                language="uk",
                smartfilter=SmartFilterInfo(should_process=True, confidence=0.3),
                signals=SignalsInfo(person_confidence=0.2, org_confidence=0.1),
                similarity=SimilarityInfo(cos_top=0.2)
            ),
            DecisionInput(
                text="Сценарий 2",
                language="uk",
                smartfilter=SmartFilterInfo(should_process=True, confidence=0.7),
                signals=SignalsInfo(person_confidence=0.6, org_confidence=0.5),
                similarity=SimilarityInfo(cos_top=0.6)
            ),
            DecisionInput(
                text="Сценарий 3",
                language="uk",
                smartfilter=SmartFilterInfo(should_process=True, confidence=0.9),
                signals=SignalsInfo(person_confidence=0.8, org_confidence=0.7, date_match=True, id_match=True),
                similarity=SimilarityInfo(cos_top=0.9)
            )
        ]
        
        # Process scenarios multiple times
        results_batch1 = [self.engine.decide(scenario) for scenario in scenarios]
        results_batch2 = [self.engine.decide(scenario) for scenario in scenarios]
        
        # Verify all results are identical
        for i, (result1, result2) in enumerate(zip(results_batch1, results_batch2)):
            assert result1.score == result2.score, f"Batch scenario {i+1} score should be identical"
            assert result1.risk == result2.risk, f"Batch scenario {i+1} risk should be identical"
            assert result1.reasons == result2.reasons, f"Batch scenario {i+1} reasons should be identical"
    
    def test_canary_regression_detection(self):
        """Test that canary can detect regressions"""
        # This test documents the expected behavior for regression detection
        # In a real scenario, this would be run in CI/CD to detect changes
        
        baseline_scenarios = [
            # LOW risk baseline
            (DecisionInput(
                text="Базовый низкий риск",
                language="uk",
                smartfilter=SmartFilterInfo(should_process=True, confidence=0.2),
                signals=SignalsInfo(person_confidence=0.1, org_confidence=0.1),
                similarity=SimilarityInfo(cos_top=0.2)
            ), RiskLevel.LOW, 0.0, 0.3),  # Expected risk, min score, max score
            
            # MEDIUM risk baseline
            (DecisionInput(
                text="Базовый средний риск",
                language="uk",
                smartfilter=SmartFilterInfo(should_process=True, confidence=0.7),
                signals=SignalsInfo(person_confidence=0.7, org_confidence=0.6),
                similarity=SimilarityInfo(cos_top=0.71)
            ), RiskLevel.MEDIUM, 0.65, 0.85),
            
            # HIGH risk baseline
            (DecisionInput(
                text="Базовый высокий риск",
                language="uk",
                smartfilter=SmartFilterInfo(should_process=True, confidence=0.9),
                signals=SignalsInfo(person_confidence=0.9, org_confidence=0.8, date_match=True, id_match=True),
                similarity=SimilarityInfo(cos_top=0.95)
            ), RiskLevel.HIGH, 0.85, 1.0),
        ]
        
        for scenario, expected_risk, min_score, max_score in baseline_scenarios:
            result = self.engine.decide(scenario)
            
            # Verify risk level hasn't changed
            assert result.risk == expected_risk, f"Risk level regression detected: expected {expected_risk}, got {result.risk}"
            
            # Verify score is within expected range
            assert min_score <= result.score <= max_score, f"Score regression detected: expected [{min_score}, {max_score}], got {result.score}"
            
            # Verify reasons are present and meaningful
            assert len(result.reasons) > 0, "Reasons should not be empty"
            assert "Overall risk score:" in result.reasons[0], "Should have overall score in reasons"

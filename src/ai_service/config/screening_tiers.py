"""
Multi-tier screening architecture configuration
Implements the recommended kNN + AC + fuzzy matching approach
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List


class ScreeningTier(Enum):
    """Screening tiers in processing order"""

    TIER_0_AC = "ac_exact"  # Aho-Corasick exact matching
    TIER_1_BLOCKING = "blocking"  # Cheap candidate filtering
    TIER_2_KNN = "knn_vector"  # kNN vector similarity
    TIER_3_RERANK = "reranking"  # Re-ranking with multiple features
    TIER_4_ML = "ml_advanced"  # Advanced ML models (future)


class RiskLevel(Enum):
    """Risk assessment levels"""

    AUTO_CLEAR = "auto_clear"  # < 0.3 - automatic clear
    REVIEW_LOW = "review_low"  # 0.3-0.6 - low priority review
    REVIEW_HIGH = "review_high"  # 0.6-0.85 - high priority review
    AUTO_HIT = "auto_hit"  # > 0.85 - automatic hit


@dataclass
class TierConfig:
    """Configuration for a screening tier"""

    enabled: bool = True
    confidence_threshold: float = 0.5
    max_candidates: int = 200
    timeout_ms: int = 1000
    parameters: Dict[str, Any] = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


class ScreeningTiersConfig:
    """Multi-tier screening configuration"""

    def __init__(self):
        """Initialize screening tiers configuration"""

        # Tier 0: AC (Aho-Corasick) - Exact/deterministic matching
        self.tier_0_ac = TierConfig(
            enabled=True,
            confidence_threshold=0.95,  # High confidence for exact matches
            max_candidates=50,  # Limited for exact patterns
            timeout_ms=100,  # Fast execution
            parameters={
                "case_sensitive": False,
                "match_whole_words": True,
                "include_aliases": True,
                "include_regex_patterns": True,
                "boost_exact_matches": 1.2,
                "patterns": [
                    "document_numbers",
                    "exact_aliases",
                    "regulatory_titles",
                    "sanctioned_entities",
                ],
            },
        )

        # Tier 1: Blocking - Cheap candidate filtering
        self.tier_1_blocking = TierConfig(
            enabled=True,
            confidence_threshold=0.0,  # No threshold - just filtering
            max_candidates=10000,  # Pre-filter from large dataset
            timeout_ms=200,
            parameters={
                "surname_key_length": 4,
                "phonetic_algorithms": ["double_metaphone", "ua_soundex", "ru_soundex"],
                "first_initial_match": True,
                "birth_year_window": 5,
                "country_codes": True,
                "minimum_name_length": 3,
                "blocking_keys": [
                    "surname_normalized",
                    "phonetic_surname",
                    "first_initial_surname",
                    "birth_decade_surname",
                    "country_surname",
                ],
            },
        )

        # Tier 2: kNN vector similarity with char n-grams
        self.tier_2_knn = TierConfig(
            enabled=True,
            confidence_threshold=0.4,
            max_candidates=200,
            timeout_ms=500,
            parameters={
                "vector_algorithms": [
                    {
                        "name": "char_tfidf",
                        "ngram_range": (3, 5),
                        "weight": 0.4,
                        "similarity": "cosine",
                    },
                    {
                        "name": "word_tfidf",
                        "ngram_range": (1, 2),
                        "weight": 0.3,
                        "similarity": "cosine",
                    },
                ],
                "hnsw_config": {"ef_construction": 200, "ef_search": 100, "M": 16},
                "index_type": "hnsw",
                "distance_metric": "cosine",
                "normalize_vectors": True,
            },
        )

        # Tier 3: Re-ranking with multiple features
        self.tier_3_rerank = TierConfig(
            enabled=True,
            confidence_threshold=0.3,
            max_candidates=50,
            timeout_ms=800,
            parameters={
                "features": {
                    "fasttext_subword": {
                        "weight": 0.35,
                        "model": "multi_cc_fasttext",
                        "similarity": "cosine",
                    },
                    "jaro_winkler": {"weight": 0.25, "threshold": 0.7},
                    "exact_rules": {
                        "weight": 0.4,
                        "rules": [
                            "exact_surname_match",
                            "initial_surname_match",
                            "birth_date_match",
                            "birth_place_match",
                            "passport_match",
                            "ukrainian_surname_suffix",
                        ],
                    },
                },
                "scoring_model": "weighted_ensemble",
                "calibration_method": "platt_scaling",
            },
        )

        # Tier 4: Advanced ML models (future implementation)
        self.tier_4_ml = TierConfig(
            enabled=False,  # Disabled by default
            confidence_threshold=0.6,
            max_candidates=20,
            timeout_ms=1500,
            parameters={
                "models": {
                    "distil_mbert": {
                        "enabled": False,
                        "weight": 0.4,
                        "max_length": 512,
                    },
                    "xlm_r": {"enabled": False, "weight": 0.3, "max_length": 512},
                    "contrastive_learning": {
                        "enabled": False,
                        "weight": 0.3,
                        "trained_on_sanctions": True,
                    },
                },
                "ensemble_method": "soft_voting",
                "gpu_acceleration": True,
            },
        )

        # Decision thresholds for final scoring
        # Threshold calibration (ascending order):
        # Auto-Clear < 0.60
        # Review-Low 0.60 - 0.74
        # Review-High 0.74 - 0.86
        # Auto-Hit >= 0.86
        self.decision_thresholds = {
            RiskLevel.AUTO_CLEAR: 0.59,
            RiskLevel.REVIEW_LOW: 0.60,
            RiskLevel.REVIEW_HIGH: 0.74,
            RiskLevel.AUTO_HIT: 0.86,
        }

        # Global processing parameters
        self.global_config = {
            "max_total_timeout_ms": 3000,
            "enable_caching": True,
            "cache_ttl_seconds": 3600,
            "parallel_processing": True,
            "early_stopping": {
                "enabled": True,
                "auto_hit_threshold": 0.95,
                "auto_clear_threshold": 0.1,
            },
            "audit_logging": {
                "enabled": True,
                "log_all_matches": True,
                "log_false_positives": True,
                "reason_codes": True,
            },
            "performance_monitoring": {
                "enabled": True,
                "track_tier_performance": True,
                "alert_slow_queries": True,
                "sla_targets": {"p95_latency_ms": 500, "p99_latency_ms": 1000},
            },
        }

    def get_tier_config(self, tier: ScreeningTier) -> TierConfig:
        """Get configuration for specific tier"""
        tier_configs = {
            ScreeningTier.TIER_0_AC: self.tier_0_ac,
            ScreeningTier.TIER_1_BLOCKING: self.tier_1_blocking,
            ScreeningTier.TIER_2_KNN: self.tier_2_knn,
            ScreeningTier.TIER_3_RERANK: self.tier_3_rerank,
            ScreeningTier.TIER_4_ML: self.tier_4_ml,
        }
        return tier_configs.get(tier)

    def get_enabled_tiers(self) -> List[ScreeningTier]:
        """Get list of enabled screening tiers in processing order"""
        enabled_tiers = []
        for tier in ScreeningTier:
            config = self.get_tier_config(tier)
            if config and config.enabled:
                enabled_tiers.append(tier)
        return enabled_tiers

    def get_risk_level(self, confidence_score: float) -> RiskLevel:
        """Determine risk level based on confidence score"""
        if confidence_score >= self.decision_thresholds[RiskLevel.AUTO_HIT]:
            return RiskLevel.AUTO_HIT
        elif confidence_score >= self.decision_thresholds[RiskLevel.REVIEW_HIGH]:
            return RiskLevel.REVIEW_HIGH
        elif confidence_score >= self.decision_thresholds[RiskLevel.REVIEW_LOW]:
            return RiskLevel.REVIEW_LOW
        else:
            return RiskLevel.AUTO_CLEAR

    def should_early_stop(self, confidence_score: float) -> bool:
        """Check if processing should stop early based on score"""
        if not self.global_config["early_stopping"]["enabled"]:
            return False

        auto_hit = self.global_config["early_stopping"]["auto_hit_threshold"]
        auto_clear = self.global_config["early_stopping"]["auto_clear_threshold"]

        return confidence_score >= auto_hit or confidence_score <= auto_clear

    def validate_config(self) -> List[str]:
        """Validate configuration and return any issues"""
        issues = []

        # Check that at least one tier is enabled
        enabled_tiers = self.get_enabled_tiers()
        if not enabled_tiers:
            issues.append("No screening tiers are enabled")

        # Check decision thresholds are in ascending order
        thresholds = [
            self.decision_thresholds[RiskLevel.AUTO_CLEAR],
            self.decision_thresholds[RiskLevel.REVIEW_LOW],
            self.decision_thresholds[RiskLevel.REVIEW_HIGH],
            self.decision_thresholds[RiskLevel.AUTO_HIT],
        ]

        for i in range(1, len(thresholds)):
            if thresholds[i] <= thresholds[i - 1]:
                issues.append("Decision thresholds are not in ascending order")
                break

        # Check timeout configurations
        total_timeout = sum(
            config.timeout_ms
            for config in [
                self.tier_0_ac,
                self.tier_1_blocking,
                self.tier_2_knn,
                self.tier_3_rerank,
                self.tier_4_ml,
            ]
            if config.enabled
        )

        if total_timeout > self.global_config["max_total_timeout_ms"]:
            issues.append(
                f"Sum of tier timeouts ({total_timeout}ms) exceeds max total timeout "
                f"({self.global_config['max_total_timeout_ms']}ms)"
            )

        return issues


# Global configuration instance
screening_config = ScreeningTiersConfig()

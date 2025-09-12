"""
Multi-tier sanctions screening orchestrator
Implements the comprehensive screening pipeline with kNN + AC + fuzzy matching
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..config.screening_tiers import (
    RiskLevel,
    ScreeningTier,
    TierConfig,
    screening_config,
)
from ..exceptions import ProcessingError
from ..utils import get_logger
from .blocking_service import BlockingService
from .high_recall_ac_generator import HighRecallACGenerator
from .reason_code_utils import compute_anomaly_reason_codes
from .reranker_service import RerankerService
from .vector_index_service import CharTfidfVectorIndex, VectorIndexConfig
from .watchlist_index_service import WatchlistIndexService


@dataclass
class ScreeningCandidate:
    """Candidate match from screening"""

    entity_id: str
    name: str
    confidence_score: float
    tier_scores: Dict[str, float]
    match_reasons: List[str]
    metadata: Dict[str, Any]


@dataclass
class ScreeningResult:
    """Final screening result"""

    input_text: str
    risk_level: RiskLevel
    final_confidence: float
    candidates: List[ScreeningCandidate]
    processing_time_ms: float
    tiers_executed: List[str]
    early_stopped: bool
    audit_trail: Dict[str, Any]


class MultiTierScreeningService:
    """Multi-tier sanctions screening service"""

    def __init__(self, orchestrator_service=None):
        """Initialize multi-tier screening service"""
        self.logger = get_logger(__name__)
        self.orchestrator = orchestrator_service
        self.config = screening_config
        # Recall-optimized AC and blocking
        self._ac_high_recall = HighRecallACGenerator()
        self._blocking = BlockingService()
        self._vector_index = CharTfidfVectorIndex(VectorIndexConfig())
        self._reranker = RerankerService(orchestrator=self.orchestrator)
        self._watchlist = WatchlistIndexService(VectorIndexConfig())

        # Validate configuration
        config_issues = self.config.validate_config()
        if config_issues:
            self.logger.warning(f"Configuration issues: {config_issues}")

        # Performance metrics
        self.metrics = {
            "total_screenings": 0,
            "tier_executions": {tier.value: 0 for tier in ScreeningTier},
            "tier_performance": {tier.value: [] for tier in ScreeningTier},
            "risk_level_distribution": {level.value: 0 for level in RiskLevel},
            "early_stops": 0,
        }

        self.logger.info("Multi-tier screening service initialized")

    async def screen_entity(
        self, input_text: str, entity_metadata: Optional[Dict[str, Any]] = None
    ) -> ScreeningResult:
        """
        Perform multi-tier screening on input text

        Args:
            input_text: Text to screen (name, payment description, etc.)
            entity_metadata: Additional metadata (DOB, country, etc.)

        Returns:
            ScreeningResult with risk assessment and candidates
        """
        start_time = time.time()
        self.metrics["total_screenings"] += 1

        try:
            # Initialize screening context
            screening_context = {
                "input_text": input_text,
                "metadata": entity_metadata or {},
                "candidates": [],
                "confidence_scores": {},
                "audit_trail": {"start_time": datetime.now().isoformat(), "tiers": []},
            }

            # Execute enabled screening tiers in sequence
            enabled_tiers = self.config.get_enabled_tiers()
            tiers_executed = []
            early_stopped = False

            for tier in enabled_tiers:
                tier_config = self.config.get_tier_config(tier)
                tier_start = time.time()

                try:
                    # Execute tier
                    tier_result = await self._execute_tier(
                        tier, tier_config, screening_context
                    )
                    # Accumulate candidates/signals across tiers
                    if tier_result.get("candidates"):
                        context_cands = screening_context.setdefault("candidates", [])
                        context_cands.extend(tier_result["candidates"])
                    if tier_result.get("signals"):
                        context_sigs = screening_context.setdefault("signals", {})
                        # merge per-tier signals
                        for k, v in tier_result["signals"].items():
                            context_sigs[k] = v

                    # Record tier execution
                    tier_time_ms = (time.time() - tier_start) * 1000
                    self.metrics["tier_executions"][tier.value] += 1
                    # Ensure tier_performance is a list
                    if not isinstance(self.metrics["tier_performance"][tier.value], list):
                        self.metrics["tier_performance"][tier.value] = []
                    self.metrics["tier_performance"][tier.value].append(tier_time_ms)
                    tiers_executed.append(tier.value)

                    # Add to audit trail
                    screening_context["audit_trail"]["tiers"].append(
                        {
                            "tier": tier.value,
                            "execution_time_ms": tier_time_ms,
                            "candidates_found": len(tier_result.get("candidates", [])),
                            "max_confidence": tier_result.get("max_confidence", 0.0),
                        }
                    )

                    # Check for early stopping
                    max_confidence = tier_result.get("max_confidence", 0.0)
                    if self.config.should_early_stop(max_confidence):
                        early_stopped = True
                        self.metrics["early_stops"] += 1
                        self.logger.info(
                            f"Early stopping at tier {tier.value} with confidence {max_confidence}"
                        )
                        break

                except Exception as e:
                    self.logger.error(f"Error executing tier {tier.value}: {e}")
                    screening_context["audit_trail"]["tiers"].append(
                        {
                            "tier": tier.value,
                            "error": str(e),
                            "execution_time_ms": (time.time() - tier_start) * 1000,
                        }
                    )

            # Compute final result
            final_result = await self._compute_final_result(
                screening_context, tiers_executed, early_stopped, start_time
            )

            # Update metrics
            self.metrics["risk_level_distribution"][final_result.risk_level.value] += 1

            return final_result

        except Exception as e:
            self.logger.error(f"Screening failed for '{input_text}': {e}")

            # Return error result
            return ScreeningResult(
                input_text=input_text,
                risk_level=RiskLevel.REVIEW_HIGH,  # Conservative approach on error
                final_confidence=0.0,
                candidates=[],
                processing_time_ms=(time.time() - start_time) * 1000,
                tiers_executed=[],
                early_stopped=False,
                audit_trail={"error": str(e)},
            )

    async def _execute_tier(
        self, tier: ScreeningTier, config: TierConfig, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a specific screening tier"""

        if tier == ScreeningTier.TIER_0_AC:
            return await self._execute_ac_tier(config, context)
        elif tier == ScreeningTier.TIER_1_BLOCKING:
            return await self._execute_blocking_tier(config, context)
        elif tier == ScreeningTier.TIER_2_KNN:
            return await self._execute_knn_tier(config, context)
        elif tier == ScreeningTier.TIER_3_RERANK:
            return await self._execute_rerank_tier(config, context)
        elif tier == ScreeningTier.TIER_4_ML:
            return await self._execute_ml_tier(config, context)
        else:
            raise ProcessingError(f"Unknown screening tier: {tier}")

    async def _execute_ac_tier(
        self, config: TierConfig, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute high-recall Aho-Corasick pre-match tier.
        Extract recall-optimized patterns/signals from the input text.
        """
        text = context["input_text"]
        candidates: List[Dict[str, Any]] = []
        signals: Dict[str, Any] = {}

        # Generate recall-optimized AC patterns from observed text
        patterns = self._ac_high_recall.generate_high_recall_patterns(
            text, language="auto"
        )
        export = self._ac_high_recall.export_for_high_recall_ac(patterns)
        stats = self._ac_high_recall.get_recall_statistics(patterns)

        signals["ac_export"] = export
        signals["ac_stats"] = stats
        # Text anomaly reason codes
        anomalies = compute_anomaly_reason_codes(text)
        if anomalies:
            signals["anomalies_reason_codes"] = anomalies
            # Track robustness metrics
            rob = self.metrics.setdefault(
                "robustness", {"mixed_script": 0, "homoglyph": 0, "zwsp": 0}
            )
            if "RC_MIXED_SCRIPT" in anomalies:
                rob["mixed_script"] += 1
            if "RC_HOMOGLYPH" in anomalies:
                rob["homoglyph"] += 1
            if "RC_ZWSP" in anomalies:
                rob["zwsp"] += 1

        # Convert presence of patterns to conservative candidate signals
        t0 = len(export.get("tier_0_exact", []))
        t1 = len(export.get("tier_1_high_recall", []))
        t2 = len(export.get("tier_2_medium_recall", []))
        t3 = len(export.get("tier_3_broad_recall", []))

        # Strong documentary signals -> near auto-hit confidence
        if t0 > 0:
            candidates.append(
                {
                    "entity_id": "AC_DOC_SIGNAL",
                    "name": "Documentary signal (ID/IBAN/passport)",
                    "confidence": 0.97,
                    "method": "ac_tier0_exact",
                    "pattern_count": t0,
                    "reason_codes": ["RC_DOCNUM"],
                }
            )

        # High-recall name/company signals
        if t1 > 0:
            # Scale confidence slightly with volume, cap below auto-hit
            conf = min(0.90, 0.80 + 0.02 * min(t1, 5))
            candidates.append(
                {
                    "entity_id": "AC_NAME_SIGNAL",
                    "name": "High-recall name/company signal",
                    "confidence": conf,
                    "method": "ac_tier1_high",
                    "pattern_count": t1,
                    "reason_codes": ["RC_EXACT", "RC_ALIAS"],
                }
            )

        if t2 > 0:
            candidates.append(
                {
                    "entity_id": "AC_PARTIAL_SIGNAL",
                    "name": "Partial/initials signal",
                    "confidence": 0.65,
                    "method": "ac_tier2_medium",
                    "pattern_count": t2,
                    "reason_codes": ["RC_INITIALS", "RC_TYPO"],
                }
            )

        if t3 > 0:
            candidates.append(
                {
                    "entity_id": "AC_BROAD_SIGNAL",
                    "name": "Broad recall signal (aggressive)",
                    "confidence": 0.55,
                    "method": "ac_tier3_broad",
                    "pattern_count": t3,
                    "reason_codes": ["RC_PHONETIC", "RC_SPACING"],
                }
            )

        max_confidence = max((c["confidence"] for c in candidates), default=0.0)

        return {
            "candidates": candidates,
            "signals": signals,
            "max_confidence": max_confidence,
            "method": "aho_corasick_high_recall",
        }

    async def _execute_blocking_tier(
        self, config: TierConfig, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute blocking/candidate filtering tier using computed keys."""
        candidates: List[Dict[str, Any]] = []
        text = context["input_text"]
        metadata = context.get("metadata", {})

        keys = self._blocking.compute_keys(text, metadata)
        signals = {"blocking_keys": keys.to_dict()}

        # Convert keys into candidate buckets with indicative confidence
        # Strong IDs
        if keys.edrpou:
            candidates.append(
                {
                    "entity_id": f"BLOCK:EDRPOU:{keys.edrpou}",
                    "name": "EDRPOU key",
                    "confidence": 0.85,
                    "method": "blocking_id",
                    "reason_codes": ["RC_METADATA_EDRPOU"],
                }
            )
        if keys.tax_id:
            candidates.append(
                {
                    "entity_id": f"BLOCK:TAX:{keys.tax_id}",
                    "name": "Tax ID key",
                    "confidence": 0.80,
                    "method": "blocking_id",
                    "reason_codes": ["RC_METADATA_TAXID"],
                }
            )

        # Name-based keys
        if keys.first_initial_surname:
            candidates.append(
                {
                    "entity_id": f"BLOCK:FI_SURN:{keys.first_initial_surname}",
                    "name": "First initial + surname",
                    "confidence": 0.62,
                    "method": "blocking_name",
                    "reason_codes": ["RC_INITIALS"],
                }
            )
        elif keys.surname_normalized:
            candidates.append(
                {
                    "entity_id": f"BLOCK:SURN:{keys.surname_normalized}",
                    "name": "Surname key",
                    "confidence": 0.58,
                    "method": "blocking_name",
                    "reason_codes": [
                        "RC_PHONETIC" if keys.phonetic_surname else "RC_EXACT"
                    ],
                }
            )
        if keys.phonetic_surname:
            candidates.append(
                {
                    "entity_id": f"BLOCK:PHON:{keys.phonetic_surname}",
                    "name": "Phonetic surname key",
                    "confidence": 0.57,
                    "method": "blocking_phonetic",
                    "reason_codes": ["RC_PHONETIC"],
                }
            )

        # Company-based keys
        if keys.legal_form_key and keys.org_core_stem:
            candidates.append(
                {
                    "entity_id": f"BLOCK:ORG:{keys.legal_form_key}:{keys.org_core_stem[:24]}",
                    "name": "Company core + legal form",
                    "confidence": 0.66,
                    "method": "blocking_company",
                    "reason_codes": ["RC_LEGALFORM"],
                }
            )

        # Metadata boosts
        if keys.birth_year and (keys.surname_normalized or keys.first_initial_surname):
            candidates.append(
                {
                    "entity_id": f"BLOCK:DOBY:{keys.birth_year}",
                    "name": "Surname + DOB year",
                    "confidence": 0.63,
                    "method": "blocking_meta",
                    "reason_codes": ["RC_METADATA_DOB"],
                }
            )
        if keys.country_code and (keys.surname_normalized or keys.org_core_stem):
            candidates.append(
                {
                    "entity_id": f"BLOCK:COUNTRY:{keys.country_code}",
                    "name": "Country + surname/org",
                    "confidence": 0.60,
                    "method": "blocking_meta",
                    "reason_codes": ["RC_METADATA_DOB"],
                }
            )

        max_confidence = max((c["confidence"] for c in candidates), default=0.0)
        return {
            "candidates": candidates,
            "signals": signals,
            "max_confidence": max_confidence,
            "method": "blocking",
        }

    async def _execute_knn_tier(
        self, config: TierConfig, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute kNN vector similarity tier (char TF-IDF, FAISS if available).
        Uses persistent watchlist if loaded, else falls back to ephemeral AC pool.
        """
        candidates: List[Dict[str, Any]] = []
        signals = context.get("signals", {})
        export = signals.get("ac_export") if isinstance(signals, dict) else None
        input_text = context["input_text"]

        # If persistent watchlist is ready, use it
        if self._watchlist and self._watchlist.ready():
            try:
                top = self._watchlist.search(
                    input_text, top_k=min(200, config.max_candidates)
                )
            except Exception as e:
                self.logger.warning(
                    f"Watchlist search failed, fallback to ephemeral: {e}"
                )
                top = []
            tfidf_cos_map: Dict[str, float] = {}
            for doc_id, score in top:
                wd = self._watchlist.get_doc(doc_id)
                if not wd:
                    continue
                tfidf_cos_map[doc_id] = float(score)
                reasons = (
                    ["RC_ALIAS"] if len((wd.text or "").split()) > 1 else ["RC_TYPO"]
                )
                # Append anomaly reason codes if any
                if isinstance(signals, dict) and signals.get("anomalies_reason_codes"):
                    reasons += [
                        r for r in signals["anomalies_reason_codes"] if r not in reasons
                    ]
                candidates.append(
                    {
                        "entity_id": wd.doc_id,
                        "name": wd.text,
                        "confidence": float(0.40 + 0.50 * max(0.0, min(1.0, score))),
                        "method": "knn_vector_watchlist",
                        "reason_codes": reasons,
                        "entity_type": wd.entity_type,
                        "doc_metadata": wd.metadata,
                    }
                )
            return {
                "candidates": candidates,
                "signals": {"tfidf_cos_map": tfidf_cos_map},
                "max_confidence": max(
                    (c["confidence"] for c in candidates), default=0.0
                ),
                "method": "knn_vector_watchlist",
            }

        # Build ephemeral index from AC candidate patterns if no persistent index
        docs: List[Tuple[str, str]] = []
        if export:
            pool = []
            for t in ("tier_1_high_recall", "tier_2_medium_recall"):
                pool.extend(export.get(t, []))
            # Dedup and keep reasonable size
            uniq = []
            seen = set()
            for p in pool:
                if not p:
                    continue
                k = p.lower().strip()
                if k not in seen:
                    seen.add(k)
                    uniq.append(p)
                if len(uniq) >= config.max_candidates:
                    break
            docs = [(f"DOC_{i}", txt) for i, txt in enumerate(uniq)]

        if not docs:
            return {"candidates": [], "max_confidence": 0.0, "method": "knn_vector"}

        try:
            self._vector_index.rebuild(docs)
            top = self._vector_index.search(input_text, top_k=min(20, len(docs)))
        except Exception as e:
            self.logger.warning(f"Vector index search failed: {e}")
            top = []

        # Map back to names and produce candidates
        id2text = {d[0]: d[1] for d in docs}
        tfidf_cos_map: Dict[str, float] = {}
        for doc_id, score in top:
            name = id2text.get(doc_id, "")
            if not name:
                continue
            tfidf_cos_map[doc_id] = float(score)
            candidates.append(
                {
                    "entity_id": doc_id,
                    "name": name,
                    "confidence": float(
                        0.40 + 0.50 * max(0.0, min(1.0, score))
                    ),  # scale to 0.4..0.9
                    "method": "knn_vector",
                    "reason_codes": (
                        ["RC_TYPO"] if len(name.split()) == 1 else ["RC_ALIAS"]
                    ),
                }
            )

        # Attach tfidf_cos_map to signals for reranker
        return {
            "candidates": candidates,
            "signals": {"tfidf_cos_map": tfidf_cos_map},
            "max_confidence": max((c["confidence"] for c in candidates), default=0.0),
            "method": "knn_vector",
        }

    async def _execute_rerank_tier(
        self, config: TierConfig, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute re-ranking tier combining embeddings, tfidf, string sims and rules."""
        existing = context.get("candidates", [])
        if not existing:
            return {"candidates": [], "max_confidence": 0.0, "method": "reranking"}
        signals = context.get("signals", {})
        tfidf_cos_map = {}
        if isinstance(signals, dict):
            tfidf_cos_map = signals.get("tfidf_cos_map", {}) or {}
        try:
            reranked = await self._reranker.rerank(
                observed=context["input_text"],
                candidates=existing,
                meta=context.get("metadata", {}),
                tfidf_cos_map=tfidf_cos_map,
            )
        except Exception as e:
            self.logger.warning(f"Rerank failed: {e}")
            reranked = existing
        return {
            "candidates": reranked,
            "max_confidence": max(
                (c.get("confidence", 0.0) for c in reranked), default=0.0
            ),
            "method": "reranking",
        }

    # ---- Admin ops: watchlist reload/status -----------------------------

    def reload_watchlist(
        self, snapshot_dir: str, as_overlay: bool = False
    ) -> Dict[str, Any]:
        info = self._watchlist.reload_snapshot(snapshot_dir, as_overlay=as_overlay)
        return {"status": "ok", **info}

    def get_watchlist_status(self) -> Dict[str, Any]:
        return self._watchlist.status()

    async def _execute_ml_tier(
        self, config: TierConfig, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute advanced ML tier (placeholder)"""
        # Placeholder for future ML implementation
        return {
            "candidates": [],
            "max_confidence": 0.0,
            "method": "ml_advanced",
            "note": "ML tier not implemented yet",
        }

    async def _compute_final_result(
        self,
        context: Dict[str, Any],
        tiers_executed: List[str],
        early_stopped: bool,
        start_time: float,
    ) -> ScreeningResult:
        """Compute final screening result"""
        # Aggregate candidates accumulated in context
        raw_cands = context.get("candidates", [])
        screening_cands: List[ScreeningCandidate] = []
        for c in raw_cands:
            try:
                screening_cands.append(
                    ScreeningCandidate(
                        entity_id=str(c.get("entity_id", "UNKNOWN")),
                        name=str(c.get("name", "")),
                        confidence_score=float(c.get("confidence", 0.0)),
                        tier_scores={
                            c.get("method", "tier"): float(c.get("confidence", 0.0))
                        },
                        match_reasons=c.get("reason_codes", []) or [],
                        metadata={
                            k: v
                            for k, v in c.items()
                            if k
                            not in ("entity_id", "name", "confidence", "reason_codes")
                        },
                    )
                )
            except Exception:
                continue

        # Final confidence: max across tiers (recall-first)
        final_confidence = max(
            (c.confidence_score for c in screening_cands), default=0.0
        )
        # Metadata gating for Auto-Hit per design (DOB/EDRPOU/TaxID)
        meta = context.get("metadata", {}) or {}
        has_strong_meta = bool(
            meta.get("dob")
            or meta.get("beneficiary_edrpou")
            or meta.get("edrpou")
            or meta.get("tax_id")
        )
        # Start with numeric risk
        risk_level = self.config.get_risk_level(final_confidence)
        # Enforce metadata requirement for auto-hit
        if risk_level == RiskLevel.AUTO_HIT and not has_strong_meta:
            risk_level = RiskLevel.REVIEW_HIGH

        processing_time_ms = (time.time() - start_time) * 1000
        return ScreeningResult(
            input_text=context["input_text"],
            risk_level=risk_level,
            final_confidence=final_confidence,
            candidates=screening_cands,
            processing_time_ms=processing_time_ms,
            tiers_executed=tiers_executed,
            early_stopped=early_stopped,
            audit_trail=context["audit_trail"],
        )

    def get_screening_metrics(self) -> Dict[str, Any]:
        """Get screening performance metrics"""
        metrics = self.metrics.copy()

        # Calculate average tier performance
        tier_performance = {}
        for tier, times in metrics["tier_performance"].items():
            if times and isinstance(times, list) and all(isinstance(t, (int, float)) for t in times):
                tier_performance[tier] = {
                    "count": len(times),
                    "avg_ms": sum(times) / len(times),
                    "p95_ms": (
                        sorted(times)[int(0.95 * len(times))]
                        if len(times) > 20
                        else max(times)
                    ),
                    "p99_ms": (
                        sorted(times)[int(0.99 * len(times))]
                        if len(times) > 100
                        else max(times)
                    ),
                }
            else:
                tier_performance[tier] = {"count": 0}
        
        metrics["tier_performance"] = tier_performance
        # Ensure robustness slice metrics are present
        if "robustness" not in metrics:
            metrics["robustness"] = {"mixed_script": 0, "homoglyph": 0, "zwsp": 0}

        return metrics

    def reset_metrics(self) -> None:
        """Reset performance metrics"""
        self.metrics = {
            "total_screenings": 0,
            "tier_executions": {tier.value: 0 for tier in ScreeningTier},
            "tier_performance": {tier.value: [] for tier in ScreeningTier},
            "risk_level_distribution": {level.value: 0 for level in RiskLevel},
            "early_stops": 0,
        }
        self.logger.info("Screening metrics reset")

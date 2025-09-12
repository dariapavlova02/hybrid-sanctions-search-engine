"""
Reranker service: combines embeddings, TF-IDF cosine (optional),
string similarity, and rule-based boosts to produce final scores and reason codes.

Weights (default):
S = 0.55*embed_cos + 0.30*tfidf_cos + 0.10*jaro + 0.05*rule
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

try:
    from rapidfuzz.distance import JaroWinkler  # type: ignore

    _HAS_RAPIDFUZZ = True
except Exception:
    _HAS_RAPIDFUZZ = False
    from difflib import SequenceMatcher

from ..utils import get_logger
from .blocking_service import BlockingService
from .reason_code_utils import compute_anomaly_reason_codes


@dataclass
class RerankWeights:
    embed_cos: float = 0.55
    tfidf_cos: float = 0.30
    jaro: float = 0.10
    rule: float = 0.05


class RerankerService:
    def __init__(
        self, orchestrator=None, weights: Optional[RerankWeights] = None
    ) -> None:
        self.logger = get_logger(__name__)
        self.orchestrator = orchestrator
        self.weights = weights or RerankWeights()
        self.blocking = BlockingService()

    async def _embed(self, text: str) -> Optional[List[float]]:
        if not self.orchestrator or not hasattr(self.orchestrator, "embedding_service"):
            return None
        try:
            # EmbeddingService.get_embeddings is synchronous
            res = self.orchestrator.embedding_service.get_embeddings([text])
            if isinstance(res, dict) and res.get("success") and res.get("embeddings"):
                emb = res["embeddings"][0]
                return emb
        except Exception:
            pass
        return None

    def _cos(self, a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        s = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return s / (na * nb)

    def _jaro(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        if _HAS_RAPIDFUZZ:
            return (
                float(JaroWinkler.normalized_similarity(a, b)) / 100.0
                if JaroWinkler.normalized_similarity(a, b) > 1
                else float(JaroWinkler.normalized_similarity(a, b))
            )
        # difflib fallback ~ not jaro but acceptable fallback
        return SequenceMatcher(None, a, b).ratio()

    def _initials_match(self, observed: str, candidate: str) -> bool:
        import re

        # Extract first letters of first two tokens
        ob_tokens = re.findall(r"[A-Za-zА-Яа-яІіЇїЄєҐґ']+", observed)
        ca_tokens = re.findall(r"[A-Za-zА-Яа-яІіЇїЄєҐґ']+", candidate)
        if len(ob_tokens) < 2 or len(ca_tokens) < 2:
            return False
        return ob_tokens[0][0].upper() == ca_tokens[0][0].upper()

    def _legal_form_match(self, text: str, candidate: str) -> bool:
        t = text.lower()
        c = candidate.lower()
        for marker in (
            "ооо",
            "тов",
            "llc",
            "inc",
            "ltd",
            "ао",
            "пат",
            "прaт",
            "іп",
            "фоп",
            "ип",
        ):
            if marker in t and marker in c:
                return True
        return False

    def _rule_boost(
        self, observed: str, candidate: str, meta: Dict
    ) -> Tuple[float, List[str]]:
        score = 0.0
        reasons: List[str] = []
        # Initials
        if self._initials_match(observed, candidate):
            score += 0.01
            reasons.append("RC_INITIALS")
        # Phonetics
        try:
            obs_keys = self.blocking.compute_keys(observed).to_dict()
            can_keys = self.blocking.compute_keys(candidate).to_dict()
            if obs_keys.get("phonetic_surname") and obs_keys.get(
                "phonetic_surname"
            ) == can_keys.get("phonetic_surname"):
                score += 0.02
                reasons.append("RC_PHONETIC")
        except Exception:
            pass
        # Legal form
        if self._legal_form_match(observed, candidate):
            score += 0.01
            reasons.append("RC_LEGALFORM")
        # Metadata
        if meta:
            if meta.get("dob"):
                score += 0.03
                reasons.append("RC_METADATA_DOB")
            if meta.get("beneficiary_edrpou") or meta.get("edrpou"):
                score += 0.05
                reasons.append("RC_METADATA_EDRPOU")
            if meta.get("tax_id"):
                score += 0.05
                reasons.append("RC_METADATA_TAXID")
        # Length mismatch penalty
        if abs(len(observed) - len(candidate)) >= max(3, int(0.4 * len(observed))):
            score -= 0.02
        # Text anomaly reason codes (no score change, audit only)
        reasons += [
            rc for rc in compute_anomaly_reason_codes(observed) if rc not in reasons
        ]
        return score, reasons

    async def rerank(
        self,
        observed: str,
        candidates: List[Dict],
        meta: Optional[Dict] = None,
        tfidf_cos_map: Optional[Dict[str, float]] = None,
    ) -> List[Dict]:
        """Return candidates with updated 'confidence' and 'reason_codes' after rerank."""
        meta = meta or {}
        # Precompute observed embedding
        obs_emb = await self._embed(observed)
        out: List[Dict] = []
        for c in candidates:
            name = str(c.get("name") or c.get("entity_id") or "")
            cand_emb = await self._embed(name)
            cos_embed = self._cos(obs_emb, cand_emb) if (obs_emb and cand_emb) else 0.0
            cos_tfidf = float((tfidf_cos_map or {}).get(c.get("entity_id", ""), 0.0))
            jaro = self._jaro(observed, name)
            rule, rc = self._rule_boost(observed, name, meta)
            score = (
                self.weights.embed_cos * cos_embed
                + self.weights.tfidf_cos * cos_tfidf
                + self.weights.jaro * jaro
                + self.weights.rule * rule
            )
            nc = dict(c)
            nc["confidence"] = max(float(c.get("confidence", 0.0)), float(score))
            nc["features"] = {
                "cos_embed": round(cos_embed, 4),
                "cos_tfidf": round(cos_tfidf, 4),
                "jaro": round(jaro, 4),
                "rule_boost": round(rule, 4),
            }
            nc["reason_codes"] = sorted(list(set((c.get("reason_codes") or []) + rc)))
            out.append(nc)
        # Sort by updated confidence desc
        out.sort(key=lambda x: x.get("confidence", 0.0), reverse=True)
        return out

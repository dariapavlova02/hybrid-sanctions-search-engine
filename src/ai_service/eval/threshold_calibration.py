"""
Offline threshold calibration utilities for sanctions screening.

Inputs: arrays/samples of model scores and ground-truth labels (1=match, 0=non-match),
optionally flags like has_strong_meta (DOB/EDRPOU/TaxID) to enforce auto-hit gating.

Outputs: thresholds (auto_hit, review, clear) optimized to satisfy Recall@review target
and maximize Auto-hit precision or minimize review load.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class Sample:
    score: float
    label: int  # 1=positive (true match), 0=negative
    has_strong_meta: bool = False


@dataclass
class CalibrationResult:
    clear: float
    review: float
    auto_hit: float
    recall_at_review: float
    auto_hit_precision: float
    review_rate: float


def evaluate(
    samples: List[Sample], clear: float, review: float, auto_hit: float
) -> Dict[str, float]:
    """Evaluate metrics for given thresholds.
    - Decision:
        if score >= auto_hit and has_strong_meta: AUTO_HIT
        elif score >= review: REVIEW
        elif score < clear: CLEAR
        else: REVIEW (gray zone)
    - recall@review: proportion of positives that end up in (AUTO_HIT or REVIEW)
    - auto_hit_precision: proportion of AUTO_HIT that are true positive
    - review_rate: fraction sent to REVIEW per all
    """
    tp_auto = 0
    fp_auto = 0
    tp_review = 0
    fn = 0
    review_count = 0
    total = len(samples)
    pos_total = sum(1 for s in samples if s.label == 1)
    for s in samples:
        if s.score >= auto_hit and s.has_strong_meta:
            # auto-hit decision
            if s.label == 1:
                tp_auto += 1
            else:
                fp_auto += 1
        elif s.score >= review:
            # send to review
            review_count += 1
            if s.label == 1:
                tp_review += 1
        elif s.score < clear:
            # clear
            if s.label == 1:
                fn += 1
        else:
            # gray zone -> review
            review_count += 1
            if s.label == 1:
                tp_review += 1
    # Metrics
    recall_at_review = (tp_auto + tp_review) / pos_total if pos_total > 0 else 0.0
    auto_hit_precision = (
        tp_auto / (tp_auto + fp_auto) if (tp_auto + fp_auto) > 0 else 1.0
    )
    review_rate = review_count / total if total > 0 else 0.0
    return {
        "recall_at_review": recall_at_review,
        "auto_hit_precision": auto_hit_precision,
        "review_rate": review_rate,
    }


def grid_search_thresholds(
    samples: List[Sample],
    recall_target: float = 0.98,
    objective: str = "min_review",
    clear_bounds: Tuple[float, float] = (0.4, 0.7),
    review_bounds: Tuple[float, float] = (0.6, 0.9),
    auto_bounds: Tuple[float, float] = (0.8, 0.98),
    step: float = 0.01,
) -> CalibrationResult:
    """Brute-force grid search for thresholds under constraints.
    objective: 'min_review' or 'max_precision'
    """
    best: Optional[CalibrationResult] = None
    best_obj = float("inf") if objective == "min_review" else -1.0
    # iterate grids
    c = clear_bounds[0]
    while c <= clear_bounds[1]:
        r = max(c + step, review_bounds[0])
        while r <= review_bounds[1]:
            a = max(r, auto_bounds[0])
            while a <= auto_bounds[1]:
                m = evaluate(samples, c, r, a)
                if m["recall_at_review"] >= recall_target:
                    if objective == "min_review":
                        obj = m["review_rate"]
                        if obj < best_obj:
                            best_obj = obj
                            best = CalibrationResult(
                                c,
                                r,
                                a,
                                m["recall_at_review"],
                                m["auto_hit_precision"],
                                m["review_rate"],
                            )
                    else:  # max_precision
                        obj = m["auto_hit_precision"]
                        if obj > best_obj:
                            best_obj = obj
                            best = CalibrationResult(
                                c,
                                r,
                                a,
                                m["recall_at_review"],
                                m["auto_hit_precision"],
                                m["review_rate"],
                            )
                a = round(a + step, 4)
            r = round(r + step, 4)
        c = round(c + step, 4)
    # Fallback: return default if nothing meets target
    if best is None:
        m = evaluate(samples, 0.60, 0.74, 0.86)
        best = CalibrationResult(
            0.60,
            0.74,
            0.86,
            m["recall_at_review"],
            m["auto_hit_precision"],
            m["review_rate"],
        )
    return best

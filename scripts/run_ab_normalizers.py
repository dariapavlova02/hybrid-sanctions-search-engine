#!/usr/bin/env python3
"""
Standalone A/B runner for normalizers (bypasses pytest plugins).
Prints a summary table with accuracy, org accuracy, flags pass rate, and p95.
"""

import asyncio
import math
import time
from typing import Any, Dict, List
from pathlib import Path
import sys

# Ensure src/ is on sys.path
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_service.tests_ab_dataset import CASES
from ai_service.services.stopwords import STOP_ALL


def _std(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


async def _call_normalize(service: Any, text: str, language: str, flags: Dict[str, Any]):
    method = getattr(service, "normalize_async", None)
    if method is None:
        method = getattr(service, "normalize")
    return await method(
        text=text,
        language=language,
        remove_stop_words=flags.get("remove_stop_words", False),
        preserve_names=flags.get("preserve_names", True),
        enable_advanced_features=flags.get("enable_advanced_features", False),
    )


def _percentile95(values_ms: List[float]) -> float:
    if not values_ms:
        return 0.0
    arr = sorted(values_ms)
    k = max(0, min(len(arr) - 1, int(math.ceil(0.95 * len(arr)) - 1)))
    return arr[k]


def _check_flags_behavior(result: Any, flags: Dict[str, Any]) -> bool:
    passed = True
    tokens = getattr(result, "tokens", None) or []
    if flags.get("remove_stop_words", False):
        lower_tokens = {t.lower() for t in tokens}
        stop_found = [w for w in lower_tokens if w in STOP_ALL]
        if stop_found:
            passed = False
    if flags.get("preserve_names") is False and tokens:
        norm = getattr(result, "normalized", "")
        if "o'brien" in norm.lower():
            passed = False
    return passed


async def main():
    from ai_service.services.morphology.normalization_service import NormalizationService as MorphNorm
    from ai_service.services.normalization_service import NormalizationService as GenericNorm

    morph = MorphNorm()
    generic = GenericNorm()
    services = {"morph": morph, "generic": generic}

    metrics: Dict[str, Dict[str, Any]] = {
        name: {"times_ms": [], "correct": 0, "total": 0, "org_correct": 0, "org_total": 0, "flags_pass": 0, "flags_total": 0}
        for name in services
    }

    for case in CASES:
        text = case["input"]
        lang = case.get("lang", "auto")
        expected_std = {_std(s) for s in case.get("expected_normalized", [])}
        expected_orgs = case.get("expected_orgs")
        flags = case.get("flags", {})

        for svc_name, svc in services.items():
            t0 = time.perf_counter()
            res = await _call_normalize(svc, text, lang, flags)
            dt_ms = (time.perf_counter() - t0) * 1000.0

            m = metrics[svc_name]
            m["times_ms"].append(dt_ms)
            m["total"] += 1

            if _std(getattr(res, "normalized", "")) in expected_std:
                m["correct"] += 1

            if expected_orgs is not None:
                m["org_total"] += 1
                orgs = getattr(res, "organizations", None) or []
                if set(map(_std, orgs)) == set(map(_std, expected_orgs)):
                    m["org_correct"] += 1

            m["flags_total"] += 1
            if _check_flags_behavior(res, flags):
                m["flags_pass"] += 1

    # Print report
    header = f"{'service':<10} | {'accuracy':>8} | {'org_core_acc':>12} | {'flags_passed':>12} | {'p95_ms':>8}"
    print("\nAB Normalizers Report (standalone)")
    print(header)
    print("-" * len(header))
    for svc_name, m in metrics.items():
        acc = (m["correct"] / m["total"]) if m["total"] else 0.0
        org_acc = (m["org_correct"] / m["org_total"]) if m["org_total"] else 0.0
        flags_rate = (m["flags_pass"] / m["flags_total"]) if m["flags_total"] else 0.0
        p95 = _percentile95(m["times_ms"])
        print(f"{svc_name:<10} | {acc:8.3f} | {org_acc:12.3f} | {flags_rate:12.3f} | {p95:8.1f}")


if __name__ == "__main__":
    asyncio.run(main())

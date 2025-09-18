"""Utilities for running legacy/factory normalization in lockstep."""

from __future__ import annotations

import math
import threading
from itertools import zip_longest
from statistics import median
from time import perf_counter_ns
from typing import Any, Callable, Dict, List, Sequence, Tuple

from ai_service.contracts.base_contracts import NormalizationResult
from ai_service.layers.normalization.flags import NormalizationFlags
from ai_service.layers.normalization.normalization_service import (
    NormalizationService as FactoryService,
)
from ai_service.adapters.legacy_normalization_adapter import (
    LegacyNormalizationAdapter as LegacyService,
)
from ai_service.utils.feature_flags import NormalizationImplementation

_THREAD_LOCAL = threading.local()


def _get_legacy_service() -> LegacyService:
    service = getattr(_THREAD_LOCAL, "_legacy_service", None)
    if service is None:
        service = LegacyService()
        setattr(_THREAD_LOCAL, "_legacy_service", service)
    return service


def _get_factory_service() -> FactoryService:
    service = getattr(_THREAD_LOCAL, "_factory_service", None)
    if service is None:
        service = FactoryService()
        # Force factory path regardless of environment defaults
        service.feature_flags.update_flags(
            normalization_implementation=NormalizationImplementation.FACTORY,
            factory_rollout_percentage=100,
            enable_dual_processing=False,
        )
        setattr(_THREAD_LOCAL, "_factory_service", service)
    return service


def _flags_to_pipeline_kwargs(flags: NormalizationFlags) -> Dict[str, bool]:
    return {
        "remove_stop_words": flags.strict_stopwords,
        "preserve_names": flags.preserve_hyphenated_case,
        "enable_advanced_features": flags.enable_ac_tier0,
    }


def run_legacy(text: str, flags: NormalizationFlags) -> Tuple[NormalizationResult, Dict[str, Any]]:
    """Run the legacy normalization pipeline with latency measurements."""
    service = _get_legacy_service()
    kwargs = _flags_to_pipeline_kwargs(flags)
    start_ns = perf_counter_ns()
    result = service.normalize(
        text,
        language="auto",
        **kwargs,
    )
    end_ns = perf_counter_ns()
    elapsed_ms = (end_ns - start_ns) / 1_000_000.0
    timings = {
        "elapsed_ms": elapsed_ms,
        "started_ns": start_ns,
        "ended_ns": end_ns,
        "flags": flags.to_dict(),
        "pipeline": "legacy",
    }
    return result, timings


def run_factory(text: str, flags: NormalizationFlags) -> Tuple[NormalizationResult, Dict[str, Any]]:
    """Run the factory normalization pipeline with latency measurements."""
    service = _get_factory_service()
    kwargs = _flags_to_pipeline_kwargs(flags)
    start_ns = perf_counter_ns()
    result = service.normalize_sync(
        text,
        language="auto",
        **kwargs,
    )
    end_ns = perf_counter_ns()
    elapsed_ms = (end_ns - start_ns) / 1_000_000.0
    timings = {
        "elapsed_ms": elapsed_ms,
        "started_ns": start_ns,
        "ended_ns": end_ns,
        "flags": flags.to_dict(),
        "pipeline": "factory",
    }
    return result, timings


def _extract_roles(result: NormalizationResult) -> List[Tuple[str, str]]:
    roles: List[Tuple[str, str]] = []
    for entry in result.trace:
        if hasattr(entry, "model_dump"):
            payload = entry.model_dump()
        elif hasattr(entry, "dict"):
            payload = entry.dict()
        else:
            payload = dict(entry) if isinstance(entry, dict) else {}
        token = str(payload.get("token", ""))
        role = str(payload.get("role", ""))
        roles.append((token, role))
    return roles


def _diff_tokens(legacy_tokens: Sequence[str], factory_tokens: Sequence[str]) -> List[Dict[str, Any]]:
    diffs: List[Dict[str, Any]] = []
    for idx, (legacy_tok, factory_tok) in enumerate(
        zip_longest(legacy_tokens, factory_tokens, fillvalue=None)
    ):
        if legacy_tok == factory_tok:
            continue
        diffs.append({
            "index": idx,
            "legacy": legacy_tok,
            "factory": factory_tok,
        })
    return diffs


def _collect_trace_delta(legacy: NormalizationResult, factory: NormalizationResult, limit: int = 10) -> List[Dict[str, Any]]:
    deltas: List[Dict[str, Any]] = []
    for idx, (legacy_trace, factory_trace) in enumerate(
        zip_longest(legacy.trace, factory.trace, fillvalue=None)
    ):
        if legacy_trace is None and factory_trace is None:
            continue

        def _to_payload(item: Any) -> Dict[str, Any]:
            if item is None:
                return {}
            if hasattr(item, "model_dump"):
                return item.model_dump()
            if hasattr(item, "dict"):
                return item.dict()
            if isinstance(item, dict):
                return item
            return {
                "token": getattr(item, "token", None),
                "role": getattr(item, "role", None),
                "rule": getattr(item, "rule", None),
                "output": getattr(item, "output", None),
            }

        legacy_payload = _to_payload(legacy_trace)
        factory_payload = _to_payload(factory_trace)

        if legacy_payload == factory_payload:
            continue

        deltas.append({
            "index": idx,
            "legacy": legacy_payload,
            "factory": factory_payload,
        })

        if len(deltas) >= limit:
            break
    return deltas


def compare_results(
    legacy: NormalizationResult,
    factory: NormalizationResult,
) -> Dict[str, Any]:
    """Compare two normalization outputs and highlight divergences."""
    equal_text = legacy.normalized == factory.normalized
    legacy_roles = _extract_roles(legacy)
    factory_roles = _extract_roles(factory)
    equal_roles = legacy_roles == factory_roles
    diff_tokens = _diff_tokens(legacy.tokens, factory.tokens)
    trace_deltas = _collect_trace_delta(legacy, factory)

    return {
        "equal_text": equal_text,
        "equal_roles": equal_roles,
        "diff_tokens": diff_tokens,
        "trace_deltas": trace_deltas,
    }


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    idx = (len(values) - 1) * percentile
    lower = math.floor(idx)
    upper = math.ceil(idx)
    if lower == upper:
        return float(values[int(idx)])
    lower_value = values[lower]
    upper_value = values[upper]
    return float(lower_value + (upper_value - lower_value) * (idx - lower))


def measure_latency(samples_provider: Callable[[], Sequence[float]]) -> Dict[str, Any]:
    """Compute latency percentiles from the provided sample set."""
    raw = [float(value) for value in samples_provider()]
    raw.sort()
    return {
        "raw": raw,
        "p50_ms": _percentile(raw, 0.5),
        "p95_ms": _percentile(raw, 0.95),
        "p99_ms": _percentile(raw, 0.99),
        "median_ms": median(raw) if raw else 0.0,
    }


__all__ = [
    "NormalizationFlags",
    "run_legacy",
    "run_factory",
    "compare_results",
    "measure_latency",
]

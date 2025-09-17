"""Smoke test ensuring factory stays close to legacy on golden set."""

from __future__ import annotations

import json
from pathlib import Path

from tests.parity.parity_runner import (
    NormalizationFlags,
    compare_results,
    measure_latency,
    run_factory,
    run_legacy,
)

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "parity_golden.jsonl"


def _load_cases() -> list[dict[str, str]]:
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def test_factory_parity_smoke() -> None:
    cases = _load_cases()
    assert len(cases) == 10, "Fixture should contain 10 parity cases"

    flags = NormalizationFlags()
    equal_text_hits = 0
    factory_times: list[float] = []

    for case in cases:
        legacy_result, _ = run_legacy(case["text"], flags)
        factory_result, factory_timing = run_factory(case["text"], flags)
        comparison = compare_results(legacy_result, factory_result)
        if comparison["equal_text"]:
            equal_text_hits += 1
        factory_times.append(factory_timing["elapsed_ms"])

    parity_ratio = equal_text_hits / len(cases)
    factory_latency = measure_latency(lambda: factory_times)

    assert parity_ratio >= 0.7, "Factory parity should stay above 70% on smoke set"
    assert factory_latency["p95_ms"] <= 20.0, "Factory p95 must remain within 20ms"

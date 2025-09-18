"""
Golden parity tests for legacy vs factory normalization.

- Reads JSON golden cases from tests/golden_cases/golden_cases.json
- Compares legacy vs factory outputs (normalized text)
- Records per-case deltas + timings, emits artifacts
- Enforces acceptance gates (parity + p95/p99)

Фикс-пак переменные окружения:
- SAFE_OPTIMIZATION=0 (отключить безопасную оптимизацию)
- GOLDEN_PARITY_MIN=0.90 (цель ≥90%, фактически к 100%)
- GOLDEN_P95_MAX=0.010 (максимум p95 в секундах)
- GOLDEN_P99_MAX=0.020 (максимум p99 в секундах)

Временный гейт: en_*, ru_diminutive, uk_diminutive, ru_declension_to_nominative, 
uk_declension кейсы обязаны стать MATCH.
"""

from __future__ import annotations
import os
import json
import csv
import time
import hashlib
from dataclasses import dataclass
from pathlib import Path
from statistics import quantiles
from typing import List, Optional, Dict, Any

import pytest

# === SUT imports (adjust if your paths differ) ===
from src.ai_service.layers.normalization.normalization_service import NormalizationService
from src.ai_service.layers.normalization.processors.normalization_factory import (
    NormalizationFactory,
    NormalizationConfig,
)
from src.ai_service.utils.feature_flags import FeatureFlags

ART_DIR = Path("out")
ART_DIR.mkdir(parents=True, exist_ok=True)
GOLDEN_JSON = Path("tests/golden_cases/golden_cases.json")  # <-- JSON источник
SAFE_LABEL_ENV = "SAFE_OPTIMIZATION"         # any truthy → parity must be 100%
PARITY_MIN_ENV = "GOLDEN_PARITY_MIN"         # default 0.90
P95_MAX_ENV    = "GOLDEN_P95_MAX"            # seconds, default 0.010
P99_MAX_ENV    = "GOLDEN_P99_MAX"            # seconds, default 0.020

# Фикс-пак переменные окружения
SAFE_OPTIMIZATION_ENV = "SAFE_OPTIMIZATION"  # 0 = отключить безопасную оптимизацию
GOLDEN_PARITY_MIN_ENV = "GOLDEN_PARITY_MIN"  # цель ≥90%, фактически к 100%
GOLDEN_P95_MAX_ENV = "GOLDEN_P95_MAX"        # 0.010 секунд
GOLDEN_P99_MAX_ENV = "GOLDEN_P99_MAX"        # 0.020 секунд


@dataclass
class GoldenCase:
    case_id: str
    input_text: str
    language: str
    expected: str

def _trace_hash(trace: Any) -> str:
    # если есть trace.json() → сериализуем, иначе делаем str()
    s = str(trace)
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]

def _expected_normalized(case: dict) -> str:
    """Extract expected normalized text from golden case JSON structure."""
    personas = case.get("expected_personas", [])
    if not personas:
        return ""
    return " | ".join(persona["normalized"] for persona in personas)

def load_golden_cases() -> List[GoldenCase]:
    if not GOLDEN_JSON.exists():
        pytest.skip(f"Golden JSON not found: {GOLDEN_JSON}")
    
    with GOLDEN_JSON.open("r", encoding="utf-8") as f:
        cases_data = json.load(f)
    
    if not cases_data:
        pytest.skip("Golden JSON has no cases")
    
    rows: List[GoldenCase] = []
    for case in cases_data:
        rows.append(
            GoldenCase(
                case_id=case["id"],
                input_text=case["input"],
                language=case.get("language", "auto"),
                expected=_expected_normalized(case),
            )
        )
    
    return rows

@pytest.fixture(scope="session")
def legacy_service() -> NormalizationService:
    return NormalizationService()

@pytest.fixture(scope="session")
def factory_service() -> NormalizationFactory:
    return NormalizationFactory()

@pytest.fixture(scope="session")
def feature_flags() -> FeatureFlags:
    """
    На golden мы включаем ВСЕ фичи в shadow-режиме (если доступно),
    чтобы тест был честным к новой логике.
    Если в вашем проекте каких-то флагов нет — просто уберите их из конструктора.
    """
    return FeatureFlags(
        enable_spacy_ner=True,
        enable_nameparser_en=True,
        strict_stopwords=True,
        enhanced_diminutives=True,
        enhanced_gender_rules=True,
        ascii_fastpath=True,
        enable_ac_tier0=True,
        enable_vector_fallback=True,
        # добавляй свои флаги по мере надобности
        debug_tracing=True,
    )

@pytest.fixture(scope="session")
def factory_cfg() -> NormalizationConfig:
    # Конфиг без изменения внешнего контракта
    return NormalizationConfig(
        # поля могут называться иначе — подстрой под свой dataclass
        remove_stop_words=True,
        preserve_names=True,
        enable_advanced_features=True,
    )

@pytest.fixture(scope="session")
def golden() -> List[GoldenCase]:
    return load_golden_cases()

def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default

def _env_bool(name: str) -> bool:
    v = os.getenv(name, "").strip().lower()
    return v in {"1", "true", "yes", "y", "on"}

def _check_critical_cases_match(results: List[Dict[str, Any]]) -> None:
    """
    Временный гейт для критических кейсов фикс-пака.
    Проверяет, что en_*, ru_diminutive, uk_diminutive, ru_declension_to_nominative, 
    uk_declension кейсы стали MATCH.
    """
    critical_patterns = [
        "en_",
        "ru_diminutive", 
        "uk_diminutive",
        "ru_declension_to_nominative",
        "uk_declension"
    ]
    
    critical_failures = []
    for result in results:
        case_id = result["case_id"]
        if any(pattern in case_id for pattern in critical_patterns):
            if not result["parity_match"]:
                critical_failures.append(case_id)
    
    if critical_failures:
        pytest.fail(
            f"Критические кейсы фикс-пака не прошли MATCH: {critical_failures}. "
            f"Всего критических кейсов: {len([r for r in results if any(pattern in r['case_id'] for pattern in critical_patterns)])}"
        )

@pytest.mark.asyncio
async def test_golden_parity_suite(
    legacy_service: NormalizationService,
    factory_service: NormalizationFactory,
    feature_flags: FeatureFlags,
    factory_cfg: NormalizationConfig,
    golden: List[GoldenCase],
):
    results: List[Dict[str, Any]] = []
    legacy_times: List[float] = []
    factory_times: List[float] = []

    for case in golden:
        # LEGACY
        t0 = time.perf_counter()
        legacy_res = await legacy_service.normalize_async(
            case.input_text,
            language=case.language if case.language != "auto" else None,
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True,
        )
        t1 = time.perf_counter()

        # FACTORY (все флаги включены, но это shadow-mode — контракт не меняем)
        t2 = time.perf_counter()
        # Устанавливаем язык в конфиге если он не "auto"
        if case.language != "auto":
            factory_cfg.language = case.language
        factory_res = await factory_service.normalize_text(
            case.input_text,
            factory_cfg,
            feature_flags,
        )
        t3 = time.perf_counter()

        legacy_norm = getattr(legacy_res, "normalized", str(legacy_res))
        factory_norm = getattr(factory_res, "normalized", str(factory_res))

        legacy_times.append(t1 - t0)
        factory_times.append(t3 - t2)

        results.append(
            {
                "case_id": case.case_id,
                "lang": case.language,
                "input": case.input_text,
                "expected": case.expected,
                "legacy": legacy_norm,
                "factory": factory_norm,
                "parity_match": legacy_norm == factory_norm,
                "exp_match_legacy": (legacy_norm == case.expected) if case.expected else None,
                "exp_match_factory": (factory_norm == case.expected) if case.expected else None,
                "legacy_trace": _trace_hash(getattr(legacy_res, "trace", "")),
                "factory_trace": _trace_hash(getattr(factory_res, "trace", "")),
                "legacy_ms": round((t1 - t0) * 1000, 3),
                "factory_ms": round((t3 - t2) * 1000, 3),
            }
        )

    # ---- Артефакты
    diff_csv = ART_DIR / "golden_diff.csv"
    with diff_csv.open("w", newline="", encoding="utf-8") as f:
        fieldnames = list(results[0].keys())
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in results:
            w.writerow(r)

    # p95/p99
    def p95(vals: List[float]) -> float:
        # statistics.quantiles with n=100 for percentile-like
        return quantiles(vals, n=100)[94] if len(vals) >= 2 else (vals[0] if vals else 0.0)

    def p99(vals: List[float]) -> float:
        return quantiles(vals, n=100)[98] if len(vals) >= 2 else (vals[0] if vals else 0.0)

    parity = sum(1 for r in results if r["parity_match"]) / len(results)
    p95_legacy = p95(legacy_times)
    p99_legacy = p99(legacy_times)
    p95_factory = p95(factory_times)
    p99_factory = p99(factory_times)

    summary_md = ART_DIR / "golden_summary.md"
    with summary_md.open("w", encoding="utf-8") as f:
        f.write("# Golden Parity Summary\n\n")
        f.write(f"- Total cases: **{len(results)}**\n")
        f.write(f"- Parity: **{parity:.1%}**\n")
        f.write(f"- Legacy p95/p99: **{p95_legacy:.4f}s / {p99_legacy:.4f}s**\n")
        f.write(f"- Factory p95/p99: **{p95_factory:.4f}s / {p99_factory:.4f}s**\n\n")
        failed = [r for r in results if not r["parity_match"]]
        if failed:
            f.write("## Failing cases\n\n")
            for r in failed[:50]:
                f.write(f"- `{r['case_id']}` [{r['lang']}]:\n")
                f.write(f"  - input: `{r['input']}`\n")
                f.write(f"  - legacy: `{r['legacy']}`\n")
                f.write(f"  - factory: `{r['factory']}`\n")
                f.write(f"  - expected: `{r['expected']}`\n")
                f.write(f"  - traces: legacy={r['legacy_trace']} factory={r['factory_trace']}\n")

    # ---- Гейты
    # 1) Временный гейт для критических кейсов фикс-пака
    _check_critical_cases_match(results)
    
    # 2) Parity gate с новыми переменными окружения
    safe_mode = _env_bool(SAFE_OPTIMIZATION_ENV)
    parity_min = 1.0 if safe_mode else _env_float(GOLDEN_PARITY_MIN_ENV, 0.90)
    if parity < parity_min:
        fails = [r["case_id"] for r in results if not r["parity_match"]]
        pytest.fail(
            f"Golden parity {parity:.1%} < {parity_min:.0%}. "
            f"Failing cases: {fails[:10]} (… see {diff_csv})"
        )

    # 3) Perf gates — оцениваем именно factory с новыми переменными
    p95_max = _env_float(GOLDEN_P95_MAX_ENV, 0.010)
    p99_max = _env_float(GOLDEN_P99_MAX_ENV, 0.020)
    if p95_factory > p95_max or p99_factory > p99_max:
        pytest.fail(
            f"Performance gate failed: factory p95={p95_factory:.4f}s (thr {p95_max:.3f}), "
            f"p99={p99_factory:.4f}s (thr {p99_max:.3f}). See {summary_md}"
        )
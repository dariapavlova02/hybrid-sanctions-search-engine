# Sprint 1 – Root-Cause Analysis & Fix Plan

## Executive Summary
- **Parity status:** Factory parity stuck at ~72% because parity harness imports `normalization_service_legacy` which was deleted. Golden smoke cannot run, so no new diffs are generated. Morphology regressions (genitive survivors, missing nominative enforcement) and EN gates being disabled keep the gap far below the 90% goal.
- **Top P0s:**
  1. **RU/UK declensions** – feminine and dative forms stay untouched (`Марии`, `Олені`), traces ignore tokenizer/morph steps, and hyphenated surnames keep feminine endings → nominative never enforced.
  2. **EN nickname/title/apostrophe path** – feature flags never flip on per-request, env var names drifted, and hyphen handling splits tokens, so nicknames/titles stay and surnames lose second part.
  3. **Tokenizer rules** – collapse-double-dot traces disappear; hyphen-preserve flag never reaches tokenizer instance.
  4. **Property harness** – `hypothesis`/`rapidfuzz` missing from runtime and identifier extractor filters out all `inn` hits, so gates for DOB/TIN never trigger.
  5. **Business gate** – Decision engine promotes matches without checking TIN + DOB because signals never expose INN hits and there is no review hook; exception flag for religious exemptions is absent.
- **Expected after fixes:** parity runner loads legacy shim, RU/UK names return nominative baseline, EN features replay (nicknames, apostrophes, double surnames), property suite green, and decision layer routes name-only hits to REVIEW with `[TIN, DOB]` requirement.

## Findings
| Area | File:Line | Symptom | Root Cause | Fix (diff/patch) | Risk |
| --- | --- | --- | --- | --- | --- |
| RU/UK Morphology | `src/ai_service/layers/normalization/morphology_adapter.py:593` | `Марии`/`Олені` stay in oblique case | `_to_nominative_uncached_with_flags` picks first `case==nomn` even when tag is plural, returning plural nominative | Prefer non-plural nominatives, fall back to `parse.normal`, preserve case after correction | Low – affects nominative selection only |
| RU/UK Morphology | `src/ai_service/layers/normalization/processors/normalization_factory.py:460` | Trace lacks morphology/tokenizer steps (`collapse_double_dots` missing) | Trace builder iterates `classified_tokens`; final tokens/improvement traces never attached | Build trace from `final_tokens`, append improvement traces (`collapse_double_dots`, hyphen) | Low |
| RU/UK Morphology | `src/ai_service/layers/normalization/processors/normalization_factory.py:1661` | Collapse rule never surfaced | Post-tokenizer improvements emit `TokenTrace` but never reach final trace | Inject improvement traces and keep rule name `collapse_double_dots` | Low |
| EN Pipeline | `src/ai_service/layers/normalization/processors/normalization_factory.py:135` | Per-request flags ignored (tests enabling `fix_initials_double_dot`/`preserve_hyphenated_case` no-op) | `TokenizerService` constructed once with static flags from manager | Sync tokenizer flags from `effective_flags` before tokenization | Medium |
| EN Pipeline | `src/ai_service/utils/feature_flags.py:140` | Env overrides `FIX_INITIALS_DOUBLE_DOT`/`PRESERVE_HYPHENATED_CASE` unused | Renamed to `AISVC_FLAG_*`, tests still export old names | Accept legacy env keys as fallback | Low |
| EN Pipeline | `src/ai_service/layers/normalization/processors/normalization_factory.py:914` | `Emily Blunt-Krasinski` → `Emily Blunt Krasinski` | `_classify_english_names` splits hyphen tokens even when nameparser fallback is used | Skip hyphen splitting unless nameparser available; keep original token for trace | Medium |
| EN Pipeline | `src/ai_service/layers/normalization/processors/normalization_factory.py:1210` | `O'Connor` → `O Connor` | Apostrophe normalization stub just reassigns `'` → `'` | Normalize ASCII apostrophes to consistent char with titlecase helper | Medium |
| Tokenizer Traces | `src/ai_service/layers/normalization/tokenizer_service.py:134` | Collapse-double-dot never logged | Trace entry stored as dict but dropped later | Convert to `TokenTrace` so trace builder can merge | Low |
| Property Tests | `requirements-dev.txt` / runtime | `ModuleNotFoundError: hypothesis` | Dependency only declared in Poetry dev group; sandbox uses requirements txt | Add `hypothesis>=6.112`, `rapidfuzz` to dev requirements | Low |
| Identifier Extraction | `src/ai_service/layers/signals/extractors/identifier_extractor.py:26` | `signals.id_match` always False (INN never detected) | Allowed person/org ID types exclude `'inn'` key emitted by patterns | Include `'inn'` (and map to person/org sets) | Medium |
| Parity Harness | *new file* | `ModuleNotFoundError: normalization_service_legacy` | Legacy shim removed in refactor; parity tests still import | Add thin wrapper delegating to `LegacyNormalizationAdapter` | Medium |
| Business Rule | `src/ai_service/core/decision_engine.py`, `unified_orchestrator.py` | Name-only hits escalate without TIN+DOB | No gate; signals lacks INN detection due to extractor bug | After extractor fix, enforce review when `person_confidence` high but missing TIN/DOB; add feature flag for exemptions; expose required fields in `DecisionOutput.details` | Medium |

## Minimal Patchset
1. **Morphology fixes** – update nominative selection and trace assembly (`morphology_adapter.py`, `normalization_factory.py`).
2. **Tokenizer & flags** – sync tokenizer flags per request, surface collapse trace, append improvement traces (`normalization_factory.py`, `tokenizer_service.py`).
3. **English gates** – accept legacy env vars, keep hyphen tokens when nameparser unavailable, normalize apostrophes, ensure nickname/title removal uses new gates (`feature_flags.py`, `normalization_factory.py`).
4. **Identifier extraction** – allow `'inn'` in person/org sets; map to existing validation (`identifier_extractor.py`).
5. **Legacy shim** – add `src/ai_service/layers/normalization/normalization_service_legacy.py` that wraps `LegacyNormalizationAdapter` for parity runner.
6. **Business review hook** – enrich `DecisionEngine`/`UnifiedOrchestrator` to label name matches lacking TIN+DOB as `REVIEW` with `required_additional_fields=['TIN','DOB']`, guarded by new feature flag `require_tin_dob_gate`; expose list in response formatter.
7. **Deps & tooling** – extend `requirements-dev.txt` with `hypothesis`, `rapidfuzz`; add tests to cover apostrophes/hyphen/dob-tin gate; extend `out/golden_diff_updated.csv` with `legacy_trace`/`factory_trace` columns.

`patch_sprint1_minimal.diff` captures the concrete edits (see repo root).

## Test Plan
Run after applying fixes:
- `pytest -q tests/parity -k golden`
- `pytest -q tests/property`
- `pytest -q tests/smoke -k normalization`
- New targeted unit tests:
  - RU/UK micro checks (`платёж Ивану Петрову`, `перевод Марии Сидоровой`, `переказ Олені Петренко`).
  - EN nicknames/titles/apostrophes/double-surname smoke.
  - Decision-engine gate tests (name-only -> review; missing sanction TIN -> skip gate).

Acceptance gates:
- ≥90% golden parity once legacy shim active.
- 5/5 regression golden cases pass (declension, initials, hyphen, apostrophe, nickname).
- Property suite green with hypothesis.
- EN smoke passes (title drop, nickname expansion, apostrophe preservation, double surname).
- RU/UK nominative micro checks pass.

## Risk & Rollback
- **Risks:** Over-normalizing feminine surnames, accidentally forcing apostrophe conversions for non-name tokens, false positives on INN patterns, noisy review gating if signals confidence thresholds misaligned.
- **Rollback:**
  - Feature flags: disable `require_tin_dob_gate`, revert tokenizer improvements via existing flags, toggle EN nickname/title flags.
  - Code: revert patch set (git revert) or drop legacy shim to restore previous behavior if parity harness no longer needed.
- **Monitoring:**
  - Track morphology cache misses & post-fix error rate (existing cache metrics).
  - Alert on increase in EN apostrophe replacements.
  - Add counters for decision review gate triggers (TIN/DOB missing) to measure adoption.

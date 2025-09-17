**Architecture Snapshot**
- Service entrypoint `src/ai_service/main.py` exposes FastAPI; orchestrator wiring lives in `src/ai_service/core/orchestrator_factory.py`.
- The canonical pipeline is implemented by `UnifiedOrchestrator` (validation → smart filter → language → unicode → normalization → signals → search → decision).
- Use `arch_flow.mmd` for the end-to-end diagram (flowchart + sequence) and `layers_matrix.csv` for the detailed L0–L5 matrix.

**Layer Overview (L0–L5)**
| Level | Purpose | Key Modules | Output |
| --- | --- | --- | --- |
| L0 Normalization & Typing | Token cleanup, role tagging, morphology, gender adjustments | `normalization_service.py`, `processors/normalization_factory.py`, `tokenizer_service.py`, FSM `role_tagger_service.py` | `NormalizationResult` with trace + person/org candidates |
| L1 Exact / Whitelist | Tiered AC matching, dictionary boosts | `patterns/unified_pattern_service.py`, `search/elasticsearch_adapters.py` | High-confidence candidates with tier metadata |
| L2 Candidate Generation | AC→vector escalation, ANN fallback | `search/hybrid_search_service.py`, `search/config.py`, `embeddings/indexing/enhanced_vector_index_service.py` | `Candidate[]` + `SearchTrace` |
| L3 Cheap Rank & Signals | RapidFuzz boosts, DoB/ID anchors, signals enrichment | `hybrid_search_service.py`, `signals/signals_service.py`, `watchlist_index_service.py` | Ranked candidates, `SignalsResult` |
| L4 Rerank / Fusion | Overlay + active watchlist merge, future cross-encoder slot | `watchlist_index_service.py`, `hybrid_search_service.py` | Re-scored top-K with hybrid trace |
| L5 Decision & Policies | Weighted score, risk thresholds, policy reasons | `core/decision_engine.py`, `config/settings.py` | `DecisionOutput` appended to unified response |

**Dataflow Highlights**
- Validation/Sanitisation uses `ValidationService.validate_and_sanitize` to strip control characters; failure short-circuits with informative error.
- Smart filter (`SmartFilterAdapter.should_process`) optionally halts low-risk inputs; trace note propagated when `allow_smart_filter_skip` is true.
- Normalization hot path: tokenizer (with flag-aware improvements), FSM role tagging, diminutive resolution, morphology adapter, gender preservation. Perf-critical nodes marked in `arch_flow.mmd` (`class hot`).
- Signals extraction (`signals_service.py`) annotates persons/organizations and passes anchors (DoB/ID) forward to search + decision layers.
- Hybrid search invoked when search flags/opts demand candidates; escalation thresholds and fallback behaviour controlled via `HybridSearchConfig` and feature flags.
- Decision engine aggregates smart filter confidence, signals, similarity, search contributions; thresholds (`AI_DECISION__THR_*`) define auto-hit / review bands.

**Feature Flags & Config Controls**
- Inventory lives in `flags_inventory.json`; key toggles:
  - `use_factory_normalizer` (default off) – switches to refactored stack; parity tracked via dual processing.
  - `ascii_fastpath`, `fix_initials_double_dot`, `preserve_hyphenated_case`, `strict_stopwords` – tokenizer/morph tweaks (L0).
  - `enable_ac_tier0`, `enable_vector_fallback`, `enable_rapidfuzz_rerank`, `enable_dob_id_anchors` – search stack behaviour (L1–L3).
  - `enforce_nominative`, `preserve_feminine_surnames` – post-morph adjustments for compliance parity.
  - `enable_decision_engine`, `ENABLE_SMART_FILTER`, `ENABLE_EMBEDDINGS` – orchestrator/service wiring (env-driven in `ServiceConfig`).

**Normalization & Role Rules**
- `rules_catalog.csv` enumerates traceable transformations (digits passthrough, double-dot collapse, surname suffix detection, diminutive resolution, yo-strategy, nominative enforcement, etc.).
- Role trace entries originate from FSM reasons (`initial_detected`, `surname_suffix_detected`, `payment_context_filtered`, `ru_stopword_conflict`).
- Morph traces appended as `TokenTrace.notes` with `type=morph` (e.g., `to_nominative`, `preserve_feminine`).

**Search Stack Summary**
- `search_stack.md` details AC mapping, vector parameters (dense_vector 384d, HNSW `ef_search=100`), fusion weights, RapidFuzz rerank thresholds, fallback mechanics, and metrics hooks.
- `HybridSearchService` records per-stage latency; fallback TODO at `hybrid_search_service.py:278` noted in risk log.

**Caching & Performance**
- Tokenization caches: `TokenizerService` uses TTL LRU; `PerformanceOptimizer` keeps per-operation stats and caches (token, role, morphology, gender).
- Morphology adapter caches result per `(lang, token, flags)` via `lru_cache_with_metrics`. Cache metrics exposed through `cache_metrics` collected by Prometheus exporter.
- Search adapters pool HTTPX clients; fallback indexes persist in-memory vectors for offline mode.
- Slow-path logging: orchestrator warns when processing >100 ms; metrics service increments `processing.slow_requests`.

**Testing Pyramid & Coverage**
- Unit: `tests/unit/normalization`, `tests/unit/tokenizer`, `tests/unit/roles`, `tests/unit/embeddings`, `tests/unit/search` (placeholder) validate processors.
- Integration: `tests/integration/test_ascii_fastpath_equivalence.py`, search trace snapshots, flag propagation, shadow mode validation.
  Smoke: `tests/smoke/test_normalization_smoke.py`, `tests/smoke/test_smoke_gates.py` check gating combos.
- Canary suites: `tests/canary/test_canary_suites.py`, `tests/canary/data` cover risky transliterations, homoglyphs.
- Parity & golden: `tests/parity/test_golden_parity.py`, `tests/golden_cases` ensure factory vs legacy agreement.
- Performance: `tests/performance/test_performance_gates.py` exercises flag toggles under load; `benchmark_ac_performance.py` available for targeted runs.

**Risks & TODOs**
- See `risks_todo.md` for prioritised backlog: checksum validation gaps (P0), hybrid fallback TODO (P1), search integration checklist (P1), strict stopwords no-op (P2).

**Integration Hooks**
- `integration_hooks.md` maps concrete extension points for AC, phonetics, ANN, reranker, morphology, and SpaCy/nameparser wiring with required parameters and metrics.

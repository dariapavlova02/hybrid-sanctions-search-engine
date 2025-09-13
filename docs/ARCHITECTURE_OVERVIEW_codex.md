# AI-Normalization-Service: Architecture Overview (from code)

This document summarizes the actual architecture and logic present in the repository based on code and tests. It avoids speculative descriptions and cites concrete files and lines.

## Top‑Level Overview

- Key packages and modules (selected):
  - `src/ai_service/main.py` — FastAPI entrypoint and endpoints.
  - `src/ai_service/services/` — Core services (normalization, language/unicode, patterns, signals, smart filter, orchestrators, etc.).
  - `src/ai_service/services/morphology/` — Morphology-focused normalization pipeline (separate NormalizationService).
  - `src/ai_service/orchestration/` — Clean orchestrator v2, pipeline interfaces and stages.
  - `src/ai_service/services/processing/` — Another processing pipeline implementation.
  - `src/ai_service/data/dicts/` — Dictionaries (nicknames, diminutives, triggers, patterns).
  - `tests/` — Unit and integration tests defining expectations and contracts.

### Entrypoint & Endpoints

- FastAPI app is created in `src/ai_service/main.py` with multiple endpoints:
  - Health: `GET /health` (stats via orchestrator) `src/ai_service/main.py:204`
  - Process: `POST /process` (full orchestrated flow) `src/ai_service/main.py:231`
  - Normalize: `POST /normalize` (legacy normalize via orchestrator) `src/ai_service/main.py:273`
  - Batch: `POST /process-batch` `src/ai_service/main.py:312`
  - Similarity: `POST /search-similar` `src/ai_service/main.py:350`
  - Complexity: `POST /analyze-complexity` `src/ai_service/main.py:372`
  - Stats: `GET /stats` `src/ai_service/main.py:386`
  - Admin: `POST /clear-cache`, `POST /reset-stats` `src/ai_service/main.py:410`, `:424`
  - Root info: `GET /` `src/ai_service/main.py:455`

Short excerpt:

```py
# Endpoints (excerpt)
@app.post("/process")
async def process_text(request: ProcessTextRequest):
    result = await orchestrator.process_text(...)
    return {"success": result.success, ...}
```

Source: `src/ai_service/main.py:231`

### Orchestrators & Pipelines (where constructed)

- Legacy monolithic orchestrator: `src/ai_service/services/orchestrator_service.py` (initializes multiple services and coordinates steps; includes heuristics for reverse transliteration, payment-context extraction, etc.).
- Clean orchestrator (SOLID): `src/ai_service/orchestration/clean_orchestrator.py` builds a pipeline from pluggable stages (Validation → Unicode → Language → Normalization → Variants/Embeddings/SmartFilter).
- Another pipeline (Chain of Responsibility): `src/ai_service/services/processing/processing_pipeline.py` with stages including SmartFilter, LanguageDetection, Unicode, TextNormalization (advanced if available), variants, embeddings.

Example stage wiring (Clean Orchestrator):

```py
self.pipeline.add_stage(ValidationStage(...))
self.pipeline.add_stage(UnicodeNormalizationStage())
self.pipeline.add_stage(LanguageDetectionStage(...))
self.pipeline.add_stage(NormalizationServiceStage(...))
```

Source: `src/ai_service/orchestration/clean_orchestrator.py:108`


## Services & Responsibilities

| Service/Class | File | Key Methods | Responsibility | Used By |
|---|---|---|---|---|
| FastAPI app | `src/ai_service/main.py` | endpoints (`/process`, `/normalize`, etc.) | HTTP surface & startup orchestrator | external clients
| OrchestratorService | `src/ai_service/services/orchestrator_service.py` | `process_text`, `search_similar_names`, `analyze_text_complexity` | Coordinates language, unicode, normalization; caching; smart filter pre-pass | `main.py`
| CleanOrchestratorService | `src/ai_service/orchestration/clean_orchestrator.py` | pipeline setup (`_setup_pipeline_stages`) | Assembles modular pipeline from stage classes | internal orchestration
| ProcessingPipeline (CoR) | `src/ai_service/services/processing/processing_pipeline.py` | `process_text` | Alternative staged pipeline with validation→smart_filter→language→unicode→normalization | internal
| NormalizationService (generic) | `src/ai_service/services/normalization_service.py` | `normalize`, `tokenize_text`, `remove_stop_words` | Generic text normalization (spaCy/NLTK); lemmatization/stemming/stopwords | ProcessingPipeline basic normalization
| NormalizationService (morphology) | `src/ai_service/services/morphology/normalization_service.py` | `normalize`, `normalize_async`, `_tag_roles` | Person name normalization; roles, diminutives, morphology, org filtering | Tests; intended per-role pipeline
| AdvancedNormalizationService | `src/ai_service/services/advanced_normalization_service.py` and `.../morphology/advanced_normalization_service.py` | `normalize_advanced` | Advanced normalization with transliterations, pymorphy3 support | OrchestratorService, ProcessingPipeline (if present)
| LanguageDetectionService | `src/ai_service/services/language_detection_service.py` | `detect_language` | Multi-step detection (dictionaries→cyrillic→patterns→langdetect→fallback) | Orchestrators, Normalization
| UnicodeService | `src/ai_service/services/unicode_service.py` | `normalize_text` | Unicode normalization with mapping and optional aggressive ASCII folding | Orchestrators, Pipelines
| SmartFilterService | `src/ai_service/services/smart_filter/smart_filter_service.py` | `should_process_text` | Early decision; combines detectors and confidence scorer | OrchestratorService pre-pass
| NameDetector | `src/ai_service/services/smart_filter/name_detector.py` | `detect_names`, `detect_name_signals` | Heuristic fallback name detection; uses flat nickname/diminutive dicts | SmartFilterService
| CompanyDetector | `src/ai_service/services/smart_filter/company_detector.py` | detection helpers | Keyword/pattern-based company signal detection | SmartFilterService
| PatternService | `src/ai_service/services/pattern_service.py` | `generate_patterns` | Regex extraction for names and payment context; dictionary patterns | OrchestratorService (context name)
| SignalService | `src/ai_service/services/signal_service.py` | `analyze_signals`, `get_name_signals` | Regex-based signals for names/dates/locations/orgs/financial | OrchestratorService, SmartFilterService
| ServiceCoordinator/Registry | `src/ai_service/services/core/service_coordinator.py` | `initialize_all_services` | Initializes and holds services; health states | Orchestrator v2, ProcessingPipeline


## Processing Pipelines (as implemented)

### OrchestratorService.process_text

Observed order (simplified):

1) Input validation/sanitization via `input_validator` → cache lookup.
2) Smart Filter pre-pass (optional) → may skip further processing with a structured result.
3) Language detection BEFORE Unicode (`detect_language`) `src/ai_service/services/orchestrator_service.py:621`.
4) Reverse transliteration heuristic (romanized Slavic) `src/ai_service/services/orchestrator_service.py:244`.
5) Unicode normalization (`UnicodeService.normalize_text`) `src/ai_service/services/orchestrator_service.py:669`.
6) Advanced normalization if available (`advanced_normalization_service.normalize_advanced`) `src/ai_service/services/orchestrator_service.py:645` else fallback to basic.
7) Variants and embeddings optionally; results assembled into `ProcessingResult`.

Short excerpt:

```py
language_result = self.language_service.detect_language(sanitized_text)
unicode_result = self.unicode_service.normalize_text(text_for_processing, aggressive=False)
advanced_norm_result = await self.advanced_normalization_service.normalize_advanced(...)
```

Source: `src/ai_service/services/orchestrator_service.py:621`, `:669`, `:645`

### Clean Orchestrator (modular)

- Stage setup shows pipeline sequence and toggles:

```py
self.pipeline.add_stage(ValidationStage(...))
self.pipeline.add_stage(UnicodeNormalizationStage())
self.pipeline.add_stage(LanguageDetectionStage(...))
self.pipeline.add_stage(NormalizationServiceStage(...))
```

Source: `src/ai_service/orchestration/clean_orchestrator.py:108`

### ProcessingPipeline (services/processing)

- Ordered stages including SmartFilter before language; TextNormalization uses AdvancedNormalization if available or falls back to `normalization_service.normalize_async`:

```py
self.stages = [ValidationStage(), SmartFilterStage(), LanguageDetectionStage(),
               UnicodeNormalizationStage(), TextNormalizationStage(), VariantGenerationStage(), EmbeddingGenerationStage()]
...
await services.normalization_service.normalize_async(context.current_text, language=context.language, ...)
```

Source: `src/ai_service/services/processing/processing_pipeline.py:335`, `:285`


## Data Contracts

- Token trace and rich normalization result (Pydantic):

```py
class TokenTrace(BaseModel):
    token: str; role: str; rule: str; morph_lang: Optional[str] = None
    normal_form: Optional[str] = None; output: str; fallback: bool = False

class NormalizationResult(BaseModel):
    model_config = {"extra": "allow"}
    normalized: str; tokens: List[str]; trace: List[TokenTrace]; errors: List[str] = []
    language: Optional[str] = None; confidence: Optional[float] = None; ...
```

Source: `src/ai_service/utils/trace.py:11`, `:24`

- ProcessingResult (dataclass) for orchestrated `/process` responses:

```py
@dataclass
class ProcessingResult:
    original_text: str; normalized_text: str; language: str; language_confidence: float
    variants: List[str]; token_variants: Optional[Dict[str, List[str]]] = None
    embeddings: Optional[List] = None; processing_time: float = 0.0; success: bool = True
```

Source: `src/ai_service/services/orchestrator_service.py:33`

- Smart Filter result:

```py
@dataclass
class FilterResult:
    should_process: bool; confidence: float; detected_signals: List[str]
    signal_details: Dict[str, Any]; processing_recommendation: str; estimated_complexity: str
```

Source: `src/ai_service/services/smart_filter/smart_filter_service.py:33`

- CompanySignal and SignalResult for detectors:

```py
@dataclass
class CompanySignal: signal_type: str; confidence: float; matches: List[str]; position: int; context: str
@dataclass
class SignalResult: signal_type: str; confidence: float; matches: List[str]; count: int; metadata: Dict[str, Any] = None
```

Sources: `src/ai_service/services/smart_filter/company_detector.py:20`, `src/ai_service/services/signal_service.py:17`

- Note: `tests/unit/test_normalization_result_fields.py` expects a dataclass `NormalizationResult` from `ai_service.services.normalization_service`, but the richer Pydantic model is defined in `utils/trace.py`. The services’ generic normalization defines its own dataclass with matching fields (see below).

Generic NormalizationResult (dataclass) in generic normalization service:

```py
@dataclass
class NormalizationResult:
    normalized: str; tokens: List[str]; language: str; confidence: float
    original_length: int; normalized_length: int; token_count: int
    processing_time: float; success: bool; errors: List[str] = None
```

Source: `src/ai_service/services/normalization_service.py:55`


## Dictionaries & Rules

- Universal stopwords used by normalization: `STOP_ALL` `src/ai_service/services/stopwords.py:6`.
- English nicknames: `ENGLISH_NICKNAMES` `src/ai_service/data/dicts/english_nicknames.py` (flat dict).
- Diminutives (RU/UK): `RUSSIAN_DIMINUTIVES`, `UKRAINIAN_DIMINUTIVES` `src/ai_service/data/dicts/*.py` (flat dicts).
- Company triggers/markers: `COMPANY_TRIGGERS` `src/ai_service/data/dicts/company_triggers.py` (used to strip legal entities and phrases).
- Smart filter thresholds/patterns: `src/ai_service/data/dicts/smart_filter_patterns.py`.
- Org legal forms and acronym handling in morphology pipeline:

```py
ORG_LEGAL_FORMS = {"ооо","зао",...,"llc","ltd","inc","corp",...}
ORG_TOKEN_RE = re.compile(r"^(?:[A-ZА-ЯЁІЇЄҐ0-9][A-ZА-ЯЁІЇЄҐ0-9\-\&\.\']{1,39})$", re.U)
```

Source: `src/ai_service/services/morphology/normalization_service.py:13`

- Flag propagation and branching (morphology normalization):

```py
async def normalize(..., remove_stop_words: bool=True, preserve_names: bool=True, enable_advanced_features: bool=True)
...
if language == 'en':
    normalized_tokens, traces = self._normalize_english_tokens(..., enable_advanced_features)
else:
    normalized_tokens, traces = self._normalize_slavic_tokens(..., enable_advanced_features)
```

Source: `src/ai_service/services/morphology/normalization_service.py:215`, `:286`

Generic normalization flags (lemmatization/stemming/stopwords):

```py
async def normalize(..., remove_stop_words=False, apply_stemming=False, apply_lemmatization=True, clean_unicode=True, preserve_names=True, enable_advanced_features=False)
```

Source: `src/ai_service/services/normalization_service.py:244`


## Role Tagging / Normalization Logic (morphology pipeline)

High-level flow in `morphology/normalization_service`:

- Tokenize and strip noise with optional segmentation of hyphens/apostrophes depending on `preserve_names` `src/ai_service/services/morphology/normalization_service.py:352`.
- Tag roles per token: `given`, `surname`, `patronymic`, `initial`, `org`, `legal_form`, `unknown` `src/ai_service/services/morphology/normalization_service.py:590`.
- Org handling: legal forms are tagged and dropped; org tokens are collected with `__ORG__` prefix `src/ai_service/services/morphology/normalization_service.py:1262`.
- Initials: `_split_multi_initial` (e.g., `П.І.`) and `_cleanup_initial` `src/ai_service/services/morphology/normalization_service.py:575`, `:569`.
- Patronymic recognition via regex (multiple case endings) `src/ai_service/services/morphology/normalization_service.py:665`.
- Diminutive → full given mapping and English nicknames in Slavic context when `enable_advanced_features` is True `src/ai_service/services/morphology/normalization_service.py:1345`.
- Surname gender adjustments (including hyphenated surnames) `src/ai_service/services/morphology/normalization_service.py:1402`.
- Quoted tokens (e.g., `"ООО 'Тест'"`): quoted unknowns are ignored; quoted orgs are excluded from personal output `src/ai_service/services/morphology/normalization_service.py:1279`.

Short excerpt (role tagging):

```py
if self._is_legal_form(cf): tagged.append((token, "legal_form"))
elif is_quoted and self._looks_like_org(base): tagged.append((token, "org"))
...
role = self._classify_personal_role(base, language)
```

Source: `src/ai_service/services/morphology/normalization_service.py:604`

Morphological nominative normalization dispatch:

```py
if enable_advanced_features:
    morphed = self._morph_nominal(base, language)
else:
    morphed = base
```

Source: `src/ai_service/services/morphology/normalization_service.py:1337`

English tokens normalization uses `ENGLISH_NICKNAMES` when enabled `src/ai_service/services/morphology/normalization_service.py:1472`.


## Smart Filter vs Normalization vs Signals

- Smart Filter responsibility: early classification and skip decision; detects name/company/context signals and computes confidence `src/ai_service/services/smart_filter/smart_filter_service.py:120`.
- Normalization responsibility (morphology variant): return person-only normalized text and tokens; separates organizations into `result.organizations` and `result.org_core` `src/ai_service/services/morphology/normalization_service.py:332`.
- Signals Service: provides generic regex-driven signal extraction, independent of normalization `src/ai_service/services/signal_service.py:64`.

Current overlaps and boundaries:
- Company/organization patterns exist both in Smart Filter (detectors) and Normalization (legal forms and org core filtering), and also in `PatternService` payment-context extraction `src/ai_service/services/pattern_service.py:83` → duplication.
- OrchestratorService strips business/legal phrases via `company_triggers` during context extraction `src/ai_service/services/orchestrator_service.py:519` — overlaps with Smart Filter and normalization org filtering.

Must-deduplicate (explicit):
- Org detection/stripping among: SmartFilter CompanyDetector, OrchestratorService `_strip_business_prefix`, Morphology normalization legal/org handling.
- Normalization service duplication: `services/normalization_service.py` (generic) vs `services/morphology/normalization_service.py` (role-based). Stage adapters/imports conflict (see Gaps).
- AdvancedNormalizationService duplicated in two locations.


## Tests Map (truth from tests)

- `tests/unit/test_flags_behavior.py` — Verifies flags impact:
  - `remove_stop_words` toggles use of `STOP_ALL` `tests/unit/test_flags_behavior.py:18` → `src/ai_service/services/stopwords.py`.
  - `preserve_names` toggles splitting of apostrophes/hyphens `tests/unit/test_flags_behavior.py:56`.
  - `enable_advanced_features` influences morphology and nickname mapping `tests/unit/test_flags_behavior.py:95`, `:137`.

- `tests/unit/test_normalization_result_fields.py` — Asserts dataclass NormalizationResult carries metadata fields and allows extras; checks language and processing_time `tests/unit/test_normalization_result_fields.py:22`.

- `tests/unit/test_org_acronyms_filter.py` — Expects `ORG_LEGAL_FORMS` constant and that org acronyms and quoted orgs are excluded from person output `tests/unit/test_org_acronyms_filter.py:12`, `:36`.

- Integration suites (`tests/integration/test_full_normalization_suite.py`, `.../test_role_based_normalization.py`) — Expect strict name normalization outputs for RU/UK/EN cases and initials formatting; use `NormalizationService.normalize` `tests/integration/test_full_normalization_suite.py:50`, `:91`, `:112`.

Note: Some tests import `ai_service.services.normalization_service.NormalizationService` but assert role-based behavior implemented in `services/morphology/normalization_service.py` — indicates module/API divergence.


## Known Gaps / TODO (from code facts)

- Stage adapter API mismatch:
  - `NormalizationServiceStage` calls `NormalizationService.normalize_async` `src/ai_service/orchestration/stages/normalization_service_stage.py:47`, but `src/ai_service/services/normalization_service.py` exposes `async def normalize(...)` and no `normalize_async`. The morphology variant exposes `normalize_async`, but the stage imports the generic service, not morphology. Must align imports and interface.

- Dual NormalizationService implementations:
  - Generic (`services/normalization_service.py`) vs Morphology (`services/morphology/normalization_service.py`) with different Result models and behavior. Consolidation needed; tests expect role-based features.

- Duplicated AdvancedNormalizationService:
  - Exists in `src/ai_service/services/advanced_normalization_service.py` and `src/ai_service/services/morphology/advanced_normalization_service.py` — similar initialization and methods. Deduplicate to one module and update orchestrators.

- Organization handling duplication:
  - SmartFilter CompanyDetector, OrchestratorService `_strip_business_prefix` using `COMPANY_TRIGGERS` `src/ai_service/services/orchestrator_service.py:489`, and Morphology normalization org filtering `src/ai_service/services/morphology/normalization_service.py:1262`.

- Flags behavior gaps:
  - Generic normalization’s `enable_advanced_features` is present in signature but largely unused for role-based morphology (generic service only lemmatizes/stems/stopwords) `src/ai_service/services/normalization_service.py:244`.
  - Morphology normalization flags are implemented and referenced across pipeline `src/ai_service/services/morphology/normalization_service.py:215`.

- Tests vs code constants:
  - `tests/unit/test_org_acronyms_filter.py` imports `ORG_LEGAL_FORMS` from `ai_service.services.normalization_service`, but that constant is defined in `services/morphology/normalization_service.py:13`. Adjust export path or re-export to satisfy tests.

- Multiple pipelines co-exist:
  - `OrchestratorService`, `CleanOrchestratorService`, and `services/processing/ProcessingPipeline` implement similar flows with overlapping logic and different normalization hooks. Choose one and standardize.

- Performance tooling exists (`utils/performance.py`) and decorators used in morphology normalization; but not consistently applied elsewhere.


## Quick Start (dev)

- Run tests (collection only): `pytest --collect-only -q` (root). Keep unit suites around normalization and flags green: `tests/unit/test_flags_behavior.py`, `tests/unit/test_normalization_result_fields.py`, `tests/unit/test_org_acronyms_filter.py`.
- Toggle flags in code when invoking normalization:
  - Generic: `NormalizationService.normalize(text, remove_stop_words=..., apply_stemming=..., apply_lemmatization=..., preserve_names=..., enable_advanced_features=...)` `src/ai_service/services/normalization_service.py:244`.
  - Morphology: `NormalizationService.normalize(text, remove_stop_words=..., preserve_names=..., enable_advanced_features=...)` `src/ai_service/services/morphology/normalization_service.py:215`.
- Trace inspection (morphology): `TokenTrace` and `NormalizationResult.trace` are produced by `services/morphology/normalization_service` methods like `_normalize_slavic_tokens` `src/ai_service/services/morphology/normalization_service.py:1262` and returned via `utils/trace.NormalizationResult` fields.


## Directory Snapshot (selected)

```text
src/ai_service/main.py
src/ai_service/services/
  normalization_service.py            # generic normalize (spaCy/NLTK)
  language_detection_service.py       # multi-stage detection
  unicode_service.py                  # unicode normalization
  signal_service.py                   # regex signal extraction
  pattern_service.py                  # regex/dictionary patterns
  smart_filter/                       # smart filter and detectors
  orchestrator_service.py             # monolithic orchestrator
  core/                               # service coordinator & orchestrator v2
  morphology/normalization_service.py # role-based name normalization
  morphology/advanced_normalization_service.py
orchestration/                        # clean orchestrator pipeline
  clean_orchestrator.py
  stages/normalization_service_stage.py
```


---

All references above are pulled from the current codebase state. Line references point to specific implementations that define actual behavior.


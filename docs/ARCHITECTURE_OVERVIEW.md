# AI Service Architecture Overview

## Top-level Overview

### Directory Structure
```
src/ai_service/
├── main.py                    # FastAPI entry point
├── config/                    # Configuration management
│   ├── settings.py           # Service configuration classes
│   ├── app.yml              # Application config
│   └── screening_tiers.py   # Multi-tier screening config
├── services/                 # Core services
│   ├── orchestrator_service.py      # Main orchestrator (1485 lines)
│   ├── normalization_service.py     # Text normalization (659 lines)
│   ├── smart_filter/               # Smart filtering components
│   │   ├── smart_filter_service.py # Main smart filter (585 lines)
│   │   ├── name_detector.py        # Name detection
│   │   ├── company_detector.py     # Company detection
│   │   └── decision_logic.py       # Decision making
│   ├── morphology/                 # Morphological analysis
│   │   ├── normalization_service.py # Advanced normalization (1669 lines)
│   │   ├── russian_morphology.py   # Russian morphology
│   │   └── ukrainian_morphology.py # Ukrainian morphology
│   ├── signal_service.py           # Signal detection (217 lines)
│   ├── embedding_service.py        # Vector embeddings (464 lines)
│   ├── language_detection_service.py # Language detection (430 lines)
│   └── unicode_service.py          # Unicode normalization (293 lines)
├── data/dicts/               # Dictionaries and patterns
│   ├── smart_filter_patterns.py    # Smart filter patterns (1317 lines)
│   ├── russian_names.py           # Russian names
│   ├── ukrainian_names.py         # Ukrainian names
│   └── english_names.py           # English names
└── utils/
    ├── trace.py              # TokenTrace, NormalizationResult models
    └── performance.py        # Performance monitoring
```

### Entry Point
**File**: `src/ai_service/main.py:37-493`
- FastAPI application with CORS middleware
- Endpoints: `/process`, `/normalize`, `/process-batch`, `/search-similar`, `/health`
- Uses `OrchestratorService` for coordination

### Orchestrator Assembly
**File**: `src/ai_service/services/orchestrator_service.py:86-1485`
```python
def __init__(self, cache_size: Optional[int] = None, default_ttl: Optional[int] = None):
    self.unicode_service = UnicodeService()
    self.language_service = LanguageDetectionService()
    self.normalization_service = NormalizationService()
    self.pattern_service = PatternService()
    self.template_builder = TemplateBuilder()
    self.embedding_service = EmbeddingService()
    self.cache_service = CacheService()
    self.signal_service = SignalService()
    self.smart_filter = SmartFilterService()
```

## Services & Responsibilities

| Service/Class | File | Main Methods | Responsibility | Used By |
|---------------|------|--------------|----------------|---------|
| **OrchestratorService** | `orchestrator_service.py:86` | `process_text()`, `process_batch()`, `search_similar()` | Coordinates all services, manages processing flow | `main.py:29` |
| **NormalizationService** | `normalization_service.py:86` | `normalize()`, `detect_language()`, `tokenize_text()` | Text normalization using SpaCy/NLTK | OrchestratorService |
| **Advanced NormalizationService** | `morphology/normalization_service.py:58` | `normalize_async()`, `_tag_roles()`, `_normalize_by_role()` | Advanced morphological normalization with pymorphy3 | Not used in main flow |
| **SmartFilterService** | `smart_filter/smart_filter_service.py:46` | `should_process()`, `analyze_text()` | Pre-filtering decisions, relevance scoring | OrchestratorService |
| **NameDetector** | `smart_filter/name_detector.py` | `detect_names()`, `analyze_name_patterns()` | Name pattern detection | SmartFilterService |
| **CompanyDetector** | `smart_filter/company_detector.py` | `detect_companies()`, `analyze_company_patterns()` | Company pattern detection | SmartFilterService |
| **SignalService** | `signal_service.py:24` | `analyze_signals()`, `detect_signals()` | Pattern matching for names, dates, organizations | SmartFilterService, OrchestratorService |
| **LanguageDetectionService** | `language_detection_service.py:14` | `detect_language()`, `get_confidence()` | Automatic language detection | NormalizationService, SmartFilterService |
| **UnicodeService** | `unicode_service.py:14` | `normalize_unicode()`, `clean_text()` | Unicode normalization, character cleaning | NormalizationService |
| **EmbeddingService** | `embedding_service.py:14` | `generate_embeddings()`, `search_similar()` | Vector embeddings using sentence-transformers | OrchestratorService |
| **TemplateBuilder** | `template_builder.py:24` | `build_templates()`, `search_patterns()` | Aho-Corasick pattern templates | OrchestratorService |
| **CacheService** | `cache_service.py:14` | `get()`, `set()`, `clear()`, `stats()` | LRU caching with TTL | OrchestratorService |

## Processing Pipelines

### Main Processing Pipeline
**File**: `src/ai_service/services/orchestrator_service.py:200-400`

1. **Input Validation** → `input_validator.validate_text()`
2. **Smart Filtering** → `smart_filter.should_process()`
3. **Language Detection** → `language_service.detect_language()`
4. **Unicode Normalization** → `unicode_service.normalize_unicode()`
5. **Text Normalization** → `normalization_service.normalize()`
6. **Signal Detection** → `signal_service.analyze_signals()`
7. **Variant Generation** → `_generate_variants()`
8. **Embedding Generation** → `embedding_service.generate_embeddings()`
9. **Response Assembly** → `ProcessingResult`

### Advanced Normalization Pipeline (Unused)
**File**: `src/ai_service/services/morphology/normalization_service.py:200-400`

1. **Tokenization** → `_strip_noise_and_tokenize()`
2. **Role Tagging** → `_tag_roles()`
3. **Morphological Analysis** → `_morph_nominal()`
4. **Diminutive Mapping** → `_apply_diminutive_mapping()`
5. **Gender Adjustment** → `_adjust_gender()`
6. **Reconstruction** → `_reconstruct_text()`

## Data Contracts

### NormalizationResult (Basic)
**File**: `src/ai_service/services/normalization_service.py:71-84`
```python
@dataclass
class NormalizationResult:
    normalized: str
    tokens: List[str]
    language: str
    confidence: float
    original_length: int
    normalized_length: int
    token_count: int
    processing_time: float
    success: bool
    errors: List[str] = None
```

### NormalizationResult (Advanced)
**File**: `src/ai_service/utils/trace.py:22-57`
```python
class NormalizationResult(BaseModel):
    normalized: str
    tokens: List[str]
    trace: List[TokenTrace]
    errors: List[str] = []
    language: Optional[str] = None
    confidence: Optional[float] = None
    original_length: Optional[int] = None
    normalized_length: Optional[int] = None
    token_count: Optional[int] = None
    processing_time: Optional[float] = None
    success: Optional[bool] = None
```

### TokenTrace
**File**: `src/ai_service/utils/trace.py:10-20`
```python
class TokenTrace(BaseModel):
    token: str
    role: str
    rule: str
    morph_lang: Optional[str] = None
    normal_form: Optional[str] = None
    output: str
    fallback: bool = False
    notes: Optional[str] = None
```

### ProcessingResult
**File**: `src/ai_service/services/orchestrator_service.py:36-84`
```python
@dataclass
class ProcessingResult:
    original_text: str
    normalized_text: str
    language: str
    language_confidence: float
    variants: List[str]
    token_variants: Optional[Dict[str, List[str]]] = None
    embeddings: Optional[List] = None
    processing_time: float = 0.0
    success: bool = True
    errors: List[str] = None
    smart_filter: Optional[Dict[str, Any]] = None
```

### SignalResult
**File**: `src/ai_service/services/signal_service.py:14-22`
```python
@dataclass
class SignalResult:
    signal_type: str
    confidence: float
    matches: List[str]
    count: int
    metadata: Dict[str, Any] = None
```

## Dictionaries & Rules

### Organization Acronyms
**File**: `src/ai_service/services/morphology/normalization_service.py:19-22`
```python
ORG_LEGAL_FORMS = {
    "ооо","зао","оао","пао","ао","ип","чп","фоп","тов","пп","кс",
    "ooo","llc","ltd","inc","corp","co","gmbh","srl","spa","s.a.","s.r.l.","s.p.a.","bv","nv","oy","ab","as","sa","ag"
}
```

### Smart Filter Patterns
**File**: `src/ai_service/data/dicts/smart_filter_patterns.py:10-30`
```python
EXCLUSION_PATTERNS = [
    r"^\d+$",  # Only digits
    r"^[^\w\s]+$",  # Only special characters
    r"^(оплата|платеж|платіж|перевод|счет|квитанция|документ)$",  # Common terms
    # ... more patterns
]
```

### Name Dictionaries
**Files**: `src/ai_service/data/dicts/`
- `russian_names.py` - Russian names
- `ukrainian_names.py` - Ukrainian names  
- `english_names.py` - English names
- `english_nicknames.py` - English nicknames

### Usage Cross-References
- **NormalizationService**: Uses ORG_LEGAL_FORMS, name dictionaries
- **SmartFilterService**: Uses smart_filter_patterns, exclusion patterns
- **SignalService**: Uses payment context patterns, name patterns

## Role Tagging / Normalization Logic

### Tokenization → Role Tagging → Normalization → Reconstruction
**File**: `src/ai_service/services/morphology/normalization_service.py:200-400`

```python
def _tag_roles(self, tokens: List[str]) -> List[TokenTrace]:
    """Tag tokens with roles: initial, patronymic, given, surname, unknown"""
    for token in tokens:
        if self._is_org_acronym(token):
            role = "unknown"  # ORG_ACRONYMS always unknown
        elif self._is_initial(token):
            role = "initial"
        elif self._is_patronymic(token):
            role = "patronymic"
        elif self._is_given_name(token):
            role = "given"
        elif self._is_surname(token):
            role = "surname"
        else:
            role = "unknown"
```

### Morphology Rules
**File**: `src/ai_service/services/morphology/normalization_service.py:400-600`
- **Russian/Ukrainian**: Uses pymorphy3 for morphological analysis
- **English**: No morphology, only capitalization
- **Gender Adjustment**: Preserves female forms, converts male→female when needed
- **Diminutive Mapping**: Maps nicknames to full names using dictionaries

### English Tokens in Cyrillic Context
**File**: `src/ai_service/services/morphology/normalization_service.py:600-800`
```python
def _normalize_english_token(self, token: str, context_lang: str) -> str:
    """English tokens in Cyrillic context - no morphology, only capitalization"""
    if context_lang in ['ru', 'uk'] and self._is_ascii(token):
        return token.capitalize()  # No morphological analysis
```

## Smart Filter vs Normalization vs Signals

### Current Responsibilities

**SmartFilterService** (`smart_filter/smart_filter_service.py:46-585`):
- Pre-filtering decisions (should_process: bool)
- Company detection using patterns
- Name detection using patterns
- Confidence scoring
- **NOT responsible for**: Text normalization, morphological analysis

**NormalizationService** (`normalization_service.py:86-659`):
- Text tokenization using SpaCy/NLTK
- Basic normalization (stemming, lemmatization)
- Language detection
- **NOT responsible for**: Pattern matching, signal detection

**Advanced NormalizationService** (`morphology/normalization_service.py:58-1669`):
- Role-based normalization
- Morphological analysis with pymorphy3
- Diminutive mapping
- Gender adjustment
- **NOT used in main flow** - separate implementation

**SignalService** (`signal_service.py:24-217`):
- Pattern matching for names, dates, organizations
- Payment context detection
- **NOT responsible for**: Text normalization, morphological analysis

### Duplication Issues
1. **Name Detection**: Both SmartFilterService and SignalService detect names
2. **Company Detection**: Both SmartFilterService and SignalService detect companies
3. **Pattern Matching**: Similar regex patterns in multiple services

## Tests Map

### Unit Tests
**Directory**: `tests/unit/`

| Test File | What it asserts | Key assertions |
|-----------|-----------------|----------------|
| `test_normalization_service.py` | Basic normalization logic | `assert result.success == True`, `assert len(result.tokens) > 0` |
| `test_smart_filter_service.py` | Smart filtering decisions | `assert result.should_process == True`, `assert result.confidence > 0.5` |
| `test_signal_service.py` | Signal detection patterns | `assert result['names']['count'] > 0`, `assert result['confidence'] > 0.0` |
| `test_org_acronyms_filter.py` | ORG acronym filtering | `assert 'ооо' in ORG_LEGAL_FORMS`, `assert role == 'unknown'` |
| `test_role_tagging_extended.py` | Role tagging logic | `assert trace.role in ['given', 'surname', 'patronymic', 'initial', 'unknown']` |
| `test_morph_and_diminutives.py` | Morphological analysis | `assert normal_form == 'expected_form'`, `assert morph_lang in ['ru', 'uk']` |

### Integration Tests
**Directory**: `tests/integration/`

| Test File | What it asserts | Key assertions |
|-----------|-----------------|----------------|
| `test_name_extraction_pipeline.py` | End-to-end pipeline | `assert result.success == True`, `assert len(result.variants) > 0` |
| `test_ru_uk_sentences.py` | Russian/Ukrainian processing | `assert result.language in ['ru', 'uk']`, `assert result.confidence > 0.7` |
| `test_mixed_script_names.py` | Mixed script handling | `assert result.normalized_text is not None` |

### E2E Tests
**Directory**: `tests/e2e/`

| Test File | What it asserts | Key assertions |
|-----------|-----------------|----------------|
| `test_sanctions_screening_pipeline.py` | Complete screening workflow | `assert result.success == True` |
| `test_nightmare_scenario.py` | Edge cases and error conditions | `assert result.errors == []` |

## Known Gaps / TODO

### Flags That Don't Affect Behavior
**File**: `src/ai_service/services/normalization_service.py:267-277`
```python
async def normalize(
    self,
    text: str,
    language: str = 'auto',
    remove_stop_words: bool = False,  # Always False for names
    apply_stemming: bool = False,     # Always False for names
    apply_lemmatization: bool = True, # Always True for names
    clean_unicode: bool = True,
    preserve_names: bool = True,      # Always True
    enable_advanced_features: bool = False  # Not implemented
):
```

### ORG_ACRONYMS Usage Issues
**File**: `src/ai_service/services/morphology/normalization_service.py:19-22`
- Defined but not consistently used across services
- SmartFilterService has its own company detection patterns
- SignalService has separate organization patterns

### Duplication Between Services
1. **Name Detection**: 
   - `smart_filter/name_detector.py` - Basic name patterns
   - `signal_service.py:32-42` - Similar name patterns
2. **Company Detection**:
   - `smart_filter/company_detector.py` - Company patterns
   - `signal_service.py:62-70` - Organization patterns
3. **Pattern Matching**:
   - Multiple regex patterns for same entities across services

### Performance Issues
**File**: `src/ai_service/services/morphology/normalization_service.py:400-600`
- No `@lru_cache` on morphological analysis
- Repeated dictionary lookups
- No caching of normalization results

### Missing Features
1. **Multi-initials splitting**: Not implemented
2. **Quoted token handling**: Basic implementation
3. **Positional defaults**: Inconsistent application
4. **Advanced features flag**: Not implemented

## Quick Start for New Developers

### Running Tests
```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests  
pytest tests/integration/ -v

# E2E tests
pytest tests/e2e/ -v
```

### Key Tests to Keep Green
- `test_normalization_service.py` - Core normalization
- `test_smart_filter_service.py` - Smart filtering
- `test_org_acronyms_filter.py` - ORG acronym filtering
- `test_role_tagging_extended.py` - Role tagging

### Enabling/Disabling Flags
**File**: `src/ai_service/config/settings.py:24-50`
```python
@dataclass
class ServiceConfig:
    enable_advanced_features: bool = True
    enable_morphology: bool = True
    preserve_names: bool = True
    clean_unicode: bool = True
```

### Viewing Trace
**File**: `src/ai_service/utils/trace.py:10-20`
```python
# TokenTrace shows processing steps
trace = TokenTrace(
    token="original",
    role="given", 
    rule="morphology",
    morph_lang="ru",
    normal_form="нормализованная",
    output="final"
)
```

## File References

- **Main Entry**: `src/ai_service/main.py:37-493`
- **Orchestrator**: `src/ai_service/services/orchestrator_service.py:86-1485`
- **Normalization**: `src/ai_service/services/normalization_service.py:86-659`
- **Advanced Normalization**: `src/ai_service/services/morphology/normalization_service.py:58-1669`
- **Smart Filter**: `src/ai_service/services/smart_filter/smart_filter_service.py:46-585`
- **Signal Service**: `src/ai_service/services/signal_service.py:24-217`
- **Data Contracts**: `src/ai_service/utils/trace.py:10-57`
- **Patterns**: `src/ai_service/data/dicts/smart_filter_patterns.py:10-1317`
- **Tests**: `tests/unit/`, `tests/integration/`, `tests/e2e/`

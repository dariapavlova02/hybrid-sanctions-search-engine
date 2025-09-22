# AI Normalization & Signals Service - Architecture Deep Dive

## 🎯 Project Overview

The AI Service is a sophisticated multi-layered system for **name normalization** and **sanctions screening** with a focus on Russian, Ukrainian, and English languages. It implements a pipeline architecture that transforms raw text into structured, normalized data with signals extraction.

### Core Mission
- **Normalize** personal names and organization core parts
- **Extract signals** (legal forms, dates of birth, IDs, etc.)
- **Generate variants** for fuzzy matching and sanctions screening
- Work **deterministically** with full traceability

---

## 🏗️ Architecture Principles

### 1. Layered Processing Pipeline
The system implements a **9-layer pipeline** as specified in `.claude/CLAUDE.md`:

```
Input Text → [9 Processing Layers] → Structured Output
```

**Layers:**
1. **Validation & Sanitization** - Input cleaning and safety
2. **Smart Filter** - Early relevance assessment
3. **Language Detection** - Auto-detect ru/uk/en
4. **Unicode Normalization** - Character standardization
5. **Name Normalization** - Core morphological processing
6. **Signals Extraction** - Structured data extraction
7. **Variants Generation** - Alternative forms
8. **Embeddings** - Vector representations
9. **Decision & Response** - Final result assembly

### 2. Strict Separation of Concerns

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Normalization │    │     Signals     │    │    Variants     │
│                 │    │                 │    │                 │
│ • Clean names   │    │ • Legal forms   │    │ • Morphological │
│ • Core orgs     │    │ • DOB parsing   │    │ • Phonetic      │
│ • Tokenization  │    │ • ID extraction │    │ • Transliteration│
│ • TokenTrace    │    │ • Evidence      │    │ • AC patterns   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 3. Contract-Based Design
All inter-layer communication uses **typed contracts** defined in `src/ai_service/contracts/`:
- `base_contracts.py` - Core data structures
- `decision_contracts.py` - Decision engine contracts
- `trace_models.py` - Debugging and traceability

---

## 📁 Directory Structure Analysis

```
src/ai_service/
├── 🔧 core/                   # Orchestration and base services
│   ├── unified_orchestrator.py    # Main pipeline coordinator
│   ├── orchestrator_factory.py   # Factory for different orchestrators
│   ├── base_service.py           # Base class for all services
│   └── decision_engine.py        # Risk assessment and decision logic
│
├── 📋 contracts/              # Type definitions and interfaces
│   ├── base_contracts.py         # Core data structures (NormalizationResult, etc.)
│   ├── decision_contracts.py     # Decision engine types
│   └── trace_models.py           # Debugging and trace structures
│
├── 🔄 layers/                 # Processing layers (the heart of the system)
│   ├── validation/               # Input validation and sanitization
│   ├── smart_filter/            # Early relevance filtering
│   ├── language/                # Language detection (ru/uk/en)
│   ├── unicode/                 # Unicode normalization and cleaning
│   ├── normalization/           # Core name processing (largest layer)
│   │   ├── processors/             # Refactored modular processors
│   │   ├── morphology/             # Pymorphy3 integration
│   │   └── ner_gateways/          # Named Entity Recognition
│   ├── signals/                 # Structured data extraction
│   ├── variants/                # Variant generation for matching
│   ├── embeddings/              # Vector representations
│   ├── patterns/                # AC pattern generation
│   ├── search/                  # Hybrid search capabilities
│   └── decision/                # Final decision logic
│
├── 💾 data/                   # Static data and dictionaries
│   ├── dicts/                    # Language-specific dictionaries
│   ├── patterns/                 # Search patterns
│   └── templates/                # Generation templates
│
├── 🔌 adapters/               # External service adapters
├── 🌐 api/                    # REST API endpoints
├── ⚙️ config/                 # Configuration management
├── 🛠️ utils/                  # Utilities and helpers
├── 📊 monitoring/             # Metrics and monitoring
└── 🧪 eval/                   # Evaluation and testing utilities
```

---

## 🔍 Key Design Patterns

### 1. **Factory Pattern**
- `OrchestratorFactory` creates appropriate orchestrators
- `NormalizationFactory` manages processor components
- Allows runtime configuration and testing flexibility

### 2. **Strategy Pattern**
- Different normalization strategies for each language
- Pluggable search strategies (AC vs Vector vs Hybrid)
- Configurable processing pipelines

### 3. **Chain of Responsibility**
- Each layer processes and passes data to the next
- Errors can be handled at any layer
- Tracing captures the full processing chain

### 4. **Observer Pattern**
- Performance monitoring throughout the pipeline
- Feature flags for runtime behavior modification
- Metrics collection at each layer

### 5. **Adapter Pattern**
- External service integration (Elasticsearch, embeddings)
- Language-specific morphology adapters
- NER gateway adapters for different models

---

## 🧩 Component Deep Dive

### Core Orchestrator (`unified_orchestrator.py`)
**Purpose**: Single source of truth for the processing pipeline

```python
class UnifiedOrchestrator:
    """Implements the authoritative 9-layer processing pipeline"""

    async def process_async(text: str) -> UnifiedProcessingResult:
        # 1. Validation & Sanitization
        # 2. Smart Filter
        # 3. Language Detection
        # 4. Unicode Normalization
        # 5. Name Normalization
        # 6. Signals Extraction
        # 7. Variants (optional)
        # 8. Embeddings (optional)
        # 9. Decision & Response
```

### Normalization Layer (`layers/normalization/`)
**Purpose**: Core name processing with morphological analysis

**Key Components:**
- `normalization_service.py` - Main normalization logic
- `processors/` - Modular, language-specific processors
- `morphology/` - Pymorphy3 integration for Russian/Ukrainian
- `tokenizer_service.py` - Text tokenization
- `role_tagger.py` - Token role classification (given/surname/patronymic)

**Architecture**: Recently refactored from monolithic to modular design

### Signals Layer (`layers/signals/`)
**Purpose**: Extract structured information from text

**Capabilities:**
- Legal form detection (ООО, LLC, etc.)
- Date of birth parsing
- ID number extraction (INN, EDRPOU, etc.)
- Organization name assembly
- Evidence tracking for explainability

### Variants Layer (`layers/variants/`)
**Purpose**: Generate alternative forms for matching

**Strategies:**
- Morphological variants (different cases)
- Transliteration (Cyrillic ↔ Latin)
- Phonetic variations
- High-recall AC patterns for sanctions screening

### Search Layer (`layers/search/`)
**Purpose**: Hybrid search combining exact and semantic matching

**Features:**
- Aho-Corasick exact matching
- Vector similarity search
- Hybrid fusion strategies
- Performance optimization and caching

---

## 🔧 Recent Architectural Improvements

### 1. **Modular Refactoring** (Latest)
Large monolithic files broken down into focused modules:
- `high_recall_ac_generator.py` (2,758 lines) → 4 focused modules
- `normalization_factory.py` (2,357 lines) → 5 specialized processors
- `hybrid_search_service.py` (2,068 lines) → 4 component modules

### 2. **Performance Optimizations**
- **Optimized Dictionary Loading** - Lazy loading, compression, chunking
- **Async/Sync Bridge** - Eliminates blocking operations
- **Memory Management** - LRU caching with memory pressure handling
- **Compatibility Layers** - Zero-downtime migration support

### 3. **Contract Standardization**
All services now implement standard contracts:
- `NormalizationResult` - Consistent output format
- `TokenTrace` - Full traceability
- `SignalsResult` - Structured extraction results

---

## 🚦 Configuration & Feature Flags

### Configuration Hierarchy
```
SERVICE_CONFIG      # Core service settings
DEPLOYMENT_CONFIG   # Environment-specific
SECURITY_CONFIG     # Authentication & authorization
INTEGRATION_CONFIG  # External service settings
```

### Feature Flags (`utils/feature_flags.py`)
Runtime behavior modification:
- Language-specific features
- Experimental algorithms
- Performance optimizations
- A/B testing capabilities

---

## 📊 Monitoring & Observability

### Metrics Collection
- **Performance**: Response times, throughput
- **Quality**: Confidence scores, error rates
- **Resource**: Memory usage, cache hit rates
- **Business**: Processing success rates

### Tracing System
- **TokenTrace**: Full normalization pipeline trace
- **SearchTrace**: Search operation tracking
- **Evidence**: Signal extraction justification

### Health Checks
- Service dependency health
- Resource utilization monitoring
- Configuration validation

---

## 🧪 Testing Strategy

### Test Structure
```
src/tests/
├── unit/           # Layer-specific unit tests
├── integration/    # Cross-layer integration tests
└── golden/         # Golden dataset validation
```

### Quality Gates
1. Unit tests for each processor
2. Integration tests for full pipeline
3. Golden dataset regression testing
4. Performance benchmarking

---

## 🔄 Development Workflow

### Standard Process
1. **Small increments** - Atomic, focused changes
2. **Git diff review** - Show changes before commit
3. **Relevant tests** - Unit → Integration
4. **Atomic commits** - Meaningful, self-contained
5. **Error traces** - Include TokenTrace for debugging

### Commit Conventions
```bash
feat(signals): birthdate parsing and ISO normalization
fix(tagging): filter legal acronyms as unknown; no fallback
perf(cache): lru_cache on morphology
chore(packaging): editable install & test collection ok
docs: update README and docstrings
```

---

## 🎯 Core Anti-Patterns (Critical)

❌ **NO hardcoding** for test compatibility
❌ **NO test bypassing** - Fix root causes
❌ **NO Smart Filter in normalization** - Strict layer separation
❌ **NO morphing English names** in Cyrillic context
❌ **NO gender conversion** of feminine surnames
❌ **NO legal forms in Normalization** - Belongs in Signals layer

---

## 🚀 Future Architecture Considerations

### Scalability
- Microservice decomposition potential
- Horizontal scaling strategies
- Caching layer optimization

### Extensibility
- Plugin architecture for new languages
- Custom processor registration
- External model integration

### Performance
- GPU acceleration for embeddings
- Distributed processing capabilities
- Advanced caching strategies

---

## 📚 Key Dependencies

### Core Runtime
- **FastAPI** - Web framework
- **Pydantic** - Data validation and serialization
- **Pymorphy3** - Morphological analysis (ru/uk)
- **sentence-transformers** - Embeddings
- **pyahocorasick** - Pattern matching

### Language Processing
- **nameparser** - English name parsing
- **elasticsearch** - Search infrastructure
- **numpy/scipy** - Numerical computations

### Development
- **pytest** - Testing framework
- **black/isort** - Code formatting
- **hypothesis** - Property-based testing

---

This architecture represents a mature, production-ready system with strong separation of concerns, comprehensive testing, and robust monitoring. The recent modular refactoring has significantly improved maintainability while preserving all functionality and ensuring zero-downtime deployment capabilities.
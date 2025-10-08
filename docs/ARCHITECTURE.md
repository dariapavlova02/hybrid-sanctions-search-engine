# 🏗️ AI Service Architecture

## Overview

AI Service is a multilingual text processing system built on a clean 9-layer architecture for normalization, structured extraction, and hybrid search capabilities.

## Architecture Principles

- **Single Responsibility**: Each layer has one clear purpose
- **Modularity**: Components can be developed and tested independently  
- **Extensibility**: New features can be added without modifying existing code
- **Performance**: Optimized for high-throughput processing
- **Observability**: Comprehensive monitoring and tracing

## 9-Layer Processing Pipeline

```
Input Text
    ↓
1. Validation & Sanitization
    ↓ 
2. Smart Filter
    ↓
3. Language Detection
    ↓
4. Unicode Normalization
    ↓
5. Name Normalization (CORE)
    ↓
6. Signals Extraction
    ↓
7. Variants Generation
    ↓
8. Embeddings Generation
    ↓
9. Decision & Response
    ↓
Processed Result
```

### Layer Details

#### 1. Validation & Sanitization
**Purpose**: Input validation and basic sanitization
**Component**: `InputValidationService`
**Responsibilities**:
- Text length validation
- Character encoding validation
- Basic input sanitization
- Attack pattern detection

#### 2. Smart Filter  
**Purpose**: Pre-processing optimization and routing
**Component**: `SmartFilterService`
**Responsibilities**:
- Determine if text should be processed
- Quick signal detection
- Performance optimization routing
- Resource usage estimation

#### 3. Language Detection
**Purpose**: Identify text language (ru/uk/en)
**Component**: `LanguageDetectionService`
**Responsibilities**:
- Automatic language detection
- Confidence scoring
- Mixed-language handling
- Script detection

#### 4. Unicode Normalization
**Purpose**: Text standardization
**Component**: `UnicodeNormalizationService`
**Responsibilities**:
- Unicode normalization (NFKC)
- Case conversion
- Whitespace normalization
- Special character handling

#### 5. Name Normalization (CORE)
**Purpose**: Morphological analysis and name normalization
**Component**: `NormalizationService`
**Responsibilities**:
- Tokenization
- Morphological analysis
- Name part identification
- Gender detection
- Role classification

#### 6. Signals Extraction
**Purpose**: Structured data extraction
**Component**: `SignalsService`
**Responsibilities**:
- Person extraction
- Organization extraction
- Date/ID extraction
- Legal form identification
- Payment context detection

#### 7. Variants Generation
**Purpose**: Generate spelling and morphological alternatives
**Component**: `VariantGenerationService`
**Responsibilities**:
- Transliteration variants
- Phonetic variants
- Morphological variants
- Abbreviation expansion

#### 8. Embeddings Generation
**Purpose**: Vector representation for semantic search
**Component**: `EmbeddingService`
**Responsibilities**:
- Multilingual embedding generation
- Model management
- Batch processing optimization
- Vector similarity calculation

#### 9. Decision & Response
**Purpose**: Final result assembly and formatting
**Component**: `DecisionService`
**Responsibilities**:
- Result aggregation
- Confidence scoring
- Response formatting
- Performance metrics

## Core Components

### UnifiedOrchestrator
**Location**: `src/ai_service/core/unified_orchestrator.py`
**Purpose**: Central coordinator for the entire pipeline
**Key Features**:
- Async processing coordination
- Error handling and recovery
- Performance monitoring
- Caching management

### HybridSearchService
**Location**: `src/ai_service/layers/search/hybrid_search_service.py`
**Purpose**: Combines AC (Aho-Corasick) and vector search
**Key Features**:
- AC pattern matching
- Vector similarity search
- Hybrid result fusion
- Performance optimization

### SmartFilterService
**Location**: `src/ai_service/layers/smart_filter/smart_filter_service.py`
**Purpose**: Intelligent pre-processing optimization
**Key Features**:
- Quick signal detection
- Resource estimation
- Routing decisions
- Performance gating

## Data Flow

### Request Processing
```python
async def process_text(text: str, options: ProcessingOptions) -> ProcessingResult:
    # 1. Input validation
    validated_text = await validation_service.validate(text)
    
    # 2. Smart filtering
    should_process = await smart_filter.should_process(validated_text)
    if not should_process:
        return create_skip_result()
    
    # 3. Language detection
    language = await language_service.detect(validated_text)
    
    # 4. Unicode normalization
    normalized_text = await unicode_service.normalize(validated_text)
    
    # 5. Name normalization
    normalization_result = await normalization_service.normalize(
        normalized_text, language
    )
    
    # 6. Signals extraction
    signals = await signals_service.extract(
        normalization_result, language
    )
    
    # 7. Variants generation (optional)
    variants = None
    if options.include_variants:
        variants = await variant_service.generate(
            normalization_result, language
        )
    
    # 8. Embeddings generation (optional)
    embeddings = None
    if options.include_embeddings:
        embeddings = await embedding_service.encode(
            normalized_text
        )
    
    # 9. Decision and response
    result = await decision_service.assemble_result(
        normalized_text, signals, variants, embeddings
    )
    
    return result
```

### Search Processing
```python
async def hybrid_search(query: str, options: SearchOptions) -> SearchResult:
    # AC search
    ac_results = await ac_service.search(query, options)
    
    # Vector search
    vector_results = await vector_service.search(query, options)
    
    # Hybrid fusion
    fused_results = await fusion_service.combine(
        ac_results, vector_results, options
    )
    
    return fused_results
```

## Configuration Architecture

### Feature Flags
**Location**: `src/ai_service/utils/feature_flags.py`
**Purpose**: Runtime behavior control
**Key Flags**:
- `use_factory_normalizer`: Choose normalization implementation
- `enable_search_optimizations`: Performance optimizations
- `enhanced_accuracy_mode`: Accuracy vs performance tradeoff

### Settings Management
**Location**: `src/ai_service/config/settings.py`
**Purpose**: Centralized configuration
**Components**:
- Environment-specific settings
- Service configurations
- Performance parameters
- Security settings

## Performance Architecture

### Multi-Level Caching
```python
# L1: In-memory LRU cache (hot data)
@lru_cache(maxsize=1000)
def cached_morphological_analysis(token: str, lang: str) -> MorphResult:

# L2: Redis cache (warm data)  
async def get_cached_result(key: str) -> Optional[CachedResult]:

# L3: Database cache (cold data)
async def get_persistent_cache(key: str) -> Optional[PersistentResult]:
```

### Async Processing
- **FastAPI**: Async web framework
- **Asyncio**: Concurrent processing
- **Connection Pooling**: Database and external service connections
- **Batch Processing**: Efficient handling of multiple requests

### Performance Monitoring
- **Prometheus**: Metrics collection
- **Grafana**: Visualization and alerting
- **Custom Metrics**: Business and performance KPIs
- **Distributed Tracing**: Request flow tracking

## Security Architecture

### Authentication & Authorization
- **API Key Authentication**: Admin endpoint protection
- **Rate Limiting**: Request throttling
- **CORS**: Cross-origin resource sharing
- **Input Validation**: Attack prevention

### Data Protection
- **Encryption**: TLS for all communications
- **Secrets Management**: Secure credential storage
- **Audit Logging**: Security event tracking
- **Data Sanitization**: PII protection

## Deployment Architecture

### Container Strategy
```dockerfile
# Multi-stage build
FROM python:3.12-slim as builder
# Build dependencies and application

FROM python:3.12-slim as runtime
# Production image with minimal footprint
```

### Kubernetes Deployment
- **Pods**: Application instances
- **Services**: Load balancing and discovery
- **ConfigMaps**: Configuration management
- **Secrets**: Sensitive data storage
- **HPA**: Horizontal pod autoscaling

### Monitoring Stack
- **Prometheus**: Metrics collection
- **Grafana**: Dashboards and alerting
- **Alertmanager**: Alert routing
- **Node Exporter**: System metrics

## Development Architecture

### Code Organization
```
src/ai_service/
├── core/                   # Core orchestration
├── layers/                 # Processing layers
│   ├── validation/         # Layer 1
│   ├── smart_filter/       # Layer 2
│   ├── language/           # Layer 3
│   ├── normalization/      # Layer 4-5
│   ├── signals/            # Layer 6
│   ├── variants/           # Layer 7
│   ├── embeddings/         # Layer 8
│   └── decision/           # Layer 9
├── search/                 # Hybrid search
├── monitoring/             # Metrics and monitoring
├── utils/                  # Shared utilities
├── config/                 # Configuration
└── api/                    # FastAPI endpoints
```

### Testing Strategy
- **Unit Tests**: Individual component testing
- **Integration Tests**: Service interaction testing
- **E2E Tests**: Full pipeline testing
- **Performance Tests**: Load and stress testing
- **Property Tests**: Hypothesis-based testing

### Quality Assurance
- **Type Hints**: Static type checking
- **Linting**: Code style enforcement
- **Pre-commit Hooks**: Automated quality checks
- **CI/CD**: Automated testing and deployment

## Technology Stack

### Core Technologies
- **Python 3.12**: Primary language
- **FastAPI**: Web framework
- **Pydantic**: Data validation
- **Asyncio**: Async programming

### ML/NLP Libraries
- **sentence-transformers**: Multilingual embeddings
- **spacy**: Natural language processing
- **pymorphy3**: Morphological analysis
- **transformers**: Transformer models

### Search & Storage
- **Elasticsearch**: Search backend
- **Redis**: Caching layer
- **PostgreSQL**: Relational data (optional)

### Monitoring & Observability
- **Prometheus**: Metrics collection
- **Grafana**: Visualization
- **Docker**: Containerization
- **Kubernetes**: Orchestration

## Evolution Strategy

### Phase 1: Foundation
- ✅ 9-layer architecture implementation
- ✅ Unified orchestrator
- ✅ Basic hybrid search
- ✅ Performance monitoring

### Phase 2: Optimization
- 🔄 Advanced caching strategies
- 🔄 Performance tuning
- 🔄 Enhanced error handling
- 🔄 Security hardening

### Phase 3: Scale
- 📋 Horizontal scaling
- 📋 Multi-region deployment
- 📋 Advanced monitoring
- 📋 Machine learning ops

### Phase 4: Intelligence
- 📋 Adaptive processing
- 📋 ML-based optimization
- 📋 Predictive scaling
- 📋 Advanced analytics

## Best Practices

### Code Quality
- **SOLID Principles**: Clean architecture
- **DRY**: Avoid code duplication
- **KISS**: Keep it simple
- **Documentation**: Comprehensive docs

### Performance
- **Caching**: Multi-level strategy
- **Async**: Non-blocking operations
- **Batching**: Efficient processing
- **Monitoring**: Continuous optimization

### Security
- **Defense in Depth**: Multiple security layers
- **Principle of Least Privilege**: Minimal access
- **Zero Trust**: Verify everything
- **Regular Audits**: Security assessments

### Operations
- **Infrastructure as Code**: Automated deployment
- **Observability**: Full system visibility
- **Incident Response**: Prepared procedures
- **Continuous Improvement**: Regular optimization
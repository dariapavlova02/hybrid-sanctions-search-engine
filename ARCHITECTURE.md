# AI Service Architecture

## System Overview

The AI Service is a production-ready sanctions screening system built with a modern microservices architecture. It provides high-accuracy entity matching through a sophisticated multi-tier processing pipeline.

## Core Architecture

### Multi-Tier Screening Pipeline

```
Input Text → Tier 0: AC Exact → Tier 1: Blocking → Tier 2: Vector Search → Tier 3: Re-ranking → Decision
                ↓               ↓                ↓                    ↓
           Pattern Match    Fast Filter      Similarity Score    Multi-feature
           (Deterministic)  (Phonetic Keys)  (TF-IDF + n-grams)  (Ensemble)
```

### 1. **Tier 0: AC Exact Matching**
- **Purpose**: Deterministic pattern matching for exact entities
- **Technology**: Pre-built pattern templates
- **Performance**: < 100ms, high precision
- **Use Cases**: Exact names, aliases, regulatory identifiers

### 2. **Tier 1: Blocking & Filtering**  
- **Purpose**: Fast candidate filtering from large datasets
- **Technology**: Phonetic algorithms (Soundex, Double Metaphone)
- **Performance**: < 200ms, high recall
- **Keys**: Surname normalization, first-initial matching, birth year windows

### 3. **Tier 2: Vector Similarity**
- **Purpose**: Semantic similarity using character and word n-grams
- **Technology**: TF-IDF vectorization + HNSW indexing
- **Performance**: < 500ms, balanced precision/recall
- **Features**: Character 3-5 grams, word 1-2 grams, cosine similarity

### 4. **Tier 3: Re-ranking & Scoring**
- **Purpose**: Multi-feature ensemble for final confidence scoring
- **Technology**: Weighted feature combination + calibration
- **Performance**: < 800ms, optimized precision
- **Features**: FastText embeddings, Jaro-Winkler, exact rule matching

## Service Components

### Text Processing Engine
```
Text Input → Unicode Cleaner → Language Detection → Morphological Analysis → Variant Generator
```

- **Unicode Service**: Normalize special characters and encoding issues
- **Language Detection**: Auto-detect Russian, Ukrainian, English
- **Morphological Analysis**: SpaCy + PyMorphy3 for declensions
- **Variant Generation**: 20+ algorithms for spelling variations

### Orchestration Layer
```
Request → Clean Orchestrator → Processing Stages → Cache Layer → Response
```

- **Clean Orchestrator**: Modern async processing pipeline
- **Legacy Orchestrator**: Backward compatibility fallback
- **Processing Stages**: Modular pipeline with error handling
- **Cache Service**: LRU cache with TTL for performance

### Screening Services
```
Screen Request → Multi-Tier Service → Decision Logic → Risk Assessment → Response
```

- **Multi-Tier Screening**: Coordinated tier execution with early stopping
- **Decision Logic**: Risk-based classification (AUTO_HIT, REVIEW, CLEAR)
- **Smart Filter**: Pattern template generation and optimization
- **Reranker**: Multi-feature scoring and candidate ranking

## Data Flow

### 1. Text Processing Flow
```
"Владимир Путин" → Normalization → "владимир путин"
                                 ↓
                    Variant Generation → ["vladimir putin", "wladimir putin", ...]
                                 ↓  
                    Language Detection → "ru" (confidence: 0.7)
```

### 2. Screening Flow
```
Entity Input → AC Exact (0.1s) → Found exact match? → AUTO_HIT
            ↓ (No exact match)
        Blocking Filter (0.2s) → Generate candidates (phonetic keys)
            ↓
        Vector Search (0.5s) → Score similarity (TF-IDF + n-grams)  
            ↓
        Re-ranking (0.8s) → Multi-feature scoring → REVIEW/CLEAR
```

### 3. Caching Strategy
```
Request Hash → Cache Check → Hit? → Return cached result
            ↓ (Cache miss)
        Process Request → Store result → Return with cache metadata
```

## Language Support

### Multi-language Processing Pipeline
- **Russian**: Full morphological support (PyMorphy3), Cyrillic normalization
- **Ukrainian**: Specialized character mapping, fallback to Russian morphology
- **English**: Standard NLP pipeline, SpaCy processing
- **Auto-detection**: langdetect with confidence scoring

### Cross-language Variant Generation
- **Transliteration**: Cyrillic ↔ Latin conversion with multiple schemas
- **Phonetic**: Cross-language phonetic matching
- **Visual**: Character similarity (е/e, а/a, р/p, etc.)

## Performance Optimizations

### Caching Architecture
- **L1 Cache**: In-memory LRU with TTL (default: 1 hour)
- **Cache Keys**: MD5 hash of normalized input parameters
- **Eviction**: Size-based (10,000 entries) + time-based cleanup
- **Metrics**: Hit rate, memory usage, entry age tracking

### Async Processing
- **FastAPI**: Modern async web framework
- **Batch Processing**: Concurrent processing with configurable limits
- **Connection Pooling**: Efficient resource management
- **Early Stopping**: Skip expensive tiers for high-confidence results

### Resource Management
- **Memory**: Configurable limits with monitoring
- **CPU**: Multi-worker support for production scaling  
- **I/O**: Async file operations and database connections
- **Timeouts**: Per-tier and global timeout configuration

## Security Architecture

### Authentication & Authorization
- **API Keys**: Bearer token authentication for admin endpoints
- **Rate Limiting**: Configurable request limits per endpoint
- **Input Validation**: Pydantic models with length limits and sanitization

### Data Security
- **No Persistent Storage**: Stateless processing with cache-only storage
- **Audit Logging**: Comprehensive request/response logging
- **Error Handling**: Sanitized error messages to prevent information leakage

## Monitoring & Observability

### Health Monitoring
- **Health Checks**: Multi-level service health validation
- **Service Dependencies**: SpaCy models, configuration validation
- **Performance Metrics**: Processing times, success rates, resource usage

### Metrics Collection
- **Processing Statistics**: Request counts, success rates, average processing times
- **Cache Metrics**: Hit rates, memory usage, eviction statistics  
- **Screening Metrics**: Tier performance, decision distributions, early stopping rates
- **Prometheus Support**: Optional Prometheus metrics export

### Logging Architecture
- **Structured Logging**: JSON format with contextual information
- **Log Levels**: DEBUG, INFO, WARNING, ERROR with per-service configuration
- **Log Rotation**: Automatic file rotation with size and backup limits
- **Error Tracking**: Dedicated error logs with stack traces

## Configuration Management

### Hierarchical Configuration
```
Environment Variables → YAML Config Files → Code Defaults
```

- **Runtime Config**: Environment-specific settings (dev, staging, prod)
- **Service Config**: Feature flags, timeouts, resource limits
- **Screening Config**: Tier settings, thresholds, algorithm parameters

### Configuration Validation
- **Startup Validation**: Configuration consistency checks
- **Schema Validation**: Pydantic-based configuration models
- **Hot Reloading**: Dynamic configuration updates (development mode)

## Deployment Architecture

### Container Strategy
- **Multi-stage Docker**: Optimized production images
- **Health Checks**: Container-level health monitoring
- **Resource Limits**: Memory and CPU constraints
- **Security**: Non-root user, minimal attack surface

### Scaling Considerations
- **Horizontal Scaling**: Stateless design for easy replication
- **Load Balancing**: Round-robin or weighted distribution
- **Resource Planning**: Memory for caches, CPU for processing
- **Database**: External watchlist storage for production

This architecture provides a robust foundation for high-throughput sanctions screening with the flexibility to scale and adapt to changing requirements.
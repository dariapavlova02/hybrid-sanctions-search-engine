# Embeddings Service Documentation

## Overview

The Embeddings Service provides pure vector generation capabilities for text normalization and similarity analysis. It's designed to work seamlessly with the AI Service's 9-layer architecture, specifically supporting the normalization and signals layers.

## Model Choice

### Default Model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

**Why this model?**

1. **Multilingual Support**: Handles Russian, Ukrainian, and English text effectively
2. **Balanced Performance**: 384-dimensional vectors provide good quality without excessive computational overhead
3. **Proven Reliability**: Widely used in production environments for multilingual tasks
4. **Memory Efficient**: L12 architecture balances quality with resource usage
5. **Consistent Results**: Produces stable embeddings across different languages and scripts

**Technical Specifications:**
- **Dimensions**: 384 (32-bit float)
- **Languages**: 50+ languages including ru/uk/en
- **Model Size**: ~80MB
- **Inference Speed**: ~10-15ms per text on CPU

## Architecture Integration

### Why Dates/IDs Are Excluded

The Embeddings Service **deliberately excludes** dates and IDs from text processing:

1. **Separation of Concerns**: 
   - **Names** → Embeddings for semantic similarity
   - **Dates/IDs** → Separate comparison in Signals/Decision layers

2. **Semantic Focus**: 
   - Embeddings work best with semantic content (names, organizations)
   - Dates/IDs are structured data that don't benefit from semantic similarity

3. **Downstream Processing**:
   - Signals layer handles structured data extraction
   - Decision layer performs exact matching for dates/IDs
   - This separation allows for more precise matching strategies

4. **Performance**:
   - Cleaner embeddings without noise from structured data
   - More focused similarity calculations

### Preprocessing Pipeline

```
Input Text → EmbeddingPreprocessor → EmbeddingService → Vector Output
                ↓
        Remove dates/IDs
        Normalize spaces
        Clean text
```

## Configuration

### Basic Configuration

```python
from ai_service.config import EmbeddingConfig

# Default configuration
config = EmbeddingConfig()
# model_name: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# device: "cpu"
# batch_size: 64
# enable_index: False
# extra_models: []
```

### Model Switching

```python
# Switch to different model
config = EmbeddingConfig(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    extra_models=["sentence-transformers/all-MiniLM-L6-v2"]
)

# Add multiple allowed models
config = EmbeddingConfig(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    extra_models=[
        "sentence-transformers/all-MiniLM-L6-v2",
        "sentence-transformers/distiluse-base-multilingual-cased"
    ]
)
```

### Advanced Configuration

```python
# Production configuration
config = EmbeddingConfig(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    device="cuda",  # GPU acceleration
    batch_size=128,  # Larger batches for better throughput
    enable_index=False,  # No automatic indexing
    extra_models=[
        "sentence-transformers/all-MiniLM-L6-v2",
        "sentence-transformers/LaBSE"
    ]
)
```

## Usage Examples

### Basic Usage

```python
from ai_service.layers.embeddings.embedding_service import EmbeddingService
from ai_service.config import EmbeddingConfig

# Initialize service
config = EmbeddingConfig()
service = EmbeddingService(config)

# Single text encoding
vector = service.encode_one("Ivan Petrov")
print(f"Vector dimension: {len(vector)}")  # 384
print(f"Vector type: {type(vector[0])}")   # <class 'float'>

# Batch encoding
texts = ["Ivan Petrov", "Anna Smith", "Олександр Коваленко"]
vectors = service.encode_batch(texts)
print(f"Batch size: {len(vectors)}")       # 3
print(f"Each vector: {len(vectors[0])}")   # 384
```

### Multilingual Examples

```python
# Russian names
ru_names = ["Иван Петров", "Анна Смирнова", "Владимир Путин"]
ru_vectors = service.encode_batch(ru_names)

# Ukrainian names  
uk_names = ["Іван Петров", "Анна Смірнова", "Володимир Путін"]
uk_vectors = service.encode_batch(uk_names)

# English names
en_names = ["Ivan Petrov", "Anna Smirnova", "Vladimir Putin"]
en_vectors = service.encode_batch(en_names)

# All vectors will be 384-dimensional and comparable
```

### Organization Names

```python
# Organization names (dates/IDs automatically removed)
org_texts = [
    "ООО Рога и Копыта ИНН1234567890",
    "PrivatBank 2023-01-15",
    "Apple Inc. founded 1976"
]

# Preprocessing removes dates/IDs, keeps organization names
vectors = service.encode_batch(org_texts)
# Results in vectors for: "ООО Рога и Копыта", "PrivatBank", "Apple Inc. founded"
```

## Performance SLA

### Latency Targets

- **Single Text**: < 15ms (p95)
- **Batch Processing**: < 200ms for 1000 texts (p95)
- **Cold Start**: < 2s (first model load)

### Memory Usage

- **Model Loading**: ~80MB RAM
- **Batch Processing**: ~1MB per 100 texts
- **Peak Memory**: < 200MB for typical workloads

### Throughput

- **CPU**: ~100 texts/second
- **GPU**: ~500 texts/second (with CUDA)

## Experimental Features

### Include Attributes Flag (Future)

```python
# Future experimental feature
from ai_service.services.embedding_preprocessor import EmbeddingPreprocessor

preprocessor = EmbeddingPreprocessor()

# Default behavior (current)
text = "Ivan Petrov 1980-01-01 passport12345"
cleaned = preprocessor.normalize_for_embedding(text)
print(cleaned)  # "Ivan Petrov"

# Experimental: include attributes
cleaned_with_attrs = preprocessor.normalize_for_embedding(
    text, 
    include_attrs=True  # Future flag
)
print(cleaned_with_attrs)  # "Ivan Petrov 1980-01-01 passport12345"
```

**Note**: This feature is planned for future development when attribute-aware embeddings are needed.

## Integration with Other Services

### Signals Service

```python
# Signals service handles structured data
from ai_service.layers.signals.signals_service import SignalsService

signals_service = SignalsService()
signals = signals_service.extract_signals("Ivan Petrov 1980-01-01 passport12345")

# Embeddings service handles semantic similarity
embeddings = service.encode_one("Ivan Petrov")

# Decision service combines both
decision = decision_service.make_decision(embeddings, signals)
```

### Normalization Service

```python
# Normalization service provides clean text
from ai_service.layers.normalization.normalization_service import NormalizationService

norm_service = NormalizationService()
normalized = norm_service.normalize("Іван Петров")

# Embeddings service processes normalized text
embeddings = service.encode_one(normalized.normalized)
```

## Troubleshooting

### Common Issues

1. **Model Loading Errors**:
   ```python
   # Check model availability
   from sentence_transformers import SentenceTransformer
   model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
   ```

2. **Memory Issues**:
   ```python
   # Reduce batch size
   config = EmbeddingConfig(batch_size=32)
   ```

3. **Performance Issues**:
   ```python
   # Enable GPU if available
   config = EmbeddingConfig(device="cuda")
   ```

### Debugging

```python
# Enable debug logging
import logging
logging.getLogger("ai_service.layers.embeddings").setLevel(logging.DEBUG)

# Check model info
info = service.get_model_info()
print(f"Model: {info['model_name']}")
print(f"Device: {info['device']}")
```

## Best Practices

1. **Batch Processing**: Always use `encode_batch` for multiple texts
2. **Model Reuse**: Initialize service once and reuse
3. **Memory Management**: Process large datasets in chunks
4. **Error Handling**: Always handle potential model loading errors
5. **Performance Monitoring**: Use provided timing logs for optimization
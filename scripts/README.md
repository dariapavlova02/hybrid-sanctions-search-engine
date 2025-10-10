# Scripts Directory

Core scripts for AI Service deployment, data preparation, and maintenance.

## 📦 Core Pipeline Scripts

### Data Preparation & Deployment

#### `prepare_sanctions_data.py`
Generate AC patterns and vector embeddings from source sanctions data.

**Usage:**
```bash
# Full preparation (AC patterns + vectors)
python scripts/prepare_sanctions_data.py

# Skip vector generation (faster)
python scripts/prepare_sanctions_data.py --skip-vectors

# Limit patterns per entity
python scripts/prepare_sanctions_data.py --max-patterns 100

# Custom output directory
python scripts/prepare_sanctions_data.py --output-dir /path/to/output
```

**Input:**
- `src/ai_service/data/sanctioned_persons.json`
- `src/ai_service/data/sanctioned_companies.json`
- `src/ai_service/data/terrorism_black_list.json`

**Output:**
- `output/sanctions/ac_patterns_YYYYMMDD_HHMMSS.json` (~1.1GB)
- `output/sanctions/vectors_YYYYMMDD_HHMMSS.json` (~206MB)

---

#### `deploy_to_elasticsearch.py`
Load prepared data into Elasticsearch indices.

**Usage:**
```bash
# Auto-detect latest files
python scripts/deploy_to_elasticsearch.py --es-host localhost:9200

# Specify files
python scripts/deploy_to_elasticsearch.py \
  --es-host localhost:9200 \
  --patterns-file output/sanctions/ac_patterns_20251010.json \
  --vectors-file output/sanctions/vectors_20251010.json \
  --create-vector-indices

# Skip warmup queries
python scripts/deploy_to_elasticsearch.py \
  --es-host localhost:9200 \
  --skip-warmup
```

**Features:**
- Batch loading (5000 patterns, 1000 vectors per batch)
- Automatic index creation with proper mappings
- Health checks and verification
- Warmup queries for cache preloading

---

#### `full_deployment_pipeline.py` ⭐ **RECOMMENDED**
Complete deployment pipeline combining preparation and deployment.

**Usage:**
```bash
# Full pipeline (prepare + deploy)
python scripts/full_deployment_pipeline.py --es-host localhost:9200

# Skip data preparation (use existing files)
python scripts/full_deployment_pipeline.py \
  --es-host localhost:9200 \
  --skip-preparation

# Only prepare data (no ES deployment)
python scripts/full_deployment_pipeline.py --prepare-only

# Production deployment
python scripts/full_deployment_pipeline.py \
  --es-host elasticsearch:9200 \
  --max-patterns 200
```

**Docker Usage:**
```bash
# Inside Docker container
docker exec ai-service-prod python scripts/full_deployment_pipeline.py \
  --es-host elasticsearch:9200
```

---

### Docker Initialization

#### `docker-entrypoint.sh`
Automatic Elasticsearch initialization when Docker container starts.

**How it works:**
1. Waits for Elasticsearch to be ready (up to 60s)
2. Checks if indices exist
3. If missing, automatically loads data from `output/sanctions/`
4. Sets environment variables for index names
5. Starts the application

**Configuration (docker-compose.yml):**
```yaml
environment:
  - ES_HOSTS=elasticsearch:9200
  - ES_INDEX_PREFIX=sanctions
  - ES_STARTUP_TIMEOUT=60
  - SKIP_ES_INIT=false
```

---

#### `create_empty_indices.py`
Create Elasticsearch indices with proper mappings (used by entrypoint).

**Usage:**
```bash
python scripts/create_empty_indices.py \
  --es-host localhost:9200 \
  --index-prefix sanctions
```

---

### Vector Generation

#### `generate_vectors.py`
Generate sentence-transformer embeddings for semantic search.

**Usage:**
```bash
python scripts/generate_vectors.py \
  --input output/sanctions/ac_patterns_20251010.json \
  --output output/sanctions/vectors_20251010.json \
  --max-patterns 10000
```

**Note:** Usually called automatically by `prepare_sanctions_data.py`.

---

## 🛠️ Utility Scripts

### INN Cache Management

#### `generate_inn_cache.py`
Generate INN validation cache for fast lookups.

**Usage:**
```bash
python scripts/generate_inn_cache.py \
  --output src/ai_service/data/inn_cache.json
```

---

#### `extract_sanctioned_inns.py`
Extract all INNs from sanctions data.

**Usage:**
```bash
python scripts/extract_sanctioned_inns.py \
  --persons src/ai_service/data/sanctioned_persons.json \
  --companies src/ai_service/data/sanctioned_companies.json \
  --output output/sanctioned_inns.json
```

---

### Monitoring & Health Checks

#### `health_check.sh`
Check service health and connectivity.

**Usage:**
```bash
bash scripts/health_check.sh

# Custom host
bash scripts/health_check.sh http://localhost:8000
```

---

#### `check_production_data.sh`
Verify production data on remote server.

**Usage:**
```bash
bash scripts/check_production_data.sh
```

**Checks:**
- Source files existence
- Output files status
- Elasticsearch indices
- Document counts

---

### Production Setup

#### `setup_production_env.sh`
Initial production environment setup.

**Usage:**
```bash
bash scripts/setup_production_env.sh
```

---

#### `emergency_procedures.sh`
Emergency rollback and recovery procedures.

**Usage:**
```bash
bash scripts/emergency_procedures.sh
```

---

## 🔧 Development & Installation

#### `post_install.py`
Install required NLP models and dependencies.

**Usage:**
```bash
python scripts/post_install.py
```

**Installs:**
- SpaCy models: `en_core_web_sm`, `ru_core_news_sm`, `uk_core_news_sm`
- NLTK data: `stopwords`, `punkt`, `averaged_perceptron_tagger`
- Pymorphy3 dictionaries: Russian, Ukrainian

---

## 📚 Documentation

- `README_SANCTIONS_PIPELINE.md` - Detailed sanctions data pipeline documentation
- `CLEANUP_PLAN.md` - Scripts cleanup and reorganization plan
- `requirements_elasticsearch.txt` - Elasticsearch Python dependencies

---

## 📂 Project Structure

```
scripts/
├── prepare_sanctions_data.py          # Data preparation
├── deploy_to_elasticsearch.py         # ES deployment
├── full_deployment_pipeline.py        # Complete pipeline ⭐
├── docker-entrypoint.sh               # Docker init
├── create_empty_indices.py            # Index creation
├── generate_vectors.py                # Vector generation
├── generate_inn_cache.py              # INN cache
├── extract_sanctioned_inns.py         # INN extraction
├── health_check.sh                    # Health monitoring
├── check_production_data.sh           # Production checks
├── setup_production_env.sh            # Production setup
├── emergency_procedures.sh            # Emergency recovery
├── post_install.py                    # Model installation
├── requirements_elasticsearch.txt     # Dependencies
└── README.md                          # This file

../tests/scripts/                      # Test scripts
../docs/examples/                      # Templates and examples
```

---

## 🚀 Quick Start

### Local Development

```bash
# 1. Install dependencies
pip install -r scripts/requirements_elasticsearch.txt

# 2. Install models
python scripts/post_install.py

# 3. Prepare data
python scripts/prepare_sanctions_data.py

# 4. Deploy to local ES
python scripts/deploy_to_elasticsearch.py --es-host localhost:9200
```

### Production Deployment

```bash
# SSH to production server
ssh root@production-server

# Full pipeline inside Docker
docker exec ai-service-prod python scripts/full_deployment_pipeline.py \
  --es-host elasticsearch:9200
```

### Docker First Run

```bash
# Just start - entrypoint handles everything
docker-compose up -d

# Check logs
docker logs ai-service
```

---

## ⚙️ Configuration

### Environment Variables

- `ES_HOSTS` - Elasticsearch hosts (comma-separated)
- `ES_INDEX_PREFIX` - Index name prefix (default: `sanctions`)
- `ES_AC_INDEX` - AC patterns index name
- `ES_VECTOR_INDEX` - Vectors index name
- `ES_STARTUP_TIMEOUT` - Startup timeout in seconds (default: 60)
- `SKIP_ES_INIT` - Skip automatic initialization (default: false)

### Index Names

Default naming:
- AC Patterns: `sanctions_ac_patterns`
- Vectors: `sanctions_vectors`

Custom prefix:
```bash
python scripts/deploy_to_elasticsearch.py \
  --index-prefix custom_prefix
```

Results in:
- `custom_prefix_ac_patterns`
- `custom_prefix_vectors`

---

## 🔍 Troubleshooting

### Vectors not loading (HTTP 413)

**Problem:** Request too large for Elasticsearch.

**Solution:** Already fixed with batching (1000 vectors per batch).

### Indices not found (404 errors)

**Problem:** Index names don't match configuration.

**Solution:** Use `full_deployment_pipeline.py` or ensure `docker-entrypoint.sh` runs on startup.

### No data in indices

**Problem:** Deployment skipped or failed.

**Check:**
```bash
curl http://localhost:9200/sanctions_ac_patterns/_count
curl http://localhost:9200/sanctions_vectors/_count
```

**Fix:**
```bash
python scripts/full_deployment_pipeline.py --es-host localhost:9200
```

---

## 📊 Data Statistics

| Item | Size | Count |
|------|------|-------|
| AC Patterns File | ~1.1GB | ~2.7M patterns |
| Vectors File | ~206MB | ~10K vectors |
| ES AC Index | ~245MB compressed | 2,768,827 docs |
| ES Vectors Index | ~XXX MB | 10,000 docs |

---

## 🔗 Related Documentation

- [Elasticsearch Deployment Guide](../ELASTICSEARCH_DEPLOYMENT.md)
- [Entrypoint Summary](../ENTRYPOINT_SUMMARY.md)
- [Elasticsearch Fix Summary](../ELASTICSEARCH_FIX_SUMMARY.md)
- [Sanctions Pipeline Details](README_SANCTIONS_PIPELINE.md)

---

## 📝 Change Log

### 2025-10-10
- ✅ Added batching to vector loading (fixes HTTP 413)
- ✅ Created `full_deployment_pipeline.py` for complete automation
- ✅ Cleaned up deprecated scripts (from 60+ to 17 essential files)
- ✅ Reorganized tests → `tests/scripts/`
- ✅ Reorganized examples → `docs/examples/`
- ✅ Updated `docker-entrypoint.sh` to load vectors automatically

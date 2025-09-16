# Elasticsearch Index Templates - cURL Commands

## 1. Component Template (Analyzers & Normalizers)

```bash
# Create component template for analyzers and normalizers
curl -X PUT "localhost:9200/_component_template/watchlist_analyzers" \
  -H "Content-Type: application/json" \
  -d '{
    "template": {
      "settings": {
        "analysis": {
          "normalizer": {
            "case_insensitive_normalizer": {
              "type": "custom",
              "filter": ["lowercase", "asciifolding", "icu_folding"]
            }
          },
          "analyzer": {
            "icu_text_analyzer": {
              "type": "custom",
              "tokenizer": "icu_tokenizer",
              "filter": ["icu_normalizer", "icu_folding", "lowercase"]
            },
            "shingle_analyzer": {
              "type": "custom",
              "tokenizer": "icu_tokenizer",
              "filter": [
                "icu_normalizer",
                "icu_folding", 
                "lowercase",
                "shingle"
              ]
            },
            "char_ngram_analyzer": {
              "type": "custom",
              "tokenizer": "keyword",
              "filter": [
                "lowercase",
                "asciifolding",
                "char_ngram_filter"
              ]
            }
          },
          "filter": {
            "char_ngram_filter": {
              "type": "ngram",
              "min_gram": 3,
              "max_gram": 5,
              "token_chars": ["letter", "digit"]
            },
            "shingle": {
              "type": "shingle",
              "min_shingle_size": 2,
              "max_shingle_size": 3,
              "output_unigrams": true
            }
          }
        }
      }
    }
  }'
```

## 2. Index Template for Persons

```bash
# Create index template for person entities
curl -X PUT "localhost:9200/_index_template/watchlist_persons_v1" \
  -H "Content-Type: application/json" \
  -d '{
    "index_patterns": ["watchlist_persons_v1*"],
    "template": {
      "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
        "index": {
          "knn": true,
          "knn.algo_param.ef_search": 100
        }
      },
      "mappings": {
        "properties": {
          "entity_id": {
            "type": "keyword"
          },
          "entity_type": {
            "type": "keyword"
          },
          "dob": {
            "type": "date",
            "format": "yyyy-MM-dd||yyyy-MM||yyyy"
          },
          "country": {
            "type": "keyword"
          },
          "normalized_name": {
            "type": "keyword",
            "normalizer": "case_insensitive_normalizer"
          },
          "aliases": {
            "type": "keyword",
            "normalizer": "case_insensitive_normalizer"
          },
          "name_text": {
            "type": "text",
            "analyzer": "icu_text_analyzer",
            "fields": {
              "shingle": {
                "type": "text",
                "analyzer": "shingle_analyzer"
              }
            }
          },
          "name_ngrams": {
            "type": "text",
            "analyzer": "char_ngram_analyzer"
          },
          "name_vector": {
            "type": "dense_vector",
            "dims": 384,
            "index": true,
            "similarity": "cosine"
          },
          "meta": {
            "type": "object",
            "enabled": true
          }
        }
      }
    },
    "composed_of": ["watchlist_analyzers"],
    "priority": 200
  }'
```

## 3. Index Template for Organizations

```bash
# Create index template for organization entities
curl -X PUT "localhost:9200/_index_template/watchlist_orgs_v1" \
  -H "Content-Type: application/json" \
  -d '{
    "index_patterns": ["watchlist_orgs_v1*"],
    "template": {
      "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
        "index": {
          "knn": true,
          "knn.algo_param.ef_search": 100
        }
      },
      "mappings": {
        "properties": {
          "entity_id": {
            "type": "keyword"
          },
          "entity_type": {
            "type": "keyword"
          },
          "dob": {
            "type": "date",
            "format": "yyyy-MM-dd||yyyy-MM||yyyy"
          },
          "country": {
            "type": "keyword"
          },
          "normalized_name": {
            "type": "keyword",
            "normalizer": "case_insensitive_normalizer"
          },
          "aliases": {
            "type": "keyword",
            "normalizer": "case_insensitive_normalizer"
          },
          "name_text": {
            "type": "text",
            "analyzer": "icu_text_analyzer",
            "fields": {
              "shingle": {
                "type": "text",
                "analyzer": "shingle_analyzer"
              }
            }
          },
          "name_ngrams": {
            "type": "text",
            "analyzer": "char_ngram_analyzer"
          },
          "name_vector": {
            "type": "dense_vector",
            "dims": 384,
            "index": true,
            "similarity": "cosine"
          },
          "meta": {
            "type": "object",
            "enabled": true
          }
        }
      }
    },
    "composed_of": ["watchlist_analyzers"],
    "priority": 200
  }'
```

## 4. Verification Commands

```bash
# Check component template
curl -X GET "localhost:9200/_component_template/watchlist_analyzers"

# Check index templates
curl -X GET "localhost:9200/_index_template/watchlist_persons_v1"
curl -X GET "localhost:9200/_index_template/watchlist_orgs_v1"

# List all templates
curl -X GET "localhost:9200/_index_template"
curl -X GET "localhost:9200/_component_template"
```

## 5. Test with Sample Data

```bash
# Test person index
curl -X POST "localhost:9200/watchlist_persons_v1/_doc" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "P001",
    "entity_type": "person",
    "dob": "1985-05-15",
    "country": "RU",
    "normalized_name": "Иван Петров",
    "aliases": ["И. Петров", "Ivan Petrov"],
    "name_text": "Иван Петров",
    "name_ngrams": "Иван Петров",
    "name_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
    "meta": {
      "source": "test",
      "confidence": 0.95
    }
  }'

# Test organization index
curl -X POST "localhost:9200/watchlist_orgs_v1/_doc" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "O001",
    "entity_type": "org",
    "country": "RU",
    "normalized_name": "Газпром",
    "aliases": ["Газпром Нефть", "Gazprom"],
    "name_text": "Газпром",
    "name_ngrams": "Газпром",
    "name_vector": [0.2, 0.3, 0.4, 0.5, 0.6],
    "meta": {
      "source": "test",
      "industry": "energy"
    }
  }'
```

## 6. Search Examples

```bash
# AC search (exact/almost-exact)
curl -X POST "localhost:9200/watchlist_persons_v1/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "should": [
          {
            "multi_match": {
              "query": "Иван Петров",
              "fields": ["normalized_name^2.0", "aliases^1.5"],
              "type": "best_fields",
              "fuzziness": 1
            }
          },
          {
            "match_phrase": {
              "name_text.shingle": {
                "query": "Иван Петров",
                "boost": 2.0
              }
            }
          }
        ]
      }
    }
  }'

# Vector search (kNN)
curl -X POST "localhost:9200/watchlist_persons_v1/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "knn": {
      "field": "name_vector",
      "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
      "k": 10,
      "num_candidates": 100
    }
  }'

# Hybrid search (AC + Vector)
curl -X POST "localhost:9200/watchlist_persons_v1/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "should": [
          {
            "multi_match": {
              "query": "Иван Петров",
              "fields": ["normalized_name^2.0", "aliases^1.5"],
              "type": "best_fields",
              "fuzziness": 1,
              "boost": 1.2
            }
          },
          {
            "knn": {
              "field": "name_vector",
              "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
              "k": 10,
              "num_candidates": 100,
              "boost": 1.0
            }
          }
        ]
      }
    }
  }'
```

## Field Descriptions

### Core Fields
- **entity_id**: Unique identifier (keyword)
- **entity_type**: Entity type - "person" or "org" (keyword)
- **dob**: Date of birth (date, optional)
- **country**: Country code (keyword)

### Search Fields
- **normalized_name**: Normalized name for exact matching (keyword with case-insensitive normalizer)
- **aliases**: Alternative names (keyword multi-value with case-insensitive normalizer)
- **name_text**: Full-text search field (text with ICU analyzer)
- **name_ngrams**: Character n-grams for fuzzy matching (text with char_ngram analyzer)
- **name_vector**: Dense vector for kNN search (dense_vector, 384 dims, cosine similarity)

### Metadata
- **meta**: Flexible metadata object (object, enabled)

## Analyzers

### case_insensitive_normalizer
- **Purpose**: Case-insensitive exact matching
- **Filters**: lowercase, asciifolding, icu_folding
- **Note**: Preserves Cyrillic characters in folding

### icu_text_analyzer
- **Purpose**: Full-text search with Unicode support
- **Tokenizer**: icu_tokenizer
- **Filters**: icu_normalizer, icu_folding, lowercase

### shingle_analyzer
- **Purpose**: Phrase matching with shingles
- **Tokenizer**: icu_tokenizer
- **Filters**: icu_normalizer, icu_folding, lowercase, shingle (2-3 grams)

### char_ngram_analyzer
- **Purpose**: Character n-grams for fuzzy matching
- **Tokenizer**: keyword
- **Filters**: lowercase, asciifolding, char_ngram_filter (3-5 grams)

#!/bin/bash

# Elasticsearch Index Templates Setup for Watchlist Search
# This script creates component templates and index templates for hybrid search

set -e

# Configuration
ES_HOST="${ES_HOST:-localhost:9200}"
ES_USER="${ES_USER:-}"
ES_PASS="${ES_PASS:-}"

# Build curl command with authentication if provided
CURL_CMD="curl -s"
if [ -n "$ES_USER" ] && [ -n "$ES_PASS" ]; then
    CURL_CMD="curl -s -u $ES_USER:$ES_PASS"
fi

echo "Setting up Elasticsearch templates for watchlist search..."
echo "Target: $ES_HOST"

# 1. Create component template for analyzers and normalizers
echo "Creating component template: watchlist_analyzers"
$CURL_CMD -X PUT "$ES_HOST/_component_template/watchlist_analyzers" \
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

echo ""

# 2. Create index template for persons
echo "Creating index template: watchlist_persons_v1"
$CURL_CMD -X PUT "$ES_HOST/_index_template/watchlist_persons_v1" \
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

echo ""

# 3. Create index template for organizations
echo "Creating index template: watchlist_orgs_v1"
$CURL_CMD -X PUT "$ES_HOST/_index_template/watchlist_orgs_v1" \
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

echo ""

# 4. Verify templates were created
echo "Verifying templates..."
echo "Component templates:"
$CURL_CMD -X GET "$ES_HOST/_component_template/watchlist_analyzers"

echo ""
echo "Index templates:"
$CURL_CMD -X GET "$ES_HOST/_index_template/watchlist_persons_v1"
$CURL_CMD -X GET "$ES_HOST/_index_template/watchlist_orgs_v1"

echo ""
echo "Setup completed successfully!"
echo ""
echo "Usage:"
echo "  ES_HOST=localhost:9200 ES_USER=elastic ES_PASS=password ./elasticsearch_setup.sh"
echo ""
echo "Test with sample data:"
echo "  curl -X POST \"$ES_HOST/watchlist_persons_v1/_doc\" -H \"Content-Type: application/json\" -d '{\"entity_id\":\"P001\",\"entity_type\":\"person\",\"normalized_name\":\"Иван Петров\",\"name_text\":\"Иван Петров\",\"name_ngrams\":\"Иван Петров\",\"name_vector\":[0.1,0.2,...],\"meta\":{\"source\":\"test\"}}'"

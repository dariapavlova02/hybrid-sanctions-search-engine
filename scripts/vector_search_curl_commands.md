# Vector Search cURL Commands

Готовые cURL команды для тестирования kNN поиска в Elasticsearch.

## 1. Basic kNN Query

### Простой kNN поиск
```bash
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "knn": {
      "field": "name_vector",
      "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
      "k": 50,
      "num_candidates": 100,
      "similarity": "cosine",
      "filter": {
        "bool": {
          "must": [
            {
              "term": {
                "entity_type": "person"
              }
            }
          ]
        }
      }
    },
    "size": 50,
    "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "dob", "meta"]
  }'
```

### kNN с фильтром по стране
```bash
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "knn": {
      "field": "name_vector",
      "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
      "k": 50,
      "num_candidates": 150,
      "similarity": "cosine",
      "filter": {
        "bool": {
          "must": [
            {
              "term": {
                "entity_type": "person"
              }
            },
            {
              "term": {
                "country": "RU"
              }
            }
          ]
        }
      }
    },
    "size": 50,
    "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "dob", "meta"]
  }'
```

## 2. Post-Filtered kNN Query

### kNN с пост-фильтрацией
```bash
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "knn": {
      "field": "name_vector",
      "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
      "k": 50,
      "num_candidates": 200,
      "similarity": "cosine"
    },
    "post_filter": {
      "bool": {
        "must": [
          {
            "term": {
              "entity_type": "person"
            }
          },
          {
            "terms": {
              "meta.source": ["sanctions", "watchlist"]
            }
          }
        ]
      }
    },
    "size": 50,
    "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "dob", "meta"]
  }'
```

## 3. Hybrid Search (AC + Vector)

### Комбинированный поиск
```bash
curl -X POST "localhost:9200/_msearch" \
  -H "Content-Type: application/x-ndjson" \
  -d '{"index": "watchlist_persons_current", "search_type": "query_then_fetch"}
{"query": {"bool": {"must": [{"term": {"entity_type": "person"}}, {"terms": {"normalized_name": ["иван", "петров"], "boost": 2.0}}]}}, "size": 50, "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "dob", "meta"]}}
{"index": "watchlist_persons_current", "search_type": "query_then_fetch"}
{"knn": {"field": "name_vector", "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], "k": 50, "num_candidates": 100, "similarity": "cosine", "filter": {"bool": {"must": [{"term": {"entity_type": "person"}}]}}}, "size": 50, "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "dob", "meta"]}}'
```

## 4. Threshold Testing

### Тестирование порога семантического сходства
```bash
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "knn": {
      "field": "name_vector",
      "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
      "k": 50,
      "num_candidates": 100,
      "similarity": "cosine",
      "filter": {
        "bool": {
          "must": [
            {
              "term": {
                "entity_type": "person"
              }
            }
          ]
        }
      }
    },
    "min_score": 0.7,
    "size": 50,
    "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "dob", "meta"]
  }'
```

## 5. Performance Testing

### С профилированием
```bash
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "knn": {
      "field": "name_vector",
      "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
      "k": 50,
      "num_candidates": 100,
      "similarity": "cosine",
      "filter": {
        "bool": {
          "must": [
            {
              "term": {
                "entity_type": "person"
              }
            }
          ]
        }
      }
    },
    "size": 50,
    "profile": true,
    "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "dob", "meta"]
  }'
```

### С объяснением скоринга
```bash
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "knn": {
      "field": "name_vector",
      "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
      "k": 50,
      "num_candidates": 100,
      "similarity": "cosine",
      "filter": {
        "bool": {
          "must": [
            {
              "term": {
                "entity_type": "person"
              }
            }
          ]
        }
      }
    },
    "size": 5,
    "explain": true,
    "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "dob", "meta"]
  }'
```

## 6. Organizations Search

### kNN поиск по организациям
```bash
curl -X POST "localhost:9200/watchlist_orgs_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "knn": {
      "field": "name_vector",
      "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
      "k": 50,
      "num_candidates": 100,
      "similarity": "cosine",
      "filter": {
        "bool": {
          "must": [
            {
              "term": {
                "entity_type": "org"
              }
            }
          ]
        }
      }
    },
    "size": 50,
    "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "meta"]
  }'
```

## 7. Batch Testing

### Тестирование нескольких векторов
```bash
# Вектор 1
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "knn": {
      "field": "name_vector",
      "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
      "k": 25,
      "num_candidates": 50,
      "similarity": "cosine",
      "filter": {"bool": {"must": [{"term": {"entity_type": "person"}}]}}
    },
    "size": 25
  }'

# Вектор 2
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "knn": {
      "field": "name_vector",
      "query_vector": [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1],
      "k": 25,
      "num_candidates": 50,
      "similarity": "cosine",
      "filter": {"bool": {"must": [{"term": {"entity_type": "person"}}]}}
    },
    "size": 25
  }'
```

## 8. Monitoring Queries

### Проверка индекса
```bash
curl -X GET "localhost:9200/watchlist_persons_current/_stats"
curl -X GET "localhost:9200/watchlist_orgs_current/_stats"
```

### Проверка маппинга векторов
```bash
curl -X GET "localhost:9200/watchlist_persons_current/_mapping" | jq '.watchlist_persons_v1_001.mappings.properties.name_vector'
```

### Проверка настроек kNN
```bash
curl -X GET "localhost:9200/watchlist_persons_current/_settings" | jq '.watchlist_persons_v1_001.settings.index.knn'
```

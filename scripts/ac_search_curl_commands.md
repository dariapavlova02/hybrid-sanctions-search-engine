# AC Search cURL Commands

Готовые cURL команды для тестирования AC-этапа поиска в Elasticsearch.

## 1. Exact Match Query

### Поиск по normalized_name
```bash
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {
            "term": {
              "entity_type": "person"
            }
          },
          {
            "bool": {
              "should": [
                {
                  "terms": {
                    "normalized_name": ["иван", "петров"],
                    "boost": 2.0
                  }
                },
                {
                  "terms": {
                    "aliases": ["иван", "петров"],
                    "boost": 1.5
                  }
                }
              ],
              "minimum_should_match": 1
            }
          }
        ]
      }
    },
    "size": 50,
    "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "meta"]
  }'
```

### Поиск по aliases
```bash
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {
            "term": {
              "entity_type": "person"
            }
          },
          {
            "terms": {
              "aliases": ["и. петров", "ivan petrov"],
              "boost": 1.5
            }
          }
        ]
      }
    },
    "size": 50,
    "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "meta"]
  }'
```

## 2. Phrase Match Query

### Точная фраза (slop=0)
```bash
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {
            "term": {
              "entity_type": "person"
            }
          },
          {
            "match_phrase": {
              "name_text.shingle": {
                "query": "иван петров",
                "slop": 0,
                "boost": 1.8
              }
            }
          }
        ]
      }
    },
    "size": 50,
    "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "meta"]
  }'
```

### Фраза с допуском (slop=1)
```bash
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {
            "term": {
              "entity_type": "person"
            }
          },
          {
            "match_phrase": {
              "name_text.shingle": {
                "query": "иван петрович",
                "slop": 1,
                "boost": 1.8
              }
            }
          }
        ]
      }
    },
    "size": 50,
    "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "meta"]
  }'
```

## 3. N-gram Match Query

### Строгий n-gram поиск
```bash
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {
            "term": {
              "entity_type": "person"
            }
          },
          {
            "match": {
              "name_ngrams": {
                "query": "иван петров",
                "operator": "AND",
                "minimum_should_match": "100%",
                "boost": 1.0
              }
            }
          }
        ]
      }
    },
    "size": 50,
    "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "meta"]
  }'
```

### Частичный n-gram поиск
```bash
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {
            "term": {
              "entity_type": "person"
            }
          },
          {
            "match": {
              "name_ngrams": {
                "query": "иван",
                "operator": "AND",
                "minimum_should_match": "100%",
                "boost": 1.0
              }
            }
          }
        ]
      }
    },
    "size": 50,
    "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "meta"]
  }'
```

## 4. Multi-Search Query

### Все типы поиска одновременно
```bash
curl -X POST "localhost:9200/_msearch" \
  -H "Content-Type: application/x-ndjson" \
  -d '{"index": "watchlist_persons_current", "search_type": "query_then_fetch"}
{"query": {"bool": {"must": [{"term": {"entity_type": "person"}}, {"bool": {"should": [{"terms": {"normalized_name": ["иван", "петров"], "boost": 2.0}}, {"terms": {"aliases": ["иван", "петров"], "boost": 1.5}}], "minimum_should_match": 1}}]}}, "size": 50, "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "meta"]}}
{"index": "watchlist_persons_current", "search_type": "query_then_fetch"}
{"query": {"bool": {"must": [{"term": {"entity_type": "person"}}, {"match_phrase": {"name_text.shingle": {"query": "иван петров", "slop": 1, "boost": 1.8}}}]}}, "size": 50, "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "meta"]}}
{"index": "watchlist_persons_current", "search_type": "query_then_fetch"}
{"query": {"bool": {"must": [{"term": {"entity_type": "person"}}, {"match": {"name_ngrams": {"query": "иван петров", "operator": "AND", "minimum_should_match": "100%", "boost": 1.0}}}]}}, "size": 50, "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "meta"]}}'
```

## 5. Organizations Search

### Exact match для организаций
```bash
curl -X POST "localhost:9200/watchlist_orgs_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {
            "term": {
              "entity_type": "org"
            }
          },
          {
            "bool": {
              "should": [
                {
                  "terms": {
                    "normalized_name": ["газпром"],
                    "boost": 2.0
                  }
                },
                {
                  "terms": {
                    "aliases": ["газпром", "gazprom"],
                    "boost": 1.5
                  }
                }
              ],
              "minimum_should_match": 1
            }
          }
        ]
      }
    },
    "size": 50,
    "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "meta"]
  }'
```

### Phrase match для организаций
```bash
curl -X POST "localhost:9200/watchlist_orgs_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {
            "term": {
              "entity_type": "org"
            }
          },
          {
            "match_phrase": {
              "name_text.shingle": {
                "query": "ооо газпром",
                "slop": 1,
                "boost": 1.8
              }
            }
          }
        ]
      }
    },
    "size": 50,
    "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "meta"]
  }'
```

## 6. Threshold Testing

### Тестирование порогов
```bash
# Exact threshold >= 1.0
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"term": {"entity_type": "person"}},
          {"terms": {"normalized_name": ["иван петров"], "boost": 2.0}}
        ]
      }
    },
    "min_score": 1.0,
    "size": 50
  }'

# Phrase threshold >= 0.8
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"term": {"entity_type": "person"}},
          {"match_phrase": {"name_text.shingle": {"query": "иван петрович", "boost": 1.8}}}
        ]
      }
    },
    "min_score": 0.8,
    "size": 50
  }'

# N-gram threshold >= 0.6
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"term": {"entity_type": "person"}},
          {"match": {"name_ngrams": {"query": "иван", "operator": "AND", "boost": 1.0}}}
        ]
      }
    },
    "min_score": 0.6,
    "size": 50
  }'
```

## 7. Performance Testing

### С профилированием
```bash
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"term": {"entity_type": "person"}},
          {"terms": {"normalized_name": ["иван", "петров"], "boost": 2.0}}
        ]
      }
    },
    "size": 50,
    "profile": true,
    "_source": ["entity_id", "entity_type", "normalized_name", "aliases"]
  }'
```

### С объяснением скоринга
```bash
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"term": {"entity_type": "person"}},
          {"terms": {"normalized_name": ["иван", "петров"], "boost": 2.0}}
        ]
      }
    },
    "size": 5,
    "explain": true,
    "_source": ["entity_id", "entity_type", "normalized_name"]
  }'
```

## 8. Batch Testing

### Тестирование нескольких кандидатов
```bash
# Кандидат 1: Иван Петров
curl -X POST "localhost:9200/_msearch" \
  -H "Content-Type: application/x-ndjson" \
  -d '{"index": "watchlist_persons_current"}
{"query": {"bool": {"must": [{"term": {"entity_type": "person"}}, {"terms": {"normalized_name": ["иван", "петров"], "boost": 2.0}}]}}, "size": 10}}
{"index": "watchlist_persons_current"}
{"query": {"bool": {"must": [{"term": {"entity_type": "person"}}, {"match_phrase": {"name_text.shingle": {"query": "иван петров", "boost": 1.8}}}]}}, "size": 10}}
{"index": "watchlist_persons_current"}
{"query": {"bool": {"must": [{"term": {"entity_type": "person"}}, {"match": {"name_ngrams": {"query": "иван петров", "operator": "AND", "boost": 1.0}}}]}}, "size": 10}}'

# Кандидат 2: Мария Сидорова
curl -X POST "localhost:9200/_msearch" \
  -H "Content-Type: application/x-ndjson" \
  -d '{"index": "watchlist_persons_current"}
{"query": {"bool": {"must": [{"term": {"entity_type": "person"}}, {"terms": {"normalized_name": ["мария", "сидорова"], "boost": 2.0}}]}}, "size": 10}}
{"index": "watchlist_persons_current"}
{"query": {"bool": {"must": [{"term": {"entity_type": "person"}}, {"match_phrase": {"name_text.shingle": {"query": "мария сидорова", "boost": 1.8}}}]}}, "size": 10}}
{"index": "watchlist_persons_current"}
{"query": {"bool": {"must": [{"term": {"entity_type": "person"}}, {"match": {"name_ngrams": {"query": "мария сидорова", "operator": "AND", "boost": 1.0}}}]}}, "size": 10}}'
```

## 9. Error Testing

### Тестирование несуществующих данных
```bash
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"term": {"entity_type": "person"}},
          {"terms": {"normalized_name": ["несуществующее", "имя"], "boost": 2.0}}
        ]
      }
    },
    "size": 50
  }'
```

### Тестирование пустого запроса
```bash
curl -X POST "localhost:9200/watchlist_persons_current/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"term": {"entity_type": "person"}},
          {"terms": {"normalized_name": [], "boost": 2.0}}
        ]
      }
    },
    "size": 50
  }'
```

## 10. Monitoring Queries

### Проверка индекса
```bash
curl -X GET "localhost:9200/watchlist_persons_current/_stats"
curl -X GET "localhost:9200/watchlist_orgs_current/_stats"
```

### Проверка маппинга
```bash
curl -X GET "localhost:9200/watchlist_persons_current/_mapping"
curl -X GET "localhost:9200/watchlist_orgs_current/_mapping"
```

### Проверка настроек
```bash
curl -X GET "localhost:9200/watchlist_persons_current/_settings"
curl -X GET "localhost:9200/watchlist_orgs_current/_settings"
```

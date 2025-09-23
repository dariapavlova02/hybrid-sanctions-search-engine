#!/bin/bash
echo "🔍 Checking Poroshenko patterns in Elasticsearch..."

echo ""
echo "1. Check patterns with wildcard:"
curl 'http://95.217.84.234:9200/ai_service_ac_patterns/_search' \
  -H 'Content-Type: application/json' \
  -d '{"query": {"wildcard": {"pattern": "*порошенко*"}}, "size": 3}' | jq '.hits.hits[]._source.pattern'

echo ""
echo "2. Check exact pattern:"
curl 'http://95.217.84.234:9200/ai_service_ac_patterns/_search' \
  -H 'Content-Type: application/json' \
  -d '{"query": {"term": {"pattern": "порошенко петро"}}, "size": 3}' | jq '.hits.hits[]._source'

echo ""
echo "3. Check cluster health:"
curl 'http://95.217.84.234:9200/_cluster/health' | jq '.'

echo ""
echo "4. Check index info:"
curl 'http://95.217.84.234:9200/ai_service_ac_patterns/_count' | jq '.'

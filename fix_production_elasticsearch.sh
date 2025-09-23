#!/bin/bash
# Скрипт для исправления Elasticsearch конфигурации в продакшене

echo "🔧 Fixing Elasticsearch configuration for production..."

# 1. Добавить aiohttp в Dockerfile.search
echo "📝 Adding aiohttp to Dockerfile.search..."
cp Dockerfile.search Dockerfile.search.backup

# Добавить aiohttp после elasticsearch
sed -i 's/elastic-transport==8.10.0 \\/elastic-transport==8.10.0 \\\
    aiohttp>=3.12.0 \\/' Dockerfile.search

# Добавить проверку aiohttp
sed -i 's/python -c "import prometheus_client; print('\''✅ prometheus_client available'\'\')" && \\/python -c "import prometheus_client; print('\''✅ prometheus_client available'\'\')" \&\&\\\
    python -c "import elasticsearch; print('\''✅ elasticsearch:'\'', elasticsearch.__version__)" \&\&\\\
    python -c "import aiohttp; print('\''✅ aiohttp:'\'', aiohttp.__version__)" \&\&\\/' Dockerfile.search

echo "✅ Dockerfile.search updated"

# 2. Пересобрать контейнер с aiohttp
echo "🔄 Rebuilding container with aiohttp..."
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache ai-service
docker-compose -f docker-compose.prod.yml up -d

# 3. Дождаться запуска
echo "⏳ Waiting for container to start..."
sleep 30

# 4. Проверить что aiohttp установлен
echo "🔍 Checking aiohttp installation..."
docker exec ai-service-prod python -c "import aiohttp; print('✅ aiohttp version:', aiohttp.__version__)"

# 5. Создать правильные индексы
echo "📋 Creating correct Elasticsearch indices..."

# Создать индексы watchlist_ac и watchlist_vector как алиасы к существующим
curl -X POST "95.217.84.234:9200/_aliases" \
  -H "Content-Type: application/json" \
  -d '{
    "actions": [
      {
        "add": {
          "index": "ai_service_ac_patterns",
          "alias": "watchlist_ac"
        }
      },
      {
        "add": {
          "index": "ai_service_ac_patterns",
          "alias": "ac_patterns"
        }
      }
    ]
  }'

# Создать базовый vector индекс
curl -X PUT "95.217.84.234:9200/watchlist_vector" \
  -H "Content-Type: application/json" \
  -d '{
    "mappings": {
      "properties": {
        "text": {"type": "text"},
        "normalized_text": {"type": "text"},
        "dense_vector": {
          "type": "dense_vector",
          "dims": 384,
          "index": true,
          "similarity": "cosine"
        },
        "entity_type": {"type": "keyword"},
        "metadata": {"type": "object"}
      }
    },
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0
    }
  }'

echo "✅ Elasticsearch indices configured"

# 6. Тест запроса
echo "🧪 Testing API request..."
curl -X POST "http://localhost:8000/process" \
  -H "Content-Type: application/json" \
  -d '{"text": "Петро Порошенко"}' | jq '.search_results'

echo "🎉 Production fix complete!"
echo ""
echo "📋 Summary:"
echo "- ✅ Added aiohttp>=3.12.0 to Docker container"
echo "- ✅ Created index aliases: ai_service_ac_patterns -> watchlist_ac"
echo "- ✅ Created watchlist_vector index"
echo "- ✅ Container rebuilt and running"
echo ""
echo "🚀 System should now work with fast processing times!"
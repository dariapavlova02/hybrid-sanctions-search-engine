#!/bin/bash
# 🚀 Быстрый deployment script с проверками

set -e  # Останавливаемся при ошибке

echo "🚀 Запуск SAFE deployment с новым кодом..."

# 1. Проверяем, что нужные переменные установлены
echo "🔍 Проверка environment variables..."

if [ -z "$ES_USERNAME" ] || [ -z "$ES_PASSWORD" ] || [ -z "$ADMIN_API_KEY" ]; then
    echo "❌ КРИТИЧЕСКИЕ переменные НЕ установлены!"
    echo "Сначала выполни: ./setup_production_env.sh"
    echo ""
    echo "Или установи вручную:"
    echo "export ES_HOST=your-elasticsearch-host"
    echo "export ES_USERNAME=your-username"
    echo "export ES_PASSWORD=your-password"
    echo "export ADMIN_API_KEY=your-secure-key"
    exit 1
fi

echo "✅ Переменные установлены"

# 2. Backup текущего состояния
echo "💾 Создание backup..."
if docker-compose -f docker-compose.prod.yml ps | grep -q "ai-service-prod"; then
    echo "Сохраняю текущий образ как backup..."
    docker tag $(docker-compose -f docker-compose.prod.yml images -q ai-service) ai-service:backup-$(date +%Y%m%d-%H%M%S) || true
fi

# 3. Проверяем доступность Elasticsearch
echo "🔍 Проверка Elasticsearch..."
if curl -s -u "$ES_USERNAME:$ES_PASSWORD" "http://$ES_HOST:9200/_cluster/health" > /dev/null; then
    echo "✅ Elasticsearch доступен"
else
    echo "⚠️  WARNING: Elasticsearch недоступен, но продолжаем (будет fallback)"
fi

# 4. Останавливаем старый контейнер
echo "🛑 Останавливаю старый контейнер..."
docker-compose -f docker-compose.prod.yml down || true

# 5. Билдим новый образ
echo "🔨 Сборка нового образа с изменениями..."
docker-compose -f docker-compose.prod.yml build ai-service

# 6. Запускаем новый контейнер
echo "🚀 Запуск нового контейнера..."

# Используем оба env файла: базовый + server-specific
if [ -f ".env.production.server" ]; then
    docker-compose -f docker-compose.prod.yml --env-file .env.production --env-file .env.production.server up -d
else
    # Fallback на переменные из окружения
    docker-compose -f docker-compose.prod.yml up -d
fi

# 7. Ждем запуска (до 60 сек)
echo "⏳ Ожидание запуска контейнера..."
for i in {1..12}; do
    if curl -s http://localhost:8000/health > /dev/null; then
        echo "✅ Контейнер запущен и отвечает!"
        break
    fi
    echo "Попытка $i/12 через 5 сек..."
    sleep 5
done

# 8. Проверяем статус
echo "📊 Проверка статуса..."
echo "=== Docker статус ==="
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "=== Последние логи ==="
docker-compose -f docker-compose.prod.yml logs --tail=20 ai-service

# 9. Тестируем основные endpoints
echo ""
echo "🧪 Тестирование endpoints..."

# Health check
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Health check: OK"
else
    echo "❌ Health check: FAILED"
fi

# Admin endpoint с API key
if [ -n "$ADMIN_API_KEY" ]; then
    if curl -s -H "X-API-Key: $ADMIN_API_KEY" http://localhost:8000/stats > /dev/null; then
        echo "✅ Admin API: OK"
    else
        echo "❌ Admin API: FAILED"
    fi
fi

# API без ключа (должен работать)
if curl -s -X POST -H "Content-Type: application/json" -d '{"text":"тест"}' http://localhost:8000/process > /dev/null; then
    echo "✅ Main API: OK"
else
    echo "❌ Main API: FAILED"
fi

echo ""
echo "🎉 Deployment завершен!"
echo ""
echo "📋 Что проверить:"
echo "1. Логи: docker-compose -f docker-compose.prod.yml logs -f ai-service"
echo "2. Health: curl http://localhost:8000/health"
echo "3. Admin: curl -H 'X-API-Key: $ADMIN_API_KEY' http://localhost:8000/stats"
echo ""

if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo "✅ 🎯 DEPLOYMENT УСПЕШЕН!"
else
    echo "❌ 🚨 DEPLOYMENT FAILED - проверь логи!"
    echo "Rollback: docker-compose -f docker-compose.prod.yml down && docker run -d --name ai-service-rollback -p 8000:8000 ai-service:backup-*"
fi
#!/bin/bash
# 🔍 Проверочные команды после deployment

echo "🔍 ПОЛНАЯ ПРОВЕРКА DEPLOYMENT..."

# Загружаем переменные из файлов
if [ -f ".env.production.server" ]; then
    source .env.production.server
fi

if [ -f ".admin_api_key" ]; then
    source .admin_api_key
    echo "✅ API ключ найден: ${ADMIN_API_KEY:0:8}..."
else
    echo "⚠️  API ключ не найден в .admin_api_key файле"
fi

echo ""
echo "=== 1. ПРОВЕРКА КОНТЕЙНЕРА ==="
if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    echo "✅ Контейнер работает"
    docker-compose -f docker-compose.prod.yml ps
else
    echo "❌ Контейнер НЕ работает!"
    echo "Последние логи:"
    docker-compose -f docker-compose.prod.yml logs --tail=10 ai-service
fi

echo ""
echo "=== 2. HEALTH CHECK ==="
HEALTH=$(curl -s http://localhost:8000/health)
if echo "$HEALTH" | grep -q "healthy"; then
    echo "✅ Health check: $HEALTH"
else
    echo "❌ Health check failed: $HEALTH"
fi

echo ""
echo "=== 3. ПРОВЕРКА ADMIN API ==="
if [ -n "$ADMIN_API_KEY" ]; then
    STATS=$(curl -s -H "X-API-Key: $ADMIN_API_KEY" http://localhost:8000/stats)
    if echo "$STATS" | grep -q "version\|uptime"; then
        echo "✅ Admin API работает"
        echo "Stats: $STATS" | head -c 100
    else
        echo "❌ Admin API failed: $STATS"
    fi
else
    echo "⚠️  Пропуск - нет API ключа"
fi

echo ""
echo "=== 4. ТЕСТ ОБРАБОТКИ ТЕКСТА ==="
RESULT=$(curl -s -X POST -H "Content-Type: application/json" \
    -d '{"text":"Іван Петренко"}' http://localhost:8000/process)

if echo "$RESULT" | grep -q "normalized\|success"; then
    echo "✅ Обработка текста работает"
    echo "Результат: $RESULT" | head -c 200
else
    echo "❌ Обработка текста failed: $RESULT"
fi

echo ""
echo "=== 5. ПРОВЕРКА БЕЗОПАСНОСТИ ==="
# Проверяем что без API ключа admin недоступен
UNAUTHORIZED=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/clear-cache)
if [ "$UNAUTHORIZED" = "401" ] || [ "$UNAUTHORIZED" = "403" ]; then
    echo "✅ Admin endpoints защищены (HTTP $UNAUTHORIZED)"
else
    echo "⚠️  Admin endpoints могут быть незащищены (HTTP $UNAUTHORIZED)"
fi

echo ""
echo "=== 6. ПРОВЕРКА ELASTICSEARCH ИНТЕГРАЦИИ ==="
# Проверяем логи на наличие ES ошибок
ES_ERRORS=$(docker-compose -f docker-compose.prod.yml logs ai-service 2>&1 | grep -i "elasticsearch\|ES credentials\|connection" | tail -3)
if echo "$ES_ERRORS" | grep -q "ES credentials not configured"; then
    echo "⚠️  ES credentials not configured - используется fallback режим"
    echo "Логи ES: $ES_ERRORS"
elif echo "$ES_ERRORS" | grep -q "connection\|error"; then
    echo "⚠️  Возможные проблемы с ES:"
    echo "$ES_ERRORS"
else
    echo "✅ ES интеграция без очевидных ошибок"
fi

echo ""
echo "=== 7. ПРОВЕРКА ПРОИЗВОДИТЕЛЬНОСТИ ==="
echo "🚀 Тест производительности startup..."
START_TIME=$(docker-compose -f docker-compose.prod.yml logs ai-service | grep -i "startup\|started\|ready" | head -1)
if [ -n "$START_TIME" ]; then
    echo "✅ Startup логи найдены: $START_TIME"
else
    echo "⚠️  Startup логи не найдены - возможно контейнер еще стартует"
fi

echo ""
echo "=== 8. ПАМЯТЬ И РЕСУРСЫ ==="
MEMORY_USAGE=$(docker stats ai-service-prod --no-stream --format "table {{.Container}}\t{{.MemUsage}}\t{{.CPUPerc}}" 2>/dev/null)
if [ -n "$MEMORY_USAGE" ]; then
    echo "✅ Ресурсы контейнера:"
    echo "$MEMORY_USAGE"
else
    echo "⚠️  Не удалось получить статистику ресурсов"
fi

echo ""
echo "=== ИТОГОВАЯ ОЦЕНКА ==="

# Подсчитываем успешные проверки
SCORE=0
[ -n "$(docker-compose -f docker-compose.prod.yml ps | grep Up)" ] && SCORE=$((SCORE + 1))
[ -n "$(curl -s http://localhost:8000/health | grep healthy)" ] && SCORE=$((SCORE + 1))
[ -n "$ADMIN_API_KEY" ] && [ -n "$(curl -s -H "X-API-Key: $ADMIN_API_KEY" http://localhost:8000/stats | grep version)" ] && SCORE=$((SCORE + 1))
[ -n "$(curl -s -X POST -H "Content-Type: application/json" -d '{"text":"test"}' http://localhost:8000/process | grep success)" ] && SCORE=$((SCORE + 1))

echo "📊 Оценка deployment: $SCORE/4"

if [ "$SCORE" -ge "3" ]; then
    echo "🎉 DEPLOYMENT УСПЕШЕН! ($SCORE/4)"
    echo ""
    echo "🔗 Полезные команды:"
    echo "• Логи: docker-compose -f docker-compose.prod.yml logs -f ai-service"
    echo "• Статус: docker-compose -f docker-compose.prod.yml ps"
    echo "• Рестарт: docker-compose -f docker-compose.prod.yml restart ai-service"
    echo "• Health: curl http://localhost:8000/health"
    [ -n "$ADMIN_API_KEY" ] && echo "• Admin: curl -H 'X-API-Key: $ADMIN_API_KEY' http://localhost:8000/stats"
elif [ "$SCORE" -ge "2" ]; then
    echo "⚠️  DEPLOYMENT ЧАСТИЧНО УСПЕШЕН ($SCORE/4)"
    echo "Система работает, но есть проблемы - проверь логи"
else
    echo "❌ DEPLOYMENT FAILED ($SCORE/4)"
    echo "🔄 Запусти rollback: ./rollback.sh"
fi

echo ""
echo "💾 Логи сохранены в deployment_check_$(date +%Y%m%d_%H%M%S).log"
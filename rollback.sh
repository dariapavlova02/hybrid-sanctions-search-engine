#!/bin/bash
# 🔄 Emergency Rollback Script

echo "🚨 EMERGENCY ROLLBACK - откат к предыдущей версии"

# Останавливаем текущий контейнер
echo "🛑 Останавливаю current контейнер..."
docker-compose -f docker-compose.prod.yml down

# Ищем backup образы
echo "🔍 Поиск backup образов..."
BACKUP_IMAGES=$(docker images --format "table {{.Repository}}:{{.Tag}}" | grep "ai-service:backup" | head -5)

if [ -z "$BACKUP_IMAGES" ]; then
    echo "❌ Backup образы не найдены!"
    echo "Попробуй запустить без изменений:"
    echo "git checkout HEAD~1"
    echo "docker-compose -f docker-compose.prod.yml build && docker-compose -f docker-compose.prod.yml up -d"
    exit 1
fi

echo "📦 Найденные backup образы:"
echo "$BACKUP_IMAGES"

# Берем самый последний
LATEST_BACKUP=$(echo "$BACKUP_IMAGES" | head -1 | awk '{print $1}')
echo "🔄 Используем: $LATEST_BACKUP"

# Временно отключаем проблемные переменные
echo "⚠️  Временно отключаю новые security требования..."
export ES_USERNAME=""
export ES_PASSWORD=""
export ES_VERIFY_CERTS=false

# Запускаем старый образ
echo "🚀 Запуск rollback версии..."
docker run -d \
    --name ai-service-rollback \
    -p 8000:8000 \
    -e APP_ENV=production \
    -e DEBUG=false \
    -e ES_VERIFY_CERTS=false \
    "$LATEST_BACKUP"

# Ждем запуска
echo "⏳ Ожидание запуска..."
sleep 10

if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ ROLLBACK УСПЕШЕН!"
    echo "Старая версия работает на http://localhost:8000"
    echo ""
    echo "🔧 Для исправления проблем:"
    echo "1. Проверь переменные окружения"
    echo "2. Исправь конфигурацию"
    echo "3. Повторно запусти ./quick_deploy.sh"
    echo ""
    echo "🧹 Для очистки rollback:"
    echo "docker stop ai-service-rollback && docker rm ai-service-rollback"
else
    echo "❌ ROLLBACK FAILED!"
    echo "Ручной rollback:"
    echo "docker run -d -p 8000:8000 python:3.12-slim python -c 'print(\"Service unavailable\")'"
fi
#!/bin/bash
# 🚨 КРИТИЧНО: Setup script для production deployment
# Выполни ЭТО ПЕРЕД переподнятием контейнера!

echo "🔧 Настройка environment variables для production..."

# 1. КРИТИЧНО: Elasticsearch credentials (убраны hardcoded!)
echo "⚠️  ВНИМАНИЕ: Установи РЕАЛЬНЫЕ credentials для Elasticsearch:"

read -p "ES_HOST (например, localhost или IP): " ES_HOST
read -p "ES_USERNAME: " ES_USERNAME
read -s -p "ES_PASSWORD: " ES_PASSWORD
echo

# 2. Генерируем безопасный API ключ
echo "🔑 Генерирую безопасный Admin API ключ..."
ADMIN_API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null)

if [ -z "$ADMIN_API_KEY" ]; then
    echo "❌ Python не найден, используй этот ключ:"
    ADMIN_API_KEY="MANUALLY-SET-32-CHAR-SECURE-KEY-HERE"
fi

echo "Сгенерированный ADMIN_API_KEY: $ADMIN_API_KEY"

# 3. Создаем .env.production.server файл
cat > .env.production.server << EOF
# 🚨 КРИТИЧЕСКИЕ переменные для production server
# Сгенерировано $(date)

# ELASTICSEARCH CREDENTIALS (ОБЯЗАТЕЛЬНО!)
ES_HOST=${ES_HOST}
ES_USERNAME=${ES_USERNAME}
ES_PASSWORD=${ES_PASSWORD}
ES_VERIFY_CERTS=true

# ADMIN API KEY (ОБЯЗАТЕЛЬНО!)
ADMIN_API_KEY=${ADMIN_API_KEY}

# SECURITY SETTINGS
CORS_ORIGINS=["https://your-domain.com"]
RATE_LIMIT_ENABLED=true
MAX_REQUESTS_PER_MINUTE=6000

EOF

echo "✅ Создан файл .env.production.server"

# 4. Экспортируем переменные в текущую сессию
export ES_HOST="${ES_HOST}"
export ES_USERNAME="${ES_USERNAME}"
export ES_PASSWORD="${ES_PASSWORD}"
export ES_VERIFY_CERTS=true
export ADMIN_API_KEY="${ADMIN_API_KEY}"

echo "✅ Переменные экспортированы в текущую сессию"

# 5. Генерируем INN cache для FAST PATH оптимизации
echo "🚀 Генерирую INN cache для быстрой проверки санкций..."
if python3 scripts/extract_sanctioned_inns.py; then
    echo "✅ INN cache успешно сгенерирован с полным покрытием (persons, companies, terrorism)"
else
    echo "⚠️  Предупреждение: Не удалось сгенерировать INN cache, будет использоваться обычный поиск"
fi

# 6. Показываем что нужно сделать дальше
echo ""
echo "🎯 ЧТО ДЕЛАТЬ ДАЛЬШЕ:"
echo "1. Проверь, что Elasticsearch доступен:"
echo "   curl -u $ES_USERNAME:$ES_PASSWORD http://$ES_HOST:9200/_cluster/health"
echo ""
echo "2. Переподними контейнер:"
echo "   docker-compose -f docker-compose.prod.yml down"
echo "   docker-compose -f docker-compose.prod.yml --env-file .env.production --env-file .env.production.server up -d"
echo ""
echo "3. Проверь статус:"
echo "   docker-compose -f docker-compose.prod.yml logs ai-service"
echo ""
echo "4. Проверь API:"
echo "   curl -H 'X-API-Key: $ADMIN_API_KEY' http://localhost:8000/health"
echo ""

# Сохраняем API key в файл для последующего использования
echo "ADMIN_API_KEY=$ADMIN_API_KEY" > .admin_api_key
echo "💾 API ключ сохранен в .admin_api_key (добавь в .gitignore!)"

echo ""
echo "🚨 ВАЖНО: Сохрани эти данные в безопасном месте!"
echo "ES_USERNAME: $ES_USERNAME"
echo "ADMIN_API_KEY: $ADMIN_API_KEY"
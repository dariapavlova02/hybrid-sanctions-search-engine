#!/bin/bash
# Скрипт для обновления env.production с критическими переменными

echo "🔧 Обновление env.production с критическими переменными..."

# Добавить недостающие переменные в конец файла
cat >> env.production << 'EOF'

# === CRITICAL AC SEARCH VARIABLES ===
# Added for production fix
ENABLE_AHO_CORASICK=true
AHO_CORASICK_CONFIDENCE_BONUS=0.3
ALLOW_SMART_FILTER_SKIP=true
PRIORITIZE_QUALITY=true
ENABLE_FAISS_INDEX=true
ENABLE_AC_TIER0=true
ENABLE_VECTOR_FALLBACK=true
EOF

echo "✅ Переменные добавлены в env.production"

echo "📋 Содержимое обновленного файла:"
tail -10 env.production

echo ""
echo "🔄 Теперь выполните на сервере:"
echo "docker-compose -f docker-compose.prod.yml down"
echo "docker-compose -f docker-compose.prod.yml build ai-service"
echo "docker-compose -f docker-compose.prod.yml up -d"
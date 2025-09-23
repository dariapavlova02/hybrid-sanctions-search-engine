#!/bin/bash
# Скрипт для настройки продакшен сервера (95.217.84.234:8000)
# Активация всех ключевых функций для санкционного скрининга

echo "🚀 Настройка продакшен сервера для AI Service"
echo "================================================"

# Создать .env файл с критически важными переменными
echo "📝 Создание .env файла..."

cat > .env << 'EOF'
# Production Environment Variables for AI Service
# Активация всех ключевых функций для санкционного скрининга

# AC Pattern Search - КРИТИЧЕСКИ ВАЖНО!
ENABLE_AHO_CORASICK=true
AHO_CORASICK_CONFIDENCE_BONUS=0.3

# SmartFilter Configuration
ENABLE_SMART_FILTER=true
ALLOW_SMART_FILTER_SKIP=true

# Search Functionality
ENABLE_SEARCH=true
ENABLE_VECTOR_FALLBACK=true

# Other Features
ENABLE_VARIANTS=true
ENABLE_EMBEDDINGS=true
ENABLE_DECISION_ENGINE=true
ENABLE_METRICS=true

# Performance
PRIORITIZE_QUALITY=true
ENABLE_FAISS_INDEX=true

# Feature Flags
ENABLE_AC_TIER0=true
EOF

echo "✅ .env файл создан"

# Показать содержимое файла
echo ""
echo "📋 Содержимое .env файла:"
cat .env

echo ""
echo "🔧 Экспорт переменных в текущую сессию..."

# Экспортировать переменные для текущей сессии
export ENABLE_AHO_CORASICK=true
export AHO_CORASICK_CONFIDENCE_BONUS=0.3
export ENABLE_SMART_FILTER=true
export ALLOW_SMART_FILTER_SKIP=true
export ENABLE_SEARCH=true
export ENABLE_VECTOR_FALLBACK=true
export ENABLE_VARIANTS=true
export ENABLE_EMBEDDINGS=true
export ENABLE_DECISION_ENGINE=true
export ENABLE_METRICS=true
export PRIORITIZE_QUALITY=true
export ENABLE_FAISS_INDEX=true
export ENABLE_AC_TIER0=true

echo "✅ Переменные экспортированы"

echo ""
echo "📊 Проверка установленных переменных:"
echo "ENABLE_AHO_CORASICK=$ENABLE_AHO_CORASICK"
echo "ENABLE_SEARCH=$ENABLE_SEARCH"
echo "ENABLE_SMART_FILTER=$ENABLE_SMART_FILTER"

echo ""
echo "🔄 ПЕРЕЗАПУСК СЕРВИСА НЕОБХОДИМ!"
echo "================================="
echo "Выполните одну из команд:"
echo ""
echo "1. Если используется systemd:"
echo "   sudo systemctl restart ai-service"
echo ""
echo "2. Если запускается вручную:"
echo "   pkill -f 'python.*main.py'"
echo "   sleep 2"
echo "   nohup python -m src.ai_service.main > service.log 2>&1 &"
echo ""
echo "3. Или с загрузкой .env:"
echo "   pkill -f 'python.*main.py'"
echo "   sleep 2"
echo "   source .env && nohup python -m src.ai_service.main > service.log 2>&1 &"

echo ""
echo "🧪 ТЕСТИРОВАНИЕ:"
echo "================"
echo "После перезапуска проверьте:"
echo ""
echo "curl -X POST http://localhost:8000/process \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo "    \"text\": \"Ковриков Роман Валерійович\","
echo "    \"options\": {"
echo "      \"enable_advanced_features\": true,"
echo "      \"enable_search\": true"
echo "    }"
echo "  }'"
echo ""
echo "Ожидаемый результат:"
echo "- smartfilter_should_process: true"
echo "- search_results.total_hits > 0"
echo ""
echo "🎯 После успешного тестирования система будет работать 'как часы'!"
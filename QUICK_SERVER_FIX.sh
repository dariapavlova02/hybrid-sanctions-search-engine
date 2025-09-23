#!/bin/bash
# 🚀 БЫСТРОЕ ИСПРАВЛЕНИЕ ПРОДАКШЕН СЕРВЕРА
# Скопируйте эти команды на сервер 95.217.84.234

echo "🚀 Быстрое исправление AI Service на продакшен сервере"
echo "======================================================"

echo "1️⃣ Создание .env файла с критическими переменными..."

cat > .env << 'EOF'
ENABLE_AHO_CORASICK=true
AHO_CORASICK_CONFIDENCE_BONUS=0.3
ENABLE_SMART_FILTER=true
ALLOW_SMART_FILTER_SKIP=true
ENABLE_SEARCH=true
ENABLE_VECTOR_FALLBACK=true
ENABLE_VARIANTS=true
ENABLE_EMBEDDINGS=true
ENABLE_DECISION_ENGINE=true
ENABLE_METRICS=true
PRIORITIZE_QUALITY=true
ENABLE_FAISS_INDEX=true
ENABLE_AC_TIER0=true
EOF

echo "✅ .env файл создан"

echo "2️⃣ Экспорт переменных для текущей сессии..."

export ENABLE_AHO_CORASICK=true
export ENABLE_SEARCH=true
export ENABLE_SMART_FILTER=true
export ALLOW_SMART_FILTER_SKIP=true

echo "✅ Переменные экспортированы"

echo "3️⃣ Перезапуск сервиса..."

# Остановить старые процессы
pkill -f 'python.*main.py'
sleep 3

# Запустить с новыми переменными
nohup python -m src.ai_service.main > service.log 2>&1 &

echo "✅ Сервис перезапущен"

echo "4️⃣ Ожидание запуска (5 секунд)..."
sleep 5

echo "5️⃣ Проверка работоспособности..."

# Health check
curl -s http://localhost:8000/health && echo " ✅ Health check OK"

echo "6️⃣ Тест SmartFilter с санкционным лицом..."

# Критический тест
curl -X POST http://localhost:8000/process \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "Ковриков Роман Валерійович",
    "options": {
      "enable_advanced_features": true,
      "enable_search": true
    }
  }' 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    should_process = data.get('decision', {}).get('decision_details', {}).get('smartfilter_should_process', False)
    total_hits = data.get('search_results', {}).get('total_hits', 0)

    if should_process and total_hits > 0:
        print('🎉 УСПЕХ! SmartFilter разрешает обработку и поиск находит результаты!')
        print(f'   SmartFilter: {should_process}')
        print(f'   Search hits: {total_hits}')
    elif should_process:
        print('⚠️  SmartFilter работает, но поиск не находит результаты')
        print(f'   SmartFilter: {should_process}')
        print(f'   Search hits: {total_hits}')
    else:
        print('❌ SmartFilter все еще блокирует! Проверьте переменные окружения')
        print(f'   SmartFilter: {should_process}')
except:
    print('❌ Ошибка при анализе ответа API')
"

echo ""
echo "🎯 Если видите 'УСПЕХ!' - система работает правильно!"
echo "🔧 Если есть проблемы - проверьте логи: tail -f service.log"
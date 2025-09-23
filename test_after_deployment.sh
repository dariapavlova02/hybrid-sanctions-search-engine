#!/bin/bash
echo "🧪 БЫСТРАЯ ПРОВЕРКА ПОСЛЕ ДЕПЛОЙМЕНТА"
echo "===================================="

echo ""
echo "1️⃣ Проверяем что сервис запустился:"
curl -s http://95.217.84.234:8002/health | jq '.'

echo ""
echo "2️⃣ Тестируем Порошенко (должен быть НЕ skip):"
curl -s -X POST http://95.217.84.234:8002/process \
  -H 'Content-Type: application/json' \
  -d '{"text": "Петро Порошенко"}' | jq '.decision.risk_level'

echo ""
echo "3️⃣ Проверяем search_contribution (должен появиться):"
curl -s -X POST http://95.217.84.234:8002/process \
  -H 'Content-Type: application/json' \
  -d '{"text": "Петро Порошенко"}' | jq '.decision.score_breakdown.search_contribution'

echo ""
echo "4️⃣ Проверяем search hits (должно быть > 0):"
curl -s -X POST http://95.217.84.234:8002/process \
  -H 'Content-Type: application/json' \
  -d '{"text": "Петро Порошенко"}' | jq '.search_results.total_hits'

echo ""
echo "5️⃣ Проверяем время обработки (должно быть < 5s):"
curl -s -X POST http://95.217.84.234:8002/process \
  -H 'Content-Type: application/json' \
  -d '{"text": "Петро Порошенко"}' | jq '.processing_time'

echo ""
echo "✅ УСПЕХ ЕСЛИ:"
echo "   - risk_level НЕ 'skip'"
echo "   - search_contribution ЕСТЬ (не null)"
echo "   - total_hits > 0"
echo "   - processing_time < 5"

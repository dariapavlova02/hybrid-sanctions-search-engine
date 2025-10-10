#!/bin/bash
# Проверка данных на production сервере

echo "=================================================="
echo "Проверка данных на production"
echo "=================================================="

# SSH параметры
PROD_SERVER="root@95.217.84.234"
APP_DIR="/opt/ai-service"

echo ""
echo "1. Проверка исходных файлов санкций:"
ssh $PROD_SERVER "ls -lh $APP_DIR/src/ai_service/data/sanctioned*.json $APP_DIR/src/ai_service/data/terrorism*.json 2>/dev/null || echo '[ERROR] Файлы не найдены'"

echo ""
echo "2. Проверка подготовленных данных (output):"
ssh $PROD_SERVER "ls -lh $APP_DIR/output/sanctions/*.json 2>/dev/null || echo '[WARN]  Директория output/sanctions пуста или не существует'"

echo ""
echo "3. Проверка индексов Elasticsearch:"
ssh $PROD_SERVER "curl -s http://localhost:9200/_cat/indices?v | grep sanctions || echo '[WARN]  Индексы sanctions не найдены'"

echo ""
echo "4. Проверка counts:"
ssh $PROD_SERVER "curl -s http://localhost:9200/sanctions_ac_patterns/_count | jq '.count' && curl -s http://localhost:9200/sanctions_vectors/_count | jq '.count'"

echo ""
echo "=================================================="
echo "Рекомендации:"
echo "=================================================="

# Проверяем что нужно сделать
HAS_SOURCE=$(ssh $PROD_SERVER "[ -f $APP_DIR/src/ai_service/data/sanctioned_persons.json ] && echo 'yes' || echo 'no'")
HAS_OUTPUT=$(ssh $PROD_SERVER "[ -f $APP_DIR/output/sanctions/ac_patterns_*.json ] && echo 'yes' || echo 'no'")

if [ "$HAS_SOURCE" = "yes" ] && [ "$HAS_OUTPUT" = "no" ]; then
    echo "[OK] Исходники есть, но output нет"
    echo "   Нужно запустить: python scripts/prepare_sanctions_data.py"
    echo ""
elif [ "$HAS_SOURCE" = "no" ]; then
    echo "[ERROR] Исходных файлов нет на production!"
    echo "   Нужно скопировать с локальной машины:"
    echo "   scp src/ai_service/data/sanctioned*.json $PROD_SERVER:$APP_DIR/src/ai_service/data/"
    echo "   scp src/ai_service/data/terrorism*.json $PROD_SERVER:$APP_DIR/src/ai_service/data/"
    echo ""
elif [ "$HAS_OUTPUT" = "yes" ]; then
    echo "[OK] Всё есть, можно делать rebuild Docker"
    echo "   docker-compose down && docker-compose build --no-cache && docker-compose up -d"
    echo ""
fi

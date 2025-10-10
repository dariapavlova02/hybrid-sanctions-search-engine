#!/bin/bash
set -e

# Docker Entrypoint Script for AI Service
# Автоматическая инициализация Elasticsearch и запуск сервиса

echo "=================================================="
echo "AI Service - Docker Entrypoint"
echo "=================================================="

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Конфигурация
ES_HOST="${ES_HOSTS:-elasticsearch:9200}"
ES_TIMEOUT="${ES_STARTUP_TIMEOUT:-60}"
INDEX_PREFIX="${ES_INDEX_PREFIX:-sanctions}"
SKIP_ES_INIT="${SKIP_ES_INIT:-false}"

# Извлекаем первый хост из списка
ES_FIRST_HOST=$(echo "$ES_HOST" | cut -d',' -f1)

echo ""
echo "Конфигурация:"
echo "  Elasticsearch: $ES_FIRST_HOST"
echo "  Index Prefix: $INDEX_PREFIX"
echo "  Skip Init: $SKIP_ES_INIT"
echo ""

# Функция ожидания Elasticsearch
wait_for_elasticsearch() {
    echo "🔄 Ожидание готовности Elasticsearch..."

    local counter=0
    local max_attempts=$((ES_TIMEOUT / 3))

    while [ $counter -lt $max_attempts ]; do
        if curl -sf "http://$ES_FIRST_HOST/_cluster/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Elasticsearch готов${NC}"
            return 0
        fi

        counter=$((counter + 1))
        echo "  Попытка $counter/$max_attempts..."
        sleep 3
    done

    echo -e "${RED}❌ Elasticsearch не готов после ${ES_TIMEOUT}s${NC}"
    return 1
}

# Функция проверки индексов
check_indices() {
    local ac_index="${INDEX_PREFIX}_ac_patterns"
    local vector_index="${INDEX_PREFIX}_vectors"

    echo "🔍 Проверка индексов..."

    local ac_exists=$(curl -sf "http://$ES_FIRST_HOST/$ac_index/_count" > /dev/null 2>&1 && echo "true" || echo "false")
    local vector_exists=$(curl -sf "http://$ES_FIRST_HOST/$vector_index/_count" > /dev/null 2>&1 && echo "true" || echo "false")
    local ac_doc_count=0
    local vector_count=0

    if [ "$ac_exists" = "true" ]; then
        ac_doc_count=$(curl -sf "http://$ES_FIRST_HOST/$ac_index/_count" | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))" 2>/dev/null || echo "0")
        echo -e "${GREEN}  ✅ $ac_index: $ac_doc_count документов${NC}"
    else
        echo -e "${YELLOW}  ⚠️  $ac_index: не существует${NC}"
    fi

    if [ "$vector_exists" = "true" ]; then
        vector_count=$(curl -sf "http://$ES_FIRST_HOST/$vector_index/_count" | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))" 2>/dev/null || echo "0")
        echo -e "${GREEN}  ✅ $vector_index: $vector_count документов${NC}"
    else
        echo -e "${YELLOW}  ⚠️  $vector_index: не существует${NC}"
    fi

    # Возвращаем true если хотя бы AC индекс существует с данными
    if [ "$ac_exists" = "true" ] && [ "${ac_doc_count:-0}" -gt 0 ]; then
        return 0
    else
        return 1
    fi
}

# Функция инициализации Elasticsearch
initialize_elasticsearch() {
    echo "🚀 Инициализация Elasticsearch..."

    # Проверяем наличие файла с паттернами
    local patterns_dir="/app/output/sanctions"

    if [ ! -d "$patterns_dir" ]; then
        echo -e "${YELLOW}⚠️  Директория $patterns_dir не существует${NC}"
        echo "ℹ️  Создание индексов без загрузки данных..."

        # Создаём пустые индексы через Python скрипт
        python3 /app/scripts/create_empty_indices.py \
            --es-host "$ES_FIRST_HOST" \
            --index-prefix "$INDEX_PREFIX"

        return $?
    fi

    # Ищем файл с паттернами
    local patterns_file=$(find "$patterns_dir" -name "ac_patterns_*.json" -type f | sort -r | head -n1)

    if [ -z "$patterns_file" ]; then
        echo -e "${YELLOW}⚠️  Файл с AC паттернами не найден${NC}"
        echo "ℹ️  Создание индексов без загрузки данных..."

        python3 /app/scripts/create_empty_indices.py \
            --es-host "$ES_FIRST_HOST" \
            --index-prefix "$INDEX_PREFIX"

        return $?
    fi

    echo "📦 Найден файл паттернов: $(basename $patterns_file)"

    # Ищем файл с векторами
    local vectors_file=$(find "$patterns_dir" -name "vectors_*.json" -type f | sort -r | head -n1)

    # Запускаем deployment скрипт
    if [ -n "$vectors_file" ]; then
        echo "📦 Найден файл векторов: $(basename $vectors_file)"
        python3 /app/scripts/deploy_to_elasticsearch.py \
            --es-host "$ES_FIRST_HOST" \
            --index-prefix "$INDEX_PREFIX" \
            --patterns-file "$patterns_file" \
            --vectors-file "$vectors_file" \
            --create-vector-indices
    else
        echo "⚠️  Файл векторов не найден, создаём только AC индекс"
        python3 /app/scripts/deploy_to_elasticsearch.py \
            --es-host "$ES_FIRST_HOST" \
            --index-prefix "$INDEX_PREFIX" \
            --patterns-file "$patterns_file"
    fi

    return $?
}

# Основная логика
main() {
    # 1. Ожидание Elasticsearch
    if ! wait_for_elasticsearch; then
        echo -e "${RED}❌ Не удалось дождаться Elasticsearch${NC}"
        echo "ℹ️  Запуск сервиса без Elasticsearch..."
        echo "⚠️  Функции поиска могут не работать!"
    else
        # 2. Проверка индексов
        if check_indices; then
            echo -e "${GREEN}✅ Индексы уже существуют с данными${NC}"
        else
            if [ "$SKIP_ES_INIT" = "true" ]; then
                echo -e "${YELLOW}⚠️  Пропуск инициализации (SKIP_ES_INIT=true)${NC}"
            else
                # 3. Инициализация Elasticsearch
                if initialize_elasticsearch; then
                    echo -e "${GREEN}✅ Elasticsearch инициализирован успешно${NC}"
                    check_indices
                else
                    echo -e "${YELLOW}⚠️  Инициализация завершилась с ошибками${NC}"
                    echo "ℹ️  Сервис продолжит работу, но функции поиска могут быть недоступны"
                fi
            fi
        fi
    fi

    echo ""
    echo "=================================================="
    echo "🚀 Запуск AI Service"
    echo "=================================================="
    echo ""

    # Устанавливаем переменные окружения для соответствия созданным индексам
    export ES_AC_INDEX="${INDEX_PREFIX}_ac_patterns"
    export ES_VECTOR_INDEX="${INDEX_PREFIX}_vectors"

    # Запуск основного приложения
    exec "$@"
}

# Запуск
main "$@"

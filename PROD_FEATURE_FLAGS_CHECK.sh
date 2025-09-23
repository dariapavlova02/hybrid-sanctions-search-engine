#!/bin/bash

echo "=== ПРОВЕРКА КРИТИЧНЫХ FEATURE FLAGS НА ПРОДАКШНЕ ==="
echo

echo "🔍 Проверяем переменные окружения..."
echo "PRESERVE_FEMININE_SUFFIX_UK=${PRESERVE_FEMININE_SUFFIX_UK:-MISSING}"
echo "ENABLE_ENHANCED_GENDER_RULES=${ENABLE_ENHANCED_GENDER_RULES:-MISSING}"
echo "ENABLE_FSM_TUNED_ROLES=${ENABLE_FSM_TUNED_ROLES:-MISSING}"
echo "PRESERVE_FEMININE_SURNAMES=${PRESERVE_FEMININE_SURNAMES:-MISSING}"
echo

echo "🔍 Smart Filter настройки..."
echo "ENABLE_SMART_FILTER=${ENABLE_SMART_FILTER:-MISSING}"
echo "ALLOW_SMART_FILTER_SKIP=${ALLOW_SMART_FILTER_SKIP:-MISSING}"
echo "ENABLE_AHO_CORASICK=${ENABLE_AHO_CORASICK:-MISSING}"
echo

echo "🔍 Morphology настройки..."
echo "MORPHOLOGY_CUSTOM_RULES_FIRST=${MORPHOLOGY_CUSTOM_RULES_FIRST:-MISSING}"
echo "ENABLE_ADVANCED_FEATURES=${ENABLE_ADVANCED_FEATURES:-MISSING}"
echo

echo "=== РЕКОМЕНДУЕМЫЕ НАСТРОЙКИ ==="
echo "Добавить в docker-compose.prod.yml или .env:"
echo
echo "environment:"
echo "  # Gender & Morphology"
echo "  - PRESERVE_FEMININE_SUFFIX_UK=true"
echo "  - ENABLE_ENHANCED_GENDER_RULES=true"
echo "  - ENABLE_FSM_TUNED_ROLES=true"
echo "  - PRESERVE_FEMININE_SURNAMES=true"
echo "  - MORPHOLOGY_CUSTOM_RULES_FIRST=true"
echo "  - ENABLE_ADVANCED_FEATURES=true"
echo "  "
echo "  # Smart Filter & Search"
echo "  - ENABLE_SMART_FILTER=true"
echo "  - ALLOW_SMART_FILTER_SKIP=false"
echo "  - ENABLE_AHO_CORASICK=true"
echo "  - ENABLE_VECTOR_FALLBACK=true"
echo

echo "После изменений перезапустить:"
echo "docker-compose -f docker-compose.prod.yml restart ai-service"
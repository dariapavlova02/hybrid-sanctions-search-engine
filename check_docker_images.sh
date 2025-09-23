#!/bin/bash
# Скрипт для проверки Docker образов на сервере

echo "🔍 Проверка доступных Docker образов..."

echo "1. Список всех локальных образов:"
docker images

echo ""
echo "2. Запущенные контейнеры:"
docker ps

echo ""
echo "3. Все контейнеры (включая остановленные):"
docker ps -a

echo ""
echo "4. Проверка docker-compose файлов:"
ls -la docker-compose*.yml

echo ""
echo "5. Содержимое docker-compose.prod.yml (если есть):"
if [ -f docker-compose.prod.yml ]; then
    cat docker-compose.prod.yml
else
    echo "Файл docker-compose.prod.yml не найден"
fi

echo ""
echo "6. Содержимое Dockerfile (если есть):"
if [ -f Dockerfile ]; then
    head -20 Dockerfile
else
    echo "Dockerfile не найден"
fi
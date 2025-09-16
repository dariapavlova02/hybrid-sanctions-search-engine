# Templates

Эта папка содержит шаблоны и конфигурации для различных компонентов системы.

## Структура

```
templates/
├── elasticsearch/                    # Шаблоны Elasticsearch
│   ├── README.md                     # Документация по ES шаблонам
│   ├── elasticsearch_setup.sh        # Скрипт установки шаблонов
│   ├── elasticsearch_curl_commands.md # cURL команды для ручной установки
│   ├── elasticsearch_templates.json  # Все шаблоны в одном файле
│   ├── elasticsearch_component_template.json # Component template
│   ├── elasticsearch_persons_template.json  # Index template для людей
│   └── elasticsearch_orgs_template.json     # Index template для организаций
└── README.md                         # Этот файл
```

## Elasticsearch Templates

Шаблоны индексов для гибридного поиска с поддержкой:
- AC (точного) поиска по нормализованным именам и алиасам
- Vector (kNN) поиска по dense векторам
- Фразового поиска с shingles
- Нечеткого поиска с n-grams

### Быстрый старт

```bash
# Установка всех шаблонов
cd templates/elasticsearch
chmod +x elasticsearch_setup.sh
./elasticsearch_setup.sh

# Или с аутентификацией
ES_HOST=localhost:9200 ES_USER=elastic ES_PASS=password ./elasticsearch_setup.sh
```

### Индексы

- **watchlist_persons_v1**: Для физических лиц
- **watchlist_orgs_v1**: Для организаций

### Поля

- **entity_id**: Уникальный идентификатор
- **entity_type**: Тип сущности (person/org)
- **normalized_name**: Нормализованное имя для точного поиска
- **aliases**: Алиасы (множественные значения)
- **name_text**: Полнотекстовый поиск с ICU анализатором
- **name_ngrams**: N-grams для нечеткого поиска
- **name_vector**: Dense вектор для kNN поиска (384 измерения)
- **meta**: Метаданные (гибкий объект)

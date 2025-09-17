# Search Integration Tests

Комплексный набор тестов для поисковой интеграции с использованием pytest, Docker Compose и изоляцией тестов.

## Структура тестов

```
tests/
├── conftest.py                    # Pytest конфигурация и фикстуры
├── requirements_test.txt          # Зависимости для тестов
├── unit/                          # Unit тесты
│   ├── test_search_contracts.py   # Тесты контрактов поиска
│   ├── test_search_integration.py # Тесты интеграции поиска
│   └── test_decision_engine_with_search.py # Тесты Decision Engine с поиском
├── integration/                   # Integration тесты
│   └── test_elasticsearch_search.py # Тесты Elasticsearch поиска
├── performance/                   # Performance тесты
│   └── test_search_performance.py # Тесты производительности поиска
└── README.md                      # Этот файл
```

## Типы тестов

### Unit тесты (`@pytest.mark.unit`)
- **Маппинг трансформаций**: ES hit → Candidate, нормализация порогов, слияние скорингов
- **Контракты данных**: SearchOpts, SearchMode, ACScore, VectorHit, Candidate, SearchInfo
- **Интеграционные функции**: extract_search_candidates, create_search_info
- **Decision Engine**: расчет весов с поиском, пороги, бонусы

### Integration тесты (`@pytest.mark.integration`)
- **Docker-ES**: создание временного индекса, индексация 5-10 сущностей (ru/uk/en)
- **AC поиск**: exact → находит только при точном normalized_name
- **Phrase поиск**: ловит «Иван Иванов»
- **N-gram поиск**: дает слабый сигнал
- **kNN поиск**: возвращает релевант при отсутствии AC
- **Fusion**: консенсус поднимает в топ

### Performance тесты (`@pytest.mark.performance`)
- **1k запросов**: p95 < 80мс end-to-end
- **Разные режимы**: AC, Vector, Hybrid
- **Concurrent запросы**: 1, 5, 10, 20 параллельных
- **Memory usage**: контроль потребления памяти
- **Error handling**: обработка ошибок

## Запуск тестов

### Установка зависимостей

```bash
# Установить зависимости для тестов
pip install -r tests/requirements_test.txt

# Или использовать make
make install-test-deps
```

### Unit тесты (без внешних зависимостей)

```bash
# Все unit тесты
pytest tests/unit/ -m "unit" -v

# Или через make
make test-unit
```

### Integration тесты (требует Docker)

```bash
# Запустить Elasticsearch
docker-compose -f docker-compose.test.yml up -d

# Дождаться готовности
curl -f http://localhost:9200/_cluster/health

# Запустить integration тесты
pytest tests/integration/ -m "integration" -v

# Или через make
make test-integration
```

### Performance тесты

```bash
# Запустить performance тесты
pytest tests/performance/ -m "performance" -v

# Или через make
make test-performance
```

### Все тесты

```bash
# Все тесты
pytest tests/ -v

# Или через make
make test-all
```

### Автоматический запуск с Docker

```bash
# Установить, запустить тесты и очистить
make test-with-docker
```

## Конфигурация

### Переменные окружения

Тесты автоматически устанавливают следующие переменные:

```bash
# Поиск
ENABLE_HYBRID_SEARCH=true
ES_URL=http://localhost:9200
ES_AUTH=
ES_VERIFY_SSL=false

# Веса поиска для Decision Engine
AI_DECISION__W_SEARCH_EXACT=0.3
AI_DECISION__W_SEARCH_PHRASE=0.25
AI_DECISION__W_SEARCH_NGRAM=0.2
AI_DECISION__W_SEARCH_VECTOR=0.15

# Пороги поиска
AI_DECISION__THR_SEARCH_EXACT=0.8
AI_DECISION__THR_SEARCH_PHRASE=0.7
AI_DECISION__THR_SEARCH_NGRAM=0.6
AI_DECISION__THR_SEARCH_VECTOR=0.5

# Бонусы поиска
AI_DECISION__BONUS_MULTIPLE_MATCHES=0.1
AI_DECISION__BONUS_HIGH_CONFIDENCE=0.05
```

### Pytest маркеры

- `@pytest.mark.unit` - Unit тесты
- `@pytest.mark.integration` - Integration тесты (требуют Elasticsearch)
- `@pytest.mark.performance` - Performance тесты
- `@pytest.mark.slow` - Медленные тесты
- `@pytest.mark.docker` - Тесты, требующие Docker

## Фикстуры

### Основные фикстуры

- `elasticsearch_container` - Docker контейнер Elasticsearch
- `elasticsearch_client` - HTTP клиент для Elasticsearch
- `test_indices` - Тестовые индексы с данными
- `mock_hybrid_search_service` - Мок HybridSearchService
- `mock_signals_result` - Мок SignalsResult
- `mock_normalization_result` - Мок NormalizationResult
- `sample_query_vector` - Образец вектора запроса

### Тестовые данные

Тесты используют следующие тестовые данные:

**Персоны:**
- `иван петров` (RU) - точное совпадение
- `мария сидорова` (UA) - фраза
- `john smith` (US) - n-gram

**Организации:**
- `ооо приватбанк` (UA) - точное совпадение
- `apple inc` (US) - фраза

## Критерии успеха

### Unit тесты
- ✅ Все контракты данных работают корректно
- ✅ Трансформации ES hit → Candidate
- ✅ Нормализация порогов
- ✅ Слияние скорингов
- ✅ Decision Engine с поиском

### Integration тесты
- ✅ Exact поиск находит только точные совпадения
- ✅ Phrase поиск ловит фразы
- ✅ N-gram поиск дает слабые сигналы
- ✅ kNN поиск возвращает релевантные результаты
- ✅ Fusion поднимает консенсус в топ

### Performance тесты
- ✅ 1k запросов, p95 < 80мс end-to-end
- ✅ Успешность > 95%
- ✅ Память < 200MB увеличение
- ✅ Concurrent запросы работают стабильно

## Отладка

### Проблемы с Docker

```bash
# Проверить статус контейнеров
docker ps

# Посмотреть логи Elasticsearch
docker logs ai-service-test-es

# Очистить все контейнеры
make clean-test-env
```

### Проблемы с тестами

```bash
# Запустить с подробным выводом
pytest tests/unit/test_search_contracts.py -v -s

# Запустить конкретный тест
pytest tests/unit/test_search_contracts.py::TestSearchOpts::test_default_values -v

# Запустить с отладкой
pytest tests/unit/test_search_contracts.py --pdb
```

### Проблемы с импортами

```bash
# Проверить PYTHONPATH
echo $PYTHONPATH

# Запустить из корня проекта
cd /path/to/ai-service
pytest tests/unit/ -v
```

## Smoke тесты

### Что покрывают smoke тесты

Smoke тесты (`tests/smoke/`) — это компактный набор быстрых тестов для критичных кейсов токенизации и ролей. Они предназначены для:

- **Быстрой проверки регрессий** в основных функциях нормализации
- **Валидации feature flags** и их влияния на поведение
- **Контроля производительности** (p95 < 20мс для каждого теста)
- **Проверки критичных сценариев**:
  - Инициалы: `И.. И. Петров` → `И. И. Петров` (с `fix_initials_double_dot=True`)
  - Дефисы: `Петрова-сидорова Олена` → `Олена Петрова-Сидорова` (с `preserve_hyphenated_case=True`)
  - Орг-контекст: `Оплата ТОВ «ПРИВАТБАНК» Ивану Петрову` → `Иван Петров` (с `strict_stopwords=True`)
  - Апострофы: `O'Neil-Smith John` → `John O'Neil-Smith` (с `preserve_hyphenated_case=True`)
  - Мульти-персоны: `Иван Петров; Олена Ковальська` → обе персоны выделены
  - Фильтрация стоп-слов: служебные/платёжные слова не попадают в `normalized`

### Как запускать smoke тесты

```bash
# Все smoke тесты
pytest tests/smoke/ -v

# Конкретный тест
pytest tests/smoke/test_normalization_smoke.py::TestNormalizationSmoke::test_initials_double_dot_collapse -v

# С измерением производительности
pytest tests/smoke/ -v -s

# Только быстрые тесты (без performance тестов)
pytest tests/smoke/ -m "not slow" -v
```

### Критерии приёмки smoke тестов

- ✅ Все smoke тесты зелёные
- ✅ При включении флагов поведение соответствует ожиданиям
- ✅ Регрессий по публичному контракту нет
- ✅ Производительность p95 < 20мс для каждого теста
- ✅ Trace содержит необходимую информацию для отладки

## Расширение тестов

### Добавление новых unit тестов

1. Создайте файл в `tests/unit/`
2. Используйте маркер `@pytest.mark.unit`
3. Добавьте фикстуры из `conftest.py`

### Добавление новых integration тестов

1. Создайте файл в `tests/integration/`
2. Используйте маркер `@pytest.mark.integration`
3. Используйте фикстуры `elasticsearch_client` и `test_indices`

### Добавление новых performance тестов

1. Создайте файл в `tests/performance/`
2. Используйте маркер `@pytest.mark.performance`
3. Измеряйте производительность и проверяйте пороги

### Добавление новых smoke тестов

1. Создайте файл в `tests/smoke/`
2. Используйте параметризацию по языкам (`@pytest.mark.parametrize("language", ["ru", "uk", "en"])`)
3. Проверяйте производительность (p95 < 20мс)
4. Тестируйте критичные сценарии с feature flags
5. Включайте проверки trace completeness

## CI/CD

Тесты можно интегрировать в CI/CD пайплайн:

```yaml
# GitHub Actions example
- name: Run unit tests
  run: make test-unit

- name: Run integration tests
  run: make test-with-docker
```
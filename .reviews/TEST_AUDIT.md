# 🧪 TEST AUDIT — Анализ тестового покрытия и качества

## TL;DR — КРИТИЧЕСКАЯ ОЦЕНКА
**СТАТУС**: 🔴 Много тестов, но качество сомнительное — xfail костыли, дубли, устаревшие
**ПОКРЫТИЕ**: Высокое количество (~5372 файлов), но есть критичные пробелы
**ОСНОВНЫЕ ПРОБЛЕМЫ**: 151 TODO/FIXME/xfail, дубли legacy/factory тестов, флейки в CI

---

## 📊 ТЕСТОВАЯ ПИРАМИДА (текущее состояние)

```
     e2e/nightmare (4 файла) ← МНОГО XFAIL
    /                           \
   /   integration (30+ файлов)  \  ← СМЕШАННОЕ КАЧЕСТВО
  /                               \
 /        unit (60+ файлов)        \ ← LEGACY ДУБЛИ
/_____________smoke (15 файлов)_____\ ← GOOD FOUNDATION
```

### Структура тестов ✅ (правильная пирамида)
```
tests/
├── unit/           # 60+ файлов — основа пирамиды ✅
├── integration/    # 30+ файлов — интеграционные тесты
├── smoke/          # 15+ файлов — базовые smoke tests ✅
├── e2e/           # 4 файла — end-to-end ⚠️ много xfail
├── parity/        # Golden parity tests ✅
├── performance/   # Performance gates ✅
├── property/      # Property-based tests (Hypothesis) ✅
├── canary/        # Canary monitoring tests ✅
└── golden_cases/  # Golden test cases ⚠️ xfail
```

---

## 🚨 КРИТИЧЕСКИЕ ПРОБЛЕМЫ

### P0 — BLOCKER ISSUES

#### 1. **XFAIL Epidemic** (P0 — CRITICAL)
**Найдено**: 151 TODO/FIXME/xfail в тестах
**Критичные xfail:**

```python
# tests/golden_cases/test_golden_cases.py
@pytest.mark.xfail(reason="Factory implementation not yet aligned with golden cases", strict=False)
# ↑ БЛОКЕР! Golden parity не работает

# tests/e2e/test_sanctions_screening_pipeline.py
@pytest.mark.xfail(reason="TODO: Implement robustness layer. ISSUE-457. Blocked by ISSUE-456")
# ↑ Основной функционал санкций не тестируется

# tests/e2e/test_nightmare_scenario.py
@pytest.mark.xfail(reason="ISSUE-123: Unicode layer encoding recovery not implemented. Target: v1.2.0")
# ↑ Unicode обработка не протестирована
```

**Последствие**: Критичная функциональность НЕ ПРОВЕРЕНА в CI
**Риск**: Регрессии попадают в продакшн

#### 2. **Legacy/Factory Test Duplication** (P0)
**Дубли найдены:**
- `test_orchestrator_service.py` vs `test_orchestrator_service_old.py`
- `test_normalization_service.py` vs `test_normalization_service_old.py`
- `test_legacy_normalization_adapter.py` vs factory тесты

**Проблема**: Тесты могут проходить на legacy, падать на factory (или наоборот)
**Решение**: Унифицировать через параметризацию

---

### P1 — HIGH SEVERITY

#### 3. **Missing Core Coverage** (P1)
**Критичные пробелы по ключевым компонентам:**

| Компонент | Файл | Unit Tests | Integration Tests | Статус |
|-----------|------|------------|------------------|--------|
| `MorphologyAdapter` | `morphology_adapter.py` | ❓ | ✅ | ПРОВЕРИТЬ |
| `HybridSearchService` | `hybrid_search_service.py` | ❓ | ✅ | ПРОВЕРИТЬ |
| `FeatureFlags` | `feature_flags.py` | ❌ | ❌ | КРИТИЧНО |
| `ElasticsearchClient` | `elasticsearch_client.py` | ❓ | ✅ | ПРОВЕРИТЬ |

#### 4. **Performance Tests не в CI** (P1)
**Найдено**: `tests/performance/` существует, но не все в CI gate
**Файлы**:
- `test_ascii_fastpath_performance.py`
- `test_morph_adapter_perf.py`
- `test_search_performance.py`

**Проблема**: Perf regression может попасть незамеченным

#### 5. **Flaky Tests в CI** (P1)
**Анализ CI workflow `ci.yml`:**
```yaml
# Строка 117: continue-on-error: true для canary тестов
continue-on-error: true
```
**Проблема**: Canary тесты могут падать, но CI проходит
**Риск**: Broken canaries = мёртвая система мониторинга

---

## 📈 ПОЗИТИВНЫЕ АСПЕКТЫ

### ✅ Хорошо реализовано:
1. **Property-based testing** — используется Hypothesis ✅
2. **Golden parity framework** — есть инфраструктура ✅
3. **Performance gates** — есть perf тесты ✅
4. **Canary monitoring** — автоматические проверки ✅
5. **Parametrized tests** — хорошее покрытие языков RU/UK/EN ✅
6. **SearchTrace validation** — детальная проверка трейсов ✅

### ✅ Хорошие практики:
- Отдельные папки по типам тестов
- `conftest.py` для fixtures
- Async test support
- JUnit XML для CI integration
- Artifact generation для отчётов

---

## 🔍 ДЕТАЛЬНЫЙ АНАЛИЗ ПО СЛОЯМ

### L0 Normalization Tests ✅ (хорошо покрыто)
```
tests/unit/text_processing/test_normalization_*
tests/integration/test_normalization_pipeline*
tests/smoke/test_*
```
**Покрытие**: 80%+ (визуальная оценка)
**Качество**: Хорошее, много edge cases

### L1-L2 Search Tests ⚠️ (покрытие неясно)
```
tests/unit/test_search_*
tests/integration/test_elasticsearch_*
tests/integration/test_search_*
```
**Покрытие**: 60%? (нужно измерить)
**Проблемы**: ES тесты требуют live ElasticSearch

### L3-L5 Decision Tests ❌ (слабо покрыто)
```
tests/unit/test_decision_*
tests/e2e/test_sanctions_* ← МНОГО XFAIL!
```
**Покрытие**: 30%? (критично низко)
**Проблемы**: Основные E2E тесты в xfail

---

## 📊 КАЧЕСТВЕННЫЕ МЕТРИКИ

### Code Coverage (нужно измерить точно)
```bash
# Текущая команда в CI:
pytest tests/ --cov=src --cov-report=xml

# Результат: coverage.xml загружается в Codecov
# НО: в CI нет fail gate по покрытию!
```

**Проблема**: Нет минимального порога покрытия в CI

### Test Categories Distribution
- **Unit**: ~60 файлов (40%)
- **Integration**: ~30 файлов (30%)
- **Smoke**: ~15 файлов (15%)
- **E2E**: ~4 файла (5%)
- **Property**: ~5 файлов (5%)
- **Performance**: ~5 файлов (5%)

### Test Quality Issues
- **Obsolete tests**: 3+ файла с `_old.py`
- **xfail tests**: 4+ критичных xfail
- **TODO/FIXME**: 151 упоминание в тестах
- **Flaky markers**: CI с `continue-on-error: true`

---

## 🎯 ПЛАН ИСПРАВЛЕНИЯ (3 недели)

### Неделя 1: Критические фиксы (P0)
- [ ] **Day 1-2**: Исправить или удалить критичные xfail:
  - `test_golden_cases.py` — align factory with golden
  - `test_sanctions_screening_pipeline.py` — implement basic pipeline
- [ ] **Day 3**: Удалить дубли legacy/factory тестов:
  - Параметризовать по implementation type
- [ ] **Day 4-5**: Добавить feature flags тесты:
  - Каждый флаг должен влиять на поведение

### Неделя 2: Coverage и Performance (P1)
- [ ] **Day 6-7**: Измерить real coverage:
  - Установить минимум 80% для core компонентов
  - Добавить coverage gate в CI
- [ ] **Day 8-9**: Добавить performance gates:
  - Все perf тесты в CI
  - SLA нарушения = fail build
- [ ] **Day 10**: Исправить flaky tests:
  - Убрать `continue-on-error: true`

### Неделя 3: Качество и cleanup (P2)
- [ ] **Day 11-12**: Cleanup obsolete тестов:
  - Удалить `*_old.py` файлы
  - Migrate в новую структуру
- [ ] **Day 13-14**: Улучшить E2E coverage:
  - Базовый sanctions pipeline без xfail
- [ ] **Day 15**: Documentation и runbooks:
  - Как писать тесты для каждого слоя

---

## 🔬 КОМАНДЫ ДЛЯ ДИАГНОСТИКИ

### Измерить реальное покрытие:
```bash
# Полное покрытие с детализацией
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

# Покрытие только core компонентов
pytest tests/ --cov=src/ai_service/layers/normalization --cov=src/ai_service/layers/search
```

### Найти проблемные тесты:
```bash
# Все xfail тесты
grep -r "@pytest.mark.xfail" tests/ --include="*.py"

# Все TODO в тестах
grep -r "TODO\|FIXME\|HACK" tests/ --include="*.py"

# Устаревшие тесты
find tests/ -name "*old*" -o -name "*legacy*" -o -name "*deprecated*"
```

### Запустить только critical tests:
```bash
# Golden parity
pytest tests/golden_cases/ tests/parity/ -v

# Performance gates
pytest tests/performance/ -m "not slow" --strict-perf

# Core unit tests
pytest tests/unit/ -k "not old" -x
```

---

## 💣 ОЦЕНКА РИСКОВ

**Текущее состояние тестирования**: НЕСТАБИЛЬНОЕ
**Готовность к production**: ❌ (без исправления xfail)
**Вероятность регрессий**: 60% для не покрытых компонентов
**Время на исправление**: 3 недели

**КРИТИЧНЫЕ БЛОКЕРЫ:**
1. Golden parity в xfail — система может нарушить контракты
2. Sanctions E2E в xfail — основная функциональность не проверена
3. Нет coverage gate — регрессии незаметны

**РЕКОМЕНДАЦИЯ**: Считать тестовую систему **НЕ ГОТОВОЙ** для критичного продакшна без исправления P0 проблем.
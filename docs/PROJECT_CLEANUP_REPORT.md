# AI Service - Project Cleanup Report

**Дата анализа:** 03.10.2025
**Цель:** Подготовка проекта к ревью тимлида
**Анализатор:** Claude Code

---

## 📊 Executive Summary

**Статистика проекта:**
- **Файлов в src/:** 212 Python файлов
- **Скриптов:** 39 в `scripts/`
- **Документация:** 26 MD файлов в `docs/`
- **Dead code:** 785 неиспользуемых определений (28.4%)
- **Временные файлы:** 12 файлов в корне

**Главные проблемы:**
1. ❌ Много временных файлов и скриптов в корне проекта
2. ❌ 28.4% мертвого кода (785 неиспользуемых definitions)
3. ❌ Дублированные конфигурационные файлы
4. ❌ Legacy код не удален
5. ❌ Backup файлы в корне
6. ❌ Пустые директории

---

## 🗂️ Проблема #1: Мусор в Корне Проекта

### Временные файлы для удаления

```bash
# Summary файлы паттернов (устарели)
./all_production_ac_patterns_fixed_full_summary.txt      # 1.1 KB
./all_production_ac_patterns_fixed_sample_summary.txt    # 1.0 KB
./production_ac_patterns_fixed_summary.txt               # 933 B
./high_recall_ac_patterns_summary.txt                    # 973 B
./ulianova_patterns_summary.txt                          # ?
./ulianova_patterns_fixed_summary.txt                    # ?
./ulianova_patterns_test_again_summary.txt               # ?
```

**Действие:** Удалить все `*_summary.txt` файлы — это временные отчеты по тестированию паттернов.

---

### Shell скрипты для переноса

```bash
# В корне (должны быть в scripts/)
./check_poroshenko_patterns.sh       # тестовый скрипт
./enable_search.sh                   # setup script
./test_poroshenko.sh                 # тестовый скрипт
```

**Действие:** Перенести в `scripts/debug/` или `scripts/testing/`.

---

### Backup файлы для удаления

```bash
./cleanup_backup_20251001_194024.tar.gz    # 28 MB (старый backup)
./patch_sprint1_minimal.diff               # 14 KB (устаревший patch)
```

**Действие:** Удалить — уже есть в git истории.

---

### Прочие проблемы

```bash
./__init__.py                    # Пустой файл в корне (не нужен)
./CLAUDE.md                      # Должен быть в .claude/ (дубликат)
./ai_service/                    # Дубликат директории с одним скриптом
```

**Действие:**
- Удалить `__init__.py`
- Удалить `CLAUDE.md` (есть `.claude/CLAUDE.md`)
- Удалить `ai_service/` (скрипт уже есть в `scripts/`)

---

### Docker файлы

```bash
Dockerfile                    # основной
Dockerfile.prod              # production
Dockerfile.search            # search service
Dockerfile.search.backup     # ❌ BACKUP (удалить)
```

**Действие:** Удалить `Dockerfile.search.backup`.

---

## 🧹 Рекомендации по очистке корня

```bash
# 1. Удалить временные summary файлы
rm -f *_summary.txt

# 2. Удалить backup файлы
rm -f cleanup_backup_*.tar.gz patch_*.diff

# 3. Удалить дубликаты
rm -f __init__.py CLAUDE.md

# 4. Удалить устаревшие Docker backup'ы
rm -f Dockerfile.search.backup

# 5. Удалить дубликат директории
rm -rf ai_service/

# 6. Переместить shell скрипты
mkdir -p scripts/testing
mv check_poroshenko_patterns.sh test_poroshenko.sh scripts/testing/
mv enable_search.sh scripts/
```

**Итог:** Очистка освободит ~30 MB и уберет 17+ лишних файлов из корня.

---

## 💀 Проблема #2: Мертвый Код (28.4%)

### Статистика (из usage_analysis.py)

```
Total Definitions:    2765
Unused Definitions:   785 (28.4%)

Classes:              379 (81 unused - 21.4%)
Functions:            332 (108 unused - 32.5%)
Methods:              2054 (596 unused - 29.0%)
```

### Критические неиспользуемые компоненты

#### Legacy сервисы (полностью не используются)

```python
# src/ai_service/layers/normalization/
- NormalizationServiceLegacy          # Старая версия (заменена на новую)
- NormalizationServiceDecomposed      # Экспериментальная версия
- NormalizationFactoryRefactored      # Рефакторинг в процессе

# src/ai_service/layers/search/
- HybridSearchServiceRefactored       # Недоделанный рефакторинг
- EnhancedElasticsearchClient         # Заменен на ElasticsearchClientFactory

# src/ai_service/core/
- CacheService                        # Не используется (есть встроенный кэш)
- OrchestratorFactoryWithSearch       # Deprecated версия
```

**Действие:** Переместить в `legacy/` или удалить, если не планируется использовать.

---

#### Неиспользуемые Contracts/Models

```python
# src/ai_service/contracts/search_contracts.py
- ACScore                             # Не используется
- VectorHit                           # Заменено на Candidate
- ElasticsearchACAdapterInterface     # Абстракция не используется
- ElasticsearchVectorAdapterInterface
- SearchServiceInterface

# src/ai_service/api/models.py
- HealthResponse                      # Endpoint не используется
- MetricsResponse                     # Endpoint не используется
- PersonResult                        # Deprecated
- OrganizationResult                  # Deprecated
```

**Действие:** Удалить неиспользуемые contracts или пометить как `@deprecated`.

---

#### Неиспользуемые Exception классы

```python
# src/ai_service/exceptions.py
- APIError                            # Не используется
- AuthorizationError                  # Нет авторизации
- CacheError
- MorphologyError
- PatternError
- ProcessingError
- RateLimitError                      # Нет rate limiting
- SearchConfigurationError
- SearchDataError
- SignalDetectionError
```

**Действие:** Оставить только используемые exceptions.

---

### Топ-10 файлов с мертвым кодом

| Файл | Unused % | Definitions | Unused |
|------|----------|-------------|--------|
| `normalization_service_legacy.py` | 95% | 40 | 38 |
| `normalization_service_decomposed.py` | 92% | 35 | 32 |
| `hybrid_search_service_refactored.py` | 88% | 25 | 22 |
| `enhanced_elasticsearch_client.py` | 85% | 20 | 17 |
| `cache_service.py` | 80% | 15 | 12 |
| `exceptions.py` | 70% | 20 | 14 |
| `name_assembler.py` | 65% | 18 | 12 |
| `search_contracts.py` | 60% | 30 | 18 |
| `api/models.py` | 55% | 22 | 12 |
| `orchestrator_factory_with_search.py` | 50% | 10 | 5 |

**Действие:** Приоритет на удаление/рефакторинг файлов с >70% мертвого кода.

---

## 📁 Проблема #3: Дубликаты и Legacy

### Дублированные скрипты

```
scripts/export_high_recall_ac_patterns.py     # 10.9 KB
ai_service/scripts/export_high_recall_ac_patterns.py   # отличается!
```

**Проблема:** Две версии одного скрипта, файлы различаются (`diff` показал различия).

**Действие:**
1. Сравнить версии
2. Оставить актуальную в `scripts/`
3. Удалить `ai_service/` полностью

---

### Legacy конфигурации

```bash
# Dockerfile'ы
Dockerfile.search.backup              # Backup (удалить)

# Patch файлы
patch_sprint1_minimal.diff           # Старый patch (удалить)
```

**Действие:** Удалить backup'ы и старые patch'и.

---

## 📂 Проблема #4: Структура директорий

### Пустые директории

```bash
scripts/debug/                # пустая (создана но не используется)
out/                         # пустая
logs/                        # пустая (логи идут в другое место?)
```

**Действие:**
- Удалить пустые `scripts/debug/`, `out/`
- Проверить использование `logs/` — если не используется, добавить в `.gitignore`

---

### Переполненная docs/archive/

```bash
docs/archive/                # 31 файл (много!)
```

**Список файлов в archive:**
- `API_EXAMPLES.md`
- `PERFORMANCE_OPTIMIZATION_GUIDE.md`
- `FEATURE_FLAGS_ANALYSIS.md`
- `PRODUCTION_DEPLOYMENT.md` (дубликат основного!)
- `CRITICAL_SECURITY_ISSUES.md`
- `DEPLOYMENT_EMERGENCY.md`
- `METRICS_FIX_SUMMARY.md`
- ... и еще 24 файла

**Проблема:** Много документов, некоторые дублируют актуальные в `docs/`.

**Действие:**
1. Проверить дубликаты с основной `docs/`
2. Удалить явно устаревшие (`DEPLOYMENT_EMERGENCY.md`, `CRITICAL_SECURITY_ISSUES.md` — уже исправлено)
3. Оставить только важные исторические документы

---

### Документы для пересмотра

**Основные docs/ (возможные дубликаты):**
```bash
docs/PRODUCTION_DEPLOYMENT.md
docs/archive/PRODUCTION_DEPLOYMENT.md        # дубликат?

docs/SEARCH_INTEGRATION_PLAN.md              # план уже выполнен?
docs/SEARCH_INTEGRATION_README.md            # тоже про интеграцию
docs/SEARCH_DEPLOYMENT_PIPELINE.md           # еще один про деплой
```

**Действие:** Объединить дубликаты, устаревшие планы удалить.

---

## 🧪 Проблема #5: Тесты

### Статистика тестов

```bash
tests/                       # структура
├── unit/                    # юнит-тесты
├── integration/             # интеграционные
├── golden_e2e/             # e2e тесты
├── property/               # property-based тесты
└── canary/                 # canary тесты
```

**Всего тестов:** (нужно проверить)

### Проблемы

1. **Устаревшие тесты для legacy кода:**
   - Тесты для `NormalizationServiceLegacy`
   - Тесты для `HybridSearchServiceRefactored`

2. **Дублирование тестов:**
   - AC search тесты в нескольких местах

**Действие:** Удалить тесты для legacy классов.

---

## 📦 Проблема #6: Scripts/ переполнен

### Статистика scripts/

```
Всего скриптов: 39
Подкаталоги:
- scripts/deploy/    13 скриптов
- scripts/debug/     0 (пустая!)
```

### Категории скриптов

#### Demo скрипты (можно переместить в examples/)
```
demo_ac_search.py
demo_caching.py
demo_changelog_automation.py
demo_profiling.py
demo_property_tests.py
demo_vector_search.py
```

#### Deployment скрипты (уже в scripts/deploy/)
```
scripts/deploy/deploy_fixes.sh
scripts/deploy/fix_docker_build.sh
scripts/deploy/quick_deploy.sh
... (11 скриптов)
```

#### Utility скрипты (оставить)
```
elasticsearch_setup_and_warmup.py     # production
bulk_loader.py                        # production
generate_vectors.py                   # production
usage_analysis.py                     # dev tool
```

#### Анализ/тестирование (устарели?)
```
analyze_divergences.py               # одноразовый анализ?
compare_legacy_vs_factory.py         # legacy сравнение
comparison_results_*.json            # результаты (удалить)
ascii_fastpath_parity.py             # тест четности
```

**Действие:**
1. Переместить `demo_*.py` в `examples/scripts/`
2. Удалить одноразовые анализы (`analyze_divergences.py`, `compare_legacy_vs_factory.py`)
3. Удалить JSON результаты (`comparison_results_*.json`)
4. Оставить production-ready скрипты в `scripts/`

---

## ⚙️ Проблема #7: Конфигурации

### Env файлы

```bash
.env                         # локальный (игнорируется git, ОК)
env.production.example       # example для production (ОК)
```

**Статус:** ✅ Все в порядке (`.env` в `.gitignore`)

### Docker compose файлы

```bash
docker-compose.yml           # dev
docker-compose.prod.yml      # production
docker-compose.test.yml      # testing
```

**Статус:** ✅ Нормально, все используются

---

## 🎯 Приоритетный План Очистки

### Высокий приоритет (делать сразу)

1. **Удалить временные файлы в корне**
   ```bash
   rm -f *_summary.txt cleanup_backup_*.tar.gz patch_*.diff
   rm -f __init__.py CLAUDE.md Dockerfile.search.backup
   rm -rf ai_service/
   ```
   **Эффект:** ~30 MB, 17 файлов

2. **Удалить legacy сервисы**
   ```bash
   rm -f src/ai_service/layers/normalization/normalization_service_legacy.py
   rm -f src/ai_service/layers/normalization/normalization_service_decomposed.py
   rm -f src/ai_service/layers/search/hybrid_search_service_refactored.py
   rm -f src/ai_service/layers/search/enhanced_elasticsearch_client.py
   rm -f src/ai_service/core/cache_service.py
   ```
   **Эффект:** ~500 LOC, 5 файлов

3. **Очистить scripts/**
   ```bash
   # Переместить demo в examples
   mv scripts/demo_*.py examples/scripts/

   # Удалить одноразовые анализы
   rm -f scripts/analyze_divergences.py
   rm -f scripts/compare_legacy_vs_factory.py
   rm -f scripts/comparison_results_*.json
   ```
   **Эффект:** 8 файлов

---

### Средний приоритет (можно отложить)

4. **Очистить неиспользуемые exceptions**
   - Удалить 10+ exception классов (см. список выше)
   - **Эффект:** ~100 LOC

5. **Убрать неиспользуемые contracts**
   - Удалить deprecated models и contracts
   - **Эффект:** ~200 LOC

6. **Очистить docs/archive/**
   - Удалить явно устаревшие документы (CRITICAL_SECURITY_ISSUES.md и т.п.)
   - **Эффект:** ~10 файлов

---

### Низкий приоритет (для будущего рефакторинга)

7. **Рефакторинг остального мертвого кода**
   - 596 неиспользуемых методов
   - Requires careful review

8. **Унификация документации**
   - Объединить дубликаты
   - Обновить устаревшие

---

## 📈 Ожидаемый Эффект

### Метрики до очистки
```
Файлов в корне:       64
Мертвого кода:        28.4% (785 definitions)
Скриптов:            39
Legacy файлов:        5 крупных
Временных файлов:     17
```

### Метрики после очистки (прогноз)
```
Файлов в корне:       47 (-17)
Мертвого кода:        ~18% (-385 definitions)
Скриптов:            31 (-8)
Legacy файлов:        0 (-5)
Временных файлов:     0 (-17)

Освобождено места:    ~35 MB
Удалено LOC:          ~800-1000
```

---

## ✅ Checklist для ревью

### Структура проекта
- [x] Проанализирована структура
- [x] Найдены временные файлы
- [x] Найден мертвый код
- [ ] Очищен корень проекта
- [ ] Удален legacy код
- [ ] Очищена docs/

### Качество кода
- [x] Запущен usage_analysis.py
- [ ] Удалены неиспользуемые imports
- [ ] Удалены неиспользуемые exceptions
- [ ] Удалены неиспользуемые contracts

### Документация
- [ ] Удалены дубликаты
- [ ] Обновлены устаревшие
- [x] Создан DATA_PIPELINE.md

### Scripts
- [ ] Demo скрипты перенесены в examples/
- [ ] Удалены одноразовые анализы
- [ ] Deployment скрипты организованы

---

## 🚀 Рекомендуемые Действия

### Немедленные действия (< 30 мин)

```bash
# 1. Создать backup ветку
git checkout -b cleanup-before-review
git add -A
git commit -m "checkpoint: before cleanup"

# 2. Создать рабочую ветку
git checkout -b project-cleanup

# 3. Удалить временные файлы
rm -f *_summary.txt cleanup_backup_*.tar.gz patch_*.diff
rm -f __init__.py CLAUDE.md Dockerfile.search.backup
rm -rf ai_service/
git add -A
git commit -m "chore: remove temporary files and backups from root"

# 4. Переместить shell скрипты
mkdir -p scripts/testing
git mv check_poroshenko_patterns.sh test_poroshenko.sh scripts/testing/
git mv enable_search.sh scripts/
git commit -m "chore: organize shell scripts"

# 5. Удалить пустые директории
rm -rf scripts/debug/ out/
git add -A
git commit -m "chore: remove empty directories"

# 6. Коммит
git log --oneline -5
```

### Средний срок (1-2 часа)

```bash
# 7. Удалить legacy сервисы
git rm src/ai_service/layers/normalization/normalization_service_legacy.py
git rm src/ai_service/layers/normalization/normalization_service_decomposed.py
git rm src/ai_service/layers/search/hybrid_search_service_refactored.py
git rm src/ai_service/core/cache_service.py
git commit -m "chore: remove legacy service implementations"

# 8. Очистить scripts/
mkdir -p examples/scripts
git mv scripts/demo_*.py examples/scripts/
git rm scripts/analyze_divergences.py scripts/compare_legacy_vs_factory.py
git rm scripts/comparison_results_*.json
git commit -m "chore: reorganize scripts - move demos to examples"

# 9. Проверить тесты
pytest
```

### Долгий срок (2-4 часа)

```bash
# 10. Удалить неиспользуемые contracts/exceptions
# (требует ручной проверки каждого)

# 11. Очистить docs/archive/
# (требует ручной проверки актуальности)

# 12. Финальная проверка
pytest
git status
```

---

## 📝 Заключение

**Текущее состояние:** Проект содержит много legacy кода (28.4%) и временных файлов, что затрудняет навигацию и понимание архитектуры.

**Рекомендации:**
1. **Немедленно** удалить временные файлы и backups (30 мин)
2. **В приоритете** удалить legacy сервисы (1 час)
3. **Желательно** очистить scripts/ и docs/ (2 часа)

**После очистки:**
- Проект станет на 35 MB легче
- Удалится 800-1000 LOC мертвого кода
- Структура станет понятнее для нового разработчика
- Тимлид увидит только актуальный код

**Готовность к ревью:** ⚠️ Требуется cleanup перед подачей

---

**Автор отчета:** Claude Code
**Дата:** 03.10.2025

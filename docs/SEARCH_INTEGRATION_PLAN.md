# Search Integration Plan

## Обзор интеграции AC/Vector поиска в существующий пайплайн

### Текущий пайплайн (9 слоёв):
1. **Validation & Sanitization** - валидация входных данных
2. **Smart Filter** - предварительная фильтрация (tier-0 lite)
3. **Language Detection** - определение языка
4. **Unicode Normalization** - нормализация Unicode
5. **Name Normalization** - морфологическая нормализация имён
6. **Signals** - извлечение и структурирование сущностей
7. **Variants** - генерация вариантов (опционально)
8. **Embeddings** - генерация эмбеддингов (опционально)
9. **Decision** - принятие решений на основе сигналов

### Новый слой поиска (Слой 9.5):
**HybridSearchService** - между Signals и Decision

---

## 1. SmartFilter: Tier-0 Lite (НЕ МЕНЯЕМ)

**Текущее состояние**: Только локальные дешёвые правила
**Действие**: НЕ ТРОГАЕМ - оставляем как есть

```python
# Существующий код остаётся без изменений
class SmartFilterService:
    def should_process(self, text: str) -> SmartFilterResult:
        # Только локальные правила, без ES
        # Если нет уверенности → идём дальше
        pass
```

---

## 2. Normalization → Signals: Формирование кандидатных строк

**Место интеграции**: После `SignalsService.extract()`
**Действие**: Извлекаем кандидатные строки из результата Signals

### 2.1. Извлечение кандидатов из Signals

```python
# В UnifiedOrchestrator.process() после Layer 6 (Signals)
def _extract_search_candidates(self, signals_result: SignalsResult) -> List[str]:
    """Извлекаем кандидатные строки для поиска из результата Signals"""
    candidates = []
    
    # Персоны
    for person in signals_result.persons:
        if person.normalized_name:
            candidates.append(person.normalized_name)
        # Добавляем алиасы
        candidates.extend(person.aliases or [])
    
    # Организации  
    for org in signals_result.organizations:
        if org.normalized_name:
            candidates.append(org.normalized_name)
        # Добавляем алиасы
        candidates.extend(org.aliases or [])
    
    # Убираем дубликаты и пустые строки
    return list(set(filter(None, candidates)))
```

### 2.2. Обогащение Signals результата

```python
# Добавляем в SignalsResult новые поля
@dataclass
class SignalsResult:
    # ... существующие поля ...
    
    # Новые поля для поиска
    search_candidates: List[str] = field(default_factory=list)
    search_metadata: Dict[str, Any] = field(default_factory=dict)
```

---

## 3. HybridSearchService: AC → Vector → Fusion

**Место интеграции**: Новый слой между Signals и Decision
**Действие**: Создаём новый сервис и интегрируем в оркестратор

### 3.1. Интеграция в UnifiedOrchestrator

```python
# В UnifiedOrchestrator.__init__()
def __init__(self, ...):
    # ... существующие сервисы ...
    
    # Новый сервис поиска
    self.hybrid_search_service: Optional[HybridSearchService] = None

# В UnifiedOrchestrator.process() после Layer 6 (Signals)
async def process(self, ...):
    # ... существующие слои 1-6 ...
    
    # ================================================================
    # Layer 6.5: Hybrid Search (NEW)
    # ================================================================
    if self.enable_hybrid_search and self.hybrid_search_service:
        logger.debug("Stage 6.5: Hybrid Search")
        layer_start = time.time()
        
        try:
            # Извлекаем кандидатов из Signals
            search_candidates = self._extract_search_candidates(signals_result)
            
            if search_candidates:
                # Выполняем гибридный поиск
                search_result = await self.hybrid_search_service.find_candidates(
                    normalized=normalization_result,
                    text=context.sanitized_text,
                    opts=SearchOpts(
                        top_k=50,
                        threshold=0.7,
                        search_mode=SearchMode.HYBRID,
                        enable_escalation=True
                    )
                )
                
                # Обогащаем Signals результатом поиска
                signals_result.search_candidates = search_candidates
                signals_result.search_metadata = {
                    "search_results": search_result,
                    "search_count": len(search_result),
                    "search_time": time.time() - layer_start
                }
                
                logger.debug(f"Hybrid search found {len(search_result)} candidates")
            
            if self.metrics_service:
                self.metrics_service.record_timer('processing.layer.hybrid_search', time.time() - layer_start)
                self.metrics_service.record_histogram('hybrid_search.candidates_found', len(search_result))
                
        except Exception as e:
            logger.warning(f"Hybrid search failed: {e}")
            if self.metrics_service:
                self.metrics_service.increment_counter('processing.hybrid_search.failed')
            errors.append(f"Hybrid search: {str(e)}")
    
    # ... остальные слои 7-9 ...
```

### 3.2. Конфигурация HybridSearchService

```python
# В OrchestratorFactory.create_orchestrator()
@staticmethod
async def create_orchestrator(
    # ... существующие параметры ...
    enable_hybrid_search: bool = False,
    hybrid_search_service: Optional[HybridSearchService] = None,
    **kwargs
) -> UnifiedOrchestrator:
    
    # ... существующие сервисы ...
    
    # Hybrid Search service - новый
    if enable_hybrid_search and hybrid_search_service is None:
        try:
            from ..layers.search import HybridSearchService, HybridSearchConfig
            search_config = HybridSearchConfig()
            hybrid_search_service = HybridSearchService(search_config)
            await hybrid_search_service.initialize()
            logger.info("Hybrid search service initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize hybrid search service: {e}")
            hybrid_search_service = None
            enable_hybrid_search = False
```

---

## 4. Decision: Добавление весов и порогов для final_score

**Место интеграции**: DecisionEngine._calculate_weighted_score()
**Действие**: Добавляем веса для результатов поиска

### 4.1. Обновление DecisionConfig

```python
# В config/settings.py
@dataclass
class DecisionConfig:
    # ... существующие веса ...
    
    # Новые веса для поиска
    w_search_exact: float = 0.3      # Вес для exact совпадений
    w_search_phrase: float = 0.25    # Вес для phrase совпадений  
    w_search_ngram: float = 0.2      # Вес для ngram совпадений
    w_search_vector: float = 0.15    # Вес для vector совпадений
    
    # Пороги для поиска
    thr_search_exact: float = 0.8    # Порог для exact совпадений
    thr_search_phrase: float = 0.7   # Порог для phrase совпадений
    thr_search_ngram: float = 0.6    # Порог для ngram совпадений
    thr_search_vector: float = 0.5   # Порог для vector совпадений
    
    # Бонусы за множественные совпадения
    bonus_multiple_matches: float = 0.1
    bonus_high_confidence: float = 0.05
```

### 4.2. Обновление DecisionInput

```python
# В contracts/decision_contracts.py
@dataclass
class SearchInfo:
    """Информация о результатах поиска"""
    has_exact_matches: bool = False
    has_phrase_matches: bool = False
    has_ngram_matches: bool = False
    has_vector_matches: bool = False
    
    exact_confidence: float = 0.0
    phrase_confidence: float = 0.0
    ngram_confidence: float = 0.0
    vector_confidence: float = 0.0
    
    total_matches: int = 0
    high_confidence_matches: int = 0
    search_time: float = 0.0

@dataclass
class DecisionInput:
    # ... существующие поля ...
    search: Optional[SearchInfo] = None
```

### 4.3. Обновление DecisionEngine

```python
# В core/decision_engine.py
def _calculate_weighted_score(self, inp: DecisionInput) -> float:
    """Calculate weighted score including search results"""
    score = 0.0
    
    # ... существующие веса ...
    
    # Новые веса для поиска
    if inp.search:
        search = inp.search
        
        # Exact совпадения (высший приоритет)
        if search.has_exact_matches and search.exact_confidence >= self.config.thr_search_exact:
            score += self.config.w_search_exact * search.exact_confidence
        
        # Phrase совпадения
        if search.has_phrase_matches and search.phrase_confidence >= self.config.thr_search_phrase:
            score += self.config.w_search_phrase * search.phrase_confidence
        
        # N-gram совпадения
        if search.has_ngram_matches and search.ngram_confidence >= self.config.thr_search_ngram:
            score += self.config.w_search_ngram * search.ngram_confidence
        
        # Vector совпадения
        if search.has_vector_matches and search.vector_confidence >= self.config.thr_search_vector:
            score += self.config.w_search_vector * search.vector_confidence
        
        # Бонусы
        if search.total_matches > 1:
            score += self.config.bonus_multiple_matches
        
        if search.high_confidence_matches > 0:
            score += self.config.bonus_high_confidence
    
    return min(score, 1.0)
```

---

## 5. Точные сигнатуры вызовов

### 5.1. HybridSearchService.find_candidates()

```python
async def find_candidates(
    self,
    normalized: NormalizationResult,
    text: str,
    opts: SearchOpts
) -> List[Candidate]:
    """
    Найти кандидатов используя гибридный поиск
    
    Args:
        normalized: Результат нормализации
        text: Исходный текст
        opts: Опции поиска
        
    Returns:
        Список кандидатов с fusion scores
        
    Raises:
        SearchServiceError: При ошибках поиска
        ElasticsearchConnectionError: При проблемах с ES
        TimeoutError: При превышении тайм-аута
    """
```

### 5.2. ElasticsearchACAdapter.search()

```python
async def search(
    self,
    candidates: List[str],
    entity_type: str,
    opts: SearchOpts
) -> List[ACScore]:
    """
    AC поиск в Elasticsearch
    
    Args:
        candidates: Кандидатные строки для поиска
        entity_type: Тип сущности (person/org)
        opts: Опции поиска
        
    Returns:
        Список AC результатов с типами и скорами
        
    Raises:
        ElasticsearchConnectionError: При проблемах с ES
        TimeoutError: При превышении тайм-аута
    """
```

### 5.3. ElasticsearchVectorAdapter.search()

```python
async def search(
    self,
    query_vector: List[float],
    entity_type: str,
    opts: SearchOpts
) -> List[VectorHit]:
    """
    Vector поиск в Elasticsearch
    
    Args:
        query_vector: 384-мерный вектор запроса
        entity_type: Тип сущности (person/org)
        opts: Опции поиска
        
    Returns:
        Список Vector результатов с similarity scores
        
    Raises:
        ElasticsearchConnectionError: При проблемах с ES
        TimeoutError: При превышении тайм-аута
    """
```

---

## 6. Схемы исключений

### 6.1. Иерархия исключений

```python
# В exceptions.py
class SearchServiceError(Exception):
    """Базовое исключение для поиска"""
    pass

class ElasticsearchConnectionError(SearchServiceError):
    """Ошибка подключения к Elasticsearch"""
    pass

class SearchTimeoutError(SearchServiceError):
    """Тайм-аут поиска"""
    pass

class SearchConfigurationError(SearchServiceError):
    """Ошибка конфигурации поиска"""
    pass

class SearchDataError(SearchServiceError):
    """Ошибка данных поиска"""
    pass
```

### 6.2. Обработка исключений в оркестраторе

```python
# В UnifiedOrchestrator.process()
try:
    search_result = await self.hybrid_search_service.find_candidates(...)
except ElasticsearchConnectionError as e:
    logger.warning(f"Elasticsearch unavailable, skipping search: {e}")
    # Продолжаем без поиска
    search_result = []
except SearchTimeoutError as e:
    logger.warning(f"Search timeout: {e}")
    # Продолжаем без поиска
    search_result = []
except SearchServiceError as e:
    logger.error(f"Search service error: {e}")
    # Продолжаем без поиска
    search_result = []
except Exception as e:
    logger.error(f"Unexpected search error: {e}")
    # Продолжаем без поиска
    search_result = []
```

---

## 7. Тайм-ауты и ретраи

### 7.1. Конфигурация тайм-аутов

```python
# В HybridSearchConfig
@dataclass
class HybridSearchConfig:
    # ... существующие поля ...
    
    # Тайм-ауты
    ac_search_timeout: float = 2.0      # AC поиск: 2 сек
    vector_search_timeout: float = 3.0  # Vector поиск: 3 сек
    total_search_timeout: float = 5.0   # Общий тайм-аут: 5 сек
    
    # Ретраи
    max_retries: int = 2
    retry_delay: float = 0.5
    backoff_multiplier: float = 2.0
    
    # Пороги для эскалации
    ac_weak_threshold: float = 0.6      # Если AC < 0.6 → Vector
    ac_empty_threshold: int = 3         # Если AC < 3 результатов → Vector
```

### 7.2. Реализация ретраев

```python
# В HybridSearchService
async def _search_with_retry(
    self,
    search_func: Callable,
    *args,
    **kwargs
) -> Any:
    """Выполнить поиск с ретраями"""
    last_exception = None
    
    for attempt in range(self.config.max_retries + 1):
        try:
            return await asyncio.wait_for(
                search_func(*args, **kwargs),
                timeout=self.config.ac_search_timeout
            )
        except (ElasticsearchConnectionError, TimeoutError) as e:
            last_exception = e
            if attempt < self.config.max_retries:
                delay = self.config.retry_delay * (self.config.backoff_multiplier ** attempt)
                logger.warning(f"Search attempt {attempt + 1} failed: {e}, retrying in {delay}s")
                await asyncio.sleep(delay)
            else:
                logger.error(f"All search attempts failed: {e}")
                raise
        except Exception as e:
            # Не ретраим для других исключений
            raise
    
    raise last_exception
```

---

## 8. Метрики и мониторинг

### 8.1. Новые метрики

```python
# В HybridSearchService
def _record_search_metrics(self, search_type: str, duration: float, result_count: int):
    """Записать метрики поиска"""
    if self.metrics_service:
        self.metrics_service.record_timer(f'search.{search_type}.duration', duration)
        self.metrics_service.record_histogram(f'search.{search_type}.results_count', result_count)
        self.metrics_service.increment_counter(f'search.{search_type}.attempts')
        
        if result_count > 0:
            self.metrics_service.increment_counter(f'search.{search_type}.success')
        else:
            self.metrics_service.increment_counter(f'search.{search_type}.empty')
```

### 8.2. Алерты

```python
# В HybridSearchService
def _check_search_health(self, duration: float, result_count: int):
    """Проверить здоровье поиска"""
    if self.metrics_service:
        # Алерт на медленный поиск
        if duration > self.config.total_search_timeout * 0.8:
            self.metrics_service.record_alert(
                'search.slow',
                f'Search took {duration:.2f}s (threshold: {self.config.total_search_timeout * 0.8:.2f}s)',
                AlertSeverity.WARNING
            )
        
        # Алерт на пустые результаты
        if result_count == 0:
            self.metrics_service.record_alert(
                'search.empty_results',
                'Search returned no results',
                AlertSeverity.INFO
            )
```

---

## 9. Порядок интеграции

### Этап 1: Подготовка
1. ✅ Создать HybridSearchService и адаптеры
2. ✅ Создать конфигурацию и контракты
3. ✅ Создать тесты

### Этап 2: Интеграция в оркестратор
1. Добавить HybridSearchService в UnifiedOrchestrator
2. Добавить слой поиска между Signals и Decision
3. Обновить OrchestratorFactory

### Этап 3: Обновление Decision
1. Добавить SearchInfo в DecisionInput
2. Обновить DecisionConfig с весами поиска
3. Обновить DecisionEngine._calculate_weighted_score()

### Этап 4: Тестирование
1. Интеграционные тесты
2. Нагрузочное тестирование
3. Мониторинг производительности

### Этап 5: Развёртывание
1. Постепенное включение (feature flag)
2. Мониторинг метрик
3. Настройка алертов

---

## 10. Конфигурация через ENV

```bash
# Включение гибридного поиска
ENABLE_HYBRID_SEARCH=true

# Elasticsearch
ES_URL=http://localhost:9200
ES_AUTH=user:password
ES_VERIFY_SSL=true

# Тайм-ауты поиска
AC_SEARCH_TIMEOUT=2.0
VECTOR_SEARCH_TIMEOUT=3.0
TOTAL_SEARCH_TIMEOUT=5.0

# Пороги эскалации
AC_WEAK_THRESHOLD=0.6
AC_EMPTY_THRESHOLD=3

# Веса для Decision
W_SEARCH_EXACT=0.3
W_SEARCH_PHRASE=0.25
W_SEARCH_NGRAM=0.2
W_SEARCH_VECTOR=0.15
```

---

## Заключение

Интеграция поиска не нарушает существующие контракты:
- SmartFilter остаётся без изменений (tier-0 lite)
- Signals обогащается кандидатными строками
- Decision получает новые веса для final_score
- Новый HybridSearchService работает между существующими слоями

Все изменения обратно совместимы и могут быть включены через feature flags.

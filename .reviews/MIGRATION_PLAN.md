# 🗺️ MIGRATION PLAN — Пошаговый план очистки и миграции

## TL;DR — ROADMAP НА 6 НЕДЕЛЬ
**ЦЕЛЬ**: Привести кодовую базу в production-ready состояние
**СТРАТЕГИЯ**: 3 спринта по 2 недели, от критичных проблем к качественным улучшениям
**ОЖИДАЕМЫЙ РЕЗУЛЬТАТ**: Стабильная, maintainable система без технического долга

---

## 🎯 EXECUTIVE SUMMARY

### Текущее состояние:
- **Feature Flags**: 🔴 Критичные дубли и несоответствия
- **Architecture**: 🟡 Хорошая структура, но legacy дубли
- **Tests**: 🔴 xfail epidemic, дубли legacy/factory
- **Dead Code**: 🟡 Умеренное замусоривание
- **Security**: 🟡 Умеренные риски
- **CI/CD**: 🟡 Функционально, но избыточно сложно

### Целевое состояние:
- ✅ Унифицированная система флагов
- ✅ Единый normalization pipeline (factory-based)
- ✅ Стабильные тесты без xfail костылей
- ✅ Чистая кодовая база без legacy дублей
- ✅ Secure by design (PII masking, input validation)
- ✅ Эффективная CI система (3 вместо 7 workflow'ов)

---

## 📅 SPRINT BREAKDOWN

### **SPRINT 1 (Недели 1-2): КРИТИЧНЫЕ ФИКСЫ** 🚨
*Фокус: P0 проблемы, блокирующие production readiness*

#### Week 1: Feature Flags & Core Stability
**Цель**: Унифицировать систему флагов и устранить критичные несоответствия

**День 1-2: Feature Flags Critical Fixes**
- [ ] **Устранить дубли флагов** в `FeatureFlags` класс (src/ai_service/utils/feature_flags.py:58-66)
- [ ] **Синхронизировать дефолты** между `flags_inventory.json` и реальным кодом
- [ ] **Добавить недостающие environment переменные** для `ascii_fastpath`
- [ ] **Создать validation** флагов при старте приложения

**День 3: Core Architecture Unification**
- [ ] **Выбрать canonical normalization**: Factory vs Legacy
- [ ] **Унифицировать orchestrator'ы**: Удалить `unified_orchestrator_with_search.py`
- [ ] **Исправить layer violations**: Normalization не должна импортировать search

**День 4-5: Critical Test Fixes**
- [ ] **Исправить критичные xfail**:
  - `test_golden_cases.py` — align factory with golden cases
  - `test_sanctions_screening_pipeline.py` — основной E2E pipeline
- [ ] **Удалить legacy test дубли**: `*_old.py` файлы
- [ ] **Добавить feature flags тесты**: каждый флаг должен влиять на поведение

#### Week 2: Security & Input Validation
**Цель**: Устранить security уязвимости и добавить защиты

**День 6-7: Security Critical Fixes**
- [ ] **Implement PII masking** в логах:
  ```python
  def safe_log(text: str) -> str:
      return f"<text:{len(text)}chars>" if len(text) > 50 else text[:5] + "*" * (len(text) - 10) + text[-5:]
  ```
- [ ] **Strengthen API token validation**:
  ```python
  import secrets
  if not secrets.compare_digest(credentials.credentials, expected_token):
      raise AuthenticationError("Invalid API key")
  ```

**День 8-9: Input Validation**
- [ ] **Add FastAPI input limits**:
  ```python
  text: str = Field(..., max_length=2000, min_length=1)
  ```
- [ ] **Rate limiting middleware**:
  ```python
  from slowapi import Limiter
  @limiter.limit("100/minute")
  ```

**День 10: CI Critical Fixes**
- [ ] **Sync environment flags** между всеми workflow'ами
- [ ] **Fix `continue-on-error: true`** для critical tests
- [ ] **Add deterministic testing**: `PYTHONHASHSEED=0`

**Sprint 1 Acceptance Criteria** ✅:
- [ ] Zero duplicate flags в коде
- [ ] Golden parity tests проходят без xfail
- [ ] PII не логируется в plain text
- [ ] API имеет basic input validation
- [ ] CI не ignore'ит critical test failures

---

### **SPRINT 2 (Недели 3-4): ARCHITECTURE CLEANUP** 🏗️
*Фокус: Унификация архитектуры и устранение legacy*

#### Week 3: Code Cleanup & Architecture
**Цель**: Очистить legacy код и унифицировать дубли

**День 11-12: Dead Code Elimination**
- [ ] **Feature flags files**: Выбрать canonical version между `config/` и `utils/`
- [ ] **Morphology adapter**: Унифицировать в один файл
- [ ] **Embedding preprocessor**: Удалить дублированный файл
- [ ] **Legacy services**: Архивировать `normalization_service_legacy.py`

**День 13-14: Service Unification**
- [ ] **spaCy gateways**: Один параметризованный файл вместо 3
- [ ] **ElasticSearch wrappers**: Объединить client и adapters
- [ ] **Orchestrator cleanup**: Один orchestrator с feature flags

**День 15: Architecture Validation**
- [ ] **Run import analysis**: No circular dependencies
- [ ] **Layer boundary check**: Clean separation L0-L5
- [ ] **Update architecture docs**: Reflect current state

#### Week 4: Performance & ML Optimizations
**Цель**: Оптимизировать производительность и ML зависимости

**День 16-17: ML Dependencies Optimization**
- [ ] **Lazy loading для torch/transformers**:
  ```python
  def get_sentence_transformer():
      import sentence_transformers  # Lazy import
      return sentence_transformers.SentenceTransformer(...)
  ```
- [ ] **Optional ML dependencies**: Graceful degradation если models недоступны

**День 18-19: Performance Improvements**
- [ ] **Regex precompilation**: Вынести из loops
- [ ] **Cache optimizations**: LRU cache keys детерминированы
- [ ] **String operations**: joins вместо concatenations

**День 20: Enhanced Testing**
- [ ] **Add coverage gates**: Minimum 80% для core components
- [ ] **Performance regression tests**: SLA violations fail build
- [ ] **Property-based test expansion**: More edge cases

**Sprint 2 Acceptance Criteria** ✅:
- [ ] Zero duplicate service files
- [ ] Single orchestrator with clean interface
- [ ] ML models load lazily
- [ ] Coverage ≥ 80% для core components
- [ ] Performance tests в CI pipeline

---

### **SPRINT 3 (Недели 5-6): QUALITY & MONITORING** 📊
*Фокус: Quality gates, monitoring, и documentation*

#### Week 5: Advanced Quality Gates
**Цель**: Comprehensive quality assurance system

**День 21-22: Enhanced CI Pipeline**
- [ ] **Consolidate 7→3 workflows**:
  - `main-ci.yml` (tests + coverage + security)
  - `quality-gates.yml` (parity + perf + search + e2e)
  - `deployment.yml` (deploy + monitoring)
- [ ] **Add missing gates**:
  ```yaml
  # Security scanning
  bandit -r src/ --format json
  safety check

  # Dependency audit
  pip-audit --requirement requirements.txt
  ```

**День 23-24: Search System Stability**
- [ ] **ElasticSearch integration**: Proper health checks и retries
- [ ] **Search trace validation**: Deterministic ordering
- [ ] **Hybrid search testing**: AC + Vector integration tests

**День 25: Monitoring & Observability**
- [ ] **Enhanced logging**: Structured logs with trace IDs
- [ ] **Metrics collection**: Performance trends, error rates
- [ ] **Alert definitions**: SLA violations, error spikes

#### Week 6: Documentation & Final Polish
**Цель**: Production readiness и knowledge transfer

**День 26-27: Documentation Update**
- [ ] **Architecture documentation**: Current state diagrams
- [ ] **API documentation**: OpenAPI/Swagger complete
- [ ] **Runbooks**: Troubleshooting, deployment, monitoring
- [ ] **Migration guides**: Legacy → Factory transition

**День 28-29: Final Integration Testing**
- [ ] **End-to-end scenarios**: Full sanctions screening pipeline
- [ ] **Load testing**: Performance под нагрузкой
- [ ] **Chaos testing**: Failure scenarios (ES down, models unavailable)

**День 30: Production Readiness Review**
- [ ] **Security audit checklist**: OWASP compliance
- [ ] **Performance benchmarks**: Established baselines
- [ ] **Monitoring dashboard**: Key metrics visible
- [ ] **Rollback procedures**: Documented и tested

**Sprint 3 Acceptance Criteria** ✅:
- [ ] Streamlined CI (3 clean workflows)
- [ ] Comprehensive monitoring dashboard
- [ ] Complete documentation set
- [ ] Production deployment ready
- [ ] Knowledge transfer complete

---

## 🚧 RISK MITIGATION STRATEGIES

### High-Risk Changes:
1. **Feature flags unification**:
   - Risk: Breaking existing integrations
   - Mitigation: Backward compatibility layer + gradual migration

2. **Normalization pipeline changes**:
   - Risk: Golden parity violations
   - Mitigation: Shadow mode testing + rollback plan

3. **CI workflow consolidation**:
   - Risk: Breaking existing automation
   - Mitigation: Parallel workflows during transition

### Rollback Plans:
- **Feature flags**: Revert to previous version с environment override
- **Architecture changes**: Git revert + redeploy
- **CI changes**: Keep old workflows during transition period

---

## 📊 SUCCESS METRICS

### Sprint 1 KPIs:
- [ ] **Feature Flag Health**: 0 duplicate flags, 100% environment coverage
- [ ] **Test Stability**: 0 xfail в critical paths
- [ ] **Security Score**: Basic PII protection + input validation

### Sprint 2 KPIs:
- [ ] **Code Quality**: 0 duplicate files, clean architecture
- [ ] **Performance**: p95 latency ≤ 10ms consistently
- [ ] **Coverage**: ≥ 80% для core components

### Sprint 3 KPIs:
- [ ] **CI Efficiency**: 3 clean workflows, deterministic results
- [ ] **Production Readiness**: Full monitoring + documentation
- [ ] **Knowledge Transfer**: Team can maintain и extend

---

## 💰 RESOURCE REQUIREMENTS

### Team Allocation:
- **Senior Engineer**: 100% (architecture decisions, critical fixes)
- **QA Engineer**: 50% (test cleanup, validation)
- **DevOps Engineer**: 30% (CI optimization, monitoring setup)

### Timeline Flexibility:
- **Critical Path**: Sprint 1 (must complete for production)
- **Nice-to-Have**: Some Sprint 3 items can defer if needed
- **Buffer**: 1 week buffer built into each sprint

---

## 🎯 FINAL READINESS CHECKLIST

### Technical Readiness:
- [ ] ✅ Feature flags система унифицирована и стабильна
- [ ] ✅ Architecture clean без legacy дублей
- [ ] ✅ Tests проходят без xfail костылей
- [ ] ✅ Security vulnerabilities устранены
- [ ] ✅ Performance meets SLA requirements
- [ ] ✅ CI/CD pipeline оптимизирован

### Operational Readiness:
- [ ] ✅ Monitoring и alerting настроены
- [ ] ✅ Documentation complete и accurate
- [ ] ✅ Team trained на новый codebase
- [ ] ✅ Runbooks для troubleshooting
- [ ] ✅ Rollback procedures tested

### Business Readiness:
- [ ] ✅ Golden parity maintained
- [ ] ✅ API contracts backward compatible
- [ ] ✅ Performance regression risks mitigated
- [ ] ✅ Security compliance achieved

---

## 🚀 POST-MIGRATION BENEFITS

### Developer Experience:
- **Faster onboarding**: Clear architecture, no legacy confusion
- **Easier debugging**: Clean logs, structured tracing
- **Confident changes**: Comprehensive test coverage

### Operational Benefits:
- **Reduced maintenance**: No duplicate code to maintain
- **Better monitoring**: Real-time insights into system health
- **Faster incident response**: Clear runbooks и tools

### Business Impact:
- **Higher reliability**: Stable system without flaky components
- **Faster feature delivery**: Clean codebase easier to extend
- **Compliance confidence**: Security и privacy best practices

**ИТОГО**: 6-недельная миграция transform'ит codebase из "working but messy" в "production-ready и maintainable".
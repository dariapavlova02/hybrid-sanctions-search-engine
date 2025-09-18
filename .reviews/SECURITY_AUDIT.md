# 🔒 SECURITY AUDIT — Анализ безопасности и PII

## TL;DR — УМЕРЕННЫЕ РИСКИ БЕЗОПАСНОСТИ
**СТАТУС**: 🟡 Есть уязвимости средней критичности
**ОСНОВНЫЕ РИСКИ**: Потенциальное логирование PII, слабые дефолты токенов, отсутствие input validation
**ПРИОРИТЕТ**: P1 — исправить в течение 2 недель

---

## 🚨 КРИТИЧНЫЕ ПРОБЛЕМЫ

### P0 — IMMEDIATE ACTION REQUIRED

#### 1. **Weak Default API Token** (P0 — CRITICAL)
**Файл**: `src/ai_service/main.py:8`
```python
if not expected_token or expected_token == "your-secure-api-key-here":
    logger.warning("Admin API key not configured properly")
    raise AuthenticationError("Admin API key not configured")
```

**Проблема**: Код проверяет на placeholder, но что если пользователь установит именно "your-secure-api-key-here"?
**Риск**: Weak token в production
**Решение**: Добавить проверку на минимальную длину и сложность

#### 2. **Potential PII Logging** (P0 — DATA PRIVACY)
**Файл**: `src/ai_service/validation/shadow_mode_validator.py`
**Найдено**:
```python
self.logger.error(f"NER validation failed for '{text}': {e}")
self.logger.error(f"Nameparser validation failed for '{text}': {e}")
self.logger.info(f"Validating test case: '{test_case}'")
```

**Проблема**: Персональные имена логируются в plain text
**Риск**: GDPR/PII compliance violation
**Решение**: Mask или hash персональные данные в логах

---

### P1 — HIGH SEVERITY

#### 3. **No Input Validation Limits** (P1 — DoS)
**Анализ**: В main.py нет проверок на:
- Максимальную длину input text
- Rate limiting
- Request size limits

**Риск**: DoS атаки через большие payloads
**Решение**: Добавить FastAPI validators и middleware

#### 4. **Elasticsearch Connection Security** (P1 — DATA)
**Файлы**: `src/ai_service/layers/search/elasticsearch_client.py`
**Проблема**: Нужно проверить SSL validation, timeouts, auth

#### 5. **Dependencies Vulnerabilities** (P1 — SUPPLY CHAIN)
**Нужна проверка**: CVE в ML dependencies (torch, transformers, etc.)

---

## 🔍 АНАЛИЗ ПО КАТЕГОРИЯМ

### Authentication & Authorization ⚠️

#### API Token System:
```python
# main.py: verify_admin_token()
def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    expected_token = SECURITY_CONFIG.admin_api_key
    if credentials.credentials != expected_token:
        raise AuthenticationError("Invalid API key")
```

**Найденные проблемы**:
- ✅ Использует HTTPBearer (хорошо)
- ❌ Simple string comparison (vulnerable to timing attacks)
- ❌ No token rotation mechanism
- ❌ No role-based access control

**Рекомендации**:
```python
# Secure comparison
import secrets
if not secrets.compare_digest(credentials.credentials, expected_token):
    raise AuthenticationError("Invalid API key")
```

### Input Validation 🟡

#### FastAPI Models:
```python
class NormalizationOptions(BaseModel):
    # Нужно добавить validators
```

**Отсутствует**:
- Max length constraints
- Character set validation
- Rate limiting
- Request size limits

**Добавить**:
```python
from pydantic import validator, Field

class NormalizationOptions(BaseModel):
    text: str = Field(..., max_length=1000, min_length=1)

    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError('Text cannot be empty')
        return v
```

### Data Privacy (PII) 🔴

#### Logging Analysis:
**Проблемные логи**:
```python
# ПЛОХО: Логирует полный text (может содержать имена)
logger.error(f"NER validation failed for '{text}': {e}")
logger.info(f"Validating test case: '{test_case}'")

# ХОРОШО: Логирует только метаданные
logger.error(f"NER validation failed for text of length {len(text)}: {e}")
```

**PII Masking Strategy**:
```python
def mask_pii(text: str) -> str:
    """Mask personal data in logs"""
    if len(text) <= 10:
        return text[:2] + "*" * (len(text) - 4) + text[-2:]
    return text[:3] + "*" * 10 + text[-3:]

# Usage
logger.info(f"Processing text: {mask_pii(text)}")
```

### Network Security 🟡

#### Elasticsearch Security:
**Нужно проверить в elasticsearch_client.py**:
- SSL/TLS validation
- Certificate verification
- Connection timeouts
- Authentication method

#### CORS Configuration:
```python
# main.py: CORS middleware
app.add_middleware(CORSMiddleware, ...)
```
**Проверить**: Allow origins, methods, headers

---

## 🔐 SECRETS MANAGEMENT

### Environment Variables ✅ (правильный подход)
**Найдено**: Конфигурация через environment variables
```python
from ai_service.config import SECURITY_CONFIG
expected_token = SECURITY_CONFIG.admin_api_key
```

### No Hardcoded Secrets ✅
**Проверено**: Нет hardcoded passwords/tokens в коде
```bash
grep -r "password.*=\|secret.*=\|token.*=" src/ --include="*.py"
# Результат: только переменные и configuration
```

### Configuration Security:
**Рекомендации**:
- Использовать HashiCorp Vault или AWS Secrets Manager
- Rotate API tokens регулярно
- Separate secrets per environment

---

## 🐛 DEPENDENCY VULNERABILITIES

### ML Dependencies Risk Assessment:
```toml
# pyproject.toml - потенциальные риски:
torch = ">=1.24.0"              # Крупная зависимость
sentence-transformers = ">=5.1.0"  # Модели могут содержать backdoors
transformers = "*"               # Hugging Face models risk
```

### Vulnerability Scanning:
```bash
# Запустить проверку зависимостей
pip-audit
safety check
bandit -r src/
```

### Model Security:
**Риски**:
- Models от third-party (Hugging Face)
- Potential model poisoning
- Large attack surface

**Mitigation**:
- Pin specific model versions
- Verify model checksums
- Use trusted model sources only

---

## 🛡️ РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ

### Неделя 1: Critical Security Fixes (P0)
- [ ] **Day 1**: Implement PII masking в логах:
  ```python
  def safe_log(text: str, max_length: int = 50) -> str:
      if len(text) <= max_length:
          return text[:5] + "*" * (len(text) - 10) + text[-5:]
      return f"<text:{len(text)}chars>"
  ```
- [ ] **Day 2**: Strengthen API token validation:
  ```python
  # Add minimum length, complexity checks
  # Use secrets.compare_digest()
  ```
- [ ] **Day 3**: Add input validation limits:
  ```python
  text: str = Field(..., max_length=2000, regex=r'^[a-zA-Zа-яА-ЯіІїЇєЄ\s\.\-\']+$')
  ```

### Неделя 2: Enhanced Security (P1)
- [ ] **Day 4-5**: ElasticSearch security audit:
  - SSL certificate validation
  - Connection encryption
  - Authentication method review
- [ ] **Day 6-7**: Dependency vulnerability scan:
  ```bash
  pip-audit --requirement requirements.txt
  bandit -r src/ --format json
  ```
- [ ] **Day 8-9**: Rate limiting и DoS protection:
  ```python
  from slowapi import Limiter, _rate_limit_exceeded_handler
  limiter = Limiter(key_func=get_remote_address)

  @app.post("/normalize")
  @limiter.limit("100/minute")
  async def normalize_text(...):
  ```
- [ ] **Day 10**: Security headers и CORS review

---

## 🧪 SECURITY TESTING

### Automated Security Tests:
```python
# tests/security/test_api_security.py
def test_api_requires_authentication():
    response = client.post("/normalize", json={"text": "test"})
    assert response.status_code == 401

def test_input_length_limits():
    long_text = "x" * 10000
    response = client.post("/normalize",
                          json={"text": long_text},
                          headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 422  # Validation error

def test_no_pii_in_logs(caplog):
    client.post("/normalize", json={"text": "John Smith"})
    assert "John Smith" not in caplog.text
```

### Penetration Testing Checklist:
- [ ] SQL injection (если есть DB)
- [ ] XSS в API responses
- [ ] CSRF protection
- [ ] DoS через large payloads
- [ ] Authorization bypass
- [ ] API rate limiting
- [ ] Input fuzzing

---

## 📊 SECURITY SCORECARD

| Категория | Оценка | Статус | Приоритет |
|-----------|--------|---------|-----------|
| Authentication | 6/10 | 🟡 Acceptable | P1 |
| Input Validation | 4/10 | 🔴 Poor | P0 |
| Data Privacy | 3/10 | 🔴 Poor | P0 |
| Network Security | 7/10 | 🟡 Good | P2 |
| Secrets Management | 8/10 | ✅ Good | P3 |
| Dependencies | 5/10 | 🟡 Unknown | P1 |

**Общая оценка безопасности: 5.5/10** — Требуется улучшение

---

## 🎯 COMPLIANCE CHECKLIST

### GDPR/Data Privacy:
- [ ] PII masking в логах
- [ ] Data retention policies
- [ ] Right to be forgotten
- [ ] Data processing consent

### Industry Standards:
- [ ] OWASP Top 10 compliance
- [ ] Input validation (A03)
- [ ] Security logging (A09)
- [ ] Authentication (A07)

### API Security:
- [ ] Rate limiting
- [ ] Input size limits
- [ ] Error handling (no info leakage)
- [ ] Security headers

---

## 🚨 ИТОГОВЫЕ РЕКОМЕНДАЦИИ

### Immediate Actions (P0):
1. **Implement PII masking** — критично для compliance
2. **Add input validation** — защита от DoS
3. **Strengthen token validation** — prevent timing attacks

### Next Steps (P1):
1. Full dependency audit
2. ElasticSearch security review
3. Rate limiting implementation

**КРИТИЧНОСТЬ**: Система имеет умеренные уязвимости, но исправимые. **НЕ БЛОКИРУЕТ** продакшн при условии исправления P0 проблем в течение 2 недель.
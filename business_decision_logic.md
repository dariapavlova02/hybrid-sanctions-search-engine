# Бизнес-логика принятия решений по полям API ответа

## 🎯 **Ключевые поля для принятия решений**

API возвращает следующие **критически важные поля** для принятия бизнес-решений:

### 1. **Основные поля риска**
```json
{
  "risk_level": "high|medium|low|skip",
  "risk_score": 0.85,
  "review_required": true,
  "required_additional_fields": ["TIN", "DOB"]
}
```

### 2. **Объяснения решения**
```json
{
  "decision_reasons": [
    "strong_smartfilter_signal",
    "person_evidence_strong", 
    "id_exact_match",
    "dob_match"
  ]
}
```

### 3. **Детальная информация**
```json
{
  "decision_details": {
    "score_breakdown": {...},
    "evidence_strength": {...},
    "normalized_features": {...}
  }
}
```

---

## 📋 **Матрица решений для бизнеса**

### 🚫 **РЕДЖЕКТ (Блокировать платеж)**

**Условия:**
- `risk_level = "high"` **И** `risk_score >= 0.85`
- `review_required = false` (нет необходимости в дополнительных данных)

**Примеры полей:**
```json
{
  "risk_level": "high",
  "risk_score": 0.92,
  "review_required": false,
  "required_additional_fields": [],
  "decision_reasons": [
    "strong_smartfilter_signal",
    "person_evidence_strong",
    "id_exact_match",
    "dob_match"
  ]
}
```

**Бизнес-логика:** Система на 100% уверена в совпадении с санкционным списком. Все необходимые данные (TIN/DOB) уже есть.

---

### ⚠️ **ЗАПРОС ДОПОЛНИТЕЛЬНЫХ ДАННЫХ**

**Условия:**
- `risk_level = "high"` **И** `risk_score >= 0.85`
- `review_required = true` **И** `required_additional_fields` не пустой

**Примеры полей:**
```json
{
  "risk_level": "high", 
  "risk_score": 0.87,
  "review_required": true,
  "required_additional_fields": ["TIN", "DOB"],
  "decision_reasons": [
    "strong_smartfilter_signal",
    "person_evidence_strong"
  ]
}
```

**Бизнес-логика:** Система видит сильное совпадение имени, но не хватает TIN или DOB для окончательного решения. Нужно запросить недостающие данные.

---

### ✅ **ПРОПУСТИТЬ ПЛАТЕЖ**

**Условия:**
- `risk_level = "low"` **ИЛИ** `risk_level = "medium"`
- `review_required = false`

**Примеры полей:**
```json
{
  "risk_level": "low",
  "risk_score": 0.35,
  "review_required": false,
  "required_additional_fields": [],
  "decision_reasons": [
    "Overall risk score: 0.350"
  ]
}
```

**Бизнес-логика:** Риск низкий или средний, нет оснований для блокировки.

---

### ⏭️ **ПРОПУСТИТЬ ОБРАБОТКУ (SKIP)**

**Условия:**
- `risk_level = "skip"`

**Примеры полей:**
```json
{
  "risk_level": "skip",
  "risk_score": 0.0,
  "review_required": false,
  "required_additional_fields": [],
  "decision_reasons": ["smartfilter_skip"]
}
```

**Бизнес-логика:** Smart Filter определил, что текст не содержит персональных данных (например, "тест" или технические сообщения).

---

## 🔍 **Детальная интерпретация полей**

### **risk_level** - Уровень риска
- **"high"** = Высокий риск (score ≥ 0.85)
- **"medium"** = Средний риск (0.5 ≤ score < 0.85)  
- **"low"** = Низкий риск (score < 0.5)
- **"skip"** = Пропустить обработку

### **risk_score** - Числовая оценка риска (0.0 - 1.0)
- **0.85+** = Критический риск
- **0.5-0.84** = Средний риск
- **0.0-0.49** = Низкий риск

### **review_required** - Требуется ли ручная проверка
- **true** = Нужны дополнительные данные (TIN/DOB)
- **false** = Достаточно данных для автоматического решения

### **required_additional_fields** - Какие поля нужно запросить
- **["TIN"]** = Нужен ИНН/ЄДРПОУ
- **["DOB"]** = Нужна дата рождения
- **["TIN", "DOB"]** = Нужны оба поля
- **[]** = Дополнительные поля не нужны

### **decision_reasons** - Причины решения
- **"strong_smartfilter_signal"** = Smart Filter видит персональные данные
- **"person_evidence_strong"** = Сильное совпадение с персоной
- **"org_evidence_strong"** = Сильное совпадение с организацией
- **"id_exact_match"** = Точное совпадение ID (TIN/паспорт)
- **"dob_match"** = Совпадение даты рождения
- **"high_vector_similarity"** = Высокое векторное сходство
- **"id_exact_match"** = Точное совпадение идентификатора

---

## 🎯 **Практические сценарии для бизнеса**

### **Сценарий 1: Полный реджект**
```json
{
  "risk_level": "high",
  "risk_score": 0.95,
  "review_required": false,
  "required_additional_fields": [],
  "decision_reasons": [
    "strong_smartfilter_signal",
    "person_evidence_strong", 
    "id_exact_match",
    "dob_match"
  ]
}
```
**Действие:** Немедленно заблокировать платеж. Все данные подтверждают совпадение.

### **Сценарий 2: Запрос TIN**
```json
{
  "risk_level": "high",
  "risk_score": 0.88,
  "review_required": true,
  "required_additional_fields": ["TIN"],
  "decision_reasons": [
    "strong_smartfilter_signal",
    "person_evidence_strong",
    "dob_match"
  ]
}
```
**Действие:** Запросить у клиента ИНН для окончательного решения.

### **Сценарий 3: Запрос DOB**
```json
{
  "risk_level": "high", 
  "risk_score": 0.86,
  "review_required": true,
  "required_additional_fields": ["DOB"],
  "decision_reasons": [
    "strong_smartfilter_signal",
    "person_evidence_strong",
    "id_exact_match"
  ]
}
```
**Действие:** Запросить у клиента дату рождения для окончательного решения.

### **Сценарий 4: Пропуск платежа**
```json
{
  "risk_level": "low",
  "risk_score": 0.25,
  "review_required": false,
  "required_additional_fields": [],
  "decision_reasons": [
    "Overall risk score: 0.250"
  ]
}
```
**Действие:** Пропустить платеж, риск минимальный.

### **Сценарий 5: Пропуск обработки**
```json
{
  "risk_level": "skip",
  "risk_score": 0.0,
  "review_required": false,
  "required_additional_fields": [],
  "decision_reasons": ["smartfilter_skip"]
}
```
**Действие:** Не обрабатывать (техническое сообщение без персональных данных).

---

## ⚙️ **Настройка порогов (для техподдержки)**

Пороги можно настроить через переменные окружения:

```bash
# Пороги риска
AI_DECISION__THR_HIGH=0.85    # Высокий риск
AI_DECISION__THR_MEDIUM=0.5   # Средний риск

# Веса компонентов
AI_DECISION__W_SMARTFILTER=0.25
AI_DECISION__W_PERSON=0.3
AI_DECISION__W_ORG=0.15
AI_DECISION__W_SIMILARITY=0.25

# Бонусы за точные совпадения
AI_DECISION__BONUS_DATE_MATCH=0.07
AI_DECISION__BONUS_ID_MATCH=0.15
```

---

## 🚨 **Критические поля для мониторинга**

Для мониторинга системы отслеживайте:

1. **Частоту высокого риска:** `risk_level = "high"`
2. **Запросы дополнительных данных:** `review_required = true`
3. **Пропуски обработки:** `risk_level = "skip"`
4. **Ошибки обработки:** `success = false`

---

## 📊 **Примеры для интеграции**

### **JavaScript/Node.js**
```javascript
function makeDecision(apiResponse) {
  const { risk_level, review_required, required_additional_fields } = apiResponse;
  
  if (risk_level === 'high' && !review_required) {
    return { action: 'REJECT', reason: 'High risk confirmed' };
  }
  
  if (risk_level === 'high' && review_required) {
    return { 
      action: 'REQUEST_DATA', 
      fields: required_additional_fields,
      reason: 'Need additional verification'
    };
  }
  
  if (risk_level === 'low' || risk_level === 'medium') {
    return { action: 'APPROVE', reason: 'Low risk' };
  }
  
  if (risk_level === 'skip') {
    return { action: 'SKIP', reason: 'No personal data detected' };
  }
}
```

### **Python**
```python
def make_decision(api_response):
    risk_level = api_response['risk_level']
    review_required = api_response['review_required']
    required_fields = api_response['required_additional_fields']
    
    if risk_level == 'high' and not review_required:
        return {'action': 'REJECT', 'reason': 'High risk confirmed'}
    
    if risk_level == 'high' and review_required:
        return {
            'action': 'REQUEST_DATA',
            'fields': required_fields,
            'reason': 'Need additional verification'
        }
    
    if risk_level in ['low', 'medium']:
        return {'action': 'APPROVE', 'reason': 'Low risk'}
    
    if risk_level == 'skip':
        return {'action': 'SKIP', 'reason': 'No personal data detected'}
```

---

## 🎯 **Итоговая таблица решений**

| risk_level | review_required | required_additional_fields | Действие |
|------------|-----------------|---------------------------|----------|
| high | false | [] | 🚫 **РЕДЖЕКТ** |
| high | true | ["TIN"] | ⚠️ **ЗАПРОС TIN** |
| high | true | ["DOB"] | ⚠️ **ЗАПРОС DOB** |
| high | true | ["TIN", "DOB"] | ⚠️ **ЗАПРОС TIN+DOB** |
| medium | false | [] | ✅ **ПРОПУСТИТЬ** |
| low | false | [] | ✅ **ПРОПУСТИТЬ** |
| skip | false | [] | ⏭️ **ПРОПУСТИТЬ ОБРАБОТКУ** |

Эта логика обеспечивает **детерминистические** и **объяснимые** решения для всех платежей.


fff

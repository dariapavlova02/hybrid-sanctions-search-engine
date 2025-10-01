# Smart TIN/DOB Requirement Logic

## ✅ Улучшенная логика - требовать только недостающие поля

### Сценарии работы:

#### 1. HIGH RISK + Нет TIN/DOB в запросе
**Запрос**: "Сергій Олійник"
**Результат**:
```json
{
  "review_required": true,
  "required_additional_fields": ["TIN", "DOB"]
}
```

#### 2. HIGH RISK + Есть TIN в запросе
**Запрос**: "Сергій Олійник ІПН 1234567890"
**Результат**:
```json
{
  "review_required": true,
  "required_additional_fields": ["DOB"]
}
```

#### 3. HIGH RISK + Есть DOB в запросе
**Запрос**: "Сергій Олійник дата народження 01.01.1990"
**Результат**:
```json
{
  "review_required": true,
  "required_additional_fields": ["TIN"]
}
```

#### 4. HIGH RISK + Есть и TIN и DOB
**Запрос**: "Сергій Олійник ІПН 1234567890 дата народження 01.01.1990"
**Результат**:
```json
{
  "review_required": false,
  "required_additional_fields": []
}
```

#### 5. LOW RISK
**Запрос**: "Джон Сміт"
**Результат**:
```json
{
  "review_required": false,
  "required_additional_fields": []
}
```

## Изменения в коде

### 1. Понижен порог срабатывания
```python
# Было: слишком высокий порог
inp.signals.person_confidence >= 0.8

# Стало: реалистичный порог
inp.signals.person_confidence >= 0.6
```

### 2. Добавлена логика санкций
```python
# Если HIGH RISK из-за санкций - всегда считать strong match
has_sanctions_match = (
    inp.search and inp.search.total_matches > 0 and
    (inp.search.has_exact_matches or inp.search.high_confidence_matches > 0)
)
```

### 3. Умная логика требования полей
```python
# Определить какие поля отсутствуют
required_fields = []
if not has_tin_evidence:
    required_fields.append('TIN')
if not has_dob_evidence:
    required_fields.append('DOB')

# Если есть и TIN и DOB - ничего не требовать
if has_tin_evidence and has_dob_evidence:
    return False, []

# Требовать только недостающие поля
return True, required_fields
```

## Детекция TIN/DOB в тексте

Система ищет в тексте:
- **TIN**: ІПН, ИНН, EDRPOU, TIN, налоговый номер
- **DOB**: дата рождения, дата народження, DOB, born, р. XX.XX.XXXX

## Deployment

Файл: `tin_dob_improved_logic.tar.gz`

После развертывания система будет умно требовать только те поля, которых реально нет в исходном запросе!
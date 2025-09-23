# Бизнес-логика принятия решения в AI Service

## Общая архитектура

```
Входные данные → Decision Engine → Выходные данные
     ↓              ↓              ↓
DecisionInput → DecisionEngine → DecisionOutput
```

## Детальная схема принятия решения

### 1. Входные данные (DecisionInput)
```
┌─────────────────────────────────────────┐
│ DecisionInput                           │
├─────────────────────────────────────────┤
│ • text: str                            │
│ • language: str                        │
│ • smartfilter: SmartFilterInfo         │
│ • signals: SignalsInfo                 │
│ • similarity: SimilarityInfo           │
│ • search: SearchInfo (опционально)     │
└─────────────────────────────────────────┘
```

### 2. Основной процесс принятия решения

```
┌─────────────────────────────────────────────────────────────────┐
│                        DecisionEngine.decide()                  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. Проверка Smart Filter                                       │
│    • should_process = True?                                    │
│    • Если False → SKIP (score=0.0)                             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Безопасное извлечение данных                               │
│    • _safe_smartfilter()                                      │
│    • _safe_signals()                                          │
│    • _safe_similarity()                                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Расчет взвешенного скора                                   │
│    _calculate_weighted_score()                                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Определение уровня риска                                   │
│    _determine_risk_level()                                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Генерация причин                                            │
│    _generate_reasons()                                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. Извлечение деталей                                          │
│    _extract_details()                                         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. Проверка бизнес-правил                                     │
│    _should_request_additional_fields()                         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. Возврат результата                                         │
│    DecisionOutput                                              │
└─────────────────────────────────────────────────────────────────┘
```

## Формула расчета скора

### Базовые компоненты
```
score = w_smartfilter * smartfilter.confidence +
        w_person * person_confidence +
        w_org * org_confidence +
        w_similarity * similarity_value +
        search_contribution +
        bonus_factors
```

### Компоненты поиска (SearchInfo)
```
search_contribution = 0.0

# Exact matches (высший приоритет)
if has_exact_matches and exact_confidence >= thr_search_exact:
    search_contribution += w_search_exact * exact_confidence

# Phrase matches
if has_phrase_matches and phrase_confidence >= thr_search_phrase:
    search_contribution += w_search_phrase * phrase_confidence

# N-gram matches
if has_ngram_matches and ngram_confidence >= thr_search_ngram:
    search_contribution += w_search_ngram * ngram_confidence

# Vector matches
if has_vector_matches and vector_confidence >= thr_search_vector:
    search_contribution += w_search_vector * vector_confidence

# Бонусы (только если есть хотя бы один компонент поиска)
if search_components_added:
    if exact_confidence >= 0.95:
        search_contribution += bonus_exact_match
    if total_matches > 1:
        search_contribution += bonus_multiple_matches
    if high_confidence_matches > 0:
        search_contribution += bonus_high_confidence
```

### Бонусные факторы
```
if date_match:
    score += bonus_date_match
if id_match:
    score += bonus_id_match
```

## Уровни риска

```
┌─────────────────────────────────────────────────────────────────┐
│                    Уровни риска                                │
├─────────────────────────────────────────────────────────────────┤
│ HIGH:   score >= thr_high (по умолчанию 0.85)                 │
│ MEDIUM: thr_medium <= score < thr_high (по умолчанию 0.5-0.85)│
│ LOW:    score < thr_medium (по умолчанию < 0.5)               │
│ SKIP:   smartfilter.should_process = False                     │
└─────────────────────────────────────────────────────────────────┘
```

## Бизнес-правила (TIN/DOB Gate)

### Условия применения
```
1. require_tin_dob_gate = True (включен)
2. risk = HIGH (высокий риск)
3. has_strong_name_match = True (сильное совпадение имени)
```

### Логика проверки
```
has_strong_name_match = (
    person_confidence >= 0.8 OR
    org_confidence >= 0.8 OR
    similarity_cos_top >= 0.8
)

has_tin = id_match OR 'inn' in evidence.extracted_ids
has_dob = date_match OR 'dob' in evidence.extracted_dates

# Исключение: если в санкционной записи нет ни TIN, ни DOB
sanction_has_no_identifiers = (
    'sanction_record' in evidence AND
    NOT evidence.sanction_record.has_tin AND
    NOT evidence.sanction_record.has_dob
)

if sanction_has_no_identifiers:
    return False, []  # Не требуем дополнительные поля

# Требуем недостающие поля
if not has_tin:
    required_fields.append('TIN')
if not has_dob:
    required_fields.append('DOB')

return True, required_fields
```

## Конфигурация (DecisionConfig)

### Веса компонентов (по умолчанию)
```
w_smartfilter = 0.25      # Вес Smart Filter
w_person = 0.3            # Вес персональных данных
w_org = 0.15              # Вес организационных данных
w_similarity = 0.25       # Вес векторного сходства
```

### Веса поиска (по умолчанию)
```
w_search_exact = 0.4      # Вес точных совпадений
w_search_phrase = 0.25    # Вес фразовых совпадений
w_search_ngram = 0.2      # Вес N-gram совпадений
w_search_vector = 0.15    # Вес векторных совпадений
```

### Пороги поиска (по умолчанию)
```
thr_search_exact = 0.8    # Порог точных совпадений
thr_search_phrase = 0.7   # Порог фразовых совпадений
thr_search_ngram = 0.6    # Порог N-gram совпадений
thr_search_vector = 0.5   # Порог векторных совпадений
```

### Бонусы (по умолчанию)
```
bonus_date_match = 0.07           # Бонус за совпадение даты
bonus_id_match = 0.15             # Бонус за совпадение ID
bonus_exact_match = 0.2           # Бонус за точное совпадение
bonus_multiple_matches = 0.1      # Бонус за множественные совпадения
bonus_high_confidence = 0.05      # Бонус за высокую уверенность
```

### Пороги риска (по умолчанию)
```
thr_high = 0.85    # Порог высокого риска
thr_medium = 0.5   # Порог среднего риска
```

## Выходные данные (DecisionOutput)

```
┌─────────────────────────────────────────────────────────────────┐
│ DecisionOutput                                                  │
├─────────────────────────────────────────────────────────────────┤
│ • risk: RiskLevel (HIGH/MEDIUM/LOW/SKIP)                       │
│ • score: float (0.0-1.0)                                       │
│ • reasons: List[str] (человекочитаемые причины)                │
│ • details: Dict[str, Any] (детальная информация)               │
│ • review_required: bool (требуется ли ручная проверка)         │
│ • required_additional_fields: List[str] (требуемые поля)       │
└─────────────────────────────────────────────────────────────────┘
```

## Детальная информация (details)

### Структура details
```
{
    "calculated_score": float,
    "score_breakdown": {
        "smartfilter_contribution": float,
        "person_contribution": float,
        "org_contribution": float,
        "similarity_contribution": float,
        "search_contribution": float,
        "date_bonus": float,
        "id_bonus": float,
        "total": float
    },
    "weights_used": {...},
    "thresholds": {...},
    "normalized_features": {...},
    "evidence_strength": {...},
    "input_signals": {...},
    "search_info": {...},
    "similarity": {...},
    "smartfilter": {...}
}
```

## Особенности реализации

### 1. Безопасность данных
- Все входные данные проверяются на None
- Используются безопасные значения по умолчанию
- Graceful degradation при отсутствии данных

### 2. Конфигурируемость
- Все веса и пороги настраиваются через ENV переменные
- Формат: `AI_DECISION__<PARAMETER_NAME>=<value>`
- Hot-reload поддержка для SearchConfig

### 3. Мониторинг и метрики
- Регистрация метрик для Prometheus
- Логирование на DEBUG уровне
- Детальная трассировка решений

### 4. Производительность
- Детерминистические вычисления
- Минимальные внешние зависимости
- Эффективная обработка больших объемов данных

## Примеры решений

### Пример 1: Высокий риск
```
Input: "Иван Петров" + strong person_confidence + exact_match
Score: 0.25*0.9 + 0.3*0.95 + 0.4*0.98 + 0.15 = 0.89
Risk: HIGH (0.89 >= 0.85)
Review: Required (missing TIN/DOB)
```

### Пример 2: Средний риск
```
Input: "Петров И." + medium person_confidence + phrase_match
Score: 0.25*0.7 + 0.3*0.6 + 0.25*0.75 = 0.51
Risk: MEDIUM (0.5 <= 0.51 < 0.85)
Review: Not required
```

### Пример 3: Низкий риск
```
Input: "Сидоров" + low confidence + no matches
Score: 0.25*0.3 + 0.3*0.2 = 0.135
Risk: LOW (0.135 < 0.5)
Review: Not required
```

### Пример 4: Пропуск
```
Input: "тест" + smartfilter.should_process = False
Risk: SKIP
Score: 0.0
Review: Not required
```

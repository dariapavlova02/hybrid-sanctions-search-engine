# Golden Parity - План Исправлений

## Критические Проблемы (Parity 0%)

### 1. Морфология - Склонение в Именительный Падеж

**Проблемные тесты:**
- `ru_declension_to_nominative`: "платёж Ивану Петрову" → должно быть "Иван Петров"
- `uk_declension`: "переказ Олені Петренко" → должно быть "Олена Петренко"

**Текущее поведение:**
- Legacy: ✅ Правильно склоняет в именительный падеж
- Factory: ❌ Сохраняет исходные падежи

**Решение:**
```python
# В MorphologyProcessor добавить:
def normalize_to_nominative(self, tokens: List[Token], language: str) -> List[Token]:
    if language in ['ru', 'uk']:
        for token in tokens:
            if token.role in ['given', 'surname', 'patronymic']:
                # Использовать pymorphy3 для склонения в именительный падеж
                token.lemma = self.morphology_adapter.get_nominative(token.lemma, language)
    return tokens
```

### 2. Уменьшительные Имена

**Проблемные тесты:**
- `ru_diminutive`: "Сашка Пушкин" → должно быть "Александр Пушкин"
- `uk_diminutive`: "Петрик Шевченко" → должно быть "Петро Шевченко"

**Текущее поведение:**
- Legacy: ✅ Расширяет уменьшительные имена
- Factory: ❌ Сохраняет уменьшительные формы

**Решение:**
```python
# В DiminutiveResolver добавить:
def expand_diminutives(self, tokens: List[Token], language: str) -> List[Token]:
    for token in tokens:
        if token.role == 'given' and language in ['ru', 'uk']:
            full_name = self.resolve_diminutive(token.lemma, language)
            if full_name:
                token.lemma = full_name
    return tokens
```

## Высокий Приоритет (Parity 20-50%)

### 3. Контекстная Фильтрация

**Проблемные тесты:**
- `ru_context_words`: "получатель: гражданин РФ Петр Сергеев" → должно быть "Петр Сергеев"
- `uk_initials_preposition`: "з О. Іваненко" → должно быть "О. Іваненко"

**Решение:**
```python
# В RoleTagger добавить фильтрацию контекстных слов:
CONTEXT_WORDS = {
    'ru': ['получатель', 'гражданин', 'рф', 'платёж', 'переказ'],
    'uk': ['з', 'від', 'для', 'до']
}

def filter_context_words(self, tokens: List[Token], language: str) -> List[Token]:
    context_words = CONTEXT_WORDS.get(language, set())
    return [t for t in tokens if t.lemma.lower() not in context_words]
```

### 4. Английская Обработка

**Проблемные тесты:**
- `en_title_suffix`: "Dr. John A. Smith Jr." → должно быть "John Smith"
- `en_nickname`: "Bill Gates" → должно быть "William Gates"
- `en_apostrophe`: "O'Connor, Sean" → должно быть "Sean O'Connor"

**Решение:**
```python
# Добавить EnglishProcessor:
class EnglishProcessor:
    TITLES = {'dr', 'mr', 'mrs', 'ms', 'prof', 'sir', 'lady'}
    SUFFIXES = {'jr', 'sr', 'ii', 'iii', 'iv'}
    NICKNAMES = {'bill': 'william', 'bob': 'robert', 'dick': 'richard'}
    
    def process_english_name(self, tokens: List[Token]) -> List[Token]:
        # Удалить титулы и суффиксы
        # Расширить никнеймы
        # Нормализовать апострофы
        pass
```

## Средний Приоритет (Parity 50-75%)

### 5. Сложные Случаи

**Проблемные тесты:**
- `mixed_org_noise`: Организационные токены не фильтруются
- `uk_passport`: Документные контексты не удаляются
- `mixed_diacritics`: Диакритические знаки не нормализуются

**Решение:**
```python
# Улучшить ORG_ACRONYMS фильтрацию:
ORG_ACRONYMS = {
    'ru': {'ооо', 'зао', 'оао', 'пао', 'ао', 'ип', 'чп', 'фоп', 'тов', 'пп'},
    'uk': {'тзов', 'пп', 'фоп', 'пв', 'ат'},
    'en': {'llc', 'ltd', 'inc', 'corp', 'co', 'gmbh', 'srl', 'spa', 'bv', 'nv'}
}

# Добавить фильтрацию документных контекстов:
DOCUMENT_PATTERNS = [
    r'паспорт\s+\w+',
    r'документ\s+\w+',
    r'серія\s+\w+',
    r'номер\s+\w+'
]
```

## Низкий Приоритет (Parity 75%+)

### 6. Поведенческие Тесты

**Хорошо работающие тесты:**
- `behavior_idempotent`: Идемпотентность
- `behavior_unknown_preserve`: Сохранение неизвестных токенов
- `behavior_case_policy`: Политика регистра
- `behavior_empty_input`: Пустой ввод

**Эти тесты показывают, что базовая функциональность работает корректно.**

## План Реализации

### Неделя 1: Морфология
- [ ] Реализовать склонение в именительный падеж
- [ ] Добавить расширение уменьшительных имен
- [ ] Протестировать на ru/uk кейсах

### Неделя 2: Контекстная Фильтрация
- [ ] Улучшить фильтрацию контекстных слов
- [ ] Добавить обработку предлогов
- [ ] Протестировать на mixed кейсах

### Неделя 3: Английская Обработка
- [ ] Реализовать удаление титулов и суффиксов
- [ ] Добавить обработку никнеймов
- [ ] Нормализовать апострофы

### Неделя 4: Финальная Валидация
- [ ] Повторный запуск golden parity тестов
- [ ] Достижение 90%+ parity
- [ ] Производительное тестирование

## Ожидаемые Результаты

После реализации всех исправлений:
- **Parity Rate**: 90%+ (с 58.1%)
- **Производительность**: Сохранить текущее ускорение 1.9x
- **Покрытие**: Все языки (ru, uk, en, mixed)
- **Качество**: Соответствие golden cases ожиданиям

# Golden Test Runner - Top Deltas Analysis Report

## 📊 Summary Statistics

- **Total cases**: 31
- **Parity rate**: 48.4% (15/31)
- **Legacy accuracy**: 41.9% (13/31)
- **Factory accuracy**: 35.5% (11/31)
- **Divergent cases**: 16
- **Success rates**: Legacy 100%, Factory 100%

## 🔍 Top 5 Critical Deltas

### 1. ru_diminutive (Сашка Пушкин)
- **Input**: Сашка Пушкин
- **Expected**: Александр Пушкин
- **Legacy**: Александр Пушкин *(diminutive_dict; morph)*
- **Factory**: Сашка Пушкин *(role_classification:given; role_classification:surname)*
- **Issue**: Factory не применяет diminutive expansion
- **Impact**: HIGH - теряется нормализация уменьшительных форм

### 2. ru_initials (Иванов И.И.)
- **Input**: Иванов И.И.
- **Expected**: Иванов И. И.
- **Legacy**: Иванов И. И. *(morph; initial_cleanup; initial_cleanup)*
- **Factory**: Иванов *(role_classification:surname; passthrough)*
- **Issue**: Factory теряет инициалы
- **Impact**: HIGH - критическая потеря данных

### 3. ru_context_words (получатель: гражданин РФ Петр Сергеев)
- **Input**: получатель: гражданин РФ Петр Сергеев
- **Expected**: Петр Сергеев
- **Legacy**: гражданин Петр Сергеев *(morph; morph_case_adjusted_given; diminutive_dict; morph)*
- **Factory**: Гражданин Пётр Сергеев *(passthrough; role_classification:given; role_classification:surname; dedup_consecutive_person_tokens; dedup_consecutive_person_tokens)*
- **Issue**: Factory не фильтрует контекстные слова
- **Impact**: MEDIUM - загрязнение вывода

### 4. uk_feminine_suffix (Наталія Ковальська)
- **Input**: Наталія Ковальська
- **Expected**: Наталія Ковальська
- **Legacy**: Наталія Ковальсько *(diminutive_dict; invariable_nominative)*
- **Factory**: Наталія Ковальська *(role_classification:given; role_classification:surname)*
- **Issue**: Legacy неправильно склоняет женскую фамилию
- **Impact**: MEDIUM - ошибка в морфологии

### 5. en_nickname (Bill Gates)
- **Input**: Bill Gates
- **Expected**: William Gates
- **Legacy**: William Gates *(english_nickname; capitalize)*
- **Factory**: Gates *(passthrough; role_classification:given)*
- **Issue**: Factory не применяет nickname expansion
- **Impact**: HIGH - теряется нормализация никнеймов

## 📈 Trace Pattern Analysis

### Legacy Trace Patterns
- **morph**: Морфологическая обработка
- **diminutive_dict**: Словарь уменьшительных форм
- **initial_cleanup**: Очистка инициалов
- **english_nickname**: Английские никнеймы
- **invariable_nominative**: Неизменяемый именительный падеж

### Factory Trace Patterns
- **role_classification**: Классификация ролей токенов
- **passthrough**: Пропуск без обработки
- **dedup_consecutive_person_tokens**: Дедупликация персональных токенов

## 🎯 Key Issues Identified

1. **Diminutive Processing**: Factory не применяет словарь уменьшительных форм
2. **Initials Handling**: Factory теряет инициалы при обработке
3. **Context Filtering**: Factory не фильтрует контекстные слова
4. **Nickname Expansion**: Factory не расширяет никнеймы
5. **Morphology Differences**: Разные подходы к морфологической обработке

## 📋 Recommendations

1. **Implement diminutive processing** в Factory pipeline
2. **Add initials preservation** в Factory pipeline
3. **Implement context word filtering** в Factory pipeline
4. **Add nickname expansion** в Factory pipeline
5. **Align morphology processing** между Legacy и Factory

## 📁 Generated Files

- `out/golden_diff_updated.csv` - Detailed CSV report with trace information
- `out/golden_analysis_report.md` - This analysis report

## 🔧 Usage

```bash
# Run golden test runner
python tools/golden_runner.py --report out/golden_diff.csv --top-deltas 20

# View CSV report
head -20 out/golden_diff_updated.csv
```

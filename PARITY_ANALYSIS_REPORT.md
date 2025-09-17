# Legacy vs Factory Parity Analysis Report

## Executive Summary

Проведен комплексный анализ расхождений между legacy NormalizationService и новой NormalizationFactory на базе 31 golden test case. Выявлен существенный gap в совместимости, требующий целенаправленных улучшений.

## Key Metrics

| Метрика | Значение | Цель |
|---------|----------|------|
| **Parity Rate** | 48.4% (15/31) | 90%+ |
| **Legacy Accuracy** | 41.9% (13/31) | Baseline |
| **Factory Accuracy** | 29.0% (9/31) | 80%+ |
| **Success Rate Legacy** | 100.0% | Maintain |
| **Success Rate Factory** | 96.8% | 100% |
| **Performance Legacy** | 1.2ms avg | Baseline |
| **Performance Factory** | 93.3ms avg | <10ms |

## Divergence Analysis

### 🔴 Critical Issues (16 divergent cases)

**1. Tokenization Problems (5 cases)**
- Double dots in initials: `И..` instead of `И.`
- Hyphenated names broken: `Петров-сидорова` vs `Петрова-Сидорова`
- Context words leaking: organization names in output
- Case policy inconsistencies

**2. Morphology Issues (4 cases)**
- Diminutive expansion failing: `Сашк` instead of `Александр`
- Gender-based morphology: female surnames incorrectly processed
- Declension not working properly

**3. Unicode & Character Handling (2 cases)**
- Apostrophes removed or processed incorrectly
- Homoglyph detection not working

**4. Multiple Person Handling (2 cases)**
- No separator insertion: missing ` | ` between persons
- Gender agreement issues across persons

**5. Unknown Category (3 cases)**
- Complex edge cases requiring individual analysis

## Priority Improvement Plan

### 🚨 Priority 1: Critical Tokenization Fixes

**1.1 Fix Double Dots in Initials**
- **Problem**: `И..` instead of `И.`
- **Cases**: ru_initials, uk_initials_preposition
- **Root Cause**: TokenProcessor expansion logic
- **Effort**: Low (1-2 days)
- **Impact**: High

**1.2 Fix Context Word Filtering**
- **Problem**: Stop words and organization names leaking
- **Cases**: mixed_org_noise, ru_context_words
- **Root Cause**: RoleClassifier not filtering properly
- **Effort**: High (1 week)
- **Impact**: High

### 🔥 Priority 2: Morphology Improvements

**2.1 Fix Diminutive Name Expansion**
- **Problem**: `Сашк` instead of `Александр`
- **Cases**: ru_diminutive
- **Root Cause**: Diminutive dictionary integration
- **Effort**: Medium (3-4 days)
- **Impact**: High

**2.2 Fix Gender-Based Morphology**
- **Problem**: Female surname forms incorrect
- **Cases**: uk_feminine_suffix
- **Root Cause**: Gender inference and adjustment
- **Effort**: Medium (3-4 days)
- **Impact**: Medium

### 🛠️ Priority 3: Secondary Fixes

**3.1 Hyphenated Name Tokenization**
- **Cases**: ru_hyphenated_surname
- **Effort**: Low (1 day)

**3.2 Apostrophe Normalization**
- **Cases**: ru_apostrophe, en_apostrophe
- **Effort**: Low (1 day)

## Detailed Case Analysis

### Factory Better Than Legacy (1 case)
- `uk_feminine_suffix`: Factory correctly preserves `Ковальська`, legacy converts to `Ковальсько`

### Legacy Better Than Factory (5 cases)
- `ru_diminutive`: Legacy correctly expands `Сашка → Александр`
- `ru_initials`: Legacy formats `И. И.` properly
- `ru_hyphenated_surname`: Legacy preserves case in `Петрова-Сидорова`
- `uk_initials_preposition`: Legacy formats `О.` correctly
- `uk_dob`: Legacy filters date properly

### Both Wrong (10 cases)
- Multiple person handling
- Context word filtering
- Title/suffix removal
- Complex morphology cases

## Performance Concerns

**Factory is 80x slower** than legacy (93ms vs 1.2ms):
- Legacy морфология оптимизирована
- Factory создает дополнительные объекты и слои
- Необходима профилировка и оптимизация

## Strategic Recommendations

### Immediate Actions (Week 1-2)
1. **Fix double dots bug** - простой и высокоэффектный фикс
2. **Improve diminutive handling** - критично для пользователей
3. **Profile performance** - понять bottlenecks

### Short Term (Month 1)
1. **Complete Priority 1-2 fixes**
2. **Add performance benchmarks**
3. **Implement incremental rollout with feature flags**
4. **Expand test coverage for edge cases**

### Long Term (Quarter 1)
1. **Achieve 90%+ parity rate**
2. **Performance optimization to <10ms**
3. **Consider hybrid approach for complex cases**
4. **Full migration planning**

## Risk Assessment

### High Risk
- **Performance regression**: 80x slower unacceptable for production
- **Accuracy regression**: 29% vs 42% factory worse than legacy
- **User-visible bugs**: diminutives, initials affect user experience

### Medium Risk
- **Context filtering**: organization names leaking into results
- **Multiple person handling**: affects structured data extraction

### Low Risk
- **Unicode edge cases**: rare scenarios
- **Title/suffix handling**: primarily English names

## Next Steps

1. **Implement Priority 1 fixes** (tokenization)
2. **Set up continuous parity monitoring**
3. **Create performance benchmarking suite**
4. **Plan gradual feature flag rollout**
5. **Establish parity regression tests**

## Conclusion

Текущий gap между legacy и factory significant, но addressable. Основные проблемы сосредоточены в tokenization и morphology layers. При фокусе на Priority 1-2 фиксах можно достичь приемлемого уровня parity в течение месяца.

**Recommendation**: Proceed with factory development but maintain legacy as fallback until 90%+ parity achieved.
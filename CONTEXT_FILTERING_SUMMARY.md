# Context Filtering Improvements Summary

## Issues Fixed

### 1. Payment Context Misclassification
**Problem:** "Сплата" (payment) was being classified as `given` name

**Solution:** Added "сплата" to all payment lexicons
- `data/lexicons/payment_context.txt`
- `src/ai_service/data/dicts/stopwords.py` - STOP_ALL
- `src/ai_service/layers/variants/templates/lexicon.py` - PAYMENT_CONTEXT and STOPWORDS_*

### 2. Insurance Context Misclassification
**Problem:** Insurance terms were being classified as names:
- "Страховий" (insurance) → `given` name
- "поліс" (policy) → `surname`

**Solution:** Added comprehensive insurance terms:
- страховий, поліс, ОСЦПВ, ОСАГО, КАСКО, страхування, страхование, policy, insurance

### 3. Transport Context Misclassification
**Problem:** Transport terms were being classified as names:
- "Поповнення" (top-up) → `given` name
- "транспортної" (transport) → `surname`
- "карти" (cards) → person entity

**Solution:** Added comprehensive transport terms:
- транспорт, поповнення, карти, проїзд, поїздка, маршрут, автобус, метро, квиток, білет, проїзний

## Terms Added (Ukrainian/Russian/English)

### Payment Terms
- оплата, сплата, платіж, платеж
- рахунок, счет, invoice, bill
- переказ, перевод, transfer
- депозит, кредит, деbit

### Insurance Terms
- страховий/страховой, поліс/полис
- ОСЦПВ, ОСАГО, КАСКО
- страхування/страхование, insurance, policy

### Transport Terms
- транспорт, транспортна/транспортный
- поповнення/пополнение, карта/карти/карты
- проїзд/проезд, поїздка/поездка
- маршрут, автобус, тролейбус/троллейбус
- метро, електричка/электричка
- квиток/квитки, билет/билеты
- проїзний/проездной

## Files Modified

### Lexicon Files
1. `data/lexicons/payment_context.txt` - Main payment context terms
2. `src/ai_service/data/dicts/stopwords.py` - STOP_ALL universal stopwords
3. `src/ai_service/layers/variants/templates/lexicon.py` - PAYMENT_CONTEXT and STOPWORDS_* sets

### Applied to All Language Variants
- **Ukrainian**: платіж, поповнення, транспортна, карти, etc.
- **Russian**: платеж, пополнение, транспортная, карты, etc.
- **English**: payment, transport, card, ticket, etc.

## Expected Results

After these fixes, the following should be properly filtered instead of being classified as names:

### Payment Context
- ✅ "Сплата за послуги" → context words filtered
- ✅ "Платіж по рахунку" → context words filtered

### Insurance Context
- ✅ "Страховий платіж за поліс" → insurance terms filtered
- ✅ "ОСЦПВ код 123456" → insurance codes filtered

### Transport Context
- ✅ "Поповнення транспортної карти" → transport terms filtered
- ✅ "Проїзд метро 1000 грн" → transport terms filtered

## Testing

To verify the fixes work:

```bash
# Test payment context
curl -X POST 'http://95.217.84.234:8000/process' -d '{"text": "Сплата за послуги"}'

# Test insurance context
curl -X POST 'http://95.217.84.234:8000/process' -d '{"text": "Страховий платіж за поліс ОСЦПВ"}'

# Test transport context
curl -X POST 'http://95.217.84.234:8000/process' -d '{"text": "Поповнення транспортної карти 1000"}'
```

**Expected:** Context terms should be filtered out, only real names should remain in `normalized_text`.

## Commits

1. `fix(normalization): add "сплата" to payment context filters` - Payment word fix
2. `fix(normalization): add insurance context filtering` - Insurance terms
3. `fix(normalization): add transport context filtering` - Transport terms

## Impact

These changes prevent the system from incorrectly extracting business/service context as personal names, significantly improving precision in:

- ✅ Payment processing texts
- ✅ Insurance documents
- ✅ Transport/travel receipts
- ✅ Service invoices
- ✅ Financial transactions

The system now has comprehensive context filtering for major service domains while preserving accurate name extraction.
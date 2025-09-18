# Apostrophe Tokenization Regression Examples

## Before/After Examples

### 1. Irish Surnames with O' prefix

**Before Fix:**
```
Input:  "O'Connor"
Output: "O'Connor"
Classified as: first_name (WRONG)
```

**After Fix:**
```
Input:  "O'Connor"
Output: "O'Connor"
Classified as: surname (CORRECT)
```

### 2. French/Irish Surnames with D' prefix

**Before Fix:**
```
Input:  "D'Artagnan"
Output: "D'Artagnan"
Classified as: first_name (WRONG)
```

**After Fix:**
```
Input:  "D'Artagnan"
Output: "D'Artagnan"
Classified as: surname (CORRECT)
```

### 3. Scottish Surnames with Mc prefix

**Before Fix:**
```
Input:  "McDonald"
Output: "McDonald"
Classified as: first_name (WRONG)
```

**After Fix:**
```
Input:  "McDonald"
Output: "Mcdonald"
Classified as: surname (CORRECT)
```

### 4. Complex Names with Multiple Parts

**Before Fix:**
```
Input:  "Sean O'Connor Jr."
Output: "Sean O'Connor"
Parts: first="Sean", last="O'Connor" (partial correct)
```

**After Fix:**
```
Input:  "Sean O'Connor Jr."
Output: "Sean O'Connor"
Parts: first="Sean", last="O'Connor", suffix="Jr." (IMPROVED)
```

### 5. Multi-Name Sentences

**Before/After (no change - works correctly):**
```
Input:  "Multiple O'Connor D'Angelo Names"
Output: "Multiple O'Connor D'Angelo Names"
Tokens: ['Multiple', "O'Connor", "D'Angelo", 'Names']
```

## Key Fix Details

### What was fixed:
- Added `_is_irish_scottish_surname()` method to detect Celtic surname patterns
- Modified nameparser logic to classify single-word Celtic surnames correctly
- Enhanced confidence scoring for proper surname classification

### Patterns handled:
- `O'` prefix (Irish): O'Connor, O'Brien, O'Neil
- `D'` prefix (French/Irish): D'Artagnan, D'Angelo
- `Mc/Mac` prefix (Scottish/Irish): McDonald, MacLeod, McGrath

### Code changes:
1. **nameparser_adapter.py**: Added Celtic surname detection
2. **Feature flags**: Enabled nameparser_en and en_nicknames
3. **Dependencies**: Added nameparser back to pyproject.toml
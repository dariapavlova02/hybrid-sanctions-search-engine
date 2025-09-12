"""
Phonetic patterns for similar sounds
"""

PHONETIC_PATTERNS = {
    'ch': ['ch', 'tch', 'cz', 'tsch', 'ч', 'tsh', 'c'],
    'sh': ['sh', 'sch', 'sz', 's', 'ш', 'sj', 'x'],
    'zh': ['zh', 'j', 'g', 'z', 'ж', 'dj', 's'],
    'kh': ['kh', 'h', 'ch', 'x', 'х', 'q', 'k'],
    'ts': ['ts', 'tz', 'c', 'z', 'ц', 'ts', 't'],
    'yu': ['yu', 'iu', 'u', 'y', 'ю', 'ju', 'u'],
    'ya': ['ya', 'ia', 'a', 'ja', 'я', 'ia', 'a'],
    'th': ['th', 't', 'd', 'θ', 'ð'],
    'ng': ['ng', 'n', 'g', 'ŋ'],
    'ph': ['ph', 'f', 'p', 'ф'],
    'qu': ['qu', 'kw', 'k', 'q'],
    'wh': ['wh', 'w', 'hw', 'h'],
    'ck': ['ck', 'k', 'c', 'к'],
    'gh': ['gh', 'g', 'h', 'г'],
    'kn': ['kn', 'n', 'k', 'н'],
    'wr': ['wr', 'r', 'w', 'р'],
    'mb': ['mb', 'm', 'b', 'м'],
    'gn': ['gn', 'n', 'g', 'н'],
    'ps': ['ps', 's', 'p', 'с'],
    'pt': ['pt', 't', 'p', 'т']
}

# Additional phonetic rules for different languages
LANGUAGE_SPECIFIC_PATTERNS = {
    'uk': {
        'і': ['i', 'y', 'yi'],
        'ї': ['yi', 'i', 'y'],
        'є': ['ye', 'e', 'ie'],
        'ґ': ['g', 'h', 'gh']
    },
    'ru': {
        'ё': ['e', 'yo', 'io'],
        'ъ': ['', 'y', 'i'],
        'ь': ['', 'y', 'i']
    },
    'de': {
        'ä': ['ae', 'a', 'e'],
        'ö': ['oe', 'o', 'e'],
        'ü': ['ue', 'u', 'y'],
        'ß': ['ss', 's', 'sz']
    },
    'fr': {
        'é': ['e', 'ey', 'ay'],
        'è': ['e', 'eh', 'ay'],
        'ê': ['e', 'ey', 'ay'],
        'ç': ['c', 's', 'k']
    },
    'es': {
        'ñ': ['ny', 'n', 'ni'],
        'á': ['a', 'ah', 'aa'],
        'é': ['e', 'ey', 'ay'],
        'í': ['i', 'ee', 'y']
    },
    'pl': {
        'ą': ['a', 'on', 'an'],
        'ć': ['c', 'ch', 'ts'],
        'ę': ['e', 'en', 'in'],
        'ł': ['l', 'w', 'u']
    },
    'cs': {
        'á': ['a', 'aa', 'ah'],
        'é': ['e', 'ey', 'ay'],
        'í': ['i', 'ee', 'y'],
        'ů': ['u', 'oo', 'ou']
    }
}

# Combine all phonetic patterns
ALL_PHONETIC_PATTERNS = {**PHONETIC_PATTERNS}

# Add language-specific patterns
for lang, patterns in LANGUAGE_SPECIFIC_PATTERNS.items():
    for pattern, variants in patterns.items():
        if pattern not in ALL_PHONETIC_PATTERNS:
            ALL_PHONETIC_PATTERNS[pattern] = variants
        else:
            # Combine with existing ones
            ALL_PHONETIC_PATTERNS[pattern].extend(variants)
            ALL_PHONETIC_PATTERNS[pattern] = list(set(ALL_PHONETIC_PATTERNS[pattern]))

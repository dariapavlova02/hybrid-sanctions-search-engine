"""
Regional transliteration patterns for different countries
"""

# Ukrainian transliteration patterns
UKRAINIAN_PATTERNS = {
    'і': 'i',
    'ї': 'yi',
    'є': 'ye',
    'ґ': 'g',
    'І': 'I',
    'Ї': 'Yi',
    'Є': 'Ye',
    'Ґ': 'G'
}

# Russian transliteration patterns
RUSSIAN_PATTERNS = {
    'ё': 'e',
    'ъ': '',
    'ь': '',
    'Ё': 'E',
    'Ъ': '',
    'Ь': ''
}

# Common Cyrillic patterns
COMMON_CYRILLIC = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l',
    'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's',
    'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch',
    'ш': 'sh', 'щ': 'shch', 'ы': 'y', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E',
    'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L',
    'М': 'M', 'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S',
    'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch',
    'Ш': 'Sh', 'Щ': 'Shch', 'Ы': 'Y', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
}

# Regional standards
REGIONAL_STANDARDS = {
    'uk_standard': {**COMMON_CYRILLIC, **UKRAINIAN_PATTERNS},
    'ru_standard': {**COMMON_CYRILLIC, **RUSSIAN_PATTERNS},
    'gost_2000': {**COMMON_CYRILLIC, **RUSSIAN_PATTERNS},
    'iso_9': {**COMMON_CYRILLIC, **RUSSIAN_PATTERNS}
}

# Export all patterns
REGIONAL_PATTERNS = {
    'ukrainian': UKRAINIAN_PATTERNS,
    'russian': RUSSIAN_PATTERNS,
    'common': COMMON_CYRILLIC,
    'standards': REGIONAL_STANDARDS
}

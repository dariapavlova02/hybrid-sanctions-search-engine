"""
Legal Forms Patterns

Contains patterns and utilities for detecting legal entity forms
in various languages (Russian, Ukrainian, English).
"""

import re
from functools import lru_cache
from typing import Dict, List, Set


# Legal forms by language
LEGAL_FORMS = {
    "ru": {
        "ООО": "Общество с ограниченной ответственностью",
        "ЗАО": "Закрытое акционерное общество", 
        "ОАО": "Открытое акционерное общество",
        "ПАО": "Публичное акционерное общество",
        "АО": "Акционерное общество",
        "ИП": "Индивидуальный предприниматель",
        "ЧП": "Частное предприятие",
        "ФЛ": "Физическое лицо",
        "ТОО": "Товарищество с ограниченной ответственностью",
        "УП": "Унитарное предприятие",
        "ЧУП": "Частное унитарное предприятие",
    },
    "uk": {
        "ТОВ": "Товариство з обмеженою відповідальністю",
        "ПАТ": "Публічне акціонерне товариство",
        "АТ": "Акціонерне товариство", 
        "ПрАТ": "Приватне акціонерне товариство",
        "ФОП": "Фізична особа-підприємець",
        "ФО": "Фізична особа",
        "КТ": "Колективне товариство",
        "ДП": "Державне підприємство",
        "УП": "Унітарне підприємство",
    },
    "en": {
        "LLC": "Limited Liability Company",
        "Inc": "Incorporated",
        "Ltd": "Limited",
        "Corp": "Corporation", 
        "Co": "Company",
        "LP": "Limited Partnership",
        "LLP": "Limited Liability Partnership",
        "PC": "Professional Corporation",
        "PLLC": "Professional Limited Liability Company",
        "GmbH": "Gesellschaft mit beschränkter Haftung",
        "SRL": "Società a Responsabilità Limitata",
        "SPA": "Società per Azioni",
        "BV": "Besloten Vennootschap",
        "NV": "Naamloze Vennootschap",
        "OY": "Osakeyhtiö",
        "AB": "Aktiebolag",
        "AS": "Aksjeselskap",
        "SA": "Société Anonyme",
        "AG": "Aktiengesellschaft",
    }
}

# All legal forms as a flat set for quick lookup
ALL_LEGAL_FORMS: Set[str] = set()
for lang_forms in LEGAL_FORMS.values():
    ALL_LEGAL_FORMS.update(lang_forms.keys())

# Legal forms regex patterns
LEGAL_FORMS_REGEX = {
    "ru": r"\b(?:ООО|ЗАО|ОАО|ПАО|АО|ИП|ЧП|ФЛ|ТОО|УП|ЧУП)\b",
    "uk": r"\b(?:ТОВ|ПАТ|АТ|ПрАТ|ФОП|ФО|КТ|ДП|УП)\b", 
    "en": r"\b(?:LLC|Inc|Ltd|Corp|Co|LP|LLP|PC|PLLC|GmbH|SRL|SPA|BV|NV|OY|AB|AS|SA|AG)\b",
}

# Combined regex for all languages
ALL_LEGAL_FORMS_REGEX = r"\b(?:" + "|".join(ALL_LEGAL_FORMS) + r")\b"


def get_legal_forms_regex(language: str = "all") -> str:
    """
    Get legal forms regex pattern for specific language or all languages.

    Args:
        language: Language code ("ru", "uk", "en") or "all" for combined pattern

    Returns:
        Regex pattern string (not compiled)
    """
    if language == "all":
        return ALL_LEGAL_FORMS_REGEX
    return LEGAL_FORMS_REGEX.get(language, ALL_LEGAL_FORMS_REGEX)


@lru_cache(maxsize=8)
def get_compiled_legal_forms_regex(language: str = "all") -> re.Pattern:
    """
    Get compiled legal forms regex pattern with LRU caching.

    Args:
        language: Language code ("ru", "uk", "en") or "all" for combined pattern

    Returns:
        Compiled regex pattern
    """
    pattern_str = get_legal_forms_regex(language)
    return re.compile(pattern_str, re.IGNORECASE)


def get_legal_forms_set(language: str = "all") -> Set[str]:
    """
    Get set of legal forms for specific language or all languages.
    
    Args:
        language: Language code ("ru", "uk", "en") or "all" for all forms
        
    Returns:
        Set of legal form abbreviations
    """
    if language == "all":
        return ALL_LEGAL_FORMS
    
    forms = set()
    for lang, lang_forms in LEGAL_FORMS.items():
        if language == lang:
            forms.update(lang_forms.keys())
    return forms


def get_legal_form_full_name(abbreviation: str, language: str = "auto") -> str:
    """
    Get full name for legal form abbreviation.
    
    Args:
        abbreviation: Legal form abbreviation (e.g., "ООО", "LLC")
        language: Language code or "auto" for automatic detection
        
    Returns:
        Full legal form name or original abbreviation if not found
    """
    if language == "auto":
        # Try to detect language by abbreviation
        for lang, forms in LEGAL_FORMS.items():
            if abbreviation in forms:
                return forms[abbreviation]
        return abbreviation
    
    if language in LEGAL_FORMS and abbreviation in LEGAL_FORMS[language]:
        return LEGAL_FORMS[language][abbreviation]
    
    return abbreviation


def is_legal_form(text: str, language: str = "auto") -> bool:
    """
    Check if text contains legal form abbreviation.
    
    Args:
        text: Text to check
        language: Language code or "auto" for automatic detection
        
    Returns:
        True if legal form found, False otherwise
    """
    if language == "auto":
        pattern = ALL_LEGAL_FORMS_REGEX
    else:
        pattern = get_legal_forms_regex(language)
    
    return bool(re.search(pattern, text, re.IGNORECASE))


def extract_legal_forms(text: str, language: str = "auto") -> List[Dict[str, str]]:
    """
    Extract all legal forms from text with their positions.
    
    Args:
        text: Text to search in
        language: Language code or "auto" for automatic detection
        
    Returns:
        List of dictionaries with legal form info
    """
    if language == "auto":
        pattern = ALL_LEGAL_FORMS_REGEX
    else:
        pattern = get_legal_forms_regex(language)
    
    forms = []
    for match in re.finditer(pattern, text, re.IGNORECASE):
        abbreviation = match.group()
        forms.append({
            "abbreviation": abbreviation,
            "full_name": get_legal_form_full_name(abbreviation, language),
            "position": match.span(),
            "text": match.group()
        })
    
    return forms


# Additional patterns and functions expected by signals service
LEGAL_FORM_REGEX = re.compile(ALL_LEGAL_FORMS_REGEX, re.IGNORECASE)

# Organization name patterns
ORGANIZATION_NAME_REGEX = re.compile(
    r'(?:[""«]([^""»]{2,50})[""»]|([А-ЯІЇЄҐA-Z][а-яіїєґa-z0-9\s\-&]{2,50}))',
    re.IGNORECASE
)

# Quoted core patterns
QUOTED_CORE_REGEX = re.compile(
    r'[""«]([^""»]{2,50})[""»]',
    re.IGNORECASE
)


def normalize_legal_form(legal_form: str) -> str:
    """
    Normalize legal form abbreviation.
    
    Args:
        legal_form: Raw legal form abbreviation
        
    Returns:
        Normalized legal form abbreviation
    """
    if not legal_form:
        return legal_form
    
    # Convert to uppercase and strip whitespace
    normalized = legal_form.upper().strip()
    
    # Handle common variations
    variations = {
        "ООО": "ООО",
        "ооо": "ООО", 
        "ООО.": "ООО",
        "ТОВ": "ТОВ",
        "тов": "ТОВ",
        "ТОВ.": "ТОВ",
        "LLC": "LLC",
        "llc": "LLC",
        "LLC.": "LLC",
        "Ltd": "Ltd",
        "ltd": "Ltd",
        "Ltd.": "Ltd",
    }
    
    return variations.get(normalized, normalized)

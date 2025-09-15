"""
Gender rules for surname post-processing in Russian and Ukrainian.

This module provides functions to detect feminine surname forms and convert
oblique cases to feminine nominative forms.
"""

from typing import Optional, Tuple, List


# Female patronymic suffixes
FEMALE_PATRONYMIC_SUFFIXES_RU = ["овна", "евна", "ична"]
FEMALE_PATRONYMIC_SUFFIXES_UK = ["івна", "ївна"]

# Common female given names for gender inference
def get_female_given_names(lang: str) -> set:
    """
    Get female given names from dictionaries.
    
    Args:
        lang: Language code ('ru' or 'uk')
        
    Returns:
        Set of female given names in lowercase
    """
    try:
        if lang == "ru":
            from ai_service.data.dicts.russian_names import RUSSIAN_NAMES
            name_dict = RUSSIAN_NAMES
        elif lang == "uk":
            from ai_service.data.dicts.ukrainian_names import UKRAINIAN_NAMES
            name_dict = UKRAINIAN_NAMES
        else:
            return set()
    except ImportError:
        return set()
    
    female_names = set()
    for name, data in name_dict.items():
        if data.get("gender") == "femn":
            # Add the main name
            female_names.add(name.lower())
            # Add variants
            for variant in data.get("variants", []):
                female_names.add(variant.lower())
            # Add diminutives
            for diminutive in data.get("diminutives", []):
                female_names.add(diminutive.lower())
    
    return female_names

# Invariable surname suffixes (should not be gender-adjusted)
INVARIABLE_SURNAME_SUFFIXES = [
    "енко", "ко", "швили", "ишвили", "дзе", "иа", "ия", "ія", "о", "у", "е"
]


def looks_like_feminine_ru(token: str) -> Tuple[bool, Optional[str]]:
    """
    Detect if a Russian token looks like a feminine surname and return
    the target feminine nominative form if derivable.
    
    Args:
        token: The token to analyze
        
    Returns:
        Tuple of (is_feminine, feminine_nominative_or_None)
    """
    token_lower = token.lower()
    
    # Check for feminine genitive endings and convert to nominative
    if token_lower.endswith("овой"):
        return True, token[:-4] + "ова"  # Ахматовой -> Ахматова
    elif token_lower.endswith("евой"):
        return True, token[:-4] + "ева"  # Пугачевой -> Пугачева
    elif token_lower.endswith("иной"):
        return True, token[:-4] + "ина"  # было :-3 — неверно
    elif token_lower.endswith("ыной"):
        return True, token[:-4] + "ына"  # было :-3 — неверно
    elif token_lower.endswith("ою"):
        return True, token[:-2] + "ова"
    elif token_lower.endswith("ею"):
        return True, token[:-2] + "ева"  # Пугачею -> Пугачева (было "ова" — исправлено)
    elif token_lower.endswith("ую"):
        return True, token[:-2] + "ая"
    
    # Check for feminine nominative endings
    elif token_lower.endswith("ова"):
        return True, token
    elif token_lower.endswith("ева"):
        return True, token
    elif token_lower.endswith("ина"):
        return True, token
    elif token_lower.endswith("ына"):
        return True, token
    elif token_lower.endswith("ая"):
        return True, token
    
    return False, None


def looks_like_feminine_uk(token: str) -> Tuple[bool, Optional[str]]:
    """
    Detect if a Ukrainian token looks like a feminine surname and return
    the target feminine nominative form if derivable.
    
    Args:
        token: The token to analyze
        
    Returns:
        Tuple of (is_feminine, feminine_nominative_or_None)
    """
    token_lower = token.lower()
    
    # Check for feminine genitive endings and convert to nominative
    if token_lower.endswith("ової"):
        return True, token[:-2] + "а"  # Павлової -> Павлова
    elif token_lower.endswith("евої"):
        return True, token[:-2] + "а"  # Павлової -> Павлова
    elif token_lower.endswith("іної"):
        return True, token[:-3] + "іна"
    elif token_lower.endswith("їної"):
        return True, token[:-3] + "їна"
    elif token_lower.endswith("ської"):
        return True, token[:-4] + "ська"
    elif token_lower.endswith("цької"):
        return True, token[:-4] + "цька"
    elif token_lower.endswith("ську"):
        return True, token[:-3] + "ська"
    elif token_lower.endswith("цьку"):
        return True, token[:-3] + "цька"
    elif token_lower.endswith("ською"):
        return True, token[:-4] + "ська"
    elif token_lower.endswith("цькою"):
        return True, token[:-4] + "цька"
    elif token_lower.endswith("ській"):
        return True, token[:-5] + "ська"  # Кравцівській -> Кравцівська
    elif token_lower.endswith("цькій"):
        return True, token[:-5] + "цька"  # Кравцівцькій -> Кравцівцька
    
    # instrumental / dative → nominative
    elif token_lower.endswith("овою"):
        return True, token[:-3] + "ова"
    elif token_lower.endswith("евою"):
        return True, token[:-3] + "ева"
    elif token_lower.endswith("овій"):
        return True, token[:-3] + "ова"
    elif token_lower.endswith("евій"):
        return True, token[:-3] + "ева"
    elif token_lower.endswith("іною"):
        return True, token[:-3] + "іна"
    elif token_lower.endswith("їною"):
        return True, token[:-3] + "їна"
    
    # Check for feminine nominative endings
    elif token_lower.endswith("ова"):
        return True, token
    elif token_lower.endswith("ева"):
        return True, token
    elif token_lower.endswith("іна"):
        return True, token
    elif token_lower.endswith("їна"):
        return True, token
    elif token_lower.endswith("ська"):
        return True, token
    elif token_lower.endswith("цька"):
        return True, token
    
    return False, None


def to_feminine_nominative_ru(token: str) -> str:
    """
    Convert a Russian token to feminine nominative form.
    
    Args:
        token: The token to convert
        
    Returns:
        Feminine nominative form
    """
    is_fem, fem_nom = looks_like_feminine_ru(token)
    if is_fem and fem_nom:
        return fem_nom
    return token


def to_feminine_nominative_uk(token: str) -> str:
    """
    Convert a Ukrainian token to feminine nominative form.
    
    Args:
        token: The token to convert
        
    Returns:
        Feminine nominative form
    """
    is_fem, fem_nom = looks_like_feminine_uk(token)
    if is_fem and fem_nom:
        return fem_nom
    return token


def is_invariable_surname(token: str) -> bool:
    """
    Check if a surname has an invariable suffix that should not be gender-adjusted.
    
    Args:
        token: The token to check
        
    Returns:
        True if the surname is invariable
    """
    token_lower = token.lower()
    
    # Check direct endings
    if any(token_lower.endswith(suffix) for suffix in INVARIABLE_SURNAME_SUFFIXES):
        return True
    
    # Check if it's a declined form of -енко/-ко surnames
    # Порошенка -> Порошенко, Петренка -> Петренко
    if token_lower.endswith("ка") and len(token) > 4:
        # Check if removing "ка" and adding "ко" would make it end with "ко"
        base = token[:-2] + "ко"
        if base.lower().endswith("ко"):
            return True
    
    return False


def infer_gender_evidence(given: List[str], patronymic: Optional[str], lang: str) -> Optional[str]:
    """
    Infer gender evidence from given names and patronymic using dictionaries.
    
    Args:
        given: List of given names
        patronymic: Patronymic name (if any)
        lang: Language code ('ru' or 'uk')
        
    Returns:
        'fem', 'masc', or None
    """
    # Import name dictionaries
    try:
        if lang == "ru":
            from ai_service.data.dicts.russian_names import RUSSIAN_NAMES
            name_dict = RUSSIAN_NAMES
        elif lang == "uk":
            from ai_service.data.dicts.ukrainian_names import UKRAINIAN_NAMES
            name_dict = UKRAINIAN_NAMES
        else:
            return None
    except ImportError:
        return None
    
    # Check given names for gender indicators using dictionaries
    # Collect all gender evidence to handle mixed scenarios
    gender_evidence = []
    
    for name in given:
        name_lower = name.lower()
        # Check exact match first (case-insensitive)
        for dict_name, name_data in name_dict.items():
            if name_lower == dict_name.lower():
                gender = name_data.get("gender")
                if gender == "femn":
                    gender_evidence.append("fem")
                elif gender == "masc":
                    gender_evidence.append("masc")
                break
        else:
            # Check variants and diminutives
            for dict_name, name_data in name_dict.items():
                if name_lower in [v.lower() for v in name_data.get("variants", [])]:
                    gender = name_data.get("gender")
                    if gender == "femn":
                        gender_evidence.append("fem")
                    elif gender == "masc":
                        gender_evidence.append("masc")
                if name_lower in [v.lower() for v in name_data.get("diminutives", [])]:
                    gender = name_data.get("gender")
                    if gender == "femn":
                        gender_evidence.append("fem")
                    elif gender == "masc":
                        gender_evidence.append("masc")
                # Check declensions (for declined forms like "Анны" -> "Анна")
                if name_lower in [v.lower() for v in name_data.get("declensions", [])]:
                    gender = name_data.get("gender")
                    if gender == "femn":
                        gender_evidence.append("fem")
                    elif gender == "masc":
                        gender_evidence.append("masc")
    
    # Return the most confident gender evidence
    if gender_evidence:
        # If we have mixed evidence, prefer feminine (more specific)
        if "fem" in gender_evidence:
            return "fem"
        elif "masc" in gender_evidence:
            return "masc"
    
    # Check patronymic for gender indicators
    if patronymic:
        patronymic_lower = patronymic.lower()
        if lang == "ru":
            if any(patronymic_lower.endswith(suffix) for suffix in FEMALE_PATRONYMIC_SUFFIXES_RU):
                return "fem"
            elif any(patronymic_lower.endswith(suffix) for suffix in ["ович", "евич", "ич"]):
                return "masc"
        elif lang == "uk":
            if any(patronymic_lower.endswith(suffix) for suffix in FEMALE_PATRONYMIC_SUFFIXES_UK):
                return "fem"
            elif any(patronymic_lower.endswith(suffix) for suffix in ["ович", "евич", "ич"]):
                return "masc"
    
    return None


def feminine_nominative_from(token: str, language: str) -> str:
    """
    Convert a token to feminine nominative form based on language.
    
    Args:
        token: The token to convert
        language: Language code ('ru' or 'uk')
        
    Returns:
        Feminine nominative form
    """
    if language == "ru":
        return to_feminine_nominative_ru(token)
    elif language == "uk":
        return to_feminine_nominative_uk(token)
    else:
        return token


def convert_given_name_to_nominative(token: str, language: str) -> str:
    """
    Convert a given name from genitive case to nominative case.
    
    Args:
        token: The token to convert (e.g., "Анны" -> "Анна")
        language: Language code ('ru' or 'uk')
        
    Returns:
        Nominative form of the given name
    """
    if language == "ru":
        return convert_given_name_to_nominative_ru(token)
    elif language == "uk":
        return convert_given_name_to_nominative_uk(token)
    else:
        return token


def convert_given_name_to_nominative_ru(token: str) -> str:
    """
    Convert a Russian given name from genitive case to nominative case.
    
    Args:
        token: The token to convert (e.g., "Анны" -> "Анна")
        
    Returns:
        Nominative form of the given name
    """
    token_lower = token.lower()
    
    # Common genitive endings for Russian given names
    if token_lower.endswith("ы"):
        # Анны -> Анна, Марии -> Мария
        return token[:-1] + "а"
    elif token_lower.endswith("и"):
        # Марии -> Мария (already ends in "и")
        if len(token) > 2:
            return token[:-1] + "я"
    elif token_lower.endswith("а"):
        # Already in nominative or genitive with "а" ending
        return token
    
    return token


def convert_given_name_to_nominative_uk(token: str) -> str:
    """
    Convert a Ukrainian given name from genitive case to nominative case.
    
    Args:
        token: The token to convert (e.g., "Анни" -> "Анна")
        
    Returns:
        Nominative form of the given name
    """
    token_lower = token.lower()
    
    # Common genitive endings for Ukrainian given names
    if token_lower.endswith("и"):
        # Анни -> Анна, Марії -> Марія
        return token[:-1] + "а"
    elif token_lower.endswith("ї"):
        # Марії -> Марія
        return token[:-1] + "я"
    elif token_lower.endswith("а"):
        # Already in nominative or genitive with "а" ending
        return token
    
    return token

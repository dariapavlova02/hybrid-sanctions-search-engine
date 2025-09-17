"""Gender heuristics for Slavic surname normalization and preservation."""

from typing import Optional, Tuple, List


FEMALE_SUFFIXES_RU = ["ова", "ева", "ина", "ына", "ая"]
FEMALE_SUFFIXES_UK = ["іна", "ська", "цька", "а"]

# Frequently encountered feminine tokens that should remain untouched even if
# they do not follow standard surname suffix rules.
EXCEPTIONS_KEEP_FEM = {
    "анна",
    "мария",
    "марія",
    "юлия",
    "юлія",
    "лия",
    "лія",
    "ольга",
    "олена",
    "ірина",
    "ирина",
}


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
            from ....data.dicts.russian_names import RUSSIAN_NAMES
            name_dict = RUSSIAN_NAMES
        elif lang == "uk":
            from ....data.dicts.ukrainian_names import UKRAINIAN_NAMES
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
        return True, token[:-4] + "ова"  # Павлової -> Павлова
    elif token_lower.endswith("евої"):
        return True, token[:-4] + "ева"  # Іваненької -> Іваненка
    elif token_lower.endswith("іної"):
        return True, token[:-3] + "іна"
    elif token_lower.endswith("їної"):
        return True, token[:-3] + "їна"
    # Longer patterns first to avoid partial matches
    elif token_lower.endswith("цькою"):
        return True, token[:-4] + "цька"
    elif token_lower.endswith("ською"):
        return True, token[:-4] + "ська"
    elif token_lower.endswith("цькій"):
        return True, token[:-5] + "цька"  # Кравцівцькій -> Кравцівцька
    elif token_lower.endswith("ській"):
        return True, token[:-4] + "ська"  # Кравцівській -> Кравцівська
    elif token_lower.endswith("ської"):
        return True, token[:-5] + "ська"
    elif token_lower.endswith("цької"):
        return True, token[:-4] + "цька"
    elif token_lower.endswith("цьку"):
        return True, token[:-3] + "цька"
    elif token_lower.endswith("ську"):
        return True, token[:-3] + "ська"
    
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
    elif token_lower.endswith("іні"):
        return True, token[:-2] + "іна"  # дательный падеж
    elif token_lower.endswith("їні"):
        return True, token[:-2] + "їна"  # дательный падеж
    
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


def is_likely_feminine_surname(token: str, lang: str) -> bool:
    """Check whether ``token`` already looks like a feminine surname."""
    if not token:
        return False

    token_lower = token.lower()
    if token_lower in EXCEPTIONS_KEEP_FEM:
        return True

    suffixes: List[str]
    if lang == "ru":
        suffixes = FEMALE_SUFFIXES_RU
    elif lang == "uk":
        suffixes = FEMALE_SUFFIXES_UK
    else:
        return False

    return any(token_lower.endswith(suffix) for suffix in suffixes)


def prefer_feminine_form(surname_nom: str, given_gender: str, lang: str) -> str:
    """Return a feminine-friendly surname form when gender is feminine."""
    if given_gender != "femn" or not surname_nom:
        return surname_nom

    if is_likely_feminine_surname(surname_nom, lang):
        return surname_nom

    lowered = surname_nom.lower()

    if lang == "ru":
        replacements = [
            ("ский", "ская"),
            ("цкий", "цкая"),
            ("кой", "кая"),
            ("ой", "ая"),
            ("ов", "ова"),
            ("ев", "ева"),
            ("ин", "ина"),
            ("ын", "ына"),
        ]
    elif lang == "uk":
        replacements = [
            ("ський", "ська"),
            ("зький", "зька"),
            ("цький", "цька"),
            ("ій", "я"),
            ("ий", "а"),
        ]
    else:
        return surname_nom

    for src, dst in replacements:
        if lowered.endswith(src):
            base = surname_nom[:-len(src)] if len(src) else surname_nom
            candidate = base + dst
            return _preserve_case(surname_nom, candidate)

    return surname_nom


def _preserve_case(source: str, target: str) -> str:
    """Apply the casing pattern of ``source`` to ``target``."""
    if not target:
        return target

    if source.isupper():
        return target.upper()

    if source.istitle():
        return "-".join(part[:1].upper() + part[1:] if part else part for part in target.split("-"))

    if source.islower():
        return target.lower()

    # Mixed case: best effort by preserving first character casing.
    prefix = target[0].upper() if source[0].isupper() else target[0].lower()
    return prefix + target[1:]


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
        candidate = token[:-2] + "ко"
        base = candidate[:-2]  # убрать "ко"
        if candidate.lower().endswith(("енко", "ко")) and len(base) >= 3:
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
            from ....data.dicts.russian_names import RUSSIAN_NAMES
            name_dict = RUSSIAN_NAMES
        elif lang == "uk":
            from ....data.dicts.ukrainian_names import UKRAINIAN_NAMES
            name_dict = UKRAINIAN_NAMES
        else:
            name_dict = {}
    except ImportError:
        name_dict = {}
    
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
            # Check declined forms of female patronymics
            elif patronymic_lower.endswith("овны") or patronymic_lower.endswith("евны") or patronymic_lower.endswith("ичны"):
                return "fem"
            elif any(patronymic_lower.endswith(suffix) for suffix in ["ович", "евич", "ич"]):
                return "masc"
        elif lang == "uk":
            if any(patronymic_lower.endswith(suffix) for suffix in FEMALE_PATRONYMIC_SUFFIXES_UK):
                return "fem"
            # Check declined forms of female patronymics: Юріївни (gen.), Юріївну (acc.), etc.
            elif patronymic_lower.endswith("івни") or patronymic_lower.endswith("ївни"):
                return "fem"
            elif patronymic_lower.endswith("івну") or patronymic_lower.endswith("ївну"):
                return "fem"
            elif any(patronymic_lower.endswith(suffix) for suffix in ["ович", "евич", "ич"]):
                return "masc"
    
    return None


def maybe_to_feminine_nom(token: str, language: str, gender_hint: Optional[str], is_declined_feminine: bool) -> str:
    """
    Safely convert a token to feminine nominative form only if there's strong evidence.

    Args:
        token: The token to convert
        language: Language code ('ru' or 'uk')
        gender_hint: Gender evidence from context ('fem', 'masc', or None)
        is_declined_feminine: Whether the token looks like a declined feminine form

    Returns:
        Feminine nominative form if appropriate, original token otherwise
    """
    if gender_hint == "fem" or is_declined_feminine:
        return feminine_nominative_from(token, language)
    return token


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
    Convert a Russian given name from oblique case to nominative case.

    Args:
        token: The token to convert (e.g., "Анны" -> "Анна", "Ивану" -> "Иван")

    Returns:
        Nominative form of the given name
    """
    token_lower = token.lower()

    # Accusative case endings (use name dictionary for validation)
    if token_lower.endswith("а") and len(token) > 2:
        # Check if it's accusative masculine using name dictionaries
        potential_nom = token[:-1]
        try:
            from ....data.dicts.russian_names import RUSSIAN_NAMES
            # Check if potential nominative is a known male name
            # Try both capitalized and as-is versions
            for name_key in [potential_nom.capitalize(), potential_nom]:
                if name_key in RUSSIAN_NAMES:
                    name_data = RUSSIAN_NAMES[name_key]
                    if name_data.get("gender") == "masc":
                        return potential_nom
        except ImportError:
            pass
    # Dative case endings
    elif token_lower.endswith("у"):
        # Ивану -> Иван
        return token[:-1]
    elif token_lower.endswith("е"):
        # Марие -> Мария
        return token[:-1] + "я"
    # Instrumental case endings (masculine)
    elif token_lower.endswith("ом"):
        # Иваном -> Иван
        return token[:-2]
    elif token_lower.endswith("ем"):
        # Сергеем -> Сергей
        return token[:-2] + "й"
    # Genitive case endings
    elif token_lower.endswith("ы"):
        # Анны -> Анна
        return token[:-1] + "а"
    elif token_lower.endswith("и"):
        # Марии -> Мария
        if len(token) > 2:
            return token[:-1] + "я"

    return token


def convert_patronymic_to_nominative(token: str, language: str) -> str:
    """
    Convert a patronymic from oblique case to nominative case.

    Args:
        token: The token to convert (e.g., "Юріївни" -> "Юріївна")
        language: Language code ('ru' or 'uk')

    Returns:
        Nominative form of the patronymic
    """
    if language == "ru":
        return convert_patronymic_to_nominative_ru(token)
    elif language == "uk":
        return convert_patronymic_to_nominative_uk(token)
    else:
        return token


def convert_patronymic_to_nominative_ru(token: str) -> str:
    """
    Convert a Russian patronymic from oblique case to nominative case.

    Args:
        token: The token to convert

    Returns:
        Nominative form of the patronymic
    """
    token_lower = token.lower()

    # Female patronymics oblique case endings
    if token_lower.endswith(("овны", "евны", "ичны")):
        # Genitive: Ивановны -> Ивановна
        return token[:-1] + "а"
    elif token_lower.endswith(("овне", "евне", "ичне")):
        # Dative: Андреевне -> Андреевна
        return token[:-1] + "а"
    elif token_lower.endswith(("овну", "евну", "ичну")):
        # Accusative: Андреевну -> Андреевна
        return token[:-1] + "а"

    # Male patronymics oblique case endings
    elif token_lower.endswith(("овичу", "евичу")):
        # Dative: Ивановичу -> Иванович
        return token[:-1]
    elif token_lower.endswith(("овичем", "евичем")):
        # Instrumental: Ивановичем -> Иванович
        return token[:-2]
    elif token_lower.endswith(("овиче", "евиче")):
        # Prepositional: Ивановиче -> Иванович
        return token[:-1]

    return token


def convert_patronymic_to_nominative_uk(token: str) -> str:
    """
    Convert a Ukrainian patronymic from oblique case to nominative case.

    Args:
        token: The token to convert (e.g., "Юріївни" -> "Юріївна")

    Returns:
        Nominative form of the patronymic
    """
    token_lower = token.lower()

    # Female patronymics genitive endings
    if token_lower.endswith("івни"):
        return token[:-1] + "а"  # Юріївни -> Юріївна
    elif token_lower.endswith("ївни"):
        return token[:-1] + "а"  # Олексіївни -> Олексіївна
    # Female patronymics accusative endings
    elif token_lower.endswith("івну"):
        return token[:-1] + "а"  # Юріївну -> Юріївна
    elif token_lower.endswith("ївну"):
        return token[:-1] + "а"  # Олексіївну -> Олексіївна

    return token


def convert_surname_to_nominative(token: str, language: str, preserve_feminine_suffix_uk: bool = False) -> str:
    """
    Convert a surname from oblique case to nominative case.
    This handles masculine surnames that may be in dative/instrumental cases.

    Args:
        token: The token to convert (e.g., "Иванову" -> "Иванов")
        language: Language code ('ru' or 'uk')
        preserve_feminine_suffix_uk: If True, preserve Ukrainian feminine suffixes (-ська/-цька)

    Returns:
        Nominative form of the surname
    """
    if language == "ru":
        return convert_surname_to_nominative_ru(token)
    elif language == "uk":
        return convert_surname_to_nominative_uk(token, preserve_feminine_suffix_uk)
    else:
        return token


def convert_surname_to_nominative_ru(token: str) -> str:
    """
    Convert a Russian surname from oblique case to nominative case.

    Args:
        token: The token to convert

    Returns:
        Nominative form of the surname
    """
    token_lower = token.lower()

    # Masculine surnames in oblique cases
    if token_lower.endswith("ову"):
        # Dative: Иванову -> Иванов
        return token[:-1]
    elif token_lower.endswith("овым"):
        # Instrumental: Ивановым -> Иванов
        return token[:-2]
    elif token_lower.endswith("ове"):
        # Prepositional: Иванове -> Иванов
        return token[:-2]

    return token


def convert_surname_to_nominative_uk(token: str, preserve_feminine_suffix_uk: bool = False) -> str:
    """
    Convert a Ukrainian surname from oblique case to nominative case.

    Args:
        token: The token to convert
        preserve_feminine_suffix_uk: If True, preserve Ukrainian feminine suffixes (-ська/-цька)

    Returns:
        Nominative form of the surname
    """
    token_lower = token.lower()

    # If preserving feminine suffixes, check for feminine forms first
    if preserve_feminine_suffix_uk:
        is_fem, fem_nom = looks_like_feminine_uk(token)
        if is_fem and fem_nom:
            return fem_nom

    # Masculine surnames in oblique cases
    if token_lower.endswith("ову"):
        # Dative: Іванову -> Іванов
        return token[:-1]
    elif token_lower.endswith("овим"):
        # Instrumental: Івановим -> Іванов
        return token[:-2]
    elif token_lower.endswith("ові"):
        # Prepositional: Іванові -> Іванов
        return token[:-2]

    return token


def convert_given_name_to_nominative_uk(token: str) -> str:
    """
    Convert a Ukrainian given name from oblique case to nominative case.

    Args:
        token: The token to convert (e.g., "Анни" -> "Анна", "Дарʼї" -> "Дарʼя")

    Returns:
        Nominative form of the given name
    """
    token_lower = token.lower()

    # Genitive case endings
    if token_lower.endswith("ї"):
        # Дарʼї -> Дарʼя, Марії -> Марія
        return token[:-1] + "я"
    elif token_lower.endswith("и"):
        # Анни -> Анна
        return token[:-1] + "а"
    # Dative case endings
    elif token_lower.endswith("у"):
        # Івану -> Іван
        return token[:-1]
    elif token_lower.endswith("е"):
        # Марії -> Марія (dative -і -> -я in Ukrainian)
        return token[:-1] + "я"
    # Instrumental case endings (masculine)
    elif token_lower.endswith("ом"):
        # Іваном -> Іван
        return token[:-2]
    elif token_lower.endswith("ієм"):
        # Сергієм -> Сергій (Ukrainian specific -ій names)
        return token[:-3] + "ій"
    elif token_lower.endswith("ем"):
        # Other -ем endings
        return token[:-2]
    elif token_lower.endswith("а"):
        # Already in nominative or genitive with "а" ending
        return token

    return token

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

# Case constants (Petrovich-style)
class Case:
    GENITIVE = 0
    DATIVE = 1
    ACCUSATIVE = 2
    INSTRUMENTAL = 3
    PREPOSITIONAL = 4

class Gender:
    MALE = 'male'
    FEMALE = 'female'
    ANDROGYNOUS = 'androgynous'

# Invariable surname suffixes (should not be gender-adjusted)
INVARIABLE_SURNAME_SUFFIXES = [
    "енко", "ко", "швили", "ишвили", "дзе", "иа", "ия", "ія", "о", "у", "е"
]

# Enhanced rule structure for surname declension
SURNAME_RULES = {
    "ru": {
        "suffixes": [
            # Masculine rules
            {
                "test": "ов",
                "gender": Gender.MALE,
                "mods": [".", ".", ".", ".", "."]  # Nominative for all cases
            },
            {
                "test": "ову",
                "gender": Gender.MALE,
                "mods": [".", ".", ".", ".", "."]  # Dative -> Nominative
            },
            {
                "test": "овым",
                "gender": Gender.MALE,
                "mods": [".", ".", ".", ".", "."]  # Instrumental -> Nominative
            },
            {
                "test": "ове",
                "gender": Gender.MALE,
                "mods": [".", ".", ".", ".", "."]  # Prepositional -> Nominative
            },
            {
                "test": "ев",
                "gender": Gender.MALE,
                "mods": [".", ".", ".", ".", "."]  # Nominative for all cases
            },
            {
                "test": "еву",
                "gender": Gender.MALE,
                "mods": [".", ".", ".", ".", "."]  # Dative -> Nominative
            },
            {
                "test": "евым",
                "gender": Gender.MALE,
                "mods": [".", ".", ".", ".", "."]  # Instrumental -> Nominative
            },
            {
                "test": "еве",
                "gender": Gender.MALE,
                "mods": [".", ".", ".", ".", "."]  # Prepositional -> Nominative
            },
            {
                "test": "ин",
                "gender": Gender.MALE,
                "mods": [".", ".", ".", ".", "."]  # Nominative for all cases
            },
            {
                "test": "ину",
                "gender": Gender.MALE,
                "mods": [".", ".", ".", ".", "."]  # Dative -> Nominative
            },
            {
                "test": "иным",
                "gender": Gender.MALE,
                "mods": [".", ".", ".", ".", "."]  # Instrumental -> Nominative
            },
            {
                "test": "ине",
                "gender": Gender.MALE,
                "mods": [".", ".", ".", ".", "."]  # Prepositional -> Nominative
            },
            {
                "test": "ский",
                "gender": Gender.MALE,
                "mods": [".", ".", ".", ".", "."]  # Nominative for all cases
            },
            {
                "test": "ского",
                "gender": Gender.MALE,
                "mods": [".", ".", ".", ".", "."]  # Genitive -> Nominative
            },
            {
                "test": "скому",
                "gender": Gender.MALE,
                "mods": [".", ".", ".", ".", "."]  # Dative -> Nominative
            },
            {
                "test": "ским",
                "gender": Gender.MALE,
                "mods": [".", ".", ".", ".", "."]  # Instrumental -> Nominative
            },
            {
                "test": "ском",
                "gender": Gender.MALE,
                "mods": [".", ".", ".", ".", "."]  # Prepositional -> Nominative
            },
            # Feminine rules
            {
                "test": "ова",
                "gender": Gender.FEMALE,
                "mods": [".", ".", ".", ".", "."]  # Nominative for all cases
            },
            {
                "test": "овой",
                "gender": Gender.FEMALE,
                "mods": ["-а", ".", ".", ".", "."]  # Genitive/Instrumental/Prepositional -> Nominative
            },
            {
                "test": "ову",
                "gender": Gender.FEMALE,
                "mods": ["-а", ".", ".", ".", "."]  # Accusative -> Nominative
            },
            {
                "test": "ева",
                "gender": Gender.FEMALE,
                "mods": [".", ".", ".", ".", "."]  # Nominative for all cases
            },
            {
                "test": "евой",
                "gender": Gender.FEMALE,
                "mods": ["-а", ".", ".", ".", "."]  # Genitive/Instrumental/Prepositional -> Nominative
            },
            {
                "test": "еву",
                "gender": Gender.FEMALE,
                "mods": ["-а", ".", ".", ".", "."]  # Accusative -> Nominative
            },
            {
                "test": "ина",
                "gender": Gender.FEMALE,
                "mods": [".", ".", ".", ".", "."]  # Nominative for all cases
            },
            {
                "test": "иной",
                "gender": Gender.FEMALE,
                "mods": ["-а", ".", ".", ".", "."]  # Genitive/Instrumental/Prepositional -> Nominative
            },
            {
                "test": "ину",
                "gender": Gender.FEMALE,
                "mods": ["-а", ".", ".", ".", "."]  # Accusative -> Nominative
            },
            {
                "test": "ская",
                "gender": Gender.FEMALE,
                "mods": [".", ".", ".", ".", "."]  # Nominative for all cases
            },
            {
                "test": "ской",
                "gender": Gender.FEMALE,
                "mods": ["-а", ".", ".", ".", "."]  # Genitive/Instrumental/Prepositional -> Nominative
            },
            {
                "test": "скую",
                "gender": Gender.FEMALE,
                "mods": ["-а", ".", ".", ".", "."]  # Accusative -> Nominative
            }
        ],
        "exceptions": [
            {
                "test": ["ткач"],
                "gender": Gender.MALE,
                "mods": [".", ".", ".", ".", "."]  # Invariable
            },
            {
                "test": ["ткач"],
                "gender": Gender.FEMALE,
                "mods": [".", ".", ".", ".", "."]  # Invariable
            },
            {
                "test": ["бондаренко", "шевченко", "петренко"],
                "gender": Gender.MALE,
                "mods": [".", ".", ".", ".", "."]  # Invariable
            },
            {
                "test": ["бондаренко", "шевченко", "петренко"],
                "gender": Gender.FEMALE,
                "mods": [".", ".", ".", ".", "."]  # Invariable
            }
        ]
    }
}

# Legacy exception system for backward compatibility
SURNAME_EXCEPTIONS = {
    "ru": {
        "male": {
            "ткач": "ткач",
            "бондаренко": "бондаренко",
            "шевченко": "шевченко",
            "петренко": "петренко",
            "ко": "ко",
            "дзе": "дзе",
            "швили": "швили",
        },
        "female": {
            "ткач": "ткач",
            "бондаренко": "бондаренко",
            "шевченко": "шевченко",
            "петренко": "петренко",
            "ко": "ко",
            "дзе": "дзе",
            "швили": "швили",
        }
    },
    "uk": {
        "male": {
            "ткач": "ткач",
            "бондаренко": "бондаренко",
            "шевченко": "шевченко",
            "петренко": "петренко",
            "ко": "ко",
            "дзе": "дзе",
            "швили": "швили",
            "енко": "енко",
        },
        "female": {
            "ткач": "ткач",
            "бондаренко": "бондаренко",
            "шевченко": "шевченко",
            "петренко": "петренко",
            "ко": "ко",
            "дзе": "дзе",
            "швили": "швили",
            "енко": "енко",
        }
    }
}


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

    # Adjectival feminine surnames (from Petrovich rules)
    elif token_lower.endswith("ской"):
        return True, token[:-4] + "ская"   # Коваленской -> Коваленская
    elif token_lower.endswith("цкой"):
        return True, token[:-4] + "цкая"   # Галицкой -> Галицкая
    elif token_lower.endswith("ней") and len(token) > 4:
        return True, token[:-3] + "няя"    # Синей -> Синяя
    elif token_lower.endswith("ой") and len(token) > 3:
        # General adjective pattern: Красивой -> Красивая
        return True, token[:-2] + "ая"
    elif token_lower.endswith("нною") and len(token) > 5:
        return True, token[:-4] + "на"     # Аннною -> Анна
    elif token_lower.endswith("ною") and len(token) > 4:
        return True, token[:-3] + "на"     # Regular -ною -> -на

    # Instrumental case patterns
    elif token_lower.endswith("овою"):
        return True, token[:-4] + "ова"    # Смирновою -> Смирнова
    elif token_lower.endswith("евою"):
        return True, token[:-4] + "ева"    # Сергеевою -> Сергеева
    elif token_lower.endswith("ою"):
        return True, token[:-2] + "ова"
    elif token_lower.endswith("евею"):
        return True, token[:-4] + "ева"  # Сергеевею -> Сергеева
    elif token_lower.endswith("ею"):
        return True, token[:-2] + "ева"  # Пугачею -> Пугачева (было "ова" — исправлено)

    # Accusative case patterns
    elif token_lower.endswith("ую"):
        return True, token[:-2] + "ая"
    elif token_lower.endswith("юю"):
        return True, token[:-2] + "яя"   # Синюю -> Синяя
    
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
    Enhanced with Petrovich-style exception handling.

    Args:
        token: The token to check

    Returns:
        True if the surname is invariable
    """
    token_lower = token.lower()

    # Check direct exceptions first (most specific)
    if (token_lower in SURNAME_EXCEPTIONS["ru"]["male"] or 
        token_lower in SURNAME_EXCEPTIONS["ru"]["female"] or
        token_lower in SURNAME_EXCEPTIONS["uk"]["male"] or 
        token_lower in SURNAME_EXCEPTIONS["uk"]["female"]):
        return True

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


def looks_like_feminine_uk(token: str) -> Tuple[bool, Optional[str]]:
    """
    Detect if a Ukrainian token looks like a feminine surname and return
    the target feminine nominative form if derivable.

    Based on Ukrainian morphological rules inspired by Petrovich library.

    Args:
        token: The token to analyze

    Returns:
        Tuple of (is_feminine, feminine_nominative_or_None)
    """
    token_lower = token.lower()

    # 1. Adjectival surnames (-ська/-цька type)
    if token_lower.endswith("ської"):
        return True, token[:-2] + "а"  # Коваленської -> Коваленська
    elif token_lower.endswith("цької"):
        return True, token[:-2] + "а"  # Галицької -> Галицька
    elif token_lower.endswith("ською"):
        return True, token[:-2] + "а"  # Коваленською -> Коваленська
    elif token_lower.endswith("цькою"):
        return True, token[:-2] + "а"  # Галицькою -> Галицька
    elif token_lower.endswith("ській"):
        return True, token[:-2] + "а"  # Коваленській -> Коваленська
    elif token_lower.endswith("цькій"):
        return True, token[:-2] + "а"  # Галицькій -> Галицька

    # Check for feminine nominative endings
    elif token_lower.endswith("ська"):
        return True, token
    elif token_lower.endswith("цька"):
        return True, token

    # 2. Possessive surnames (-ова/-ева type)
    elif token_lower.endswith("ової"):
        return True, token[:-2] + "а"  # Петрової -> Петрова
    elif token_lower.endswith("евої"):
        return True, token[:-2] + "а"  # Сергеевої -> Сергеева
    elif token_lower.endswith("овою"):
        return True, token[:-2] + "а"  # Петровою -> Петрова
    elif token_lower.endswith("евою"):
        return True, token[:-2] + "а"  # Сергеевою -> Сергеева
    elif token_lower.endswith("овій"):
        return True, token[:-2] + "а"  # Петровій -> Петрова
    elif token_lower.endswith("евій"):
        return True, token[:-2] + "а"  # Сергеевій -> Сергеева
    elif token_lower.endswith("ову"):
        return True, token[:-1] + "а"  # Петрову -> Петрова
    elif token_lower.endswith("еву"):
        return True, token[:-1] + "а"  # Сергееву -> Сергеева

    # Check for feminine nominative endings
    elif token_lower.endswith("ова"):
        return True, token
    elif token_lower.endswith("ева"):
        return True, token
    elif token_lower.endswith("іна"):
        return True, token
    elif token_lower.endswith("їна"):
        return True, token

    return False, None


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
    Enhanced with comprehensive declension patterns inspired by advanced morphology rules.

    Args:
        token: The token to convert (e.g., "Анны" -> "Анна", "Ивану" -> "Иван")

    Returns:
        Nominative form of the given name
    """
    token_lower = token.lower()

    # Enhanced rules based on comprehensive declension patterns

    # Genitive case patterns (most common)
    if token_lower.endswith("ы") and len(token) > 2:
        # Feminine genitive: Анны -> Анна, Ольги -> Ольга
        if token_lower.endswith("ги"):
            return token[:-2] + "га"  # Ольги -> Ольга
        else:
            return token[:-1] + "а"   # Анны -> Анна

    elif token_lower.endswith("и") and len(token) > 2:
        # Special cases for genitive feminine
        if token_lower == "вики":
            return "Вика"
        elif token_lower.endswith("ги"):
            return token[:-2] + "га"  # Ольги -> Ольга
        elif token_lower.endswith("лии"):
            return token[:-1] + "я"  # Юлии -> Юлия
        elif token_lower.endswith("рии"):
            return token[:-1] + "я"  # Марии -> Мария
        elif token_lower.endswith("нии"):
            return token[:-1] + "я"  # Евгении -> Евгения
        # Check if it's a diminutive (should not be converted)
        elif not any(suffix in token_lower for suffix in ["еньк", "очк", "ечк", "ушк", "юшк"]):
            return token[:-1] + "я"

    # Dative case patterns
    elif token_lower.endswith("у") and len(token) > 2:
        # Masculine dative: Ивану -> Иван, Петру -> Петр
        return token[:-1]

    elif token_lower.endswith("е") and len(token) > 2:
        # Feminine dative: Марие -> Мария, Анне -> Анна
        if token_lower.endswith("не"):
            return token[:-1] + "а"  # Анне -> Анна
        else:
            return token[:-1] + "я"  # Марие -> Мария

    # Accusative case patterns
    elif token_lower.endswith("а") and len(token) > 2:
        # Could be masculine accusative or already nominative feminine
        # Use name dictionary validation for masculine names
        potential_nom = token[:-1]
        try:
            from ....data.dicts.russian_names import RUSSIAN_NAMES
            for name_key in [potential_nom.capitalize(), potential_nom]:
                if name_key in RUSSIAN_NAMES:
                    name_data = RUSSIAN_NAMES[name_key]
                    if name_data.get("gender") == "masc":
                        return potential_nom  # Ивана -> Иван
        except ImportError:
            pass
        # If not found as masculine, assume already nominative feminine
        return token

    # Instrumental case patterns
    elif token_lower.endswith("ом") and len(token) > 3:
        # Masculine instrumental: Иваном -> Иван, Петром -> Петр
        return token[:-2]

    elif token_lower.endswith("ем") and len(token) > 3:
        # Masculine instrumental: Сергеем -> Сергей, Алексеем -> Алексей
        if token_lower.endswith("еем"):
            return token[:-2] + "й"  # Сергеем -> Сергей
        else:
            return token[:-2]  # Other -ем endings

    elif token_lower.endswith("ей") and len(token) > 3:
        # Feminine instrumental: Анной would be covered above, this for other patterns
        return token[:-2] + "я"  # Some rare cases

    # Prepositional case patterns
    elif token_lower.endswith("ке") and len(token) > 3:
        # Feminine prepositional: о Танечке -> Танечка
        return token[:-1] + "а"

    # Already in nominative or no clear pattern
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


def _apply_rule_modification(mods: list, name: str, case: int) -> str:
    """
    Apply rule modification for surname declension.
    
    Args:
        mods: List of modifications for each case
        name: Original name
        case: Target case (we always want nominative = 0)
    
    Returns:
        Modified name
    """
    if mods[case] == ".":
        return name  # No change needed
    
    # For "-а" modification, remove the last character and add "а"
    if mods[case] == "-а":
        if len(name) > 1:
            return name[:-1] + "а"
        return name
    
    # For other modifications, count dashes to determine how many characters to remove
    chars_to_remove = mods[case].count('-')
    result = name[:len(name) - chars_to_remove]
    result += mods[case].replace('-', '')
    
    return result


def _find_declension_rules(name: str, case: int, name_form: str, gender: str, language: str) -> str:
    """
    Find and apply enhanced rules for surname declension.
    
    Args:
        name: Name to decline
        case: Target case (always nominative = 0)
        name_form: Type of name ('surname')
        gender: Gender ('male' or 'female')
        language: Language code ('ru' or 'uk')
    
    Returns:
        Declined name
    """
    if language not in SURNAME_RULES:
        return name
    
    rules = SURNAME_RULES[language]
    
    # Check exceptions first
    if "exceptions" in rules:
        for rule in rules["exceptions"]:
            if rule["gender"] == gender and name.lower() in rule["test"]:
                return _apply_rule_modification(rule["mods"], name, case)
    
    # Check suffix rules
    if "suffixes" in rules:
        for rule in rules["suffixes"]:
            if rule["gender"] == gender:
                suffix = rule["test"]
                if name.lower().endswith(suffix):
                    return _apply_rule_modification(rule["mods"], name, case)
    
    return name


def convert_surname_to_nominative_ru(token: str) -> str:
    """
    Convert a Russian surname from oblique case to nominative case.
    Enhanced with comprehensive patterns inspired by advanced morphology rules.

    Args:
        token: The token to convert

    Returns:
        Nominative form of the surname
    """
    token_lower = token.lower()

    # Check for exceptions first (invariable surnames)
    if token_lower in SURNAME_EXCEPTIONS["ru"]["male"]:
        return token  # Return as-is for invariable surnames

    # Handle hyphenated surnames
    if '-' in token:
        parts = token.split('-')
        return '-'.join([convert_surname_to_nominative_ru(part) for part in parts])

    # Enhanced surname declension patterns

    # 1. Surnames ending in -ов/-ев - check for feminine forms first
    is_fem, fem_nom = looks_like_feminine_ru(token)
    if is_fem and fem_nom:
        return fem_nom  # Use the feminine nominative form

    # If not feminine, check masculine patterns
    if token_lower.endswith("ова") and len(token) > 4:
        # This should have been caught above, but if not feminine context, convert to masculine
        return token[:-1]  # Иванова -> Иванов (only if no feminine context)
    elif token_lower.endswith("овым"):
        # Masculine instrumental: Ивановым -> Иванов
        return token[:-3]
    elif token_lower.endswith("ове"):
        # Masculine prepositional: Иванове -> Иванов
        return token[:-2]

    elif token_lower.endswith("ева") and len(token) > 4:
        # This should have been caught by looks_like_feminine_ru, but fallback to masculine
        return token[:-1]  # Сергеева -> Сергеев (only if no feminine context)
    elif token_lower.endswith("евым"):
        # Masculine instrumental: Сергеевым -> Сергеев
        return token[:-3]
    elif token_lower.endswith("еве"):
        # Masculine prepositional: Сергееве -> Сергеев
        return token[:-2]

    # 2. Surnames ending in -ин (patronymic-derived)
    elif token_lower.endswith("ина"):
        # Feminine nominative already: Путина
        return token
    elif token_lower.endswith("иной"):
        # Feminine genitive/instrumental/prepositional: Путиной -> Путина
        return token[:-2] + "а"
    elif token_lower.endswith("ину"):
        # Feminine accusative OR masculine dative: Путину -> Путина
        return token[:-1] + "а"
    elif token_lower.endswith("иным"):
        # Masculine instrumental: Путиным -> Путин
        return token[:-3]
    elif token_lower.endswith("ине"):
        # Masculine prepositional: Путине -> Путин
        return token[:-2]

    # 3. Adjective-type surnames ending in -ский/-цкий
    elif token_lower.endswith("ская"):
        # Feminine nominative already: Достоевская
        return token
    elif token_lower.endswith("ской"):
        # Feminine genitive/instrumental/prepositional: Достоевской -> Достоевская
        return token[:-2] + "а"
    elif token_lower.endswith("скую"):
        # Feminine accusative: Достоевскую -> Достоевская
        return token[:-3] + "ая"
    elif token_lower.endswith("ским"):
        # Masculine instrumental: Достоевским -> Достоевский
        return token[:-3] + "ий"
    elif token_lower.endswith("ском"):
        # Masculine prepositional: Достоевском -> Достоевский
        return token[:-3] + "ий"
    elif token_lower.endswith("ского"):
        # Masculine genitive: Достоевского -> Достоевский
        return token[:-4] + "ий"
    elif token_lower.endswith("скому"):
        # Masculine dative: Достоевскому -> Достоевский
        return token[:-4] + "ий"

    elif token_lower.endswith("цкая"):
        # Feminine nominative already: Вяземецкая
        return token
    elif token_lower.endswith("цкой"):
        # Feminine genitive/instrumental/prepositional: Вяземецкой -> Вяземецкая
        return token[:-2] + "а"
    elif token_lower.endswith("цкую"):
        # Feminine accusative: Вяземецкую -> Вяземецкая
        return token[:-3] + "ая"
    elif token_lower.endswith("цким"):
        # Masculine instrumental: Вяземецким -> Вяземецкий
        return token[:-3] + "ий"
    elif token_lower.endswith("цком"):
        # Masculine prepositional: Вяземецком -> Вяземецкий
        return token[:-3] + "ий"
    elif token_lower.endswith("цкого"):
        # Masculine genitive: Вяземецкого -> Вяземецкий
        return token[:-4] + "ий"
    elif token_lower.endswith("цкому"):
        # Masculine dative: Вяземецкому -> Вяземецкий
        return token[:-4] + "ий"

    # 4. Generic patterns for other surname types
    elif token_lower.endswith("а") and len(token) > 4:
        # Could be genitive masculine: Петрова -> Петров
        # But avoid converting feminine nominatives
        if not any(token_lower.endswith(fem_suffix) for fem_suffix in ["ова", "ева", "ина", "ская", "цкая"]):
            return token[:-1]

    elif token_lower.endswith("у") and len(token) > 4:
        # Dative masculine: Петрову -> Петров (if not covered above)
        if not token_lower.endswith("ову") and not token_lower.endswith("еву") and not token_lower.endswith("ину"):
            return token[:-1]

    elif token_lower.endswith("ом") and len(token) > 4:
        # Instrumental masculine: Петровом -> Петров
        return token[:-2]

    elif token_lower.endswith("е") and len(token) > 4:
        # Prepositional masculine: Петрове -> Петров (if not covered above)
        if not token_lower.endswith("ове") and not token_lower.endswith("еве") and not token_lower.endswith("ине"):
            return token[:-1]

    # 5. Preserve already correct nominative forms
    return token


def convert_surname_to_nominative_uk(token: str, preserve_feminine_suffix_uk: bool = False) -> str:
    """
    Convert a Ukrainian surname from oblique case to nominative case.
    Enhanced with comprehensive Ukrainian patterns inspired by advanced morphology rules.

    Args:
        token: The token to convert
        preserve_feminine_suffix_uk: If True, preserve Ukrainian feminine suffixes (-ська/-цька)

    Returns:
        Nominative form of the surname
    """
    token_lower = token.lower()

    # Check for exceptions first (invariable surnames)
    if token_lower in SURNAME_EXCEPTIONS["uk"]["male"]:
        return token  # Return as-is for invariable surnames

    # Handle hyphenated surnames
    if '-' in token:
        parts = token.split('-')
        return '-'.join([convert_surname_to_nominative_uk(part, preserve_feminine_suffix_uk) for part in parts])

    # Priority 1: Check for feminine forms first (based on Petrovich logic)
    is_fem_uk, fem_nom_uk = looks_like_feminine_uk(token)
    if is_fem_uk and fem_nom_uk:
        return fem_nom_uk  # Use the feminine nominative form

    # Enhanced Ukrainian surname declension patterns

    # 1. Surnames ending in -енко (most common Ukrainian pattern)
    if token_lower.endswith("енко"):
        # Already nominative: Шевченко, Петренко
        return token
    elif token_lower.endswith("енка"):
        # Genitive: Шевченка -> Шевченко
        return token[:-1] + "о"
    elif token_lower.endswith("енку"):
        # Dative: Шевченку -> Шевченко
        return token[:-1] + "о"
    elif token_lower.endswith("енком"):
        # Instrumental: Шевченком -> Шевченко
        return token[:-2] + "о"
    elif token_lower.endswith("енкові"):
        # Prepositional: Шевченкові -> Шевченко
        return token[:-3] + "о"
    elif token_lower.endswith("енці"):
        # Prepositional feminine: Шевченці -> Шевченко
        return token[:-2] + "о"
    elif token_lower.endswith("енкою"):
        # Instrumental feminine: Шевченкою -> Шевченко
        return token[:-3] + "о"

    # 2. Surnames ending in -ук/-юк/-чук (Ukrainian patronymic)
    elif token_lower.endswith("ук") or token_lower.endswith("юк") or token_lower.endswith("чук"):
        # Already nominative: Кухарук, Петрук, Савчук
        return token
    elif token_lower.endswith("ука"):
        # Genitive: Кухарука -> Кухарук
        return token[:-1]
    elif token_lower.endswith("уку"):
        # Dative: Кухаруку -> Кухарук
        return token[:-1]
    elif token_lower.endswith("уком"):
        # Instrumental: Кухаруком -> Кухарук
        return token[:-2]
    elif token_lower.endswith("укові"):
        # Prepositional: Кухарукові -> Кухарук
        return token[:-3]
    elif token_lower.endswith("юка"):
        # Genitive: Петрюка -> Петрюк
        return token[:-1]
    elif token_lower.endswith("юку"):
        # Dative: Петрюку -> Петрюк
        return token[:-1]
    elif token_lower.endswith("юком"):
        # Instrumental: Петрюком -> Петрюк
        return token[:-2]
    elif token_lower.endswith("юкові"):
        # Prepositional: Петрюкові -> Петрюк
        return token[:-3]
    elif token_lower.endswith("чука"):
        # Genitive: Савчука -> Савчук
        return token[:-1]
    elif token_lower.endswith("чуку"):
        # Dative: Савчуку -> Савчук
        return token[:-1]
    elif token_lower.endswith("чуком"):
        # Instrumental: Савчуком -> Савчук
        return token[:-2]
    elif token_lower.endswith("чукові"):
        # Prepositional: Савчукові -> Савчук
        return token[:-3]

    # 3. Surnames ending in -ський/-цький (adjective-type)
    elif token_lower.endswith("ський"):
        # Masculine nominative already: Коваленський
        return token
    elif token_lower.endswith("ська"):
        # Feminine nominative already: Коваленська
        if preserve_feminine_suffix_uk:
            return token
        else:
            return token[:-2] + "ський"  # Convert to masculine
    elif token_lower.endswith("ської"):
        # Feminine genitive: Коваленської -> Коваленська
        if preserve_feminine_suffix_uk:
            return token[:-2] + "а"
        else:
            return token[:-4] + "ський"
    elif token_lower.endswith("ському"):
        # Masculine dative: Коваленському -> Коваленський
        return token[:-4] + "ський"
    elif token_lower.endswith("ським"):
        # Masculine instrumental: Коваленським -> Коваленський
        return token[:-3] + "ський"
    elif token_lower.endswith("ському"):
        # Masculine prepositional: Коваленському -> Коваленський
        return token[:-4] + "ський"
    elif token_lower.endswith("ською"):
        # Feminine instrumental: Коваленською -> Коваленська
        if preserve_feminine_suffix_uk:
            return token[:-2] + "а"
        else:
            return token[:-4] + "ський"
    elif token_lower.endswith("ській"):
        # Feminine prepositional: Коваленській -> Коваленська
        if preserve_feminine_suffix_uk:
            return token[:-2] + "а"
        else:
            return token[:-4] + "ський"

    elif token_lower.endswith("цький"):
        # Masculine nominative already: Галицький
        return token
    elif token_lower.endswith("цька"):
        # Feminine nominative already: Галицька
        if preserve_feminine_suffix_uk:
            return token
        else:
            return token[:-2] + "цький"  # Convert to masculine
    elif token_lower.endswith("цької"):
        # Feminine genitive: Галицької -> Галицька
        if preserve_feminine_suffix_uk:
            return token[:-2] + "а"
        else:
            return token[:-4] + "цький"
    elif token_lower.endswith("цькому"):
        # Masculine dative: Галицькому -> Галицький
        return token[:-4] + "цький"
    elif token_lower.endswith("цьким"):
        # Masculine instrumental: Галицьким -> Галицький
        return token[:-3] + "цький"
    elif token_lower.endswith("цькою"):
        # Feminine instrumental: Галицькою -> Галицька
        if preserve_feminine_suffix_uk:
            return token[:-2] + "а"
        else:
            return token[:-4] + "цький"


    # 5. Surnames ending in -ов/-ев (masculine patterns)
    elif token_lower.endswith("ова") and len(token) > 4:
        # CRITICAL FIX: Check if this is actually a feminine given name, not a surname
        try:
            from ....data.dicts.ukrainian_names import UKRAINIAN_NAMES
            # Check if token is a known feminine given name (like "Олександра")
            for name_key in [token.capitalize(), token]:
                if name_key in UKRAINIAN_NAMES:
                    name_data = UKRAINIAN_NAMES[name_key]
                    if name_data.get("gender") == "femn":
                        # This is a feminine given name, not a surname - do not convert!
                        return token  # Keep "Олександра" as "Олександра"
        except ImportError:
            pass

        # This should have been caught above, but if not feminine context, convert to masculine
        return token[:-1]  # Петрова -> Петров (only if no feminine context)
    elif token_lower.endswith("ева") and len(token) > 4:
        # CRITICAL FIX: Check if this is actually a feminine given name, not a surname
        try:
            from ....data.dicts.ukrainian_names import UKRAINIAN_NAMES
            # Check if token is a known feminine given name
            for name_key in [token.capitalize(), token]:
                if name_key in UKRAINIAN_NAMES:
                    name_data = UKRAINIAN_NAMES[name_key]
                    if name_data.get("gender") == "femn":
                        # This is a feminine given name, not a surname - do not convert!
                        return token  # Keep feminine name as-is
        except ImportError:
            pass

        # This should have been caught above, but if not feminine context, convert to masculine
        return token[:-1]  # Сергеева -> Сергеев (only if no feminine context)
    elif token_lower.endswith("ової") and len(token) > 5:
        # Feminine genitive: Петрової -> Петров
        return token[:-3]
    elif token_lower.endswith("евої") and len(token) > 5:
        # Feminine genitive: Сергеевої -> Сергеев
        return token[:-3]
    elif token_lower.endswith("ову") and len(token) > 4:
        # Feminine accusative: Петрову -> Петров
        return token[:-2]
    elif token_lower.endswith("еву") and len(token) > 4:
        # Feminine accusative: Сергееву -> Сергеев
        return token[:-2]
    elif token_lower.endswith("овою") and len(token) > 5:
        # Feminine instrumental: Петровою -> Петров
        return token[:-3]
    elif token_lower.endswith("евою") and len(token) > 5:
        # Feminine instrumental: Сергеевою -> Сергеев
        return token[:-3]
    elif token_lower.endswith("овім") and len(token) > 5:
        # Masculine instrumental: Петровим -> Петров
        return token[:-3]
    elif token_lower.endswith("евім") and len(token) > 5:
        # Masculine instrumental: Сергеевим -> Сергеев
        return token[:-3]
    elif token_lower.endswith("ові") and len(token) > 4:
        # Masculine prepositional: Петрові -> Петров
        return token[:-2]
    elif token_lower.endswith("еві") and len(token) > 4:
        # Masculine prepositional: Сергееві -> Сергеев
        return token[:-2]

    # 6. Generic patterns for other surname types
    elif token_lower.endswith("а") and len(token) > 4:
        # Could be genitive masculine: but now excluding patterns already handled above
        # But avoid converting feminine nominatives
        if not any(token_lower.endswith(fem_suffix) for fem_suffix in ["ська", "цька"]):
            return token[:-1]

    elif token_lower.endswith("у") and len(token) > 4:
        # Dative masculine: Петрову -> Петров (if not covered above)
        if not any(token_lower.endswith(covered) for covered in ["ову", "еву", "ску", "цку", "енку", "уку", "юку", "чуку"]):
            return token[:-1]

    elif token_lower.endswith("ом") and len(token) > 4:
        # Instrumental masculine: Петровом -> Петров
        return token[:-2]

    elif token_lower.endswith("і") and len(token) > 4:
        # Prepositional masculine: Петрові -> Петров (if not covered above)
        if not any(token_lower.endswith(covered) for covered in ["ові", "еві", "скі", "цкі"]):
            return token[:-1]

    # 6. Preserve already correct nominative forms
    return token


def convert_given_name_to_nominative_uk(token: str) -> str:
    """
    Convert a Ukrainian given name from oblique case to nominative case.
    Enhanced with comprehensive declension patterns inspired by advanced morphology rules.

    Args:
        token: The token to convert (e.g., "Анни" -> "Анна", "Дарʼї" -> "Дарʼя")

    Returns:
        Nominative form of the given name
    """
    token_lower = token.lower()

    # Enhanced Ukrainian declension patterns

    # Genitive case patterns
    if token_lower.endswith("ї") and len(token) > 2:
        # Feminine genitive: Дарʼї -> Дарʼя, Марії -> Марія, Софії -> Софія
        return token[:-1] + "я"

    elif token_lower.endswith("і") and len(token) > 2:
        # Feminine genitive: Анні -> Анна, Оксані -> Оксана
        # Special case for names ending in -ії -> -ія
        if token_lower.endswith("ії"):
            return token[:-1] + "я"  # Марії -> Марія
        elif token_lower.endswith("ні"):
            return token[:-1] + "а"  # Анні -> Анна
        elif token_lower.endswith("и"):
            return token[:-1] + "а"  # General pattern
        else:
            return token[:-1] + "а"  # General genitive pattern

    elif token_lower.endswith("и") and len(token) > 2:
        # Feminine genitive: Анни -> Анна, Ольги -> Ольга
        if token_lower.endswith("ги"):
            return token[:-2] + "га"  # Ольги -> Ольга
        else:
            return token[:-1] + "а"   # Анни -> Анна

    # Dative case patterns
    elif token_lower.endswith("у") and len(token) > 2:
        # Masculine dative: Івану -> Іван, Петру -> Петр
        return token[:-1]

    elif token_lower.endswith("і") and len(token) > 2:
        # Feminine dative: Анні -> Анна, Марії -> Марія
        if token_lower.endswith("ії"):
            return token[:-1] + "я"  # Марії -> Марія
        else:
            return token[:-1] + "а"  # Анні -> Анна

    elif token_lower.endswith("е") and len(token) > 2:
        # Some dative patterns: Оксане -> Оксана
        return token[:-1] + "а"

    # Accusative case patterns
    elif token_lower.endswith("а") and len(token) > 2:
        # Could be masculine accusative or already nominative feminine
        # CRITICAL FIX: Check if current token is already a feminine name in nominative
        try:
            from ....data.dicts.ukrainian_names import UKRAINIAN_NAMES
            # First check if the original token is a known feminine name
            for name_key in [token.capitalize(), token]:
                if name_key in UKRAINIAN_NAMES:
                    name_data = UKRAINIAN_NAMES[name_key]
                    if name_data.get("gender") == "femn":
                        # Already feminine nominative - DO NOT CONVERT
                        return token  # Олександра stays Олександра

            # Only then check if it could be masculine accusative
            potential_nom = token[:-1]
            for name_key in [potential_nom.capitalize(), potential_nom]:
                if name_key in UKRAINIAN_NAMES:
                    name_data = UKRAINIAN_NAMES[name_key]
                    if name_data.get("gender") == "masc":
                        return potential_nom  # Івана -> Іван
        except ImportError:
            pass
        # If not found as masculine, assume already nominative feminine
        return token

    # Instrumental case patterns
    elif token_lower.endswith("ом") and len(token) > 3:
        # Masculine instrumental: Іваном -> Іван, Петром -> Петр
        return token[:-2]

    elif token_lower.endswith("ем") and len(token) > 3:
        # Masculine instrumental: Олексієм -> Олексій
        if token_lower.endswith("ієм"):
            return token[:-2] + "й"  # Сергієм -> Сергій
        else:
            return token[:-2]  # Other -ем endings

    elif token_lower.endswith("ією") and len(token) > 4:
        # Feminine instrumental: Вікторією -> Вікторія
        return token[:-2] + "я"
    elif token_lower.endswith("ею") and len(token) > 3:
        # Feminine instrumental: Анною -> Анна
        return token[:-2] + "а"

    elif token_lower.endswith("ою") and len(token) > 3:
        # Feminine instrumental: Мар'єю -> Мар'я, Дар'єю -> Дар'я
        if token_lower.endswith("'єю"):
            return token[:-2] + "я"
        else:
            return token[:-2] + "а"

    # Prepositional case patterns
    elif token_lower.endswith("ці") and len(token) > 3:
        # Feminine prepositional: про Анці -> Анна
        return token[:-2] + "а"

    elif token_lower.endswith("ї") and len(token) > 3:
        # Feminine prepositional: про Марії -> Марія
        return token[:-1] + "я"

    # Vocative case patterns (Ukrainian specific)
    elif token_lower.endswith("е") and len(token) > 3:
        # Masculine vocative: Іване -> Іван, Петре -> Петр
        return token[:-1]
    elif token_lower.endswith("о") and len(token) > 3:
        # Feminine vocative: Олено -> Олена, Марино -> Марина
        return token[:-1] + "а"
    elif token_lower.endswith("ю") and len(token) > 3:
        # Feminine vocative: Анно -> Анна (rare, but possible)
        return token[:-1] + "а"

    # Already in nominative or no clear pattern
    return token

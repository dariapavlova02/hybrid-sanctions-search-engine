"""
Identifier Patterns

Contains patterns and utilities for detecting various types of identifiers
(INN, EDRPOU, VAT, LEI, etc.) in different formats.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Pattern, Tuple


# ISO 3166-1 alpha-2 country codes used for SWIFT/BIC validation
ISO_COUNTRY_CODES = {
    "AD", "AE", "AF", "AG", "AI", "AL", "AM", "AO", "AQ", "AR", "AS", "AT", "AU", "AW", "AX",
    "AZ", "BA", "BB", "BD", "BE", "BF", "BG", "BH", "BI", "BJ", "BL", "BM", "BN", "BO", "BQ",
    "BR", "BS", "BT", "BV", "BW", "BY", "BZ", "CA", "CC", "CD", "CF", "CG", "CH", "CI", "CK",
    "CL", "CM", "CN", "CO", "CR", "CU", "CV", "CW", "CX", "CY", "CZ", "DE", "DJ", "DK", "DM",
    "DO", "DZ", "EC", "EE", "EG", "EH", "ER", "ES", "ET", "FI", "FJ", "FK", "FM", "FO", "FR",
    "GA", "GB", "GD", "GE", "GF", "GG", "GH", "GI", "GL", "GM", "GN", "GP", "GQ", "GR", "GS",
    "GT", "GU", "GW", "GY", "HK", "HM", "HN", "HR", "HT", "HU", "ID", "IE", "IL", "IM", "IN",
    "IO", "IQ", "IR", "IS", "IT", "JE", "JM", "JO", "JP", "KE", "KG", "KH", "KI", "KM", "KN",
    "KP", "KR", "KW", "KY", "KZ", "LA", "LB", "LC", "LI", "LK", "LR", "LS", "LT", "LU", "LV",
    "LY", "MA", "MC", "MD", "ME", "MF", "MG", "MH", "MK", "ML", "MM", "MN", "MO", "MP", "MQ",
    "MR", "MS", "MT", "MU", "MV", "MW", "MX", "MY", "MZ", "NA", "NC", "NE", "NF", "NG", "NI",
    "NL", "NO", "NP", "NR", "NU", "NZ", "OM", "PA", "PE", "PF", "PG", "PH", "PK", "PL", "PM",
    "PN", "PR", "PS", "PT", "PW", "PY", "QA", "RE", "RO", "RS", "RU", "RW", "SA", "SB", "SC",
    "SD", "SE", "SG", "SH", "SI", "SJ", "SK", "SL", "SM", "SN", "SO", "SR", "SS", "ST", "SV",
    "SX", "SY", "SZ", "TC", "TD", "TF", "TG", "TH", "TJ", "TK", "TL", "TM", "TN", "TO", "TR",
    "TT", "TV", "TW", "TZ", "UA", "UG", "UM", "US", "UY", "UZ", "VA", "VC", "VE", "VG", "VI",
    "VN", "VU", "WF", "WS", "YE", "YT", "ZA", "ZM", "ZW",
}


@dataclass
class IdentifierPattern:
    """Pattern definition for identifier detection"""
    name: str
    type: str
    pattern: str
    description: str
    validation_func: str = None


# Identifier patterns by type
IDENTIFIER_PATTERNS = [
    # Ukrainian patterns
    IdentifierPattern(
        name="INN_UA_8",
        type="inn",
        pattern=r"\b(?:ИНН|інн|ІПН|inn|ідентифікаційний\s+номер)[:\s]*(\d{8})\b",
        description="Ukrainian INN 8 digits"
    ),
    IdentifierPattern(
        name="INN_UA_10", 
        type="inn",
        pattern=r"\b(?:ИНН|інн|ІПН|inn|ідентифікаційний\s+номер)[:\s]*(\d{10})\b",
        description="Ukrainian INN 10 digits"
    ),
    IdentifierPattern(
        name="INN_UA_12",
        type="inn", 
        pattern=r"\b(?:ИНН|інн|ІПН|inn|ідентифікаційний\s+номер)[:\s]*(\d{12})\b",
        description="Ukrainian INN 12 digits"
    ),
    IdentifierPattern(
        name="EDRPOU_6",
        type="edrpou",
        pattern=r"\b(?:ЄДРПОУ|едрпou|edrpou|єдиний\s+державний\s+реєстр)[:\s]*(\d{6})\b",
        description="Ukrainian EDRPOU 6 digits"
    ),
    IdentifierPattern(
        name="EDRPOU_8",
        type="edrpou", 
        pattern=r"\b(?:ЄДРПОУ|едрпou|edrpou|єдиний\s+державний\s+реєстр)[:\s]*(\d{8})\b",
        description="Ukrainian EDRPOU 8 digits"
    ),
    
    # Russian patterns
    IdentifierPattern(
        name="INN_RU_10",
        type="inn",
        pattern=r"\b(?:ИНН|инн|inn|идентификационный\s+номер)[:\s]*(\d{10})\b",
        description="Russian INN 10 digits"
    ),
    IdentifierPattern(
        name="INN_RU_12",
        type="inn",
        pattern=r"\b(?:ИНН|инн|inn|идентификационный\s+номер)[:\s]*(\d{12})\b", 
        description="Russian INN 12 digits"
    ),
    IdentifierPattern(
        name="OGRN_13",
        type="ogrn",
        pattern=r"\b(?:ОГРН|огрн|ogrn|основной\s+государственный\s+регистрационный\s+номер)[:\s]*(\d{13})\b",
        description="Russian OGRN 13 digits"
    ),
    IdentifierPattern(
        name="OGRNIP_15",
        type="ogrnip",
        pattern=r"\b(?:ОГРНИП|огрнип|ogrnip|основной\s+государственный\s+регистрационный\s+номер\s+индивидуального\s+предпринимателя)[:\s]*(\d{15})\b",
        description="Russian OGRNIP 15 digits"
    ),
    
    # International patterns
    IdentifierPattern(
        name="VAT_EU",
        type="vat",
        pattern=r"\b(?:VAT|vat|НДС|ндс|пдв|ПДВ)[:\s]*([A-Z]{2}\d{8,12})\b",
        description="EU VAT number"
    ),
    IdentifierPattern(
        name="LEI",
        type="lei",
        pattern=r"\b([A-Z0-9]{4}[0-9]{2}[A-Z0-9]{2}[A-Z0-9]{4}[A-Z0-9]{4}[A-Z0-9]{2}[A-Z0-9]{2})\b",
        description="Legal Entity Identifier"
    ),
    IdentifierPattern(
        name="IBAN_GENERIC",
        type="iban",
        pattern=r"\b(?:IBAN[:\s]*)?([A-Z]{2}\s*\d{2}(?:\s*[A-Z0-9]){11,30})\b",
        description="International Bank Account Number"
    ),
    IdentifierPattern(
        name="SWIFT_BIC",
        type="swift_bic",
        pattern=r"\b(?:SWIFT|BIC|SWIFT/BIC|МФО|MFO)[:\s]*([A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b",
        description="SWIFT/BIC code"
    ),
    IdentifierPattern(
        name="EIN_US",
        type="ein",
        pattern=r"\b(?:EIN|ein|федеральный\s+налоговый\s+номер)[:\s]*(\d{2}-\d{7})\b",
        description="US Employer Identification Number"
    ),

    # TIN patterns (Taxpayer Identification Number)
    IdentifierPattern(
        name="TIN_US_9",
        type="inn",
        pattern=r"\b(?:TIN|tin|taxpayer\s+identification\s+number)[:\s]*(\d{9})\b",
        description="US TIN 9 digits"
    ),
    IdentifierPattern(
        name="TIN_US_10",
        type="inn",
        pattern=r"\b(?:TIN|tin|taxpayer\s+identification\s+number)[:\s]*(\d{10})\b",
        description="US TIN 10 digits"
    ),

    IdentifierPattern(
        name="SSN_US",
        type="ssn",
        pattern=r"\b(?:SSN|Social\s+Security\s+Number)?[:\s]*((?:\d{3}-\d{2}-\d{4})|\d{9})\b",
        description="US Social Security Number"
    ),

    # Passport patterns
    IdentifierPattern(
        name="PASSPORT_RF_DIRECT",
        type="passport_rf",
        pattern=r"\b(?:паспорт|серия|passport|series)[:\s]*([А-ЯA-Z]{2}\s*\d{6})\b",
        description="Russian passport with direct context"
    ),
    IdentifierPattern(
        name="PASSPORT_RF_SERIES_NUMBER",
        type="passport_rf",
        pattern=r"\bсерия\s+([А-ЯA-Z]{2})\s+номер\s+(\d{6})\b",
        description="Russian passport series AA номер ######"
    ),
    IdentifierPattern(
        name="PASSPORT_RF_CONTEXT",
        type="passport_rf",
        pattern=r"(?:паспорт|документ|series|passport).*?([А-ЯA-Z]{2}\s*\d{6})",
        description="Russian passport in sentence context"
    ),
    IdentifierPattern(
        name="PASSPORT_UA_DIRECT",
        type="passport_ua",
        pattern=r"\b(?:паспорт|серія|passport)[:\s]*([А-ЯA-Z]{2}\s*\d{6})\b",
        description="Ukrainian passport series-number (old format)"
    ),
    IdentifierPattern(
        name="PASSPORT_UA_ID_CARD",
        type="passport_ua",
        pattern=r"\b(?:ID[\s-]?карт[аи]|айді[\s-]?карт[аи]|паспорт|id[\s-]?card)[:\s]*(\d{9})\b",
        description="Ukrainian ID card (9 digits)"
    ),
    IdentifierPattern(
        name="PASSPORT_UA_GENERIC_9",
        type="passport_ua",
        pattern=r"\b(\d{9})\b(?=.*(?:паспорт|серія|passport|карт|id|документ))",
        description="Ukrainian ID card number in context"
    ),

    # Generic patterns (context-free)
    IdentifierPattern(
        name="INN_GENERIC_8",
        type="inn",
        pattern=r"\b(\d{8})\b(?=.*(?:ИНН|інн|ІПН|inn|tin|идентификационный|ідентифікаційний))",
        description="Generic 8-digit INN in context"
    ),
    IdentifierPattern(
        name="INN_GENERIC_10",
        type="inn", 
        pattern=r"\b(\d{10})\b(?=.*(?:ИНН|інн|ІПН|inn|tin|идентификационный|ідентифікаційний))",
        description="Generic 10-digit INN in context"
    ),
    IdentifierPattern(
        name="INN_GENERIC_12",
        type="inn",
        pattern=r"\b(\d{12})\b(?=.*(?:ИНН|інн|ІПН|inn|tin|идентификационный|ідентифікаційний))",
        description="Generic 12-digit INN in context"
    ),
    IdentifierPattern(
        name="EDRPOU_GENERIC_6",
        type="edrpou",
        pattern=r"\b(\d{6})\b(?=.*(?:ЄДРПОУ|едрпou|edrpou|єдиний|единый))",
        description="Generic 6-digit EDRPOU in context"
    ),
    IdentifierPattern(
        name="EDRPOU_GENERIC_8", 
        type="edrpou",
        pattern=r"\b(\d{8})\b(?=.*(?:ЄДРПОУ|едрпou|edrpou|єдиний|единый))",
        description="Generic 8-digit EDRPOU in context"
    ),
]

# Compiled patterns cache (set to None to force recompilation)
_compiled_patterns_cache: List[Tuple[IdentifierPattern, Pattern]] = None


def get_compiled_patterns_cached() -> List[Tuple[IdentifierPattern, Pattern]]:
    """
    Get compiled regex patterns with caching.
    
    Returns:
        List of tuples (pattern_def, compiled_regex)
    """
    global _compiled_patterns_cache
    
    if _compiled_patterns_cache is None:
        _compiled_patterns_cache = []
        for pattern_def in IDENTIFIER_PATTERNS:
            try:
                compiled = re.compile(pattern_def.pattern, re.IGNORECASE)
                _compiled_patterns_cache.append((pattern_def, compiled))
            except re.error as e:
                # Skip invalid patterns
                continue
    
    return _compiled_patterns_cache


def normalize_identifier(value: str, identifier_type: str) -> str:
    """
    Normalize identifier value by removing formatting.
    
    Args:
        value: Raw identifier value
        identifier_type: Type of identifier (inn, edrpou, etc.)
        
    Returns:
        Normalized identifier value
    """
    if not value:
        return value
    
    # Remove common formatting characters
    normalized = re.sub(r'[^\w]', '', value.upper())
    
    # Type-specific normalization
    if identifier_type in ['inn', 'edrpou', 'ogrn', 'ogrnip']:
        # Keep only digits
        normalized = re.sub(r'[^\d]', '', normalized)
    elif identifier_type == 'vat':
        # Keep letters and digits
        normalized = re.sub(r'[^A-Z0-9]', '', normalized)
    elif identifier_type == 'lei':
        # Keep letters and digits, ensure uppercase
        normalized = re.sub(r'[^A-Z0-9]', '', normalized.upper())
    elif identifier_type == 'iban':
        normalized = re.sub(r'\s+', '', normalized.upper())
    elif identifier_type == 'swift_bic':
        normalized = re.sub(r'[^A-Z0-9]', '', normalized.upper())
    elif identifier_type == 'ein':
        # Keep only digits and hyphens
        normalized = re.sub(r'[^\d-]', '', normalized)
    elif identifier_type == 'ssn':
        normalized = re.sub(r'[^\d]', '', normalized)
    elif identifier_type in ['passport_rf', 'passport_ua']:
        # Keep letters and digits, remove spaces between series and number
        normalized = re.sub(r'[^A-ZА-Я0-9]', '', normalized.upper())
        # Format as AA###### for series-number format or ######### for ID cards
        if len(normalized) == 8:  # 2 letters + 6 digits
            normalized = normalized[:2] + normalized[2:]
        elif len(normalized) == 9:  # Ukrainian ID card - just digits
            normalized = re.sub(r'[^\d]', '', normalized)
    
    return normalized


def get_validation_function(identifier_type: str):
    """
    Get validation function for identifier type.

    Args:
        identifier_type: Type of identifier

    Returns:
        Validation function callable or None
    """
    validation_functions = {
        'inn': validate_inn,
        'edrpou': validate_edrpou,
        'ogrn': validate_ogrn,
        'ogrnip': validate_ogrnip,
        'vat': validate_vat,
        'lei': validate_lei,
        'ein': validate_ein,
        'iban': validate_iban,
        'swift_bic': validate_swift_bic,
        'ssn': validate_ssn,
    }
    return validation_functions.get(identifier_type)


def validate_inn(value: str) -> bool:
    """Validate INN checksum using Russian/Ukrainian algorithms"""
    if not value or not value.isdigit():
        return False

    if len(value) not in [10, 12]:
        return False

    # INN checksum validation
    if len(value) == 10:
        # 10-digit INN (legal entities)
        check_weights = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        check_sum = sum(int(value[i]) * check_weights[i] for i in range(9))
        check_digit = check_sum % 11
        if check_digit > 9:
            check_digit = check_digit % 10
        return int(value[9]) == check_digit

    elif len(value) == 12:
        # 12-digit INN (individual entrepreneurs)
        # First check digit
        check_weights_1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        check_sum_1 = sum(int(value[i]) * check_weights_1[i] for i in range(10))
        check_digit_1 = check_sum_1 % 11
        if check_digit_1 > 9:
            check_digit_1 = check_digit_1 % 10

        # Second check digit
        check_weights_2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        check_sum_2 = sum(int(value[i]) * check_weights_2[i] for i in range(11))
        check_digit_2 = check_sum_2 % 11
        if check_digit_2 > 9:
            check_digit_2 = check_digit_2 % 10

        return (int(value[10]) == check_digit_1 and
                int(value[11]) == check_digit_2)

    return False


def validate_edrpou(value: str) -> bool:
    """Validate EDRPOU checksum using Ukrainian algorithm"""
    if not value or not value.isdigit():
        return False

    if len(value) not in [6, 8]:
        return False

    # EDRPOU checksum validation
    if len(value) == 8:
        # 8-digit EDRPOU with check digit
        check_weights = [1, 2, 3, 4, 5, 6, 7]
        check_sum = sum(int(value[i]) * check_weights[i] for i in range(7))
        check_digit = check_sum % 11

        if check_digit > 9:
            # If result > 9, use alternative weights
            alt_weights = [3, 4, 5, 6, 7, 8, 9]
            check_sum = sum(int(value[i]) * alt_weights[i] for i in range(7))
            check_digit = check_sum % 11
            if check_digit > 9:
                check_digit = 0

        return int(value[7]) == check_digit

    elif len(value) == 6:
        # 6-digit EDRPOU (no check digit, only length validation)
        return True

    return False


def validate_ogrn(value: str) -> bool:
    """Validate OGRN checksum using Russian algorithm"""
    if not value or not value.isdigit():
        return False

    if len(value) != 13:
        return False

    # OGRN checksum validation for 13-digit numbers
    # Take first 12 digits, divide by 11, remainder should match 13th digit
    first_12 = int(value[:12])
    check_digit = first_12 % 11

    # If remainder is 10, check digit should be 0
    if check_digit == 10:
        check_digit = 0

    return int(value[12]) == check_digit


def validate_ogrnip(value: str) -> bool:
    """Validate OGRNIP checksum using Russian algorithm"""
    if not value or not value.isdigit():
        return False

    if len(value) != 15:
        return False

    # OGRNIP checksum validation for 15-digit numbers
    # Take first 14 digits, divide by 13, remainder should match 15th digit
    first_14 = int(value[:14])
    check_digit = first_14 % 13

    # If remainder is 10, 11, or 12, check digit should be 0
    if check_digit >= 10:
        check_digit = check_digit % 10

    return int(value[14]) == check_digit


def validate_vat(value: str) -> bool:
    """Validate VAT number"""
    if not value:
        return False
    
    # Basic format validation for EU VAT
    if re.match(r'^[A-Z]{2}\d{8,12}$', value):
        return True
    
    return False


def validate_lei(value: str) -> bool:
    """Validate LEI"""
    if not value:
        return False
    
    # LEI is exactly 20 characters
    if len(value) == 20 and re.match(r'^[A-Z0-9]{20}$', value):
        return True
    
    return False


def validate_ein(value: str) -> bool:
    """Validate EIN"""
    if not value:
        return False

    digits_only = re.sub(r'[^\d]', '', value)
    if len(digits_only) != 9 or not digits_only.isdigit():
        return False

    prefix = digits_only[:2]
    valid_prefixes = {
        '01', '02', '03', '04', '05', '06',
        '10', '11', '12', '13', '14', '15', '16',
        '20', '21', '22', '23', '24', '25', '26', '27',
        '30', '31', '32', '33', '34', '35', '36', '37', '38', '39',
        '40', '41', '42', '43', '44', '45', '46', '47', '48',
        '50', '51', '52', '53', '54', '55', '56', '57', '58', '59',
        '60', '61', '62', '63', '64', '65', '66', '67', '68',
        '71', '72', '73', '74', '75', '76', '77',
        '80', '81', '82', '83', '84', '85', '86', '87', '88',
        '90', '91', '92', '93', '94', '95', '98', '99',
    }

    if prefix not in valid_prefixes:
        return False

    # If formatted with hyphen, ensure placement is correct
    if '-' in value and not re.match(r'^\d{2}-\d{7}$', value):
        return False

    return True


def validate_iban(value: str) -> bool:
    """Validate IBAN using ISO 7064 mod-97-10."""
    if not value:
        return False

    normalized = re.sub(r'\s+', '', value.upper())
    if not 15 <= len(normalized) <= 34:
        return False
    if not re.fullmatch(r'[A-Z0-9]+', normalized):
        return False

    rearranged = normalized[4:] + normalized[:4]
    remainder = 0
    for char in rearranged:
        if char.isdigit():
            remainder = (remainder * 10 + int(char)) % 97
        else:
            remainder = (remainder * 100 + (ord(char) - 55)) % 97

    return remainder == 1


def validate_swift_bic(value: str) -> bool:
    """Validate SWIFT/BIC format and structural rules."""
    if not value:
        return False

    normalized = re.sub(r'\s+', '', value.upper())
    if len(normalized) not in (8, 11):
        return False

    if not re.fullmatch(r'[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?', normalized):
        return False

    country_code = normalized[4:6]
    if country_code not in ISO_COUNTRY_CODES:
        return False

    location_code = normalized[6:8]
    if location_code in {"00", "0O", "O0", "OO"}:
        return False

    if len(normalized) == 11:
        branch_code = normalized[8:]
        if branch_code.upper() == "XXX":
            return True
        if branch_code == "000":
            return False

    return True


def validate_ssn(value: str) -> bool:
    """Validate US Social Security Number."""
    if not value:
        return False

    digits_only = re.sub(r'[^\d]', '', value)
    if len(digits_only) != 9:
        return False

    area, group, serial = digits_only[:3], digits_only[3:5], digits_only[5:]

    if area == '000' or area == '666' or '900' <= area <= '999':
        return False
    if group == '00' or serial == '0000':
        return False

    # Exclude well-known invalid SSNs that routinely appear in fraud datasets
    if digits_only in {'078051120', '219099999'}:
        return False

    return True


def extract_identifiers(text: str, identifier_types: List[str] = None) -> List[Dict]:
    """
    Extract all identifiers from text.
    
    Args:
        text: Text to search in
        identifier_types: List of identifier types to search for (None for all)
        
    Returns:
        List of found identifiers with metadata
    """
    if identifier_types is None:
        identifier_types = ['inn', 'edrpou', 'ogrn', 'ogrnip', 'vat', 'lei', 'ein', 'iban', 'swift_bic', 'ssn']
    
    found_identifiers = []
    
    for pattern_def, compiled_regex in get_compiled_patterns_cached():
        if identifier_types and pattern_def.type not in identifier_types:
            continue
        
        for match in compiled_regex.finditer(text):
            raw_value = match.group(1) if match.groups() else match.group(0)
            normalized_value = normalize_identifier(raw_value, pattern_def.type)
            
            # Validate if validation function exists
            validator = get_validation_function(pattern_def.type)
            is_valid = True
            if validator:
                is_valid = validator(normalized_value)
            
            confidence = 0.9 if is_valid else 0.6
            
            found_identifiers.append({
                "type": pattern_def.type,
                "value": normalized_value,
                "raw": match.group(0),
                "name": pattern_def.name,
                "description": pattern_def.description,
                "confidence": confidence,
                "position": match.span(),
                "valid": is_valid,
            })
    
    return found_identifiers

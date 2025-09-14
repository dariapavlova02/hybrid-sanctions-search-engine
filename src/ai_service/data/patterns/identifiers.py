"""
Identifier Patterns

Contains patterns and utilities for detecting various types of identifiers
(INN, EDRPOU, VAT, LEI, etc.) in different formats.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Pattern, Tuple


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
        pattern=r"\b(?:ИНН|інн|inn|ідентифікаційний\s+номер)[:\s]*(\d{8})\b",
        description="Ukrainian INN 8 digits"
    ),
    IdentifierPattern(
        name="INN_UA_10", 
        type="inn",
        pattern=r"\b(?:ИНН|інн|inn|ідентифікаційний\s+номер)[:\s]*(\d{10})\b",
        description="Ukrainian INN 10 digits"
    ),
    IdentifierPattern(
        name="INN_UA_12",
        type="inn", 
        pattern=r"\b(?:ИНН|інн|inn|ідентифікаційний\s+номер)[:\s]*(\d{12})\b",
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
        name="EIN_US",
        type="ein",
        pattern=r"\b(?:EIN|ein|федеральный\s+налоговый\s+номер)[:\s]*(\d{2}-\d{7})\b",
        description="US Employer Identification Number"
    ),
    
    # Generic patterns (context-free)
    IdentifierPattern(
        name="INN_GENERIC_8",
        type="inn",
        pattern=r"\b(\d{8})\b(?=.*(?:ИНН|інн|inn|идентификационный|ідентифікаційний))",
        description="Generic 8-digit INN in context"
    ),
    IdentifierPattern(
        name="INN_GENERIC_10",
        type="inn", 
        pattern=r"\b(\d{10})\b(?=.*(?:ИНН|інн|inn|идентификационный|ідентифікаційний))",
        description="Generic 10-digit INN in context"
    ),
    IdentifierPattern(
        name="INN_GENERIC_12",
        type="inn",
        pattern=r"\b(\d{12})\b(?=.*(?:ИНН|інн|inn|идентификационный|ідентифікаційний))",
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

# Compiled patterns cache
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
    elif identifier_type == 'ein':
        # Keep only digits and hyphens
        normalized = re.sub(r'[^\d-]', '', normalized)
    
    return normalized


def get_validation_function(identifier_type: str) -> str:
    """
    Get validation function name for identifier type.
    
    Args:
        identifier_type: Type of identifier
        
    Returns:
        Validation function name or None
    """
    validation_functions = {
        'inn': 'validate_inn',
        'edrpou': 'validate_edrpou', 
        'ogrn': 'validate_ogrn',
        'ogrnip': 'validate_ogrnip',
        'vat': 'validate_vat',
        'lei': 'validate_lei',
        'ein': 'validate_ein',
    }
    return validation_functions.get(identifier_type)


def validate_inn(value: str) -> bool:
    """Validate INN checksum"""
    if not value or not value.isdigit():
        return False
    
    if len(value) not in [10, 12]:
        return False
    
    # Basic length validation for now
    # TODO: Implement actual checksum validation
    return True


def validate_edrpou(value: str) -> bool:
    """Validate EDRPOU"""
    if not value or not value.isdigit():
        return False
    
    if len(value) not in [6, 8]:
        return False
    
    # Basic length validation for now
    # TODO: Implement actual checksum validation
    return True


def validate_ogrn(value: str) -> bool:
    """Validate OGRN"""
    if not value or not value.isdigit():
        return False
    
    if len(value) != 13:
        return False
    
    # Basic length validation for now
    # TODO: Implement actual checksum validation
    return True


def validate_ogrnip(value: str) -> bool:
    """Validate OGRNIP"""
    if not value or not value.isdigit():
        return False
    
    if len(value) != 15:
        return False
    
    # Basic length validation for now
    # TODO: Implement actual checksum validation
    return True


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
    
    # EIN format: XX-XXXXXXX
    if re.match(r'^\d{2}-\d{7}$', value):
        return True
    
    return False


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
        identifier_types = ['inn', 'edrpou', 'ogrn', 'ogrnip', 'vat', 'lei', 'ein']
    
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
                validation_func = globals().get(validator)
                if validation_func:
                    is_valid = validation_func(normalized_value)
            
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

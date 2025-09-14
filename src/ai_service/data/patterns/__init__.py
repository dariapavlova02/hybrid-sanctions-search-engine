"""
Data Patterns Module

Contains pattern definitions and utilities for various data extraction tasks.
"""

from .legal_forms import (
    ALL_LEGAL_FORMS,
    ALL_LEGAL_FORMS_REGEX,
    LEGAL_FORMS,
    LEGAL_FORMS_REGEX,
    LEGAL_FORM_REGEX,
    ORGANIZATION_NAME_REGEX,
    QUOTED_CORE_REGEX,
    extract_legal_forms,
    get_legal_form_full_name,
    get_legal_forms_regex,
    get_legal_forms_set,
    is_legal_form,
    normalize_legal_form,
)

from .identifiers import (
    IDENTIFIER_PATTERNS,
    extract_identifiers,
    get_compiled_patterns_cached,
    get_validation_function,
    normalize_identifier,
    validate_ein,
    validate_edrpou,
    validate_inn,
    validate_lei,
    validate_ogrn,
    validate_ogrnip,
    validate_vat,
)

from .dates import (
    DATE_PATTERNS,
    MONTH_NAMES,
    extract_birthdates_from_text,
    extract_dates_near_text,
    format_date_iso,
    get_compiled_patterns,
    is_valid_date,
)

__all__ = [
    # Legal forms
    "ALL_LEGAL_FORMS",
    "ALL_LEGAL_FORMS_REGEX", 
    "LEGAL_FORMS",
    "LEGAL_FORMS_REGEX",
    "LEGAL_FORM_REGEX",
    "ORGANIZATION_NAME_REGEX",
    "QUOTED_CORE_REGEX",
    "extract_legal_forms",
    "get_legal_form_full_name",
    "get_legal_forms_regex",
    "get_legal_forms_set",
    "is_legal_form",
    "normalize_legal_form",
    
    # Identifiers
    "IDENTIFIER_PATTERNS",
    "extract_identifiers",
    "get_compiled_patterns_cached",
    "get_validation_function",
    "normalize_identifier",
    "validate_ein",
    "validate_edrpou", 
    "validate_inn",
    "validate_lei",
    "validate_ogrn",
    "validate_ogrnip",
    "validate_vat",
    
    # Dates
    "DATE_PATTERNS",
    "MONTH_NAMES",
    "extract_birthdates_from_text",
    "extract_dates_near_text",
    "format_date_iso",
    "get_compiled_patterns",
    "is_valid_date",
]

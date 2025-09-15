"""
Morphology module for name normalization.

This module provides gender rules and morphological processing
for Russian and Ukrainian names.
"""

from .gender_rules import (
    looks_like_feminine_ru,
    looks_like_feminine_uk,
    to_feminine_nominative_ru,
    to_feminine_nominative_uk,
    is_invariable_surname,
    infer_gender_evidence,
    feminine_nominative_from,
    convert_given_name_to_nominative,
    convert_given_name_to_nominative_ru,
    convert_given_name_to_nominative_uk,
    get_female_given_names,
    FEMALE_PATRONYMIC_SUFFIXES_RU,
    FEMALE_PATRONYMIC_SUFFIXES_UK,
    INVARIABLE_SURNAME_SUFFIXES,
)

__all__ = [
    "looks_like_feminine_ru",
    "looks_like_feminine_uk", 
    "to_feminine_nominative_ru",
    "to_feminine_nominative_uk",
    "is_invariable_surname",
    "infer_gender_evidence",
    "feminine_nominative_from",
    "convert_given_name_to_nominative",
    "convert_given_name_to_nominative_ru",
    "convert_given_name_to_nominative_uk",
    "get_female_given_names",
    "FEMALE_PATRONYMIC_SUFFIXES_RU",
    "FEMALE_PATRONYMIC_SUFFIXES_UK",
    "INVARIABLE_SURNAME_SUFFIXES",
]

"""
Lexicon loader for role classification.

Loads stopwords, legal forms, and payment context words from lexicon files.
"""

import os
import json
from pathlib import Path
from typing import Dict, Set, Optional
from dataclasses import dataclass


@dataclass
class Lexicons:
    """Container for all loaded lexicons."""
    stopwords: Dict[str, Set[str]]  # lang -> set of stopwords
    stopwords_init: Dict[str, Set[str]]  # lang -> set of stopwords for initials conflict prevention
    stopwords_person: Dict[str, Set[str]]  # lang -> set of person stopwords
    legal_forms: Set[str]  # case-insensitive legal forms
    legal_forms_lang: Dict[str, Set[str]]  # lang -> set of legal forms
    payment_context: Set[str]  # payment context words


def load_lexicons(base_path: Optional[Path] = None) -> Lexicons:
    """
    Load all lexicons from the data/lexicons directory.
    
    Args:
        base_path: Base path to lexicon files. If None, uses default location.
        
    Returns:
        Lexicons object with loaded data.
    """
    if base_path is None:
        # Default to project root/data/lexicons
        # Try to find the project root by looking for pyproject.toml
        current_path = Path(__file__).parent
        while current_path != current_path.parent:
            if (current_path / "pyproject.toml").exists():
                base_path = current_path / "data" / "lexicons"
                break
            current_path = current_path.parent
        else:
            # Fallback to relative path from current file
            base_path = Path(__file__).parent.parent.parent.parent / "data" / "lexicons"
    
    stopwords = {}
    stopwords_init = {}
    stopwords_person = {}
    legal_forms = set()
    legal_forms_lang = {}
    payment_context = set()
    
    # Load stopwords for each language
    for lang in ["ru", "uk", "en"]:
        stopwords_file = base_path / f"stopwords_{lang}.txt"
        if stopwords_file.exists():
            stopwords[lang] = _load_word_list(stopwords_file)
        else:
            stopwords[lang] = set()
    
    # Load stopwords for initials conflict prevention
    for lang in ["ru", "uk", "en"]:
        stopwords_init_file = base_path / f"{lang}_stopwords_init.txt"
        if stopwords_init_file.exists():
            stopwords_init[lang] = _load_word_list(stopwords_init_file)
        else:
            stopwords_init[lang] = set()
    
    # Load person stopwords for each language
    for lang in ["ru", "uk", "en"]:
        stopwords_person_file = base_path / f"stopwords_person_{lang}.json"
        if stopwords_person_file.exists():
            stopwords_person[lang] = _load_json_word_list(stopwords_person_file, lang)
        else:
            stopwords_person[lang] = set()
    
    # Load legal forms
    legal_forms_file = base_path / "legal_forms.txt"
    if legal_forms_file.exists():
        legal_forms = _load_word_list(legal_forms_file)
    
    # Load legal forms for each language
    for lang in ["ru", "uk", "en"]:
        legal_forms_lang_file = base_path / f"legal_forms_{lang}.json"
        if legal_forms_lang_file.exists():
            legal_forms_lang[lang] = _load_json_word_list(legal_forms_lang_file, lang)
        else:
            legal_forms_lang[lang] = set()
    
    # Load payment context
    payment_context_file = base_path / "payment_context.txt"
    if payment_context_file.exists():
        payment_context = _load_word_list(payment_context_file)
    
    return Lexicons(
        stopwords=stopwords,
        stopwords_init=stopwords_init,
        stopwords_person=stopwords_person,
        legal_forms=legal_forms,
        legal_forms_lang=legal_forms_lang,
        payment_context=payment_context
    )


def _load_word_list(file_path: Path) -> Set[str]:
    """
    Load a word list from a file, trimming whitespace and skipping comments.
    
    Args:
        file_path: Path to the word list file.
        
    Returns:
        Set of words from the file.
    """
    words = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    words.add(line.lower())
    except Exception as e:
        # Log error but don't fail - return empty set
        print(f"Warning: Could not load {file_path}: {e}")
    
    return words


def _load_json_word_list(file_path: Path, lang: str) -> Set[str]:
    """
    Load a word list from a JSON file with language-specific structure.
    
    Args:
        file_path: Path to the JSON file.
        lang: Language code to extract from JSON.
        
    Returns:
        Set of words from the file for the specified language.
    """
    words = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if lang in data and isinstance(data[lang], list):
                words = set(word.lower() for word in data[lang] if isinstance(word, str))
    except Exception as e:
        # Log error but don't fail - return empty set
        print(f"Warning: Could not load {file_path}: {e}")
    
    return words


# Global lexicon cache
_lexicon_cache: Optional[Lexicons] = None


def get_lexicons() -> Lexicons:
    """
    Get lexicons with caching.
    
    Returns:
        Cached Lexicons object.
    """
    global _lexicon_cache
    if _lexicon_cache is None:
        _lexicon_cache = load_lexicons()
    return _lexicon_cache


def is_stopword(word: str, language: str) -> bool:
    """
    Check if a word is a stopword for the given language.
    
    Args:
        word: Word to check
        language: Language code
        
    Returns:
        True if the word is a stopword
    """
    lexicons = get_lexicons()
    return word.lower() in lexicons.stopwords.get(language, set())


def is_legal_form(word: str) -> bool:
    """
    Check if a word is a legal form.
    
    Args:
        word: Word to check
        
    Returns:
        True if the word is a legal form
    """
    lexicons = get_lexicons()
    return word.lower() in lexicons.legal_forms


def clear_lexicon_cache():
    """Clear the lexicon cache (useful for testing)."""
    global _lexicon_cache
    _lexicon_cache = None
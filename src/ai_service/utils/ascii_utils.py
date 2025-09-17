"""
ASCII utilities for fastpath optimization.
"""

import re
from typing import List, Tuple, Optional
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


def is_ascii_name(text: str) -> bool:
    """
    Check if text contains only ASCII characters suitable for fastpath processing.
    
    Args:
        text: Input text to check
        
    Returns:
        True if text is ASCII and suitable for fastpath, False otherwise
    """
    if not text or not text.strip():
        return False
    
    # Check if text is purely ASCII
    if not text.isascii():
        return False
    
    # Check if text contains only letters, spaces, hyphens, apostrophes, and dots
    # This covers typical name patterns: "John Smith", "Mary-Jane", "O'Connor", "J. R. R. Tolkien"
    if not re.match(r'^[A-Za-z\s\-\'\.]+$', text):
        return False
    
    # Check if text has reasonable length (not too short, not too long)
    if len(text.strip()) < 2 or len(text.strip()) > 100:
        return False
    
    return True


def is_ascii_token(token: str) -> bool:
    """
    Check if a single token is ASCII and suitable for fastpath processing.
    
    Args:
        token: Single token to check
        
    Returns:
        True if token is ASCII and suitable for fastpath, False otherwise
    """
    if not token or not token.strip():
        return False
    
    # Check if token is purely ASCII
    if not token.isascii():
        return False
    
    # Check if token contains only letters, hyphens, apostrophes, and dots
    if not re.match(r'^[A-Za-z\-\'\.]+$', token):
        return False
    
    # Check if token has reasonable length
    if len(token.strip()) < 1 or len(token.strip()) > 50:
        return False
    
    return True


def extract_ascii_tokens(text: str) -> List[str]:
    """
    Extract ASCII tokens from text for fastpath processing.
    
    Args:
        text: Input text
        
    Returns:
        List of ASCII tokens
    """
    if not text or not text.strip():
        return []
    
    # Split on whitespace and filter ASCII tokens
    tokens = text.split()
    ascii_tokens = [token for token in tokens if is_ascii_token(token)]
    
    return ascii_tokens


def ascii_fastpath_normalize(text: str, language: str = "en") -> Tuple[List[str], List[str], str]:
    """
    Fast ASCII-only normalization without heavy Unicode/morphology operations.
    
    This function provides a lightweight alternative to the full normalization
    pipeline for ASCII names, maintaining the same output format.
    
    Args:
        text: ASCII text to normalize
        language: Language code (default: "en")
        
    Returns:
        Tuple of (tokens, roles, normalized_text)
    """
    if not is_ascii_name(text):
        raise ValueError("Text is not suitable for ASCII fastpath")
    
    # Basic tokenization - split on whitespace
    tokens = text.strip().split()
    
    # Simple role classification for ASCII names
    roles = []
    for token in tokens:
        # Remove punctuation for role classification
        clean_token = re.sub(r'[^\w]', '', token.lower())
        
        if len(clean_token) == 1 and clean_token.isalpha():
            # Single letter - likely initial
            roles.append("initial")
        elif clean_token in _get_common_given_names(language):
            # Common given name
            roles.append("given")
        elif clean_token in _get_common_surnames(language):
            # Common surname
            roles.append("surname")
        else:
            # Unknown - classify as given if capitalized, surname otherwise
            if token[0].isupper():
                roles.append("given")
            else:
                roles.append("surname")
    
    # Basic normalization - title case for names
    normalized_tokens = []
    for token in tokens:
        if token.isupper() and len(token) > 1:
            # All caps -> Title Case
            normalized_tokens.append(token.title())
        elif token.islower() and len(token) > 1:
            # All lowercase -> Title Case
            normalized_tokens.append(token.title())
        else:
            # Keep as is (handles initials, mixed case, etc.)
            normalized_tokens.append(token)
    
    normalized_text = " ".join(normalized_tokens)
    
    return normalized_tokens, roles, normalized_text


def _get_common_given_names(language: str) -> set:
    """Get common given names for ASCII fastpath."""
    # This is a minimal set for fastpath - full dictionaries are loaded elsewhere
    common_names = {
        "en": {
            "john", "jane", "michael", "sarah", "david", "mary", "robert", "jennifer",
            "william", "elizabeth", "james", "patricia", "richard", "linda", "charles",
            "barbara", "thomas", "susan", "christopher", "jessica", "daniel", "sarah",
            "matthew", "karen", "anthony", "nancy", "mark", "lisa", "donald", "betty",
            "steven", "helen", "paul", "sandra", "andrew", "donna", "joshua", "carol",
            "kenneth", "ruth", "kevin", "sharon", "brian", "michelle", "george", "laura",
            "edward", "sarah", "ronald", "kimberly", "timothy", "deborah", "jason", "dorothy",
            "jeffrey", "lisa", "ryan", "nancy", "jacob", "karen", "gary", "betty",
            "nicholas", "helen", "eric", "sandra", "jonathan", "donna", "stephen", "carol",
            "larry", "ruth", "justin", "sharon", "scott", "michelle", "brandon", "laura",
            "benjamin", "sarah", "samuel", "kimberly", "gregory", "deborah", "alexander", "dorothy"
        }
    }
    
    return common_names.get(language, set())


def _get_common_surnames(language: str) -> set:
    """Get common surnames for ASCII fastpath."""
    # This is a minimal set for fastpath - full dictionaries are loaded elsewhere
    common_surnames = {
        "en": {
            "smith", "johnson", "williams", "brown", "jones", "garcia", "miller", "davis",
            "rodriguez", "martinez", "hernandez", "lopez", "gonzalez", "wilson", "anderson",
            "thomas", "taylor", "moore", "jackson", "martin", "lee", "perez", "thompson",
            "white", "harris", "sanchez", "clark", "ramirez", "lewis", "robinson", "walker",
            "young", "allen", "king", "wright", "scott", "torres", "nguyen", "hill",
            "flores", "green", "adams", "nelson", "baker", "hall", "rivera", "campbell",
            "mitchell", "carter", "roberts", "gomez", "phillips", "evans", "turner", "diaz",
            "parker", "cruz", "edwards", "collins", "reyes", "stewart", "morris", "morales",
            "murphy", "cook", "rogers", "gutierrez", "ortiz", "morgan", "cooper", "peterson",
            "bailey", "reed", "kelly", "howard", "ramos", "kim", "cox", "ward", "richardson",
            "watson", "brooks", "chavez", "wood", "james", "bennett", "gray", "mendoza",
            "ruiz", "hughes", "price", "alvarez", "castillo", "sanders", "patel", "myers",
            "long", "ross", "foster", "jimenez"
        }
    }
    
    return common_surnames.get(language, set())


def validate_ascii_fastpath_equivalence(
    text: str, 
    fastpath_result: Tuple[List[str], List[str], str],
    full_result: Tuple[List[str], List[str], str]
) -> bool:
    """
    Validate that ASCII fastpath produces equivalent results to full normalization.
    
    Args:
        text: Original input text
        fastpath_result: Result from ASCII fastpath
        full_result: Result from full normalization pipeline
        
    Returns:
        True if results are equivalent, False otherwise
    """
    fastpath_tokens, fastpath_roles, fastpath_text = fastpath_result
    full_tokens, full_roles, full_text = full_result
    
    # Check if token counts match
    if len(fastpath_tokens) != len(full_tokens):
        logger.warning(f"Token count mismatch: fastpath={len(fastpath_tokens)}, full={len(full_tokens)}")
        return False
    
    # Check if roles match
    if fastpath_roles != full_roles:
        logger.warning(f"Role mismatch: fastpath={fastpath_roles}, full={full_roles}")
        return False
    
    # Check if normalized text is similar (allowing for minor differences)
    if fastpath_text.lower() != full_text.lower():
        logger.warning(f"Text mismatch: fastpath='{fastpath_text}', full='{full_text}'")
        return False
    
    return True

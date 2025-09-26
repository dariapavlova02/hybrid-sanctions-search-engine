"""
Name permutation utilities for improving homoglyph detection
"""

from typing import List, Set
import re


def generate_name_permutations(query: str) -> List[str]:
    """
    Generate name permutations to improve search recall.

    Args:
        query: Original query string

    Returns:
        List of query permutations including original

    Examples:
        "John Smith" -> ["John Smith", "Smith John"]
        "Anna Maria Ivanova" -> ["Anna Maria Ivanova", "Ivanova Anna Maria", "Maria Anna Ivanova", ...]
    """
    if not query or not query.strip():
        return [query]

    # Clean and tokenize
    tokens = re.findall(r'\b[A-Za-zА-Яа-яёЁІіЇїЄєʼ]+\b', query.strip())

    if len(tokens) < 2:
        # Single word - no permutations needed
        return [query]

    if len(tokens) == 2:
        # Two words - simple swap
        original = ' '.join(tokens)
        swapped = f"{tokens[1]} {tokens[0]}"
        return [original, swapped] if swapped != original else [original]

    if len(tokens) == 3:
        # Three words - common patterns for names
        # Assume: [Given] [Middle/Patronymic] [Surname]
        given, middle, surname = tokens

        permutations = [
            f"{given} {middle} {surname}",      # Original: Given Middle Surname
            f"{surname} {given} {middle}",      # Surname Given Middle
            f"{given} {surname}",               # Given Surname (no middle)
            f"{surname} {given}",               # Surname Given (no middle)
        ]

        # Remove duplicates and empty
        return list(dict.fromkeys(perm for perm in permutations if perm.strip()))

    # More than 3 words - generate key patterns only to avoid explosion
    if len(tokens) > 3:
        # Assume first = given, last = surname, middle = everything else
        given = tokens[0]
        surname = tokens[-1]
        middle_parts = tokens[1:-1]

        permutations = [
            ' '.join(tokens),                           # Original order
            f"{surname} {given} {' '.join(middle_parts)}" if middle_parts else f"{surname} {given}",  # Surname first
            f"{given} {surname}",                       # Given Surname only
            f"{surname} {given}",                       # Surname Given only
        ]

        return list(dict.fromkeys(perm for perm in permutations if perm.strip()))

    return [query]


def generate_homoglyph_permutations(original_query: str, normalized_query: str) -> List[str]:
    """
    Generate permutations for both original and normalized queries.

    Args:
        original_query: Query with homoglyphs
        normalized_query: Query after homoglyph normalization

    Returns:
        List of all permutations to try for search
    """
    if not original_query or not normalized_query:
        return [original_query or normalized_query]

    # Generate permutations for normalized query (main target)
    normalized_perms = generate_name_permutations(normalized_query)

    # If queries are different (homoglyphs detected), also try original permutations
    if original_query != normalized_query:
        original_perms = generate_name_permutations(original_query)
        # Combine and deduplicate
        all_perms = normalized_perms + original_perms
        return list(dict.fromkeys(all_perms))

    return normalized_perms


def get_best_permutation_results(search_results_list: List[tuple]) -> tuple:
    """
    Select best results from multiple permutation searches.

    Args:
        search_results_list: List of (query, search_results) tuples

    Returns:
        (best_query, best_results) tuple
    """
    if not search_results_list:
        return (None, None)

    # Find permutation with highest scoring result
    best_query = None
    best_results = None
    best_score = 0.0

    for query, results in search_results_list:
        if results and hasattr(results, 'candidates') and results.candidates:
            # Get highest score from this permutation
            top_score = max((getattr(c, 'score', 0.0) or getattr(c, 'final_score', 0.0))
                          for c in results.candidates)

            if top_score > best_score:
                best_score = top_score
                best_query = query
                best_results = results

    # If no results found, return first permutation
    if best_results is None and search_results_list:
        best_query, best_results = search_results_list[0]

    return (best_query, best_results)
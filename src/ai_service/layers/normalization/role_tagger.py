"""
Role tagger for token classification.

Classifies tokens as stopwords, organizations, or person candidates based on
lexicons and context rules.
"""

import re
from typing import List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from .lexicon_loader import Lexicons


class TokenRole(Enum):
    """Token role classification."""
    STOPWORD = "stopword"
    ORGANIZATION = "organization"
    PERSON_CANDIDATE = "person_candidate"
    UNKNOWN = "unknown"


@dataclass
class RoleTag:
    """Role tag for a token."""
    token: str
    role: TokenRole
    span_id: Optional[int] = None
    confidence: float = 1.0
    reason: str = ""


class RoleTagger:
    """Role tagger for token classification."""
    
    def __init__(self, lexicons: Lexicons, window: int = 3):
        """
        Initialize role tagger.

        Args:
            lexicons: Loaded lexicons
            window: Context window size for organization detection
        """
        self.lexicons = lexicons
        self.window = window
        
        # Pre-compile patterns for efficiency
        self._uppercase_pattern = re.compile(r'^[А-ЯA-Z]{2,}$')
        self._legal_form_pattern = re.compile(
            r'^(' + '|'.join(re.escape(form) for form in lexicons.legal_forms) + r')$',
            re.IGNORECASE
        )
        
        # Pre-compile additional common patterns
        self._initial_pattern = re.compile(r'^[A-Za-zА-ЯЁІЇЄҐ]\.$')
        self._punctuation_pattern = re.compile(r'^[^\w\s]+$')
        self._cyrillic_pattern = re.compile(r'[А-Яа-яЁёІіЇїЄєҐґ]')
        self._latin_pattern = re.compile(r'[A-Za-z]')
    
    def tag(self, tokens: List[str], language: str) -> List[RoleTag]:
        """
        Tag tokens with roles based on lexicons and context rules.

        Args:
            tokens: List of tokens to tag
            language: Language code (ru, uk, en)

        Returns:
            List of RoleTag objects
        """
        if not tokens:
            return []

        # Get stopwords for the language
        stopwords = self.lexicons.stopwords.get(language, set())
        
        # First pass: tag stopwords and identify legal forms
        tags = []
        legal_form_indices = []
        
        for i, token in enumerate(tokens):
            token_lower = token.lower()
            
            # Check if token is a stopword
            if token_lower in stopwords:
                tags.append(RoleTag(
                    token=token,
                    role=TokenRole.STOPWORD,
                    reason="stopword"
                ))
            # Check if token is a legal form
            elif self._is_legal_form(token):
                legal_form_indices.append(i)
                tags.append(RoleTag(
                    token=token,
                    role=TokenRole.UNKNOWN,  # Will be updated in second pass
                    reason="legal_form"
                ))
            else:
                tags.append(RoleTag(
                    token=token,
                    role=TokenRole.UNKNOWN,
                    reason="unknown"
                ))
        
        # Second pass: identify organization spans
        organization_spans = self._find_organization_spans(tokens, legal_form_indices)
        
        # Update tags based on organization spans
        for span in organization_spans:
            for i in range(span[0], span[1] + 1):
                if i < len(tags):
                    tags[i].role = TokenRole.ORGANIZATION
                    tags[i].span_id = span[2]  # span_id
                    tags[i].reason = "organization_span"
        
        # Third pass: mark remaining unknown tokens as person candidates
        for tag in tags:
            if tag.role == TokenRole.UNKNOWN:
                tag.role = TokenRole.PERSON_CANDIDATE
                tag.reason = "person_candidate"
        
        return tags

    def _is_legal_form(self, token: str) -> bool:
        """Check if token is a legal form."""
        return bool(self._legal_form_pattern.match(token))
    
    def _is_uppercase_name(self, token: str) -> bool:
        """Check if token looks like an uppercase organization name."""
        return bool(self._uppercase_pattern.match(token))
    
    def _is_initial(self, token: str) -> bool:
        """Check if token looks like an initial (single letter + dot)."""
        return bool(self._initial_pattern.match(token))
    
    def _is_punctuation(self, token: str) -> bool:
        """Check if token is punctuation."""
        return bool(self._punctuation_pattern.match(token))
    
    def _has_cyrillic(self, token: str) -> bool:
        """Check if token contains Cyrillic characters."""
        return bool(self._cyrillic_pattern.search(token))
    
    def _has_latin(self, token: str) -> bool:
        """Check if token contains Latin characters."""
        return bool(self._latin_pattern.search(token))
    
    def _find_organization_spans(self, tokens: List[str], legal_form_indices: List[int]) -> List[Tuple[int, int, int]]:
        """
        Find organization spans around legal forms.
        
        Args:
            tokens: List of tokens
            legal_form_indices: Indices of legal form tokens
            
        Returns:
            List of (start, end, span_id) tuples
        """
        spans = []
        span_id = 0
        
        for legal_form_idx in legal_form_indices:
            # Look for uppercase names in the context window
            start = max(0, legal_form_idx - self.window)
            end = min(len(tokens) - 1, legal_form_idx + self.window)
            
            # Find the best organization span
            best_span = self._find_best_organization_span(tokens, start, end, legal_form_idx)
            
            if best_span:
                spans.append((best_span[0], best_span[1], span_id))
                span_id += 1

        return spans
    
    def _find_best_organization_span(self, tokens: List[str], start: int, end: int, legal_form_idx: int) -> Optional[Tuple[int, int]]:
        """
        Find the best organization span around a legal form.
        
        Args:
            tokens: List of tokens
            start: Start of search window
            end: End of search window
            legal_form_idx: Index of the legal form
            
        Returns:
            (start, end) tuple of the best span, or None
        """
        # Look for uppercase names near the legal form
        uppercase_indices = []
        
        for i in range(start, end + 1):
            if i != legal_form_idx and i < len(tokens) and self._is_uppercase_name(tokens[i]):
                uppercase_indices.append(i)
        
        if not uppercase_indices:
            return None
        
        # Find the closest uppercase name to the legal form
        closest_idx = min(uppercase_indices, key=lambda x: abs(x - legal_form_idx))
        
        # Create span from legal form to uppercase name
        span_start = min(legal_form_idx, closest_idx)
        span_end = max(legal_form_idx, closest_idx)
        
        return (span_start, span_end)

    def get_person_candidates(self, tags: List[RoleTag]) -> List[str]:
        """
        Get tokens that are person candidates (not stopwords or organizations).
        
        Args:
            tags: List of role tags

        Returns:
            List of person candidate tokens
        """
        return [
            tag.token for tag in tags 
            if tag.role == TokenRole.PERSON_CANDIDATE
        ]

    def get_organization_spans(self, tags: List[RoleTag]) -> List[Tuple[int, int, str]]:
        """
        Get organization spans from tags.

        Args:
            tags: List of role tags

        Returns:
            List of (start, end, span_text) tuples
        """
        spans = {}
        
        for i, tag in enumerate(tags):
            if tag.role == TokenRole.ORGANIZATION and tag.span_id is not None:
                if tag.span_id not in spans:
                    spans[tag.span_id] = []
                spans[tag.span_id].append((i, tag.token))
        
        result = []
        for span_id, token_list in spans.items():
            if token_list:
                start_idx = min(idx for idx, _ in token_list)
                end_idx = max(idx for idx, _ in token_list)
                span_text = " ".join(token for _, token in sorted(token_list))
                result.append((start_idx, end_idx, span_text))
        
        return result
    
    def get_stopword_count(self, tags: List[RoleTag]) -> int:
        """Get count of stopword tokens."""
        return sum(1 for tag in tags if tag.role == TokenRole.STOPWORD)
    
    def get_organization_count(self, tags: List[RoleTag]) -> int:
        """Get count of organization tokens."""
        return sum(1 for tag in tags if tag.role == TokenRole.ORGANIZATION)
"""
Role tagger for token classification.

Classifies tokens as stopwords, organizations, or person candidates based on
lexicons and context rules.
"""

import re
import ahocorasick
from typing import List, Optional, Set, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum

# Import unified lexicon
from ..variants.templates.lexicon import (
    get_stopwords, is_legal_form, is_payment_context,
    get_all_lexicon_tokens, LEGAL_FORMS
)


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
    """Role tagger for token classification with Aho-Corasick acceleration."""

    def __init__(self, window: int = 3, enable_ac: bool = True):
        """
        Initialize role tagger.

        Args:
            window: Context window size for organization detection
            enable_ac: Enable Aho-Corasick acceleration for pattern matching
        """
        self.window = window
        self.enable_ac = enable_ac

        # Pre-compile patterns for efficiency
        self._uppercase_pattern = re.compile(r'^[А-ЯA-Z]{2,}$')
        self._legal_form_pattern = re.compile(
            r'^(' + '|'.join(re.escape(form) for form in LEGAL_FORMS) + r')$',
            re.IGNORECASE
        )

        # Initialize Aho-Corasick automaton for fast pattern matching
        self._ac_automaton = None
        if enable_ac:
            self._build_ac_automaton()
        
        # Pre-compile additional common patterns
        self._initial_pattern = re.compile(r'^[A-Za-zА-ЯЁІЇЄҐ]\.$')
        self._punctuation_pattern = re.compile(r'^[^\w\s]+$')
        self._cyrillic_pattern = re.compile(r'[А-Яа-яЁёІіЇїЄєҐґ]')
        self._latin_pattern = re.compile(r'[A-Za-z]')

    def _build_ac_automaton(self):
        """Build Aho-Corasick automaton from lexicon patterns."""
        try:
            automaton = ahocorasick.Automaton()

            # Add all lexicon tokens as patterns
            all_tokens = get_all_lexicon_tokens()
            for i, token in enumerate(all_tokens):
                # Store token with metadata for classification
                automaton.add_word(token.lower(), (i, token, self._classify_lexicon_token(token)))

            automaton.make_automaton()
            self._ac_automaton = automaton
        except ImportError:
            # Fallback to regex if ahocorasick not available
            self.enable_ac = False
            self._ac_automaton = None

    def _classify_lexicon_token(self, token: str) -> str:
        """Classify a lexicon token by type."""
        if is_legal_form(token):
            return 'legal_form'
        elif is_payment_context(token):
            return 'payment_context'
        else:
            return 'stopword'
    
    def tag(self, tokens: List[str], language: str, trace: Optional[List[Any]] = None) -> List[RoleTag]:
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
        stopwords = get_stopwords(language)
        
        # First pass: use AC automaton or fallback to basic matching
        if self.enable_ac and self._ac_automaton:
            tags, legal_form_indices = self._tag_with_ac(tokens, language, trace)
        else:
            tags, legal_form_indices = self._tag_basic(tokens, stopwords, trace)
        
        # Second pass: identify organization spans
        organization_spans = self._find_organization_spans(tokens, legal_form_indices)
        
        # Update tags based on organization spans
        for span in organization_spans:
            for i in range(span[0], span[1] + 1):
                if i < len(tags):
                    original_role = tags[i].role.value
                    tags[i].role = TokenRole.ORGANIZATION
                    tags[i].span_id = span[2]  # span_id
                    tags[i].reason = "organization_span"

                    # Add trace step if tracing is enabled
                    if trace is not None:
                        trace.append({
                            'stage': 'role_tagger',
                            'rule': f'organization_span_{span[2]}',
                            'token': tags[i].token,
                            'role': 'organization',
                            'evidence': {
                                'pos': i,
                                'original_role': original_role,
                                'span': f'{span[0]}-{span[1]}'
                            }
                        })
        
        # Third pass: mark remaining unknown tokens as person candidates
        for i, tag in enumerate(tags):
            if tag.role == TokenRole.UNKNOWN:
                tag.role = TokenRole.PERSON_CANDIDATE
                tag.reason = "person_candidate"

                # Add trace step if tracing is enabled
                if trace is not None:
                    trace.append({
                        'stage': 'role_tagger',
                        'rule': 'unknown_to_person_candidate',
                        'token': tag.token,
                        'role': 'person_candidate',
                        'evidence': {
                            'pos': i,
                            'default_assignment': True
                        }
                    })
        
        return tags

    def _tag_with_ac(self, tokens: List[str], language: str, trace: Optional[List[Any]] = None) -> Tuple[List[RoleTag], List[int]]:
        """Tag tokens using Aho-Corasick automaton for fast pattern matching."""
        tags = []
        legal_form_indices = []
        stopwords = get_stopwords(language)

        # For small token sets, AC overhead is not worth it, use basic matching
        if len(tokens) < 10:
            return self._tag_basic(tokens, stopwords, trace)

        # Create matches dict by checking each token individually (more efficient than concatenation)
        matches = {}
        for token in tokens:
            token_lower = token.lower()
            # Use the automaton to find exact matches for this token
            for end_idx, (pattern_id, original_token, token_type) in self._ac_automaton.iter(token_lower):
                if end_idx == len(token_lower) - 1:  # Exact match
                    matches[token_lower] = token_type
                    break

        # Tag individual tokens based on matches, prioritizing language-specific stopwords
        for i, token in enumerate(tokens):
            token_lower = token.lower()

            # First check language-specific stopwords (highest priority)
            if token_lower in stopwords:
                tags.append(RoleTag(
                    token=token,
                    role=TokenRole.STOPWORD,
                    reason="stopword"
                ))

                # Add trace step if tracing is enabled
                if trace is not None:
                    trace.append({
                        'stage': 'role_tagger',
                        'rule': f'stopword_{language}',
                        'token': token,
                        'role': 'stopword',
                        'evidence': {
                            'pos': i,
                            'language': language,
                            'method': 'language_specific'
                        }
                    })
            # Then check AC matches
            elif token_lower in matches:
                token_type = matches[token_lower]
                if token_type == 'legal_form':
                    legal_form_indices.append(i)
                    tags.append(RoleTag(
                        token=token,
                        role=TokenRole.UNKNOWN,
                        reason="legal_form"
                    ))

                    # Add trace step if tracing is enabled
                    if trace is not None:
                        trace.append({
                            'stage': 'role_tagger',
                            'rule': 'ac_legal_form',
                            'token': token,
                            'role': 'unknown',
                            'evidence': {
                                'pos': i,
                                'token_type': token_type,
                                'method': 'aho_corasick'
                            }
                        })

                elif token_type == 'payment_context':
                    tags.append(RoleTag(
                        token=token,
                        role=TokenRole.STOPWORD,
                        reason="payment_context"
                    ))

                    # Add trace step if tracing is enabled
                    if trace is not None:
                        trace.append({
                            'stage': 'role_tagger',
                            'rule': 'ac_payment_context',
                            'token': token,
                            'role': 'stopword',
                            'evidence': {
                                'pos': i,
                                'token_type': token_type,
                                'method': 'aho_corasick'
                            }
                        })

                else:
                    tags.append(RoleTag(
                        token=token,
                        role=TokenRole.UNKNOWN,
                        reason=token_type
                    ))
            else:
                tags.append(RoleTag(
                    token=token,
                    role=TokenRole.UNKNOWN,
                    reason="unknown"
                ))

        return tags, legal_form_indices

    def _tag_basic(self, tokens: List[str], stopwords: set, trace: Optional[List[Any]] = None) -> Tuple[List[RoleTag], List[int]]:
        """Fallback tagging method using basic pattern matching."""
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

                # Add trace step if tracing is enabled
                if trace is not None:
                    trace.append({
                        'stage': 'role_tagger',
                        'rule': 'basic_stopword',
                        'token': token,
                        'role': 'stopword',
                        'evidence': {
                            'pos': i,
                            'method': 'basic_lookup'
                        }
                    })
            # Check if token is a legal form
            elif self._is_legal_form(token):
                legal_form_indices.append(i)
                tags.append(RoleTag(
                    token=token,
                    role=TokenRole.UNKNOWN,
                    reason="legal_form"
                ))

                # Add trace step if tracing is enabled
                if trace is not None:
                    trace.append({
                        'stage': 'role_tagger',
                        'rule': 'basic_legal_form',
                        'token': token,
                        'role': 'unknown',
                        'evidence': {
                            'pos': i,
                            'method': 'basic_lookup'
                        }
                    })
            else:
                tags.append(RoleTag(
                    token=token,
                    role=TokenRole.UNKNOWN,
                    reason="unknown"
                ))

        return tags, legal_form_indices

    def _is_legal_form(self, token: str) -> bool:
        """Check if token is a legal form."""
        return is_legal_form(token)
    
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
#!/usr/bin/env python3
"""
Name assembler service for composing person names from tagged tokens.

This service assembles person names from tokens with assigned roles,
filtering out organization and stopword tokens while preserving
proper formatting and typography.
"""

import time
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum

from ...utils.logging_config import get_logger
from .role_tagger_service import TokenRole


class PersonRole(Enum):
    """Valid person roles for name assembly."""
    GIVEN = "given"
    SURNAME = "surname" 
    PATRONYMIC = "patronymic"
    INITIAL = "initial"


@dataclass
class TokenWithRole:
    """Token with assigned role for name assembly."""
    text: str
    normalized: str
    role: TokenRole
    confidence: float
    reason: str
    evidence: List[str]
    state_from: Optional[str] = None
    state_to: Optional[str] = None
    window_context: Optional[Dict[str, Any]] = None


@dataclass
class AssembledPerson:
    """Assembled person name with metadata."""
    given: Optional[str] = None
    surname: Optional[str] = None
    patronymic: Optional[str] = None
    initials: List[str] = None
    full_name: str = ""
    confidence: float = 0.0
    tokens_used: List[str] = None
    assembly_traces: List[str] = None


@dataclass
class AssembledNames:
    """Result of name assembly operation."""
    persons: List[AssembledPerson]
    traces: List[str]
    processing_time: float
    total_tokens: int
    person_tokens: int
    excluded_tokens: int


class NameAssembler:
    """
    Name assembler service for composing person names from tagged tokens.
    
    Responsibilities:
    - Filter tokens by person roles (given, surname, patronymic, initial)
    - Exclude organization and stopword tokens
    - Preserve hyphenated names with proper typography
    - Handle multi-person scenarios with separators
    - Generate detailed assembly traces
    """
    
    def __init__(self):
        """Initialize name assembler service."""
        self.logger = get_logger(__name__)
        
        # Valid person roles for assembly
        self.person_roles: Set[TokenRole] = {
            TokenRole.GIVEN,
            TokenRole.SURNAME, 
            TokenRole.PATRONYMIC,
            TokenRole.INITIAL
        }
        
        # Excluded roles (org, unknown, stopwords)
        self.excluded_roles: Set[TokenRole] = {
            TokenRole.ORG,
            TokenRole.UNKNOWN
        }
        
        # Multi-person separator
        self.person_separator = " | "
        
        # Statistics
        self._total_requests = 0
        self._total_processing_time = 0.0
        self._total_tokens_processed = 0
        self._total_persons_assembled = 0
    
    def assemble(
        self,
        tagged_tokens: List[TokenWithRole],
        language: str,
        flags: Optional[Dict[str, Any]] = None
    ) -> AssembledNames:
        """
        Assemble person names from tagged tokens.
        
        Args:
            tagged_tokens: List of tokens with assigned roles
            language: Language code
            flags: Feature flags for assembly behavior
            
        Returns:
            AssembledNames with assembled persons and metadata
        """
        start_time = time.perf_counter()
        self._total_requests += 1
        
        # Initialize result containers
        persons = []
        traces = []
        person_tokens = 0
        excluded_tokens = 0
        
        # Filter tokens by person roles
        person_tokens_list = []
        excluded_tokens_list = []
        
        for token in tagged_tokens:
            if token.role in self.person_roles:
                person_tokens_list.append(token)
                person_tokens += 1
                traces.append({
                    "type": "assemble",
                    "action": "include_person_token",
                    "token": token.text,
                    "role": token.role.value,
                    "reason": token.reason
                })
            else:
                excluded_tokens_list.append(token)
                excluded_tokens += 1
                traces.append({
                    "type": "assemble", 
                    "action": "exclude_token",
                    "token": token.text,
                    "role": token.role.value,
                    "reason": f"role_{token.role.value}_excluded"
                })
        
        # Group tokens into persons
        if person_tokens_list:
            persons = self._group_tokens_into_persons(
                person_tokens_list, 
                language,
                traces
            )
        
        processing_time = time.perf_counter() - start_time
        self._total_processing_time += processing_time
        self._total_tokens_processed += len(tagged_tokens)
        self._total_persons_assembled += len(persons)
        
        return AssembledNames(
            persons=persons,
            traces=traces,
            processing_time=processing_time,
            total_tokens=len(tagged_tokens),
            person_tokens=person_tokens,
            excluded_tokens=excluded_tokens
        )
    
    def _group_tokens_into_persons(
        self,
        person_tokens: List[TokenWithRole],
        language: str,
        traces: List[Dict[str, Any]]
    ) -> List[AssembledPerson]:
        """
        Group person tokens into individual persons.
        
        Args:
            person_tokens: List of tokens with person roles
            language: Language code
            traces: List to append assembly traces
            
        Returns:
            List of AssembledPerson objects
        """
        persons = []
        current_person_tokens = []
        
        for token in person_tokens:
            # Check if this token starts a new person
            if self._should_start_new_person(token, current_person_tokens):
                # Finish current person if exists
                if current_person_tokens:
                    person = self._assemble_person_from_tokens(
                        current_person_tokens, 
                        language,
                        traces
                    )
                    persons.append(person)
                
                # Start new person
                current_person_tokens = [token]
            else:
                # Add to current person
                current_person_tokens.append(token)
        
        # Finish last person
        if current_person_tokens:
            person = self._assemble_person_from_tokens(
                current_person_tokens,
                language, 
                traces
            )
            persons.append(person)
        
        return persons
    
    def _should_start_new_person(
        self,
        token: TokenWithRole,
        current_tokens: List[TokenWithRole]
    ) -> bool:
        """
        Determine if token should start a new person.
        
        Args:
            token: Current token
            current_tokens: Tokens in current person being assembled
            
        Returns:
            True if token should start new person
        """
        # If no current tokens, this starts a person
        if not current_tokens:
            return True
        
        # If token is surname and we already have a surname, start new person
        if token.role == TokenRole.SURNAME:
            has_surname = any(t.role == TokenRole.SURNAME for t in current_tokens)
            if has_surname:
                return True
        
        # If token is given and we already have a given, start new person
        if token.role == TokenRole.GIVEN:
            has_given = any(t.role == TokenRole.GIVEN for t in current_tokens)
            if has_given:
                return True
        
        return False
    
    def _assemble_person_from_tokens(
        self,
        tokens: List[TokenWithRole],
        language: str,
        traces: List[Dict[str, Any]]
    ) -> AssembledPerson:
        """
        Assemble a single person from tokens.
        
        Args:
            tokens: Tokens for this person
            language: Language code
            traces: List to append assembly traces
            
        Returns:
            AssembledPerson object
        """
        # Initialize person components
        given = None
        surname = None
        patronymic = None
        initials = []
        tokens_used = []
        assembly_traces = []
        
        # Process tokens by role
        for token in tokens:
            tokens_used.append(token.text)
            
            if token.role == TokenRole.GIVEN:
                given = token.normalized
                assembly_traces.append(f"assigned_given: {token.text} -> {given}")
                
            elif token.role == TokenRole.SURNAME:
                surname = token.normalized
                assembly_traces.append(f"assigned_surname: {token.text} -> {surname}")
                
            elif token.role == TokenRole.PATRONYMIC:
                patronymic = token.normalized
                assembly_traces.append(f"assigned_patronymic: {token.text} -> {patronymic}")
                
            elif token.role == TokenRole.INITIAL:
                initials.append(token.normalized)
                assembly_traces.append(f"assigned_initial: {token.text} -> {token.normalized}")
        
        # Build full name with proper formatting
        full_name = self._build_full_name(
            given, surname, patronymic, initials, language
        )
        
        # Calculate confidence based on token confidence
        confidence = self._calculate_confidence(tokens)
        
        # Add assembly trace
        traces.append({
            "type": "assemble",
            "action": "emit_person",
            "value": full_name,
            "components": {
                "given": given,
                "surname": surname, 
                "patronymic": patronymic,
                "initials": initials
            },
            "tokens_used": tokens_used
        })
        
        return AssembledPerson(
            given=given,
            surname=surname,
            patronymic=patronymic,
            initials=initials,
            full_name=full_name,
            confidence=confidence,
            tokens_used=tokens_used,
            assembly_traces=assembly_traces
        )
    
    def _build_full_name(
        self,
        given: Optional[str],
        surname: Optional[str], 
        patronymic: Optional[str],
        initials: List[str],
        language: str
    ) -> str:
        """
        Build full name from components with proper formatting.
        
        Args:
            given: Given name
            surname: Surname
            patronymic: Patronymic
            initials: List of initials
            language: Language code
            
        Returns:
            Formatted full name
        """
        components = []
        
        # Add given name or initials
        if given:
            components.append(given)
        elif initials:
            # Join initials with dots
            initials_str = ".".join(initials) + "."
            components.append(initials_str)
        
        # Add patronymic
        if patronymic:
            components.append(patronymic)
        
        # Add surname
        if surname:
            components.append(surname)
        
        return " ".join(components)
    
    def _calculate_confidence(self, tokens: List[TokenWithRole]) -> float:
        """
        Calculate confidence for assembled person.
        
        Args:
            tokens: Tokens used in assembly
            
        Returns:
            Average confidence score
        """
        if not tokens:
            return 0.0
        
        total_confidence = sum(token.confidence for token in tokens)
        return total_confidence / len(tokens)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get name assembler statistics.
        
        Returns:
            Dictionary with assembler statistics
        """
        avg_processing_time = (
            self._total_processing_time / self._total_requests
            if self._total_requests > 0 else 0.0
        )
        
        avg_tokens_per_request = (
            self._total_tokens_processed / self._total_requests
            if self._total_requests > 0 else 0.0
        )
        
        avg_persons_per_request = (
            self._total_persons_assembled / self._total_requests
            if self._total_requests > 0 else 0.0
        )
        
        return {
            'total_requests': self._total_requests,
            'avg_processing_time': avg_processing_time,
            'total_processing_time': self._total_processing_time,
            'total_tokens_processed': self._total_tokens_processed,
            'total_persons_assembled': self._total_persons_assembled,
            'avg_tokens_per_request': avg_tokens_per_request,
            'avg_persons_per_request': avg_persons_per_request
        }
    
    def reset_stats(self) -> None:
        """Reset assembler statistics."""
        self._total_requests = 0
        self._total_processing_time = 0.0
        self._total_tokens_processed = 0
        self._total_persons_assembled = 0

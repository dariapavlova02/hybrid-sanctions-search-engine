#!/usr/bin/env python3
"""
FSM-based role tagger service for token role classification.

Implements a finite state machine for deterministic role assignment with detailed tracing.
Replaces fragile if-else logic with configurable state transitions.
"""

import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
from abc import ABC, abstractmethod

from .lexicon_loader import Lexicons, get_lexicons, is_stopword, is_legal_form

logger = logging.getLogger(__name__)


class FSMState(Enum):
    """FSM states for role classification."""
    START = "START"
    SURNAME_EXPECTED = "SURNAME_EXPECTED"
    GIVEN_EXPECTED = "GIVEN_EXPECTED"
    PATRONYMIC_EXPECTED = "PATRONYMIC_EXPECTED"
    ORG_EXPECTED = "ORG_EXPECTED"
    DONE = "DONE"


class TokenRole(Enum):
    """Token roles in the normalization pipeline."""
    SURNAME = "surname"
    GIVEN = "given"
    PATRONYMIC = "patronymic"
    INITIAL = "initial"
    ORG = "org"
    UNKNOWN = "unknown"


@dataclass
class Token:
    """Token with features for FSM processing."""
    text: str
    norm: str
    is_capitalized: bool
    is_all_caps: bool
    has_hyphen: bool
    pos: int
    lang: str = "ru"
    
    @property
    def looks_like_initial(self) -> bool:
        """Check if token looks like an initial (single letter + dot)."""
        return bool(re.match(r'^[A-Za-zА-ЯЁІЇЄҐ]\.$', self.text))
    
    @property
    def is_punct(self) -> bool:
        """Check if token is punctuation."""
        return not any(c.isalnum() for c in self.text)


@dataclass
class RoleTag:
    """Role tag with detailed tracing information."""
    role: TokenRole
    confidence: float
    reason: str
    evidence: List[str] = field(default_factory=list)
    state_from: Optional[FSMState] = None
    state_to: Optional[FSMState] = None
    window_context: Optional[List[str]] = None


@dataclass
class RoleRules:
    """Configuration for FSM transition rules."""
    # State transition rules: (current_state, token_features) -> (new_state, role, reason)
    transitions: Dict[Tuple[FSMState, str], Tuple[FSMState, TokenRole, str]] = field(default_factory=dict)
    
    # Feature detection rules
    surname_suffixes: Set[str] = field(default_factory=lambda: {
        "енко", "ук", "юк", "чук", "ов", "ова", "ев", "ева", 
        "ін", "іна", "ский", "ская", "ський", "ська", "ян", "дзе"
    })
    
    patronymic_suffixes: Set[str] = field(default_factory=lambda: {
        "ович", "евич", "йович", "івна", "ївна", "овна", "евна", "ична", "ич"
    })
    
    # Context window for organization detection
    org_context_window: int = 3
    
    # Feature flags
    strict_stopwords: bool = True
    prefer_surname_first: bool = False


class FSMTransitionRule(ABC):
    """Abstract base class for FSM transition rules."""
    
    @abstractmethod
    def can_apply(self, state: FSMState, token: Token, context: List[Token]) -> bool:
        """Check if this rule can be applied."""
        pass
    
    @abstractmethod
    def apply(self, state: FSMState, token: Token, context: List[Token]) -> Tuple[FSMState, TokenRole, str, List[str]]:
        """Apply the rule and return (new_state, role, reason, evidence)."""
        pass


class InitialDetectionRule(FSMTransitionRule):
    """Rule for detecting initials."""
    
    def can_apply(self, state: FSMState, token: Token, context: List[Token]) -> bool:
        return token.looks_like_initial
    
    def apply(self, state: FSMState, token: Token, context: List[Token]) -> Tuple[FSMState, TokenRole, str, List[str]]:
        evidence = ["dot_after_capital"]
        
        if state == FSMState.START:
            return FSMState.GIVEN_EXPECTED, TokenRole.INITIAL, "initial_detected", evidence
        elif state == FSMState.GIVEN_EXPECTED:
            return FSMState.SURNAME_EXPECTED, TokenRole.INITIAL, "initial_detected", evidence
        else:
            return state, TokenRole.INITIAL, "initial_detected", evidence


class SurnameSuffixRule(FSMTransitionRule):
    """Rule for detecting surnames by suffix patterns."""
    
    def __init__(self, surname_suffixes: Set[str]):
        self.surname_suffixes = surname_suffixes
    
    def can_apply(self, state: FSMState, token: Token, context: List[Token]) -> bool:
        if not token.is_capitalized or token.is_punct:
            return False
        
        # Check if token ends with surname suffix
        token_lower = token.norm.lower()
        return any(token_lower.endswith(suffix) for suffix in self.surname_suffixes)
    
    def apply(self, state: FSMState, token: Token, context: List[Token]) -> Tuple[FSMState, TokenRole, str, List[str]]:
        evidence = ["surname_suffix_match"]
        token_lower = token.norm.lower()
        
        # Find matching suffix
        for suffix in self.surname_suffixes:
            if token_lower.endswith(suffix):
                evidence.append(f"suffix_{suffix}")
                break
        
        if state == FSMState.START:
            return FSMState.GIVEN_EXPECTED, TokenRole.SURNAME, "surname_suffix_detected", evidence
        elif state == FSMState.GIVEN_EXPECTED:
            return FSMState.PATRONYMIC_EXPECTED, TokenRole.SURNAME, "surname_suffix_detected", evidence
        else:
            return state, TokenRole.SURNAME, "surname_suffix_detected", evidence


class PatronymicSuffixRule(FSMTransitionRule):
    """Rule for detecting patronymics by suffix patterns."""
    
    def __init__(self, patronymic_suffixes: Set[str]):
        self.patronymic_suffixes = patronymic_suffixes
    
    def can_apply(self, state: FSMState, token: Token, context: List[Token]) -> bool:
        if not token.is_capitalized or token.is_punct:
            return False
        
        # Check if token ends with patronymic suffix
        token_lower = token.norm.lower()
        return any(token_lower.endswith(suffix) for suffix in self.patronymic_suffixes)
    
    def apply(self, state: FSMState, token: Token, context: List[Token]) -> Tuple[FSMState, TokenRole, str, List[str]]:
        evidence = ["patronymic_suffix_match"]
        token_lower = token.norm.lower()
        
        # Find matching suffix (check longer suffixes first)
        sorted_suffixes = sorted(self.patronymic_suffixes, key=len, reverse=True)
        for suffix in sorted_suffixes:
            if token_lower.endswith(suffix):
                evidence.append(f"suffix_{suffix}")
                break
        
        return FSMState.DONE, TokenRole.PATRONYMIC, "patronymic_suffix_detected", evidence


class OrganizationContextRule(FSMTransitionRule):
    """Rule for detecting organization context."""
    
    def __init__(self, lexicons: Lexicons, window: int = 3):
        self.lexicons = lexicons
        self.window = window
    
    def can_apply(self, state: FSMState, token: Token, context: List[Token]) -> bool:
        # Check if there's a legal form in the context window
        start_idx = max(0, token.pos - self.window)
        end_idx = min(len(context), token.pos + self.window + 1)
        
        for i in range(start_idx, end_idx):
            if i < len(context) and is_legal_form(context[i].text, self.lexicons):
                return True
        
        return False
    
    def apply(self, state: FSMState, token: Token, context: List[Token]) -> Tuple[FSMState, TokenRole, str, List[str]]:
        evidence = ["org_legal_form_context"]
        window_tokens = []
        
        # Find legal form in context
        start_idx = max(0, token.pos - self.window)
        end_idx = min(len(context), token.pos + self.window + 1)
        
        for i in range(start_idx, end_idx):
            if i < len(context):
                window_tokens.append(context[i].text)
                if is_legal_form(context[i].text, self.lexicons):
                    evidence.append(f"legal_form_{context[i].text}")
        
        if token.is_all_caps:
            evidence.append("CAPS")
        
        return state, TokenRole.ORG, "org_legal_form_context", evidence


class StopwordRule(FSMTransitionRule):
    """Rule for detecting stopwords."""
    
    def __init__(self, lexicons: Lexicons, strict: bool = True):
        self.lexicons = lexicons
        self.strict = strict
    
    def can_apply(self, state: FSMState, token: Token, context: List[Token]) -> bool:
        return is_stopword(token.text, token.lang, self.lexicons)
    
    def apply(self, state: FSMState, token: Token, context: List[Token]) -> Tuple[FSMState, TokenRole, str, List[str]]:
        evidence = [f"stopword_{token.lang}"]
        
        if self.strict:
            return state, TokenRole.UNKNOWN, "stopword_filtered", evidence
        else:
            # In non-strict mode, stopwords might still get roles
            return state, TokenRole.UNKNOWN, "stopword_detected", evidence


class DefaultPersonRule(FSMTransitionRule):
    """Default rule for person name tokens."""
    
    def can_apply(self, state: FSMState, token: Token, context: List[Token]) -> bool:
        return (token.is_capitalized and 
                not token.is_punct and 
                not token.is_all_caps and
                len(token.text) > 1)
    
    def apply(self, state: FSMState, token: Token, context: List[Token]) -> Tuple[FSMState, TokenRole, str, List[str]]:
        evidence = ["person_heuristic"]
        
        if state == FSMState.START:
            return FSMState.GIVEN_EXPECTED, TokenRole.GIVEN, "given_detected", evidence
        elif state == FSMState.GIVEN_EXPECTED:
            return FSMState.SURNAME_EXPECTED, TokenRole.GIVEN, "given_detected", evidence
        elif state == FSMState.SURNAME_EXPECTED:
            return FSMState.PATRONYMIC_EXPECTED, TokenRole.SURNAME, "surname_detected", evidence
        else:
            return state, TokenRole.UNKNOWN, "fallback_unknown", evidence


class RoleTaggerService:
    """FSM-based role tagger service with detailed tracing."""
    
    def __init__(self, lexicons: Lexicons = None, rules: RoleRules = None, window: int = 3):
        """
        Initialize role tagger service.
        
        Args:
            lexicons: Lexicons object for stopword/legal form detection
            rules: RoleRules configuration
            window: Context window size for organization detection
        """
        self.lexicons = lexicons or get_lexicons()
        self.rules = rules or RoleRules()
        self.window = window
        
        # Initialize FSM rules
        self._init_rules()
        
        logger.debug(f"RoleTaggerService initialized with window={window}")
    
    def _init_rules(self):
        """Initialize FSM transition rules."""
        # Order matters - higher priority rules first
        self.rules_list = [
            StopwordRule(self.lexicons, self.rules.strict_stopwords),
            OrganizationContextRule(self.lexicons, self.rules.org_context_window),
            InitialDetectionRule(),
            SurnameSuffixRule(self.rules.surname_suffixes),
            PatronymicSuffixRule(self.rules.patronymic_suffixes),
            DefaultPersonRule(),
        ]
    
    def tag(self, tokens: List[str], lang: str, flags: Any = None) -> List[RoleTag]:
        """
        Tag tokens with roles using FSM.
        
        Args:
            tokens: List of token strings
            lang: Language code
            flags: Feature flags (for future use)
            
        Returns:
            List of RoleTag objects with detailed tracing
        """
        if not tokens:
            return []
        
        logger.debug(f"Tagging {len(tokens)} tokens for language {lang}")
        
        # Convert strings to Token objects
        token_objects = self._create_token_objects(tokens, lang)
        
        # Apply FSM processing
        role_tags = self._process_with_fsm(token_objects)
        
        logger.debug(f"Tagged tokens: {self._get_role_summary(role_tags)}")
        return role_tags
    
    def _create_token_objects(self, tokens: List[str], lang: str) -> List[Token]:
        """Convert token strings to Token objects with features."""
        token_objects = []
        
        for i, token_text in enumerate(tokens):
            # Normalize token
            norm_text = token_text.strip()
            
            # Extract features
            is_capitalized = norm_text and norm_text[0].isupper()
            is_all_caps = norm_text.isupper() and len(norm_text) > 1
            has_hyphen = '-' in norm_text
            
            token_obj = Token(
                text=token_text,
                norm=norm_text,
                is_capitalized=is_capitalized,
                is_all_caps=is_all_caps,
                has_hyphen=has_hyphen,
                pos=i,
                lang=lang
            )
            
            token_objects.append(token_obj)
        
        return token_objects
    
    def _process_with_fsm(self, tokens: List[Token]) -> List[RoleTag]:
        """Process tokens through FSM."""
        role_tags = []
        current_state = FSMState.START
        
        for i, token in enumerate(tokens):
            # Apply rules in order of priority
            role_tag = self._apply_rules(current_state, token, tokens)
            
            # Set state information in the tag BEFORE updating state
            role_tag.state_from = current_state
            
            # Update state based on the assigned role
            current_state = self._update_state(current_state, role_tag.role)
            
            # Set final state
            role_tag.state_to = current_state
            
            role_tags.append(role_tag)
        
        return role_tags
    
    def _apply_rules(self, state: FSMState, token: Token, context: List[Token]) -> RoleTag:
        """Apply FSM rules to determine token role."""
        for rule in self.rules_list:
            if rule.can_apply(state, token, context):
                new_state, role, reason, evidence = rule.apply(state, token, context)
                
                return RoleTag(
                    role=role,
                    confidence=1.0,
                    reason=reason,
                    evidence=evidence,
                    state_from=state,
                    state_to=new_state,
                    window_context=[t.text for t in context[max(0, token.pos-self.window):token.pos+self.window+1]]
                )
        
        # Fallback: unknown role
        return RoleTag(
            role=TokenRole.UNKNOWN,
            confidence=0.0,
            reason="fallback_unknown",
            evidence=["no_rule_matched"],
            state_from=state,
            state_to=state
        )
    
    def _update_state(self, current_state: FSMState, role: TokenRole) -> FSMState:
        """Update FSM state based on assigned role."""
        if role == TokenRole.INITIAL:
            if current_state == FSMState.START:
                return FSMState.GIVEN_EXPECTED
            elif current_state == FSMState.GIVEN_EXPECTED:
                return FSMState.SURNAME_EXPECTED
        elif role == TokenRole.GIVEN:
            if current_state == FSMState.START:
                return FSMState.SURNAME_EXPECTED
            elif current_state == FSMState.GIVEN_EXPECTED:
                return FSMState.SURNAME_EXPECTED
        elif role == TokenRole.SURNAME:
            if current_state == FSMState.START:
                return FSMState.GIVEN_EXPECTED
            elif current_state == FSMState.GIVEN_EXPECTED:
                return FSMState.PATRONYMIC_EXPECTED
            elif current_state == FSMState.SURNAME_EXPECTED:
                return FSMState.PATRONYMIC_EXPECTED
        elif role == TokenRole.PATRONYMIC:
            return FSMState.DONE
        elif role == TokenRole.ORG:
            return FSMState.ORG_EXPECTED
        
        return current_state
    
    def _get_role_summary(self, tags: List[RoleTag]) -> Dict[str, int]:
        """Get summary of role distribution for logging."""
        role_counts = {}
        for tag in tags:
            role_counts[tag.role.value] = role_counts.get(tag.role.value, 0) + 1
        return role_counts
    
    def get_trace_entries(self, tokens: List[str], role_tags: List[RoleTag]) -> List[Dict[str, Any]]:
        """
        Generate trace entries for NormalizationResult.
        
        Args:
            tokens: Original token strings
            role_tags: Role tags from FSM processing
            
        Returns:
            List of trace dictionaries
        """
        trace_entries = []
        
        for i, (token, role_tag) in enumerate(zip(tokens, role_tags)):
            trace_entry = {
                "type": "role",
                "token": token,
                "role": role_tag.role.value,
                "state_from": role_tag.state_from.value if role_tag.state_from else None,
                "state_to": role_tag.state_to.value if role_tag.state_to else None,
                "reason": role_tag.reason,
                "evidence": role_tag.evidence,
                "confidence": role_tag.confidence
            }
            
            if role_tag.window_context:
                trace_entry["window"] = len(role_tag.window_context)
                trace_entry["window_tokens"] = role_tag.window_context
            
            trace_entries.append(trace_entry)
        
        return trace_entries

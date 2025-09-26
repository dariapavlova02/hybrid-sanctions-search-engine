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

from .lexicon_loader import Lexicons, get_lexicons
from .token_ops import is_hyphenated_surname
from ...utils.logging_config import get_logger


def is_stopword(token: str, lang: str, lexicons: Lexicons) -> bool:
    """Check if token is a stopword."""
    if not lexicons or not lexicons.stopwords:
        return False
    
    lang_stopwords = lexicons.stopwords.get(lang, set())
    return token.lower() in lang_stopwords


def is_legal_form(token: str, lexicons: Lexicons) -> bool:
    """Check if token is a legal form."""
    # Use the legal_forms module directly
    from ...data.patterns.legal_forms import is_legal_form as check_legal_form
    return check_legal_form(token, "auto")


def is_legal_form_lang(token: str, lang: str, lexicons: Lexicons) -> bool:
    """Check if token is a legal form for specific language."""
    # Use the legal_forms module directly
    from ...data.patterns.legal_forms import is_legal_form as check_legal_form
    return check_legal_form(token, lang)


def is_person_stopword(token: str, lang: str, lexicons: Lexicons) -> bool:
    """Check if token is a person stopword."""
    if not lexicons or not lexicons.stopwords_person:
        return False
    
    lang_stopwords = lexicons.stopwords_person.get(lang, set())
    return token.lower() in lang_stopwords

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
    OTHER = "other"
    ID = "id"  # For numeric identifiers like INN/ITN
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
    
    # Pre-compiled patterns for efficiency
    _initial_pattern = re.compile(r'^[A-Za-zА-ЯЁІЇЄҐ]\.$')
    _punctuation_pattern = re.compile(r'^[^\w\s]+$')
    
    @property
    def looks_like_initial(self) -> bool:
        """Check if token looks like an initial (single letter + dot)."""
        return bool(self._initial_pattern.match(self.text))
    
    @property
    def is_punct(self) -> bool:
        """Check if token is punctuation."""
        return bool(self._punctuation_pattern.match(self.text))


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
        "енко", "енк", "ук", "юк", "чук", "ов", "ова", "ев", "ева",
        "ін", "іна", "ский", "ская", "ський", "ська", "ян", "дзе"
    })
    
    patronymic_suffixes: Set[str] = field(default_factory=lambda: {
        # Masculine patronymics
        "ович", "евич", "йович", "ич",
        # Feminine patronymics  
        "івна", "ївна", "овна", "евна", "ична",
        # Additional patterns for comprehensive coverage
        "овича", "евича", "йовича", "ича",  # Genitive masculine
        "івни", "ївни", "овни", "евни", "ични",  # Genitive feminine
        "овичу", "евичу", "йовичу", "ичу",  # Dative masculine
        "івні", "ївні", "овні", "евні", "ичні",  # Dative feminine
        "овичем", "евичем", "йовичем", "ичем",  # Instrumental masculine
        "івною", "ївною", "овною", "евною", "ичною",  # Instrumental feminine
        "овиче", "евиче", "йовиче", "иче",  # Vocative masculine
        "івно", "ївно", "овно", "евно", "ично"  # Vocative feminine
    })
    
    # Context window for organization detection
    org_context_window: int = 3

    # Feature flags
    prefer_surname_first: bool = False
    strict_stopwords: bool = False


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
        matched_suffix = None
        for suffix in sorted_suffixes:
            if token_lower.endswith(suffix):
                evidence.append(f"suffix_{suffix}")
                matched_suffix = suffix
                break
        
        # Special handling for ambiguous "-ович" endings (Belarusian surnames)
        if matched_suffix == "ович" and token.is_capitalized:
            # Check if this might be a surname by looking for adjacent given name
            has_adjacent_given = False
            for i, ctx_token in enumerate(context):
                if (ctx_token.pos == token.pos - 1 or ctx_token.pos == token.pos + 1) and \
                   ctx_token.is_capitalized and not ctx_token.looks_like_initial:
                    # Check if adjacent token looks like a given name
                    if not any(ctx_token.norm.lower().endswith(suffix) for suffix in self.patronymic_suffixes):
                        has_adjacent_given = True
                        break
            
            if not has_adjacent_given:
                # No adjacent given name, likely a Belarusian surname
                evidence.append("ambiguous_ovich_surname")
                return state, TokenRole.SURNAME, "ambiguous_ovich_surname", evidence
        
        # Determine next state based on current state
        if state == FSMState.START:
            return FSMState.SURNAME_EXPECTED, TokenRole.PATRONYMIC, "patronymic_detected", evidence
        elif state == FSMState.GIVEN_EXPECTED:
            return FSMState.SURNAME_EXPECTED, TokenRole.PATRONYMIC, "patronymic_detected", evidence
        else:
            return state, TokenRole.PATRONYMIC, "patronymic_detected", evidence


class OrganizationContextRule(FSMTransitionRule):
    """Rule for detecting organization context with ±3 token window."""
    
    def __init__(self, lexicons: Lexicons, window: int = 3):
        self.lexicons = lexicons
        self.window = window
    
    def can_apply(self, state: FSMState, token: Token, context: List[Token]) -> bool:
        # Check if there's a legal form in the context window
        start_idx = max(0, token.pos - self.window)
        end_idx = min(len(context), token.pos + self.window + 1)
        
        for i in range(start_idx, end_idx):
            if i < len(context):
                # Check both global and language-specific legal forms
                if (is_legal_form(context[i].text, self.lexicons) or 
                    is_legal_form_lang(context[i].text, token.lang, self.lexicons)):
                    return True
        
        return False
    
    def apply(self, state: FSMState, token: Token, context: List[Token]) -> Tuple[FSMState, TokenRole, str, List[str]]:
        evidence = ["org_legal_form_context"]
        window_tokens = []
        legal_forms_found = []
        
        # Find legal form in context window
        start_idx = max(0, token.pos - self.window)
        end_idx = min(len(context), token.pos + self.window + 1)
        
        for i in range(start_idx, end_idx):
            if i < len(context):
                window_tokens.append(context[i].text)
                # Check both global and language-specific legal forms
                if (is_legal_form(context[i].text, self.lexicons) or 
                    is_legal_form_lang(context[i].text, token.lang, self.lexicons)):
                    legal_forms_found.append(context[i].text)
                    evidence.append(f"legal_form_{context[i].text}")
        
        if token.is_all_caps:
            evidence.append("CAPS")
        
        # Add context window information to evidence
        evidence.append(f"context_window_{len(window_tokens)}")
        evidence.append(f"legal_forms_count_{len(legal_forms_found)}")
        
        return state, TokenRole.ORG, "org_legal_form_context", evidence


class OrganizationNgramRule(FSMTransitionRule):
    """Rule for marking entire n-gram as organization when legal form + UPPERCASE found."""
    
    def __init__(self, lexicons: Lexicons, window: int = 3):
        self.lexicons = lexicons
        self.window = window
    
    def can_apply(self, state: FSMState, token: Token, context: List[Token]) -> bool:
        # Check if there's a legal form + UPPERCASE pattern in the context window
        start_idx = max(0, token.pos - self.window)
        end_idx = min(len(context), token.pos + self.window + 1)
        
        has_legal_form = False
        has_uppercase = False
        
        for i in range(start_idx, end_idx):
            if i < len(context):
                # Check for legal form
                if (is_legal_form(context[i].text, self.lexicons) or 
                    is_legal_form_lang(context[i].text, token.lang, self.lexicons)):
                    has_legal_form = True
                
                # Check for UPPERCASE token
                if context[i].is_all_caps and len(context[i].text) > 1:
                    has_uppercase = True
        
        return has_legal_form and has_uppercase
    
    def apply(self, state: FSMState, token: Token, context: List[Token]) -> Tuple[FSMState, TokenRole, str, List[str]]:
        evidence = ["org_legal_form_context", "ngram_organization"]
        window_tokens = []
        legal_forms_found = []
        uppercase_tokens = []
        
        # Find legal form and UPPERCASE in context window
        start_idx = max(0, token.pos - self.window)
        end_idx = min(len(context), token.pos + self.window + 1)
        
        for i in range(start_idx, end_idx):
            if i < len(context):
                window_tokens.append(context[i].text)
                # Check both global and language-specific legal forms
                if (is_legal_form(context[i].text, self.lexicons) or 
                    is_legal_form_lang(context[i].text, token.lang, self.lexicons)):
                    legal_forms_found.append(context[i].text)
                    evidence.append(f"legal_form_{context[i].text}")
                
                # Check for UPPERCASE
                if context[i].is_all_caps and len(context[i].text) > 1:
                    uppercase_tokens.append(context[i].text)
                    evidence.append(f"uppercase_{context[i].text}")
        
        # Add context window information to evidence
        evidence.append(f"context_window_{len(window_tokens)}")
        evidence.append(f"legal_forms_count_{len(legal_forms_found)}")
        evidence.append(f"uppercase_count_{len(uppercase_tokens)}")
        
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


class PaymentContextRule(FSMTransitionRule):
    """Rule for detecting payment context words."""
    
    def __init__(self, lexicons: Lexicons, strict: bool = True):
        self.lexicons = lexicons
        self.strict = strict
    
    def can_apply(self, state: FSMState, token: Token, context: List[Token]) -> bool:
        if not self.lexicons or not self.lexicons.payment_context:
            return False
        return token.text.lower() in self.lexicons.payment_context
    
    def apply(self, state: FSMState, token: Token, context: List[Token]) -> Tuple[FSMState, TokenRole, str, List[str]]:
        evidence = ["payment_context_word"]
        
        if self.strict:
            return state, TokenRole.UNKNOWN, "payment_context_filtered", evidence
        else:
            return state, TokenRole.UNKNOWN, "payment_context_detected", evidence


class LegalFormRule(FSMTransitionRule):
    """Rule for classifying legal forms as UNKNOWN to prevent them being treated as names."""

    def __init__(self, lexicons: Lexicons):
        self.lexicons = lexicons

    def can_apply(self, state: FSMState, token: Token, context: List[Token]) -> bool:
        # Check if token is a legal form
        return (is_legal_form(token.text, self.lexicons) or
                is_legal_form_lang(token.text, token.lang, self.lexicons))

    def apply(self, state: FSMState, token: Token, context: List[Token]) -> Tuple[FSMState, TokenRole, str, List[str]]:
        evidence = ["legal_form_detected"]
        evidence.append(f"form_{token.text}")
        evidence.append(f"lang_{token.lang}")

        return state, TokenRole.UNKNOWN, "legal_form_detected", evidence


class PersonStopwordRule(FSMTransitionRule):
    """Rule for detecting person stopwords with context filtering."""
    
    def __init__(self, lexicons: Lexicons, strict: bool = False, window: int = 3):
        self.lexicons = lexicons
        self.strict = strict
        self.window = window
    
    def can_apply(self, state: FSMState, token: Token, context: List[Token]) -> bool:
        if not self.strict:
            return False
        
        # Check if token is a person stopword
        if not is_person_stopword(token.text, token.lang, self.lexicons):
            return False
        
        # Check if there's a legal form in the context window that would make this an ORG
        start_idx = max(0, token.pos - self.window)
        end_idx = min(len(context), token.pos + self.window + 1)
        
        for i in range(start_idx, end_idx):
            if i < len(context):
                if (is_legal_form(context[i].text, self.lexicons) or 
                    is_legal_form_lang(context[i].text, token.lang, self.lexicons)):
                    # If there's a legal form nearby, don't filter as person stopword
                    return False
        
        return True
    
    def apply(self, state: FSMState, token: Token, context: List[Token]) -> Tuple[FSMState, TokenRole, str, List[str]]:
        evidence = ["person_stopword_filtered"]
        
        # Add context information
        start_idx = max(0, token.pos - self.window)
        end_idx = min(len(context), token.pos + self.window + 1)
        context_tokens = [context[i].text for i in range(start_idx, end_idx) if i < len(context)]
        evidence.append(f"context_window_{len(context_tokens)}")
        
        return state, TokenRole.UNKNOWN, "person_stopword_filtered", evidence


class RussianStopwordInitRule(FSMTransitionRule):
    """Rule for preventing Russian stopwords from being marked as initials."""
    
    def __init__(self, lexicons: Lexicons, strict: bool = True):
        self.lexicons = lexicons
        self.strict = strict
    
    def can_apply(self, state: FSMState, token: Token, context: List[Token]) -> bool:
        if not self.strict or token.lang != "ru":
            return False
        
        if not self.lexicons or not self.lexicons.stopwords_init:
            return False
        
        ru_stopwords_init = self.lexicons.stopwords_init.get("ru", set())
        return token.text.lower() in ru_stopwords_init
    
    def apply(self, state: FSMState, token: Token, context: List[Token]) -> Tuple[FSMState, TokenRole, str, List[str]]:
        evidence = ["ru_stopword_conflict"]
        return state, TokenRole.UNKNOWN, "ru_stopword_conflict", evidence


class UkrainianInitPrepositionRule(FSMTransitionRule):
    """Rule for preventing Ukrainian one/two-letter prepositions from being marked as initials."""
    
    def __init__(self, lexicons: Lexicons, strict: bool = True):
        self.lexicons = lexicons
        self.strict = strict
        # Ukrainian one/two-letter prepositions that conflict with initials
        self.uk_prepositions = {"з", "зі", "у", "в", "і", "й", "та"}
    
    def can_apply(self, state: FSMState, token: Token, context: List[Token]) -> bool:
        if not self.strict or token.lang != "uk":
            return False
        
        # Check if token is a Ukrainian preposition
        return token.text.lower() in self.uk_prepositions
    
    def apply(self, state: FSMState, token: Token, context: List[Token]) -> Tuple[FSMState, TokenRole, str, List[str]]:
        evidence = ["uk_stopword_conflict"]
        return state, TokenRole.UNKNOWN, "uk_stopword_conflict", evidence


class LegalFormOrgSpanRule(FSMTransitionRule):
    """Rule for detecting ORG spans: LEGAL_FORM + UPPERCASE_TOKEN{2+} → ORG block."""
    
    def __init__(self, lexicons: Lexicons, window: int = 3):
        self.lexicons = lexicons
        self.window = window
    
    def can_apply(self, state: FSMState, token: Token, context: List[Token]) -> bool:
        # Check if current token is uppercase and has 2+ characters
        if not (token.is_all_caps and len(token.text) >= 2):
            return False
        
        # Check if there's a legal form in the context window
        start_idx = max(0, token.pos - self.window)
        end_idx = min(len(context), token.pos + self.window + 1)
        
        for i in range(start_idx, end_idx):
            if i < len(context):
                context_token = context[i]
                if (is_legal_form(context_token.text, self.lexicons) or 
                    is_legal_form_lang(context_token.text, token.lang, self.lexicons)):
                    return True
        
        return False
    
    def apply(self, state: FSMState, token: Token, context: List[Token]) -> Tuple[FSMState, TokenRole, str, List[str]]:
        evidence = ["org_acronym_block"]
        
        # Find the legal form in context
        start_idx = max(0, token.pos - self.window)
        end_idx = min(len(context), token.pos + self.window + 1)
        
        legal_form_found = None
        for i in range(start_idx, end_idx):
            if i < len(context):
                context_token = context[i]
                if (is_legal_form(context_token.text, self.lexicons) or 
                    is_legal_form_lang(context_token.text, token.lang, self.lexicons)):
                    legal_form_found = context_token.text
                    break
        
        if legal_form_found:
            evidence.append(f"legal_form_{legal_form_found}")
        
        evidence.append(f"uppercase_token_{token.text}")
        
        return FSMState.ORG_EXPECTED, TokenRole.ORG, "org_acronym_block", evidence


class SingleCharNumberRule(FSMTransitionRule):
    """Rule for handling single characters and numbers as 'other' role."""
    
    def can_apply(self, state: FSMState, token: Token, context: List[Token]) -> bool:
        # Handle single characters and numbers
        return len(token.text) == 1 and (token.text.isdigit() or token.text.isalpha())
    
    def apply(self, state: FSMState, token: Token, context: List[Token]) -> Tuple[FSMState, TokenRole, str, List[str]]:
        evidence = ["single_char_or_number"]
        return state, TokenRole.OTHER, "single_char_number", evidence


class NumericIdentifierRule(FSMTransitionRule):
    """Rule for detecting numeric identifiers (INN/ITN/EDRPOU etc.) and keeping them as ID tokens."""

    def __init__(self):
        self.logger = get_logger(__name__)

    def can_apply(self, state: FSMState, token: Token, context: List[Token]) -> bool:
        # Check if token is numeric
        if not token.text.isdigit():
            return False

        length = len(token.text)

        # Check if there's an ID marker nearby (within 2 positions)
        id_markers = {"іпн", "инн", "inn", "itn", "єдрпоу", "едрпоу", "edrpou", "окпо", "okpo", "огрн", "ogrn", "кпп", "kpp"}
        has_id_marker = False

        # Check previous and next tokens for ID markers
        for i in range(max(0, token.pos - 2), min(len(context), token.pos + 3)):
            if i != token.pos and i < len(context):
                check_token = context[i].text.lower()
                if check_token in id_markers:
                    self.logger.debug(f"Found ID marker '{check_token}' near numeric token '{token.text}'")
                    has_id_marker = True
                    break

        # Apply different length rules based on context
        if has_id_marker:
            # With ID marker: allow 6-16 digits (e.g., EDRPOU can be 8 digits)
            if not (6 <= length <= 16):
                return False
        else:
            # Without ID marker: require 10-16 digits (typical for INN/TIN)
            if not (10 <= length <= 16):
                return False

        return True

    def apply(self, state: FSMState, token: Token, context: List[Token]) -> Tuple[FSMState, TokenRole, str, List[str]]:
        evidence = ["numeric_id_detected", f"length_{len(token.text)}"]

        # Check for nearby ID markers for better evidence
        id_markers = {"іпн", "инн", "inn", "itn", "єдрпоу", "едрпоу", "edrpou", "окпо", "okpo", "огрн", "ogrn", "кпп", "kpp"}
        for i in range(max(0, token.pos - 2), min(len(context), token.pos + 3)):
            if i != token.pos and i < len(context):
                check_token = context[i].text.lower()
                if check_token in id_markers:
                    evidence.append(f"marker_{check_token}_nearby")
                    break

        self.logger.debug(f"Classified '{token.text}' as ID with evidence: {evidence}")
        return state, TokenRole.ID, "numeric_identifier", evidence


class DefaultPersonRule(FSMTransitionRule):
    """Default rule for person name tokens that considers morphology and dictionaries."""

    def __init__(self, role_classifier=None, language="ru", lexicons=None):
        self.role_classifier = role_classifier
        self.language = language
        self.lexicons = lexicons
        self.logger = get_logger(__name__)  # Add logger for debugging

    def can_apply(self, state: FSMState, token: Token, context: List[Token]) -> bool:
        # Accept both capitalized and non-capitalized names
        # but exclude punctuation and single characters
        basic_checks = (not token.is_punct and
                       len(token.text) > 1 and
                       token.text.isalpha())  # Only alphabetic characters

        if not basic_checks:
            return False

        # Handle all-caps tokens more intelligently
        if token.is_all_caps:
            # Exclude very short all-caps tokens that are likely acronyms
            if len(token.text) <= 2:
                return False

            # For longer all-caps tokens, check if they might be names using the role classifier
            if self.role_classifier:
                lang = getattr(token, 'lang', self.language) or self.language
                predicted_role = self.role_classifier._classify_personal_role(token.text, lang)
                # If the role classifier recognizes it as a person role, allow it
                if predicted_role in ["given", "surname", "patronymic"]:
                    return True

                # Also check dictionaries directly
                token_lower = token.text.lower()
                if (token_lower in self.role_classifier.given_names.get(lang, set()) or
                    token_lower in self.role_classifier.surnames.get(lang, set()) or
                    token_lower in self.role_classifier.diminutives.get(lang, set())):
                    return True

            # If no role classifier or it doesn't recognize it, be more conservative
            # Allow all-caps tokens of reasonable length (3+ chars) for Ukrainian/Russian names
            lang = getattr(token, 'lang', self.language) or self.language
            if len(token.text) >= 3 and lang in ['uk', 'ru']:
                # Check if it contains Cyrillic characters (likely Ukrainian/Russian name)
                if any(ord(c) >= 0x0400 and ord(c) <= 0x04FF for c in token.text):
                    return True

        # Additional exclusions to prevent non-names from getting person roles
        if self.lexicons:
            # Exclude payment context words
            if (self.lexicons.payment_context and
                token.text.lower() in self.lexicons.payment_context):
                return False

            # Exclude legal forms
            if is_legal_form(token.text, self.lexicons):
                return False

            # Exclude general stopwords (already handled by StopwordRule, but double-check)
            if is_stopword(token.text, token.lang, self.lexicons):
                return False

        return True

    def apply(self, state: FSMState, token: Token, context: List[Token]) -> Tuple[FSMState, TokenRole, str, List[str]]:
        evidence = ["person_heuristic"]

        # Use role classifier to determine actual role if available
        if self.role_classifier:
            # Use token's language if available, otherwise fall back to instance language
            lang = getattr(token, 'lang', self.language) or self.language
            predicted_role = self.role_classifier._classify_personal_role(token.text, lang)

            # Debug logging for classification issues
            if token.text == "Катерина":
                self.logger.info(f"🔍 ROLE TAGGER DEBUG: Token='Катерина', lang='{lang}', predicted_role='{predicted_role}'")
                self.logger.info(f"🔍 Available given_names for {lang}: {len(self.role_classifier.given_names.get(lang, set()))} names")
                if 'катерина' in self.role_classifier.given_names.get(lang, set()):
                    self.logger.info(f"✅ 'катерина' IS in given_names[{lang}]")
                else:
                    self.logger.info(f"❌ 'катерина' NOT in given_names[{lang}]")
                    # Show first few names for debugging
                    sample_names = list(self.role_classifier.given_names.get(lang, set()))[:10]
                    self.logger.info(f"🔍 Sample names in given_names[{lang}]: {sample_names}")

            if predicted_role == "surname":
                if state == FSMState.START:
                    return FSMState.SURNAME_EXPECTED, TokenRole.SURNAME, "surname_detected", evidence + [f"morphology_{predicted_role}"]
                elif state == FSMState.GIVEN_EXPECTED:
                    return FSMState.PATRONYMIC_EXPECTED, TokenRole.SURNAME, "surname_detected", evidence + [f"morphology_{predicted_role}"]
                elif state == FSMState.SURNAME_EXPECTED:
                    return FSMState.PATRONYMIC_EXPECTED, TokenRole.SURNAME, "surname_detected", evidence + [f"morphology_{predicted_role}"]

            elif predicted_role == "given":
                if state == FSMState.START:
                    return FSMState.SURNAME_EXPECTED, TokenRole.GIVEN, "given_detected", evidence + [f"morphology_{predicted_role}"]
                elif state == FSMState.SURNAME_EXPECTED:
                    return FSMState.PATRONYMIC_EXPECTED, TokenRole.GIVEN, "given_detected", evidence + [f"morphology_{predicted_role}"]
                elif state == FSMState.GIVEN_EXPECTED:
                    # Check if this token is the same as the previous given name (duplicate)
                    if context and len(context) >= 1:
                        prev_token = context[-1]  # Previous token
                        if prev_token.text.lower() == token.text.lower():
                            return FSMState.GIVEN_EXPECTED, TokenRole.GIVEN, "duplicate_given_detected", evidence + [f"morphology_{predicted_role}"]
                    return FSMState.SURNAME_EXPECTED, TokenRole.GIVEN, "given_detected", evidence + [f"morphology_{predicted_role}"]

            elif predicted_role == "patronymic":
                return FSMState.DONE, TokenRole.PATRONYMIC, "patronymic_detected", evidence + [f"morphology_{predicted_role}"]

        # Enhanced fallback logic - check dictionaries directly if classifier failed
        if self.role_classifier:
            # If classifier returned "unknown", try direct dictionary lookup
            lang = getattr(token, 'lang', self.language) or self.language
            token_lower = token.text.lower()

            # Debug logging for fallback logic
            if token.text == "Катерина":
                self.logger.info(f"🔧 FALLBACK DEBUG: Checking dictionaries directly for 'катерина' in lang='{lang}'")

            # Check if it's in given names dictionary
            if token_lower in self.role_classifier.given_names.get(lang, set()):
                if state == FSMState.START:
                    return FSMState.SURNAME_EXPECTED, TokenRole.GIVEN, "given_detected", evidence + [f"dict_lookup_given_{lang}"]
                elif state == FSMState.SURNAME_EXPECTED:
                    return FSMState.PATRONYMIC_EXPECTED, TokenRole.GIVEN, "given_detected", evidence + [f"dict_lookup_given_{lang}"]
                elif state == FSMState.GIVEN_EXPECTED:
                    return FSMState.SURNAME_EXPECTED, TokenRole.GIVEN, "given_detected", evidence + [f"dict_lookup_given_{lang}"]

            # Check if it's in surnames dictionary
            if token_lower in self.role_classifier.surnames.get(lang, set()):
                if state == FSMState.START:
                    return FSMState.SURNAME_EXPECTED, TokenRole.SURNAME, "surname_detected", evidence + [f"dict_lookup_surname_{lang}"]
                elif state == FSMState.GIVEN_EXPECTED:
                    return FSMState.PATRONYMIC_EXPECTED, TokenRole.SURNAME, "surname_detected", evidence + [f"dict_lookup_surname_{lang}"]
                elif state == FSMState.SURNAME_EXPECTED:
                    return FSMState.PATRONYMIC_EXPECTED, TokenRole.SURNAME, "surname_detected", evidence + [f"dict_lookup_surname_{lang}"]

            # Check diminutives
            if token_lower in self.role_classifier.diminutives.get(lang, set()):
                if state == FSMState.START:
                    return FSMState.SURNAME_EXPECTED, TokenRole.GIVEN, "given_detected", evidence + [f"dict_lookup_diminutive_{lang}"]
                elif state == FSMState.SURNAME_EXPECTED:
                    return FSMState.PATRONYMIC_EXPECTED, TokenRole.GIVEN, "given_detected", evidence + [f"dict_lookup_diminutive_{lang}"]
                elif state == FSMState.GIVEN_EXPECTED:
                    return FSMState.SURNAME_EXPECTED, TokenRole.GIVEN, "given_detected", evidence + [f"dict_lookup_diminutive_{lang}"]

        # Fallback to original positional logic if no classifier or still unknown role
        if state == FSMState.START:
            return FSMState.GIVEN_EXPECTED, TokenRole.GIVEN, "given_detected", evidence + ["positional_fallback"]
        elif state == FSMState.GIVEN_EXPECTED:
            # Check if this token is the same as the previous given name (duplicate)
            if context and len(context) >= 1:
                prev_token = context[-1]  # Previous token
                if prev_token.text.lower() == token.text.lower():
                    return FSMState.GIVEN_EXPECTED, TokenRole.GIVEN, "duplicate_given_detected", evidence + ["positional_fallback"]
            return FSMState.SURNAME_EXPECTED, TokenRole.GIVEN, "given_detected", evidence + ["positional_fallback"]
        elif state == FSMState.SURNAME_EXPECTED:
            # Check if this token is the same as the previous given name (duplicate)
            if context and len(context) >= 2:
                prev_token = context[-2]  # Previous token
                if prev_token.text.lower() == token.text.lower():
                    return FSMState.SURNAME_EXPECTED, TokenRole.GIVEN, "duplicate_given_detected", evidence + ["positional_fallback"]
            return FSMState.PATRONYMIC_EXPECTED, TokenRole.SURNAME, "surname_detected", evidence + ["positional_fallback"]
        else:
            return state, TokenRole.UNKNOWN, "fallback_unknown", evidence


class RoleTaggerService:
    """FSM-based role tagger service with detailed tracing."""
    
    def __init__(self, stopwords=None, org_legal_forms=None, lang='auto', strict_stopwords=False, role_classifier=None):
        """
        Initialize role tagger service.

        Args:
            stopwords: Dict[str, Set[str]] - language -> set of stopwords
            org_legal_forms: Set[str] - set of legal forms for organization detection
            lang: str - language code ('ru', 'uk', 'en', 'auto')
            strict_stopwords: bool - enable strict stopword filtering
            role_classifier: RoleClassifier - role classifier for morphological analysis
        """
        # Load default lexicons if not provided
        self.lexicons = get_lexicons()

        # Store role classifier and language
        self.role_classifier = role_classifier
        self.lang = lang

        # Override with provided parameters if given
        if stopwords is not None:
            if not isinstance(stopwords, dict):
                raise TypeError(f"stopwords must be Dict[str, Set[str]], got {type(stopwords)}")
            self.lexicons.stopwords.update(stopwords)

        if org_legal_forms is not None:
            if not isinstance(org_legal_forms, set):
                raise TypeError(f"org_legal_forms must be Set[str], got {type(org_legal_forms)}")
            self.lexicons.legal_forms.update(org_legal_forms)

        # Initialize rules
        self.rules = RoleRules(strict_stopwords=strict_stopwords)

        # Set context window for organization detection
        self.window = 3

        # Pre-compile regex patterns for efficiency
        self._init_patterns()

        # Initialize FSM rules
        self._init_rules()

        logger.debug(f"RoleTaggerService initialized with window={self.window}, role_classifier={'available' if role_classifier else 'none'}")
    
    def _init_patterns(self):
        """Initialize pre-compiled regex patterns."""
        # Common patterns used in FSM rules
        self._initial_pattern = re.compile(r'^[A-Za-zА-ЯЁІЇЄҐ]\.$')
        self._punctuation_pattern = re.compile(r'^[^\w\s]+$')
        self._cyrillic_pattern = re.compile(r'[А-Яа-яЁёІіЇїЄєҐґ]')
        self._latin_pattern = re.compile(r'[A-Za-z]')
        self._uppercase_pattern = re.compile(r'^[А-ЯA-Z]{2,}$')
        self._legal_form_pattern = re.compile(
            r'^(' + '|'.join(re.escape(form) for form in self.lexicons.legal_forms) + r')$',
            re.IGNORECASE
        )
    
    def _init_rules(self):
        """Initialize FSM transition rules."""
        # Order matters - higher priority rules first
        self.rules_list = [
            NumericIdentifierRule(),  # HIGH PRIORITY: Preserve numeric IDs
            LegalFormRule(self.lexicons),  # HIGH PRIORITY: Classify legal forms as UNKNOWN
            RussianStopwordInitRule(self.lexicons, False),
            UkrainianInitPrepositionRule(self.lexicons, False),
            StopwordRule(self.lexicons, False),
            PaymentContextRule(self.lexicons, False),
            PersonStopwordRule(self.lexicons, True, self.rules.org_context_window),
            OrganizationContextRule(self.lexicons, self.rules.org_context_window),
            LegalFormOrgSpanRule(self.lexicons, self.rules.org_context_window),  # NEW: ORG span detection
            OrganizationNgramRule(self.lexicons, self.rules.org_context_window),
            InitialDetectionRule(),
            SurnameSuffixRule(self.rules.surname_suffixes),
            PatronymicSuffixRule(self.rules.patronymic_suffixes),
            SingleCharNumberRule(),  # Handle single characters and numbers as 'other'
            DefaultPersonRule(self.role_classifier, self.lang, self.lexicons),  # Pass role classifier, language, and lexicons
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
            current_state = self._update_state(current_state, role_tag.role, token)
            
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
    
    def _update_state(self, current_state: FSMState, role: TokenRole, token: Optional[Token] = None) -> FSMState:
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
            # Special handling for hyphenated surnames - stay in SURNAME_EXPECTED
            if token and is_hyphenated_surname(token.text):
                if current_state == FSMState.START:
                    return FSMState.SURNAME_EXPECTED  # Allow more surnames after hyphenated
                elif current_state == FSMState.GIVEN_EXPECTED:
                    return FSMState.SURNAME_EXPECTED  # Allow more surnames after hyphenated
                elif current_state == FSMState.SURNAME_EXPECTED:
                    return FSMState.SURNAME_EXPECTED  # Stay in surname mode
            else:
                # Regular surname handling
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
            
            # Add specific trace fields for context filtering
            if "payment_context_filtered" in role_tag.reason:
                trace_entry["payment_context_filtered"] = True
            if "org_legal_form_context" in role_tag.reason:
                trace_entry["org_legal_form_context"] = True
            if "person_stopword_filtered" in role_tag.reason:
                trace_entry["person_stopword_filtered"] = True
            if "uk_stopword_conflict" in role_tag.reason:
                trace_entry["uk_stopword_conflict"] = True
            
            trace_entries.append(trace_entry)
        
        return trace_entries

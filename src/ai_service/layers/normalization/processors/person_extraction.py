"""
Person extraction utilities for grouping and structuring personal information.
"""

import re
from typing import List, Dict, Set, Tuple, Optional, Any
from dataclasses import dataclass

from .config import NormalizationConfig
from ....contracts.base_contracts import TokenTrace


@dataclass
class PersonCandidate:
    """Represents a potential person extracted from tokens."""
    tokens: List[str]
    roles: List[str]
    start_index: int
    end_index: int
    confidence: float
    gender: Optional[str] = None
    language: Optional[str] = None


class PersonExtractor:
    """Handles extraction and grouping of person-related information from tokens."""

    def __init__(self):
        """Initialize the person extractor."""
        # Separators that indicate person boundaries
        self.person_separators = {
            "ru": {"и", "а", "или", "либо", ",", ";"},
            "uk": {"і", "та", "або", "чи", ",", ";"},
            "en": {"and", "or", ",", ";"}
        }

        # Role transition patterns that suggest person boundaries
        self.boundary_patterns = [
            # New given name after a complete name suggests new person
            ("surname", "given"),
            ("patronymic", "given"),
            # Multiple surnames suggest separate people
            ("surname", "surname"),
        ]

    def extract_persons_from_sequence(
        self,
        tokens: List[str],
        roles: List[str],
        language: str = "ru",
        config: Optional[NormalizationConfig] = None
    ) -> List[PersonCandidate]:
        """Extract person candidates from a sequence of tokens and roles."""
        if not tokens or not roles or len(tokens) != len(roles):
            return []

        persons = []
        current_person_tokens = []
        current_person_roles = []
        current_start_idx = 0

        for i, (token, role) in enumerate(zip(tokens, roles)):
            # Check if this token starts a new person
            if self._is_person_boundary(i, tokens, roles, language):
                # Save current person if we have tokens
                if current_person_tokens:
                    person = self._create_person_candidate(
                        current_person_tokens,
                        current_person_roles,
                        current_start_idx,
                        i - 1,
                        language
                    )
                    persons.append(person)

                # Start new person
                current_person_tokens = [token] if self._is_person_role(role) else []
                current_person_roles = [role] if self._is_person_role(role) else []
                current_start_idx = i
            else:
                # Add token to current person if it's a person role
                if self._is_person_role(role):
                    current_person_tokens.append(token)
                    current_person_roles.append(role)

        # Add the last person
        if current_person_tokens:
            person = self._create_person_candidate(
                current_person_tokens,
                current_person_roles,
                current_start_idx,
                len(tokens) - 1,
                language
            )
            persons.append(person)

        return persons

    def group_person_tokens(
        self,
        tokens: List[str],
        roles: List[str],
        traces: List[TokenTrace],
        language: str = "ru"
    ) -> List[List[str]]:
        """Group tokens into person sequences based on roles and separators."""
        if not tokens:
            return []

        persons = self.extract_persons_from_sequence(tokens, roles, language)
        return [person.tokens for person in persons]

    def detect_gender_from_sequence(
        self,
        tokens: List[str],
        roles: List[str],
        language: str = "ru"
    ) -> Optional[str]:
        """Detect gender from a sequence of person tokens."""
        if not tokens or not roles:
            return None

        # Look for gender indicators in given names and patronymics
        for token, role in zip(tokens, roles):
            if role == "given":
                gender = self._detect_gender_from_given_name(token, language)
                if gender:
                    return gender

            elif role == "patronymic":
                gender = self._detect_gender_from_patronymic(token, language)
                if gender:
                    return gender

        return None

    def validate_person_structure(
        self,
        tokens: List[str],
        roles: List[str]
    ) -> Dict[str, Any]:
        """Validate the structure of a person's tokens."""
        if not tokens or not roles:
            return {"valid": False, "reason": "Empty tokens or roles"}

        validation = {
            "valid": True,
            "confidence": 0.0,
            "has_given": False,
            "has_surname": False,
            "has_patronymic": False,
            "has_initials": False,
            "structure_score": 0.0
        }

        role_counts = {}
        for role in roles:
            role_counts[role] = role_counts.get(role, 0) + 1

        # Check for basic name components
        validation["has_given"] = "given" in role_counts
        validation["has_surname"] = "surname" in role_counts
        validation["has_patronymic"] = "patronymic" in role_counts
        validation["has_initials"] = "initial" in role_counts

        # Calculate structure score
        score = 0.0
        if validation["has_given"]:
            score += 0.4
        if validation["has_surname"]:
            score += 0.4
        if validation["has_patronymic"]:
            score += 0.15
        if validation["has_initials"]:
            score += 0.05

        # Penalty for too many of the same role
        for role, count in role_counts.items():
            if count > 2:
                score -= 0.1 * (count - 2)

        validation["structure_score"] = max(0.0, min(1.0, score))
        validation["confidence"] = validation["structure_score"]

        # Mark as invalid if score is too low
        if validation["structure_score"] < 0.3:
            validation["valid"] = False
            validation["reason"] = "Insufficient name structure"

        return validation

    def _is_person_boundary(
        self,
        index: int,
        tokens: List[str],
        roles: List[str],
        language: str
    ) -> bool:
        """Check if the current position represents a boundary between persons."""
        if index == 0:
            return True

        current_token = tokens[index].lower() if index < len(tokens) else ""
        current_role = roles[index] if index < len(roles) else ""
        prev_role = roles[index - 1] if index > 0 and index - 1 < len(roles) else ""

        # Check for explicit separators
        if current_token in self.person_separators.get(language, set()):
            return True

        # Check for role transition patterns
        if prev_role and current_role:
            transition = (prev_role, current_role)
            if transition in self.boundary_patterns:
                return True

        # Check for repeated given names (likely different people)
        if current_role == "given" and prev_role == "given":
            return True

        return False

    def _is_person_role(self, role: str) -> bool:
        """Check if a role belongs to a person."""
        person_roles = {"given", "surname", "patronymic", "initial", "suffix"}
        # Explicitly exclude non-person roles
        non_person_roles = {"unknown", "context", "stopword", "legal_form", "org", "numeric", "date"}

        # Must be a person role AND not explicitly a non-person role
        return role in person_roles and role not in non_person_roles

    def _create_person_candidate(
        self,
        tokens: List[str],
        roles: List[str],
        start_idx: int,
        end_idx: int,
        language: str
    ) -> PersonCandidate:
        """Create a person candidate from tokens and metadata."""
        validation = self.validate_person_structure(tokens, roles)
        gender = self.detect_gender_from_sequence(tokens, roles, language)

        return PersonCandidate(
            tokens=tokens,
            roles=roles,
            start_index=start_idx,
            end_index=end_idx,
            confidence=validation["confidence"],
            gender=gender,
            language=language
        )

    def _detect_gender_from_given_name(
        self,
        name: str,
        language: str
    ) -> Optional[str]:
        """Detect gender from a given name."""
        if not name:
            return None

        name_lower = name.lower()

        # Basic gender detection based on name endings
        if language in ["ru", "uk"]:
            # Russian/Ukrainian patterns
            if name_lower.endswith(('а', 'я', 'ия', 'ья', 'на', 'ка')):
                return "femn"
            elif name_lower.endswith(('й', 'ь', 'н', 'м', 'р', 'с', 'т', 'л')):
                return "masc"

        # TODO: Add more sophisticated gender detection using dictionaries
        return None

    def _detect_gender_from_patronymic(
        self,
        patronymic: str,
        language: str
    ) -> Optional[str]:
        """Detect gender from a patronymic."""
        if not patronymic:
            return None

        patronymic_lower = patronymic.lower()

        if language in ["ru", "uk"]:
            # Feminine patronymic endings
            if patronymic_lower.endswith(('овна', 'евна', 'ична', 'инична', 'ївна')):
                return "femn"
            # Masculine patronymic endings
            elif patronymic_lower.endswith(('ович', 'евич', 'ич', 'ыч', 'ович')):
                return "masc"

        return None

    def merge_adjacent_persons(
        self,
        persons: List[PersonCandidate],
        max_gap: int = 1
    ) -> List[PersonCandidate]:
        """Merge adjacent person candidates that might be the same person."""
        if len(persons) <= 1:
            return persons

        merged = []
        current = persons[0]

        for next_person in persons[1:]:
            # Check if they should be merged
            gap = next_person.start_index - current.end_index - 1
            if gap <= max_gap and self._should_merge_persons(current, next_person):
                # Merge the persons
                current = PersonCandidate(
                    tokens=current.tokens + next_person.tokens,
                    roles=current.roles + next_person.roles,
                    start_index=current.start_index,
                    end_index=next_person.end_index,
                    confidence=max(current.confidence, next_person.confidence),
                    gender=current.gender or next_person.gender,
                    language=current.language or next_person.language
                )
            else:
                # Keep current person and start new one
                merged.append(current)
                current = next_person

        merged.append(current)
        return merged

    def _should_merge_persons(
        self,
        person1: PersonCandidate,
        person2: PersonCandidate
    ) -> bool:
        """Check if two person candidates should be merged."""
        # Don't merge if one has a complete name structure
        validation1 = self.validate_person_structure(person1.tokens, person1.roles)
        validation2 = self.validate_person_structure(person2.tokens, person2.roles)

        if validation1["structure_score"] > 0.7 and validation2["structure_score"] > 0.7:
            return False

        # Merge if one is mostly initials and the other has more substance
        initials1 = sum(1 for role in person1.roles if role == "initial")
        initials2 = sum(1 for role in person2.roles if role == "initial")

        if initials1 > len(person1.roles) * 0.8 or initials2 > len(person2.roles) * 0.8:
            return True

        return False
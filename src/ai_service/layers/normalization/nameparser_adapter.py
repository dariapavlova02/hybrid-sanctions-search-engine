"""
Nameparser adapter for English name normalization.

This module provides a standardized interface to the nameparser library
for parsing English names into structured components.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Use lazy import to avoid module-level warning
from ...utils.lazy_imports import NAMEPARSER

def get_human_name():
    """Get HumanName class if nameparser is available."""
    if NAMEPARSER is not None:
        return NAMEPARSER.HumanName
    return None

# Set availability flag based on lazy import
NAMEPARSER_AVAILABLE = NAMEPARSER is not None
HumanName = get_human_name()


@dataclass
class ParsedName:
    """Container for parsed name components."""
    first: str
    middles: List[str]
    last: str
    suffix: str
    nickname: str
    particles: List[str]
    title: str
    full_name: str
    confidence: float = 0.0


class NameparserAdapter:
    """
    Adapter for nameparser library with nickname expansion and particle handling.
    """

    def __init__(self, lexicons_path: Optional[Path] = None):
        """
        Initialize the adapter with lexicon paths.

        Args:
            lexicons_path: Path to lexicons directory
        """
        self.lexicons_path = lexicons_path or Path(__file__).parent.parent.parent.parent.parent / "data" / "lexicons"
        self.nicknames: Dict[str, str] = {}
        self.surname_particles: Set[str] = set()
        self._load_lexicons()

    def _load_lexicons(self) -> None:
        """Load nickname and particle lexicons."""
        try:
            # Load nicknames
            nicknames_path = self.lexicons_path / "en_nicknames.json"
            if nicknames_path.exists():
                with open(nicknames_path, "r", encoding="utf-8") as f:
                    self.nicknames = json.load(f)
                logger.info(f"Loaded {len(self.nicknames)} English nicknames")
            else:
                logger.warning(f"Nicknames file not found: {nicknames_path}")

            # Load surname particles
            particles_path = self.lexicons_path / "en_surname_particles.txt"
            if particles_path.exists():
                with open(particles_path, "r", encoding="utf-8") as f:
                    self.surname_particles = {line.strip().lower() for line in f if line.strip()}
                logger.info(f"Loaded {len(self.surname_particles)} surname particles")
            else:
                logger.warning(f"Surname particles file not found: {particles_path}")

        except Exception as e:
            logger.error(f"Failed to load lexicons: {e}")

    def parse_en_name(self, text: str, enable_nicknames: bool = True, filter_titles_suffixes: bool = True) -> ParsedName:
        """
        Parse an English name using nameparser with graceful fallback.

        Args:
            text: The name text to parse

        Returns:
            ParsedName object with structured components
        """
        if not text or not text.strip():
            return ParsedName(
                first="", middles=[], last="", suffix="", 
                nickname="", particles=[], title="", full_name="", confidence=0.0
            )

        # Graceful fallback if nameparser is not available
        if not NAMEPARSER_AVAILABLE or HumanName is None:
            logger.warning("nameparser not available, using fallback parsing")
            return self._fallback_parse_en_name(text.strip(), enable_nicknames, filter_titles_suffixes)

        try:
            # Parse with nameparser
            parsed = HumanName(text.strip())

            # Special handling for Irish/Scottish surnames with apostrophes
            # If only one component and it looks like a surname, treat it as surname
            components_count = len([x for x in [parsed.first, parsed.middle, parsed.last] if x])
            if components_count == 1 and self._is_irish_scottish_surname(parsed.first):
                # Move from first to last name
                first_raw = ""
                last_raw = parsed.first
                middles_raw = []
            else:
                # Extract components normally
                first_raw = parsed.first or ""
                middles_raw = [m for m in parsed.middle.split() if m] if parsed.middle else []
                last_raw = parsed.last or ""

            suffix_raw = parsed.suffix or ""
            title_raw = parsed.title or ""
            
            # Detect nickname (simple heuristic: if first name is common nickname)
            nickname = ""
            first = first_raw
            if enable_nicknames and first_raw and first_raw.lower() in self.nicknames:
                nickname = first_raw
                first = self.nicknames[first_raw.lower()]
            
            # Normalize case
            first = first.title()
            middles = [m.title() for m in middles_raw]
            last = last_raw.title()
            suffix = suffix_raw  # Keep suffixes as-is (no titlecase)
            title = title_raw  # Keep titles as-is (no titlecase)
            
            # Extract particles from last name
            particles = self._extract_particles(last)
            
            # Calculate confidence based on parsing quality
            confidence = self._calculate_confidence(parsed, first, last)
            
            return ParsedName(
                first=first,
                middles=middles,
                last=last,
                suffix=suffix,
                nickname=nickname,
                particles=particles,
                title=title,
                full_name=text.strip(),
                confidence=confidence
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse name '{text}': {e}")
            return ParsedName(
                first="", middles=[], last="", suffix="", 
                nickname="", particles=[], title="", full_name=text.strip(), confidence=0.0
            )

    def _is_irish_scottish_surname(self, name: str) -> bool:
        """
        Check if a name looks like an Irish or Scottish surname.

        Common patterns:
        - O' prefix (Irish): O'Connor, O'Brien, O'Neil
        - Mc/Mac prefix (Scottish/Irish): McDonald, MacLeod, McGrath
        - D' prefix (French/Irish): D'Artagnan, D'Angelo
        """
        if not name:
            return False

        name_lower = name.lower()

        # Irish O' surnames
        if name_lower.startswith("o'") and len(name) > 2:
            return True

        # Scottish/Irish Mc/Mac surnames
        if (name_lower.startswith("mc") or name_lower.startswith("mac")) and len(name) > 2:
            return True

        # French/Irish D' surnames
        if name_lower.startswith("d'") and len(name) > 2:
            return True

        return False

    def _extract_particles(self, last_name: str) -> List[str]:
        """
        Extract surname particles from the last name.

        Args:
            last_name: The last name to analyze

        Returns:
            List of particles found
        """
        if not last_name:
            return []
        
        words = last_name.lower().split()
        particles = []
        
        for word in words:
            if word in self.surname_particles:
                particles.append(word)
        
        return particles

    def _calculate_confidence(self, parsed: HumanName, first: str, last: str) -> float:
        """
        Calculate confidence score for the parsed name.

        Args:
            parsed: The parsed HumanName object
            first: The first name
            last: The last name

        Returns:
            Confidence score between 0.0 and 1.0
        """
        score = 0.0
        
        # Base score for having first and last names
        if first and last:
            score += 0.6
        elif first or last:
            score += 0.3
        
        # Bonus for middle names
        if parsed.middle:
            score += 0.1
        
        # Bonus for suffix
        if parsed.suffix:
            score += 0.1
        
        # Bonus for title
        if parsed.title:
            score += 0.1
        
        # Penalty for very short names
        if len(first) < 2 and len(last) < 2:
            score -= 0.2
        
        return max(0.0, min(1.0, score))

    def expand_nickname(self, name: str) -> Tuple[str, bool]:
        """
        Expand a nickname to its full form.

        Args:
            name: The name to potentially expand

        Returns:
            Tuple of (expanded_name, was_expanded)
        """
        if not name:
            return name, False
        
        name_lower = name.lower()
        if name_lower in self.nicknames:
            return self.nicknames[name_lower], True
        
        return name, False

    def is_surname_particle(self, word: str) -> bool:
        """
        Check if a word is a surname particle.

        Args:
            word: The word to check

        Returns:
            True if the word is a surname particle
        """
        return word.lower() in self.surname_particles

    def reconstruct_name(self, parsed: ParsedName, include_particles: bool = True) -> str:
        """
        Reconstruct the full name from parsed components.

        Args:
            parsed: The parsed name components
            include_particles: Whether to include particles in reconstruction

        Returns:
            Reconstructed full name
        """
        parts = []
        
        # Add first name
        if parsed.first:
            parts.append(parsed.first)
        
        # Add middle names
        if parsed.middles:
            parts.extend(parsed.middles)
        
        # Add last name with particles
        if parsed.last:
            if include_particles and parsed.particles:
                # Reconstruct with particles
                last_parts = parsed.particles + [parsed.last]
                parts.append(" ".join(last_parts))
            else:
                parts.append(parsed.last)
        
        # Add suffix
        if parsed.suffix:
            parts.append(parsed.suffix)
        
        return " ".join(parts)

    def _fallback_parse_en_name(self, text: str, enable_nicknames: bool = True, filter_titles_suffixes: bool = True) -> ParsedName:
        """
        Fallback parsing when nameparser is not available.
        
        Args:
            text: The name text to parse
            
        Returns:
            ParsedName object with basic parsing
        """
        if not text:
            return ParsedName(
                first="", middles=[], last="", suffix="", 
                nickname="", particles=[], title="", full_name="", confidence=0.0
            )
        
        # Handle common titles and suffixes
        title = ""
        suffix = ""
        
        # Common titles
        titles = ["Dr.", "Mr.", "Mrs.", "Ms.", "Prof.", "Rev.", "Sir", "Lady"]
        # Common suffixes
        suffixes = ["Jr.", "Sr.", "III", "IV", "V", "Ph.D.", "M.D.", "Esq."]
        # Middle initials (single letter followed by period)
        initials = []
        
        parts = text.strip().split()
        
        # Check for title at beginning (only if filtering is enabled)
        if filter_titles_suffixes and parts and parts[0] in titles:
            title = parts[0]
            parts = parts[1:]
        
        # Check for suffix at end (only if filtering is enabled)
        if filter_titles_suffixes and parts and parts[-1] in suffixes:
            suffix = parts[-1]
            parts = parts[:-1]
        
        # Check for middle initials (only if filtering is enabled)
        if filter_titles_suffixes:
            # Remove single-letter middle names (initials)
            filtered_parts = []
            for part in parts:
                if len(part) == 2 and part[1] == '.' and part[0].isalpha():
                    # This is a middle initial, skip it
                    initials.append(part)
                else:
                    filtered_parts.append(part)
            parts = filtered_parts
        
        if len(parts) == 0:
            return ParsedName(
                first="", middles=[], last="", suffix=suffix, 
                nickname="", particles=[], title=title, full_name=text, confidence=0.0
            )
        elif len(parts) == 1:
            # Single name - assume it's a surname
            return ParsedName(
                first="", middles=[], last=parts[0].title(), suffix=suffix, 
                nickname="", particles=[], title=title, full_name=text, confidence=0.3
            )
        else:
            # Multiple parts - first is given, last is surname, middle are middle names
            first = parts[0].title()
            last = parts[-1].title()
            middles = [part.title() for part in parts[1:-1]]
            
            # Check for nickname expansion (only if enabled)
            nickname = ""
            if enable_nicknames and first.lower() in self.nicknames:
                nickname = first
                first = self.nicknames[first.lower()]
            
            return ParsedName(
                first=first, middles=middles, last=last, suffix=suffix, 
                nickname=nickname, particles=[], title=title, full_name=text, confidence=0.5
            )


# Singleton instance
_nameparser_adapter: Optional[NameparserAdapter] = None


def get_nameparser_adapter(lexicons_path: Optional[Path] = None) -> NameparserAdapter:
    """
    Get a singleton instance of NameparserAdapter.

    Args:
        lexicons_path: Path to lexicons directory

    Returns:
        NameparserAdapter instance
    """
    global _nameparser_adapter
    if _nameparser_adapter is None:
        _nameparser_adapter = NameparserAdapter(lexicons_path)
    return _nameparser_adapter

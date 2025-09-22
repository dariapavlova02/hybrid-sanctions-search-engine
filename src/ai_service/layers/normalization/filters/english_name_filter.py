"""English name filtering for titles, suffixes and middle names."""

import re
from typing import List, Tuple, Optional
from ....utils.logging_config import get_logger

logger = get_logger(__name__)

# English titles to remove
ENGLISH_TITLES = {
    # Common titles
    'mr', 'mrs', 'ms', 'miss', 'mx',
    # Professional titles
    'dr', 'prof', 'professor',
    # Honorifics
    'sir', 'dame', 'lord', 'lady',
    # Religious
    'rev', 'reverend', 'father', 'fr', 'sister', 'sr',
    # Military
    'capt', 'captain', 'col', 'colonel', 'gen', 'general',
    'lt', 'lieutenant', 'sgt', 'sergeant', 'adm', 'admiral',
    'maj', 'major', 'cmdr', 'commander',
    # Legal/Government
    'hon', 'honorable', 'judge', 'justice', 'president',
    'ambassador', 'amb', 'senator', 'sen', 'governor', 'gov'
}

# English suffixes to remove (academic/professional only, preserve generation suffixes)
ENGLISH_SUFFIXES = {
    # Academic degrees
    'phd', 'ph.d', 'md', 'm.d', 'dds', 'd.d.s', 'jd', 'j.d',
    'mba', 'm.b.a', 'ma', 'm.a', 'ms', 'm.s', 'bs', 'b.s',
    'ba', 'b.a', 'edd', 'ed.d', 'psyd', 'psy.d',
    # Professional certifications
    'cpa', 'c.p.a', 'rn', 'r.n', 'pe', 'p.e',
    # Legal suffixes
    'esq', 'esquire'
}

# Generation suffixes to preserve (not remove)
GENERATION_SUFFIXES = {
    'jr', 'sr', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x',
    '2nd', '3rd', '4th', '5th'
}

# Name particles to preserve in surname block
SURNAME_PARTICLES = {
    'van', 'von', 'de', 'del', 'della', 'der', 'di', 'da', 'dos', 'du',
    'le', 'la', 'las', 'los', 'st', 'st.', 'ste', 'ste.',
    'al', 'el', 'ibn', 'bin', 'abu', 'ben', 'bar',
    # Spanish surname particles (excluding compound given names)
    'de la', 'de las', 'de los'
}

# Compound given name patterns that should NOT be treated as surname particles
COMPOUND_GIVEN_NAMES = {
    'del carmen', 'maria del carmen', 'ana maria', 'ana maría'
}


class EnglishNameFilter:
    """Filter English names to canonical First Last format."""

    def __init__(self):
        """Initialize the filter."""
        # Compile regex patterns for efficiency
        self._title_pattern = self._compile_title_pattern()
        self._suffix_pattern = self._compile_suffix_pattern()

    def _compile_title_pattern(self) -> re.Pattern:
        """Compile regex pattern for titles."""
        # Match titles at start of string with optional punctuation
        titles = '|'.join(re.escape(title) for title in ENGLISH_TITLES)
        return re.compile(
            rf'^({titles})\.?\s+',
            re.IGNORECASE
        )

    def _compile_suffix_pattern(self) -> re.Pattern:
        """Compile regex pattern for suffixes."""
        # Match suffixes at end with optional comma/punctuation
        suffixes = '|'.join(re.escape(suffix) for suffix in ENGLISH_SUFFIXES)
        return re.compile(
            rf',?\s+({suffixes})\.?$',
            re.IGNORECASE
        )

    def filter_name(self, name: str) -> Tuple[str, List[str]]:
        """
        Filter English name to canonical First Last format.

        Args:
            name: Input name string

        Returns:
            Tuple of (filtered_name, applied_rules)
        """
        if not name or not name.strip():
            return name, []

        original_name = name.strip()
        current_name = original_name
        applied_rules = []

        # Step 1: Remove leading titles (may have multiple)
        while True:
            title_match = self._title_pattern.search(current_name)
            if not title_match:
                break
            removed_title = title_match.group(1)
            current_name = self._title_pattern.sub('', current_name).strip()
            applied_rules.append(f"title_filter:removed_{removed_title.lower()}")
            logger.debug(f"Removed title '{removed_title}' from name")

        # Step 2: Remove trailing suffixes (may have multiple)
        while True:
            suffix_match = self._suffix_pattern.search(current_name)
            if not suffix_match:
                break
            removed_suffix = suffix_match.group(1)
            current_name = self._suffix_pattern.sub('', current_name).strip()
            applied_rules.append(f"suffix_filter:removed_{removed_suffix.lower()}")
            logger.debug(f"Removed suffix '{removed_suffix}' from name")

        # Step 3: Apply middle name filtering
        filtered_name, middle_rules = self._filter_middle_names(current_name)
        applied_rules.extend(middle_rules)

        return filtered_name, applied_rules

    def _filter_middle_names(self, name: str) -> Tuple[str, List[str]]:
        """
        Filter middle names to keep only First Last.

        Args:
            name: Name after title/suffix removal

        Returns:
            Tuple of (filtered_name, applied_rules)
        """
        if not name or not name.strip():
            return name, []

        # Tokenize by whitespace, preserving hyphens and apostrophes within tokens
        tokens = name.split()
        if len(tokens) <= 2:
            # Already in First Last format or shorter
            return name, []

        applied_rules = []

        # Check for compound given names first
        name_lower = name.lower()
        for compound_name in COMPOUND_GIVEN_NAMES:
            if compound_name in name_lower:
                # Special handling for compound given names
                if compound_name == 'del carmen':
                    # "Maria del Carmen Fernandez" -> "Maria del Carmen Fernandez"
                    # Keep "del Carmen" as part of given name
                    return name, []
                elif compound_name in ['ana maria', 'ana maría']:
                    # "Ana María de la Cruz" -> "Ana de la Cruz" (remove María)
                    # Find position of "María" and remove it
                    parts = name.split()
                    if len(parts) >= 3 and parts[1].lower() in ['maría', 'maria']:
                        # Remove the middle name (María)
                        filtered = f"{parts[0]} {' '.join(parts[2:])}"
                        applied_rules.append("middle_name_filter:removed_1_tokens")
                        return filtered, applied_rules

        # Step 1: Identify surname block (from the end)
        surname_tokens = []
        remaining_tokens = tokens[:]

        # Collect surname particles and the final surname
        i = len(remaining_tokens) - 1
        while i >= 0:
            token = remaining_tokens[i]
            token_lower = token.lower().rstrip('.')

            # Always include the last token as part of surname
            if i == len(remaining_tokens) - 1:
                surname_tokens.insert(0, token)
                i -= 1
                continue

            # Check for multi-word particles first (e.g., "de la")
            for particle in sorted(SURNAME_PARTICLES, key=len, reverse=True):
                particle_tokens = particle.split()
                if len(particle_tokens) > 1 and i >= len(particle_tokens) - 1:
                    # Check if current position matches end of multi-word particle
                    match = True
                    for j, p_token in enumerate(reversed(particle_tokens)):
                        if i - j < 0 or remaining_tokens[i - j].lower().rstrip('.') != p_token:
                            match = False
                            break
                    if match:
                        # Add all tokens of the multi-word particle
                        for j in range(len(particle_tokens)):
                            surname_tokens.insert(0, remaining_tokens[i - len(particle_tokens) + 1 + j])
                        i -= len(particle_tokens)
                        break
            else:
                # Single word particle check
                if token_lower in SURNAME_PARTICLES:
                    surname_tokens.insert(0, token)
                    i -= 1
                    continue

                # Include hyphenated parts of compound surnames
                if (len(surname_tokens) > 0 and
                    (token.endswith('-') or surname_tokens[0].startswith('-'))):
                    surname_tokens.insert(0, token)
                    i -= 1
                    continue

                # Stop collecting surname tokens
                break

        # Remove collected surname tokens from remaining
        surname_count = len(surname_tokens)
        first_tokens = remaining_tokens[:-surname_count] if surname_count > 0 else remaining_tokens

        # Step 2: Keep only the first given name
        if len(first_tokens) > 1:
            given_name = first_tokens[0]
            removed_middle = first_tokens[1:]
            applied_rules.append(f"middle_name_filter:removed_{len(removed_middle)}_tokens")
            logger.debug(f"Removed middle names: {removed_middle}")
        elif len(first_tokens) == 1:
            given_name = first_tokens[0]
        else:
            # Only surname, no given name
            given_name = ""

        # Step 3: Reconstruct name
        if given_name and surname_tokens:
            filtered_name = f"{given_name} {' '.join(surname_tokens)}"
        elif surname_tokens:
            filtered_name = ' '.join(surname_tokens)
        elif given_name:
            filtered_name = given_name
        else:
            filtered_name = name  # Fallback

        return filtered_name, applied_rules

    def should_apply_filter(self, language: str, text: str = "") -> bool:
        """
        Check if filter should be applied for given language and text.

        Only apply filter to formal names with titles, suffixes, or multiple middle names.
        """
        if language != "en":
            return False

        if not text:
            return False

        # Apply filter only if text contains formal indicators
        text_lower = text.lower()

        # Check for titles
        for title in ENGLISH_TITLES:
            if f"{title}." in text_lower or f"{title} " in text_lower:
                return True

        # Check for suffixes (both removable and generation)
        for suffix in ENGLISH_SUFFIXES:
            if f", {suffix}" in text_lower or f" {suffix}." in text_lower or text_lower.endswith(f" {suffix}"):
                return True

        # Check for generation suffixes (preserved but still trigger filtering)
        for suffix in GENERATION_SUFFIXES:
            if f", {suffix}" in text_lower or f" {suffix}." in text_lower or text_lower.endswith(f" {suffix}"):
                return True

        # Check for compound given names that need special handling
        for compound_name in COMPOUND_GIVEN_NAMES:
            if compound_name in text_lower:
                return True

        # Normalize double dots for pattern analysis
        normalized_text = text.replace('..', '.')
        tokens = normalized_text.split()

        # Check for multiple middle names (4+ tokens = potentially multiple middles)
        # Only apply if there are also formal indicators, not just simple nickname sequences
        if len(tokens) >= 4:  # First + multiple middle + Last
            # Check if this looks like a formal name with particles or if it's just nicknames
            text_has_particles = any(token.lower().rstrip('.') in SURNAME_PARTICLES for token in tokens)
            if text_has_particles:
                return True
            # Don't apply to simple nickname sequences like "Bill Jim Bob Davis"

        # Check for 3 tokens with specific patterns
        if len(tokens) == 3:
            first_token, middle_token, last_token = tokens

            # Don't apply to double initials pattern (J. J. Smith, A. B. Smith)
            if (len(first_token) <= 2 and first_token.endswith('.') and
                len(middle_token) <= 2 and middle_token.endswith('.')):
                return False

            # Apply if middle token is a single initial (G., P., etc.)
            if len(middle_token) <= 2 and middle_token.endswith('.'):
                return True

            # For full middle names, only apply if there are other formal indicators
            # Don't apply to simple nickname patterns like "Bill Bob Johnson"
            if len(middle_token) > 2 and not middle_token.endswith('.'):
                # Only apply if the name has other formal characteristics
                # This prevents filtering simple nickname cases
                return False

        # Don't apply to simple cases like "John Smith", "J. Smith"
        return False


# Global instance for use in normalization pipeline
english_name_filter = EnglishNameFilter()
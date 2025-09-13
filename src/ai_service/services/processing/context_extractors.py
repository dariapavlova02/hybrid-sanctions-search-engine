"""
Context Extractors
Specialized extractors for payment context, names, and companies.
Extracted from the monolithic orchestrator service.
"""

import re
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Tuple

from ..config import SERVICE_CONFIG
from ..utils import get_logger
from .pattern_service import PatternService


class ContextExtractor(ABC):
    """Abstract base class for context extractors"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"{__name__}.{name}")
    
    @abstractmethod
    def extract(self, text: str, language: str, **kwargs) -> Optional[str]:
        """
        Extract relevant information from text
        
        Args:
            text: Input text
            language: Detected language
            **kwargs: Additional parameters
            
        Returns:
            Extracted information or None
        """
        pass


class PaymentContextNameExtractor(ContextExtractor):
    """Extracts names from payment context using pattern matching"""
    
    def __init__(self, pattern_service: PatternService):
        super().__init__("payment_context_name")
        self.pattern_service = pattern_service
    
    def extract(self, text: str, language: str, **kwargs) -> Optional[str]:
        """Extract payment context name"""
        
        try:
            # Try with detected language first
            patterns = self.pattern_service.generate_patterns(text, language)
            ctx_patterns = [
                p for p in patterns
                if getattr(p, "pattern_type", "") == "payment_context"
            ]
            
            if not ctx_patterns:
                # Fallback: try the other Slavic language for mixed texts
                alt_lang = "ru" if language == "uk" else "uk"
                patterns_alt = self.pattern_service.generate_patterns(text, alt_lang)
                ctx_patterns = [
                    p for p in patterns_alt
                    if getattr(p, "pattern_type", "") == "payment_context"
                ]
            
            if not ctx_patterns:
                # Last fallback: auto-detect inside PatternService
                patterns_auto = self.pattern_service.generate_patterns(text, "auto")
                ctx_patterns = [
                    p for p in patterns_auto
                    if getattr(p, "pattern_type", "") == "payment_context"
                ]
            
            if not ctx_patterns:
                return None
            
            # Choose the longest extracted pattern as best candidate
            best = max(ctx_patterns, key=lambda p: (len(p.pattern or ""), p.confidence))
            return best.pattern
            
        except Exception as e:
            self.logger.debug(f"Payment context extraction failed: {e}")
            return None


class InitialSurnameExtractor(ContextExtractor):
    """Extracts single-initial + surname patterns (e.g., 'P. Poroshenko')"""
    
    def __init__(self):
        super().__init__("initial_surname")
    
    def extract(self, text: str, language: str, **kwargs) -> Optional[str]:
        """Extract initial + surname pattern"""
        
        match = re.search(
            r"\b([A-Za-zА-ЯІЇЄ])\.\s*([A-Za-zА-ЯІЇЄ][a-zA-Zа-яіїєґ\-]+)\b",
            text
        )
        
        if match:
            return f"{match.group(1)}. {match.group(2)}"
        
        return None


class CompanyContextExtractor(ContextExtractor):
    """Extracts company names from payment/recipient context"""
    
    def __init__(self, pattern_service: PatternService):
        super().__init__("company_context")
        self.pattern_service = pattern_service
    
    def extract(self, text: str, language: str, **kwargs) -> Optional[str]:
        """Extract company context"""
        
        try:
            patterns = self.pattern_service.generate_patterns(text, language)
            company_patterns = [
                p for p in patterns
                if getattr(p, "pattern_type", "") == "company_context"
            ]
            
            # Filter out patterns that are just legal entity markers
            filtered_patterns = [
                p for p in company_patterns
                if self._not_just_marker(p.pattern or "")
            ]
            
            if not filtered_patterns:
                # Try alternative language
                alt_lang = "ru" if language == "uk" else "uk"
                alt_patterns = self.pattern_service.generate_patterns(text, alt_lang)
                company_patterns = [
                    p for p in alt_patterns
                    if getattr(p, "pattern_type", "") == "company_context"
                ]
                filtered_patterns = [
                    p for p in company_patterns
                    if self._not_just_marker(p.pattern or "")
                ]
            
            if not filtered_patterns:
                # Last fallback
                auto_patterns = self.pattern_service.generate_patterns(text, "auto")
                company_patterns = [
                    p for p in auto_patterns
                    if getattr(p, "pattern_type", "") == "company_context"
                ]
                filtered_patterns = [
                    p for p in company_patterns
                    if self._not_just_marker(p.pattern or "")
                ]
            
            if not filtered_patterns:
                return None
            
            best = max(filtered_patterns, key=lambda p: (len(p.pattern or ""), p.confidence))
            return best.pattern
            
        except Exception as e:
            self.logger.debug(f"Company context extraction failed: {e}")
            return None
    
    def _not_just_marker(self, pattern: str) -> bool:
        """Check if pattern is not just a legal entity marker"""
        
        try:
            from ..data.dicts.company_triggers import COMPANY_TRIGGERS
            
            legal_entities = set()
            for lang in ("ru", "uk", "en"):
                legal_entities.update(
                    COMPANY_TRIGGERS.get(lang, {}).get("legal_entities", [])
                )
            
            return pattern.lower() not in {le.lower() for le in legal_entities}
            
        except Exception:
            # Fallback: simple length check
            return len(pattern) > 4


class StopWordsCleaner:
    """Utility class for cleaning stop words around name regions"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self._stop_words = {"ru": set(), "uk": set(), "en": set()}
    
    def clean(self, text: str, language: str) -> str:
        """Remove known stop words around the possible name region"""
        
        stop_words = set(self._stop_words.get(language, []))
        
        # For Slavic texts, union RU and UK to handle mixed phrasing
        if language in ("ru", "uk"):
            stop_words = stop_words.union(self._stop_words.get("ru", set())).union(
                self._stop_words.get("uk", set())
            )
        
        # Add long legal phrases (not part of normalized names)
        try:
            from ..data.dicts.company_triggers import COMPANY_TRIGGERS
            
            for lang in ("ru", "uk", "en"):
                for phrase in COMPANY_TRIGGERS.get(lang, {}).get("long_phrases", []):
                    stop_words.add(phrase.lower())
        except Exception:
            pass
        
        if not text or not stop_words:
            return text
        
        tokens = re.findall(r"[A-Za-zА-Яа-яІіЇїЄєҐґ\'-]+", text)
        
        # Remove leading/trailing stop words
        while tokens and tokens[0].lower() in stop_words:
            tokens.pop(0)
        while tokens and tokens[-1].lower() in stop_words:
            tokens.pop()
        
        return " ".join(tokens)


class CompanyNameNormalizer:
    """Normalizes company names by removing document tails and legal entity markers"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def normalize(self, text: str, language: str) -> str:
        """
        Normalize company name: drop doc tails, keep legal entity prefix and core name
        
        Args:
            text: Company name to normalize
            language: Language of the text
            
        Returns:
            Normalized company name
        """
        
        if not text:
            return ""
        
        normalized = text
        
        # Remove trailing contract/date/number tails
        normalized = re.split(
            r"\b(по\s+договор[ау]|догов[оі]р[ау]?|контракт[ау]?|№|#|от\s+\d|від\s+\d)",
            normalized,
            maxsplit=1,
        )[0]
        
        normalized = re.sub(r"\s+", " ", normalized).strip()
        
        # Remove enclosing quotes
        normalized = re.sub(r'^["«»\']\s*|\s*["«»\']$', "", normalized)
        
        # Handle legal entity markers based on configuration
        try:
            from ..data.dicts.company_triggers import COMPANY_TRIGGERS
            
            legal_entities = set()
            long_phrases = []
            
            for lang in ("ru", "uk", "en"):
                data = COMPANY_TRIGGERS.get(lang, {})
                legal_entities.update([x.lower() for x in data.get("legal_entities", [])])
                long_phrases.extend([x.lower() for x in data.get("long_phrases", [])])
            
            # Optionally keep legal entity abbreviations
            if not SERVICE_CONFIG.keep_legal_entity_prefix:
                parts = normalized.split()
                while parts and parts[0].lower().strip('."«»"') in legal_entities:
                    parts.pop(0)
                normalized = " ".join(parts)
            
            # Remove long phrases at start regardless
            for phrase in long_phrases:
                normalized = re.sub(
                    rf"^(?:{re.escape(phrase)})\s+",
                    "",
                    normalized,
                    flags=re.IGNORECASE
                )
        
        except Exception as e:
            self.logger.debug(f"Error processing legal entities: {e}")
        
        return normalized.strip()


class NameCanonicalizer:
    """Canonicalizes person names using morphological analysis"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self._uk_surname_suffixes = ('енко', 'енка', 'енку', 'енком', 'енці')
    
    def canonicalize(self, name_phrase: str, language: str) -> Optional[str]:
        """
        Canonicalize name phrase to standard form
        
        Args:
            name_phrase: Name phrase to canonicalize
            language: Language for morphological processing
            
        Returns:
            Canonicalized name or None if processing fails
        """
        
        try:
            # This would need morphological services to be properly integrated
            # For now, return a basic cleaned version
            
            # Basic cleanup: trim whitespace, normalize spacing
            cleaned = re.sub(r'\s+', ' ', name_phrase.strip())
            
            # Capitalize first letter of each word
            words = cleaned.split()
            canonicalized_words = []
            
            for word in words:
                if len(word) > 0:
                    canonicalized_words.append(word[0].upper() + word[1:].lower())
            
            result = ' '.join(canonicalized_words)
            
            self.logger.debug(f"Canonicalized '{name_phrase}' -> '{result}'")
            return result
            
        except Exception as e:
            self.logger.debug(f"Name canonicalization failed: {e}")
            return None
    
    def is_ukrainian_surname(self, surname: str) -> bool:
        """Check if surname looks Ukrainian based on suffixes"""
        
        if not surname:
            return False
        
        return surname.lower().endswith(self._uk_surname_suffixes)


class FOPProcessor:
    """Processes individual entrepreneur (FOP/IP) entries"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def extract_person_from_fop(self, text: str) -> Optional[str]:
        """
        Extract person name from FOP/IP text
        
        Args:
            text: Text containing FOP/IP designation
            
        Returns:
            Extracted person name or None
        """
        
        # Match FOP/IP marker and extract what follows
        match = re.search(
            r"\b(?:фоп|ип|fop|ip)\b\s*(.+)$",
            text,
            re.IGNORECASE,
        )
        
        if not match:
            return None
        
        fop_tail = match.group(1).strip()
        
        # Extract name-like tokens
        tokens = re.findall(
            r"[A-Za-zА-Яа-яІіЇїЄєҐґ\'\u02BC\u2019\-]+",
            fop_tail
        )
        
        name_tokens = []
        for token in tokens:
            if len(token) < 2:
                continue
            
            # Heuristic: first letter uppercase, contains letters/apostrophes
            if re.match(r"^[A-ZА-ЯІЇЄ][a-zA-Zа-яіїєґ\'\u02BC\u2019\-]+$", token):
                name_tokens.append(token)
            # Patronymic endings (ru/uk)
            elif re.search(r"(вич|вна|івна|йович|ьович|ич)$", token, re.IGNORECASE):
                name_tokens.append(token)
        
        # Keep up to first three plausible name tokens
        if name_tokens:
            result = " ".join(name_tokens[:3])
            self.logger.debug(f"Extracted FOP person: '{fop_tail}' -> '{result}'")
            return result
        
        return None


class ContextExtractionCoordinator:
    """
    Coordinates all context extraction operations
    Replaces the context extraction logic from the orchestrator service
    """
    
    def __init__(self, pattern_service: PatternService):
        """Initialize with required services"""
        
        self.logger = get_logger(__name__)
        
        # Initialize extractors
        self.payment_name_extractor = PaymentContextNameExtractor(pattern_service)
        self.initial_surname_extractor = InitialSurnameExtractor()
        self.company_extractor = CompanyContextExtractor(pattern_service)
        
        # Initialize utilities
        self.stop_words_cleaner = StopWordsCleaner()
        self.company_normalizer = CompanyNameNormalizer()
        self.name_canonicalizer = NameCanonicalizer()
        self.fop_processor = FOPProcessor()
    
    def extract_best_name_candidate(
        self, text: str, language: str, apply_cleaning: bool = True
    ) -> Optional[str]:
        """
        Extract the best name candidate from text using multiple strategies
        
        Args:
            text: Input text
            language: Detected language
            apply_cleaning: Whether to apply stop word cleaning
            
        Returns:
            Best name candidate or None
        """
        
        # Strategy 1: Extract name from payment context
        candidate = self.payment_name_extractor.extract(text, language)
        
        # Strategy 2: If not found, try after cleaning stop words
        if not candidate and apply_cleaning:
            cleaned_text = self.stop_words_cleaner.clean(text, language)
            if cleaned_text and cleaned_text != text:
                candidate = self.payment_name_extractor.extract(cleaned_text, language)
        
        # Strategy 3: Try initial + surname pattern
        if not candidate:
            candidate = self.initial_surname_extractor.extract(text, language)
            if not candidate and apply_cleaning:
                cleaned_text = self.stop_words_cleaner.clean(text, language)
                if cleaned_text and cleaned_text != text:
                    candidate = self.initial_surname_extractor.extract(cleaned_text, language)
        
        # Strategy 4: Canonicalize if we found something
        if candidate:
            try:
                canonical = self.name_canonicalizer.canonicalize(candidate, language)
                
                # Heuristic: force Ukrainian if surname looks Ukrainian
                if language != "uk" and candidate:
                    parts = re.findall(r"[A-Za-zА-Яа-яІіЇїЄєҐґ\'-]+", candidate)
                    if len(parts) > 1 and self.name_canonicalizer.is_ukrainian_surname(parts[-1]):
                        canonical_uk = self.name_canonicalizer.canonicalize(candidate, "uk")
                        canonical = canonical_uk or canonical
                
                return canonical or candidate
                
            except Exception as e:
                self.logger.debug(f"Name canonicalization failed: {e}")
                return candidate
        
        return None
    
    def extract_best_company_candidate(
        self, text: str, language: str, apply_cleaning: bool = True
    ) -> Optional[str]:
        """
        Extract the best company candidate from text
        
        Args:
            text: Input text
            language: Detected language
            apply_cleaning: Whether to apply stop word cleaning
            
        Returns:
            Best company candidate or None
        """
        
        # Check for FOP/IP cases first - treat as person, not company
        if re.search(r"\b(фоп|ип|fop|ip)\b", text, re.IGNORECASE):
            return self.fop_processor.extract_person_from_fop(text)
        
        # Extract company name
        candidate = self.company_extractor.extract(text, language)
        
        if not candidate and apply_cleaning:
            cleaned_text = self.stop_words_cleaner.clean(text, language)
            if cleaned_text and cleaned_text != text:
                candidate = self.company_extractor.extract(cleaned_text, language)
        
        # Normalize company name if found
        if candidate:
            normalized = self.company_normalizer.normalize(candidate, language)
            return normalized if normalized and len(normalized) > 1 else None
        
        return None
    
    def determine_best_entity(
        self, text: str, language: str, prefer_company: bool = None
    ) -> Tuple[Optional[str], str]:
        """
        Determine the best entity (person or company) from text
        
        Args:
            text: Input text
            language: Detected language
            prefer_company: Whether to prefer company over person when both exist
            
        Returns:
            Tuple of (best_entity, entity_type)
        """
        
        # Extract both candidates
        name_candidate = self.extract_best_name_candidate(text, language)
        company_candidate = self.extract_best_company_candidate(text, language)
        
        # If only one type found, return it
        if name_candidate and not company_candidate:
            return name_candidate, "person"
        
        if company_candidate and not name_candidate:
            return company_candidate, "company"
        
        # If both found, apply preference logic
        if name_candidate and company_candidate:
            if prefer_company is None:
                prefer_company = SERVICE_CONFIG.prefer_company_when_both
            
            if prefer_company:
                self.logger.info(f"Both found, preferring company: '{company_candidate}' over '{name_candidate}'")
                return company_candidate, "company"
            else:
                self.logger.info(f"Both found, preferring person: '{name_candidate}' over '{company_candidate}'")
                return name_candidate, "person"
        
        # Neither found
        return None, "unknown"
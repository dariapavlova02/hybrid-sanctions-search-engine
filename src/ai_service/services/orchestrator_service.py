"""
Orchestrator for coordinating all AI system services
"""

# Standard library imports
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
import os

# Local imports
from ..config import PERFORMANCE_CONFIG, SERVICE_CONFIG
from ..exceptions import (
    CacheError,
    EmbeddingError,
    LanguageDetectionError,
    NormalizationError,
    ProcessingError,
    ServiceInitializationError,
    VariantGenerationError,
)
from ..utils import get_logger
from ..utils.input_validation import ValidationResult, input_validator
from .cache_service import CacheService
from .embedding_service import EmbeddingService
from .language_detection_service import LanguageDetectionService
from .normalization_service import NormalizationService
from .pattern_service import PatternService
from .signal_service import SignalService
from .smart_filter.smart_filter_service import SmartFilterService
from .template_builder import TemplateBuilder
from .unicode_service import UnicodeService


@dataclass
class ProcessingResult:
    """Text processing result"""

    original_text: str
    normalized_text: str
    language: str
    language_confidence: float
    variants: List[str]
    token_variants: Optional[Dict[str, List[str]]] = None
    embeddings: Optional[List] = None
    processing_time: float = 0.0
    success: bool = True
    errors: List[str] = None
    smart_filter: Optional[Dict[str, Any]] = None

    @property
    def error(self) -> str:
        """Get first error message for backward compatibility"""
        if self.errors and len(self.errors) > 0:
            return self.errors[0]
        return ""

    def to_dict(self) -> dict:
        """
        Converts the ProcessingResult to a dictionary for JSON serialization.

        This method creates a dictionary representation of the processing
        result that can be easily serialized to JSON format. Useful for
        API responses, logging, or data storage.

        Returns:
            dict: A dictionary containing all the processing result fields
                  in a serializable format.
        """
        return {
            "original_text": self.original_text,
            "normalized_text": self.normalized_text,
            "language": self.language,
            "language_confidence": self.language_confidence,
            "variants": self.variants,
            "token_variants": self.token_variants,
            "embeddings": self.embeddings,
            "processing_time": self.processing_time,
            "success": self.success,
            "errors": self.errors,
            "smart_filter": self.smart_filter,
        }


class OrchestratorService:
    """Orchestrator for coordinating all services"""

    def __init__(
        self, cache_size: Optional[int] = None, default_ttl: Optional[int] = None
    ):
        """
        Initialize orchestrator service

        Args:
            cache_size: Cache size (uses config default if None)
            default_ttl: Default TTL in seconds (uses config default if None)

        Raises:
            ServiceInitializationError: If service initialization fails
        """
        self.logger = get_logger(__name__)

        try:
            # Use configuration defaults if not provided
            cache_size = cache_size or PERFORMANCE_CONFIG.cache_size
            default_ttl = default_ttl or PERFORMANCE_CONFIG.cache_ttl

            # Initialize all services
            self.unicode_service = UnicodeService()
            self.language_service = LanguageDetectionService()
            self.normalization_service = NormalizationService()
            self.pattern_service = PatternService()
            self.template_builder = TemplateBuilder()
            self.embedding_service = EmbeddingService()
            self.cache_service = CacheService(
                max_size=cache_size, default_ttl=default_ttl
            )
            self.signal_service = SignalService()
            self._stop_words = {"ru": set(), "uk": set(), "en": set()}

            # Initialize smart filter with existing services
            try:
                self.smart_filter = SmartFilterService(
                    language_service=self.language_service,
                    signal_service=self.signal_service,
                )
                self.logger.info("Smart filter service initialized successfully")
            except Exception as e:
                self.logger.warning(
                    f"Smart filter initialization failed, continuing without: {e}"
                )
                self.smart_filter = None
        except Exception as e:
            self.logger.error(f"Failed to initialize orchestrator services: {e}")
            raise ServiceInitializationError(f"Service initialization failed: {str(e)}")

        # Processing statistics
        self.processing_stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "total_time": 0.0,
            "average_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
            "smart_filter_skipped": 0,
            "smart_filter_processed": 0,
        }

        # Aliases for backward compatibility
        self._cache = self.cache_service
        self._stats = self.processing_stats

        self.logger.info("OrchestratorService initialized with all services")

        # Memory logging controls (optional)
        try:
            self._memlog_interval = int(os.getenv("AI_SERVICE_MEMLOG_INTERVAL", "0"))
        except Exception:
            self._memlog_interval = 0
        self._processed_since_memlog = 0

    def _log_memory_snapshot(self) -> None:
        """Log a lightweight memory snapshot and cache stats (optional)."""
        try:
            rss_mb = None
            try:
                import psutil  # type: ignore

                p = psutil.Process()
                rss_mb = p.memory_info().rss / (1024 * 1024)
            except Exception:
                rss_mb = None

            cache_stats = {}
            try:
                cache_stats = self.cache_service.get_stats()
            except Exception:
                cache_stats = {}

            msg = {
                "rss_mb": round(rss_mb, 2) if rss_mb is not None else None,
                "cache_size": cache_stats.get("current_size"),
                "cache_max": cache_stats.get("max_size"),
                "cache_mem_mb": cache_stats.get("memory_usage_mb"),
                "hit_rate": cache_stats.get("hit_rate"),
                "expirations": cache_stats.get("expirations"),
                "evictions": cache_stats.get("evictions"),
            }
            self.logger.info(f"Memory snapshot: {msg}")
        except Exception:
            # Never fail pipeline due to diagnostics
            pass

    def _extract_payment_context_name(self, text: str, language: str) -> Optional[str]:
        """Use PatternService to extract a likely name from payment context."""
        try:
            # Try with detected language first
            patterns = self.pattern_service.generate_patterns(text, language)
            # Prefer payment_context patterns
            ctx = [
                p
                for p in patterns
                if getattr(p, "pattern_type", "") == "payment_context"
            ]
            if not ctx:
                # Fallback: try the other Slavic language to handle mixed texts
                alt_lang = "ru" if language == "uk" else "uk"
                patterns_alt = self.pattern_service.generate_patterns(text, alt_lang)
                ctx = [
                    p
                    for p in patterns_alt
                    if getattr(p, "pattern_type", "") == "payment_context"
                ]
            if not ctx:
                # Last fallback: auto-detect inside PatternService
                patterns_auto = self.pattern_service.generate_patterns(text, "auto")
                ctx = [
                    p
                    for p in patterns_auto
                    if getattr(p, "pattern_type", "") == "payment_context"
                ]
            if not ctx:
                return None
            # Choose the longest extracted pattern as best candidate
            best = max(ctx, key=lambda p: (len(p.pattern or ""), p.confidence))
            return best.pattern
        except Exception:
            return None

    def _extract_initial_surname(self, text: str, language: str) -> Optional[str]:
        """Extract a single-initial + surname pattern (e.g., 'P. Poroshenko' or 'P. Poroshenko')."""
        import re

        m = re.search(
            r"\b([A-Za-zА-ЯІЇЄ])\.\s*([A-Za-zА-ЯІЇЄ][a-zA-Zа-яіїєґ\-]+)\b", text
        )
        if m:
            return f"{m.group(1)}. {m.group(2)}"
        return None

    def _strip_stop_words(self, text: str, language: str) -> str:
        """Remove known stop words around the possible name region."""
        import re

        sw = set(self._stop_words.get(language, []))
        # For Slavic texts, union RU and UK to handle mixed phrasing like "payment from" etc.
        if language in ("ru", "uk"):
            sw = sw.union(self._stop_words.get("ru", set())).union(
                self._stop_words.get("uk", set())
            )
        # Add long legal phrases (not part of normalized names)
        try:
            from ..data.dicts.company_triggers import COMPANY_TRIGGERS

            for lang in ("ru", "uk", "en"):
                for phrase in COMPANY_TRIGGERS.get(lang, {}).get("long_phrases", []):
                    sw.add(phrase.lower())
        except Exception:
            pass
        if not text or not sw:
            return text
        tokens = re.findall(r"[A-Za-zА-Яа-яІіЇїЄєҐґ\'-]+", text)
        # Remove leading/trailing stop words
        while tokens and tokens[0].lower() in sw:
            tokens.pop(0)
        while tokens and tokens[-1].lower() in sw:
            tokens.pop()
        return " ".join(tokens)

    def _maybe_reverse_transliterate(self, text: str, detected_lang: str) -> str:
        """Detect romanized Slavic phrases and convert to Cyrillic before processing.

        Heuristics: looks for common romanized payment/context words and Slavic digraphs.
        Chooses 'uk' if 'vid'/'perekaz'/'platizh' present; 'ru' if 'ot'/'dlya'/'perevod' present.
        """
        import re

        t = text or ""
        low = t.lower()
        # Quick romanized indicators
        roman_signals = [
            "oplata",
            "platezh",
            "perevod",
            "perekaz",
            "vid",
            "ot",
            "dlya",
            "na imya",
            "na imia",
        ]
        if not any(sig in low for sig in roman_signals):
            return t
        # Determine target language
        target = "uk" if any(x in low for x in ["vid", "perekaz", "platizh"]) else "ru"
        # Ordered digraph mapping (target-dependent where needed)
        digraphs_common = [
            ("shch", "щ"),
            ("sch", "щ"),
            ("dzh", "дж"),
            ("dz", "дз"),
            ("cz", "ч"),
            ("sz", "ш"),
            ("rz", "ж"),
            ("yo", "ё"),
            ("jo", "ё"),
            ("zh", "ж"),
            ("kh", "х"),
            ("ch", "ч"),
            ("sh", "ш"),
            ("yu", "ю"),
            ("ju", "ю"),
            ("ya", "я"),
            ("ja", "я"),
            ("ts", "ц"),
        ]
        digraphs_uk = [("ye", "є"), ("yi", "ї"), ("ii", "ії")]
        digraphs_ru = [("ye", "е")]
        single = {
            "a": "а",
            "b": "б",
            "v": "в",
            "g": "г",
            "d": "д",
            "e": "е",
            "z": "з",
            "i": "и",
            "y": "ы",
            "j": "й",
            "k": "к",
            "l": "л",
            "m": "м",
            "n": "н",
            "o": "о",
            "p": "п",
            "r": "р",
            "s": "с",
            "t": "т",
            "u": "у",
            "f": "ф",
            "h": "х",
            "c": "к",
            "q": "к",
            "x": "кс",
            "w": "в",
        }
        # Special words map (contexts)
        specials = {
            "oplata": "оплата",
            "platezh": "платеж",
            "perevod": "перевод",
            "perekaz": "переказ",
            "vid": "від",
            "ot": "от",
            "dlya": "для",
            "na imya": "на имя",
            "na imia": "на імʼя",
        }
        # Phrase-level replacements on the whole string
        for k, v in specials.items():
            t = re.sub(rf"\b{re.escape(k)}\b", v, t, flags=re.IGNORECASE)

        # Work on tokens to preserve casing roughly
        def translit_token(tok: str) -> str:
            s = tok
            # Apply digraphs
            for a, b in digraphs_common + (
                digraphs_uk if target == "uk" else digraphs_ru
            ):
                s = re.sub(a, b, s, flags=re.IGNORECASE)
            # Single letters
            res = ""
            i = 0
            while i < len(s):
                ch = s[i]
                lo = ch.lower()
                if lo in single:
                    cy = single[lo]
                    cy = cy.upper() if ch.isupper() else cy
                    res += cy
                else:
                    res += ch
                i += 1
            return res

        # Split on whitespace, transliterate only ASCII words
        out_tokens = []
        for tok in t.split():
            if re.fullmatch(r"[A-Za-z\-]+", tok):
                lk = tok.lower()
                if lk in specials:
                    out_tokens.append(specials[lk])
                else:
                    out_tokens.append(translit_token(tok))
            else:
                out_tokens.append(tok)
        return " ".join(out_tokens)

    def _extract_company_context_name(self, text: str, language: str) -> Optional[str]:
        """Extract company name from payment/recipient context."""
        try:
            patterns = self.pattern_service.generate_patterns(text, language)
            comps = [
                p
                for p in patterns
                if getattr(p, "pattern_type", "") == "company_context"
            ]

            def _not_just_marker(pat: str) -> bool:
                try:
                    from ..data.dicts.company_triggers import COMPANY_TRIGGERS

                    legal = set(
                        COMPANY_TRIGGERS.get("ru", {}).get("legal_entities", [])
                    ) | set(COMPANY_TRIGGERS.get("uk", {}).get("legal_entities", []))
                    return pat.lower() not in legal
                except Exception:
                    return True if len(pat) > 4 else False

            comps = [p for p in comps if _not_just_marker(p.pattern or "")]
            if not comps:
                # Try alternative language
                alt_lang = "ru" if language == "uk" else "uk"
                comps = [
                    p
                    for p in self.pattern_service.generate_patterns(text, alt_lang)
                    if getattr(p, "pattern_type", "") == "company_context"
                ]
                comps = [p for p in comps if _not_just_marker(p.pattern or "")]
            if not comps:
                # Last fallback
                comps = [
                    p
                    for p in self.pattern_service.generate_patterns(text, "auto")
                    if getattr(p, "pattern_type", "") == "company_context"
                ]
                comps = [p for p in comps if _not_just_marker(p.pattern or "")]
            if not comps:
                return None
            best = max(comps, key=lambda p: (len(p.pattern or ""), p.confidence))
            return best.pattern
        except Exception:
            return None

    def _normalize_company_name(self, text: str, language: str) -> str:
        """Normalize company name: drop doc tails, keep legal entity prefix and core name."""
        import re

        s = text or ""
        # Remove trailing contract/date/number tails
        s = re.split(
            r"\b(по\s+договор[ау]|догов[оі]р[ау]?|контракт[ау]?|№|#|от\s+\d|від\s+\d)",
            s,
            maxsplit=1,
        )[0]
        s = re.sub(r"\s+", " ", s).strip()
        # Remove enclosing quotes
        s = re.sub(r'^["«»\']\s*|\s*["«»\']$', "", s)
        # Drop legal entity markers (abbrev) and long phrases
        try:
            from ..data.dicts.company_triggers import COMPANY_TRIGGERS

            legal = set()
            long_phrases = []
            for lang in ("ru", "uk", "en"):
                data = COMPANY_TRIGGERS.get(lang, {})
                legal.update([x.lower() for x in data.get("legal_entities", [])])
                long_phrases.extend([x.lower() for x in data.get("long_phrases", [])])
            # Optionally keep abbreviations
            if not SERVICE_CONFIG.keep_legal_entity_prefix:
                parts = s.split()
                while parts and parts[0].lower().strip('."«»”') in legal:
                    parts.pop(0)
                s = " ".join(parts)
            # Remove long phrases anywhere at start regardless
            for phrase in long_phrases:
                s = re.sub(rf"^(?:{re.escape(phrase)})\s+", "", s, flags=re.IGNORECASE)
        except Exception:
            pass
        return s.strip()

    async def process_text(
        self,
        text: str,
        generate_variants: bool = True,
        generate_embeddings: bool = False,
        cache_result: bool = True,
        force_reprocess: bool = False,
        smart_filter_result: Optional[Any] = None,
        timeout: Optional[float] = None,
    ) -> ProcessingResult:
        """
        Complete text processing through all services

        Args:
            text: Input text
            generate_variants: Generate variants
            generate_embeddings: Generate embeddings
            cache_result: Cache result
            force_reprocess: Force reprocessing

        Returns:
            ProcessingResult with processing results
        """
        start_time = datetime.now()

        # Handle timeout if specified
        if timeout is not None and timeout <= 0:
            return ProcessingResult(
                original_text=text,
                normalized_text="",
                language="unknown",
                language_confidence=0.0,
                variants=[],
                token_variants={},
                embeddings=None,
                processing_time=0.0,
                success=False,
                errors=[f"Invalid timeout value: {timeout}"],
            )

        try:
            # 0. INPUT VALIDATION AND SANITIZATION
            validation_result = input_validator.validate_and_sanitize(
                text,
                strict_mode=False,  # Allow processing with warnings
                remove_homoglyphs=True,
            )

            # Log validation warnings for audit
            if validation_result.warnings:
                self.logger.warning(
                    f"Input validation warnings for text '{text[:50]}...': {validation_result.warnings}"
                )

            # Use sanitized text for processing
            sanitized_text = validation_result.sanitized_text

            # If text was blocked by validation
            if not validation_result.is_valid:
                self.logger.error(
                    f"Input validation failed for text '{text[:50]}...': {validation_result.blocked_patterns}"
                )
                return ProcessingResult(
                    original_text=text,
                    normalized_text=sanitized_text,
                    language="unknown",
                    language_confidence=0.0,
                    variants=[],
                    token_variants={},
                    processing_time=(datetime.now() - start_time).total_seconds(),
                    success=False,
                    errors=[
                        f"Input validation failed: {', '.join(validation_result.blocked_patterns)}"
                    ],
                )

            # Check cache (using original text for cache key)
            # Important: do not cache when embeddings are requested to avoid retaining large vectors.
            cache_key = self._generate_cache_key(
                text, generate_variants, generate_embeddings
            )

            if not generate_embeddings and not force_reprocess and cache_result:
                cached_result = self.cache_service.get(cache_key)
                if cached_result:
                    self.processing_stats["cache_hits"] += 1
                    self.logger.debug(f"Cache hit for text: {text[:50]}...")
                    return cached_result

            self.processing_stats["cache_misses"] += 1

            # 1. SMART FILTER PRE-PROCESSING (Early filtering)
            if smart_filter_result is None and self.smart_filter is not None:
                try:
                    smart_filter_result = self.smart_filter.should_process_text(
                        sanitized_text
                    )

                    # If smart filter suggests skipping processing (very low quality texts)
                    if not smart_filter_result.should_process:
                        self.processing_stats["smart_filter_skipped"] += 1
                        self.logger.info(
                            f"SmartFilter skipped processing: {smart_filter_result.processing_recommendation}"
                        )

                        return ProcessingResult(
                            original_text=text,
                            normalized_text=sanitized_text,
                            language="unknown",
                            language_confidence=0.0,
                            variants=[],
                            token_variants={},
                            processing_time=(
                                datetime.now() - start_time
                            ).total_seconds(),
                            success=True,
                            errors=[],
                            smart_filter={
                                "should_process": False,
                                "confidence": smart_filter_result.confidence,
                                "reason": smart_filter_result.processing_recommendation,
                                "detected_signals": smart_filter_result.detected_signals,
                                "complexity": smart_filter_result.estimated_complexity,
                            },
                        )

                    self.processing_stats["smart_filter_processed"] += 1
                    self.logger.info(
                        f"SmartFilter analysis: confidence={smart_filter_result.confidence:.3f}, signals={smart_filter_result.detected_signals}"
                    )

                except Exception as e:
                    self.logger.warning(
                        f"SmartFilter analysis failed, continuing without: {e}"
                    )
                    smart_filter_result = None

            # 2. CRITICAL: Language detection BEFORE Unicode normalization!
            # This prevents loss of Cyrillic characters through unidecode
            # Use sanitized text for language detection
            language_result = self.language_service.detect_language(sanitized_text)
            language = language_result["language"]
            language_confidence = language_result["confidence"]

            self.logger.info(
                f"Language detected before normalization: {language} (confidence: {language_confidence:.2f})"
            )

            # 1.1 Handle romanized Slavic texts: e.g., 'Oplata vid Petro Poroshenko'
            text_for_processing = self._maybe_reverse_transliterate(
                sanitized_text, language
            )

            # 2. Unicode normalization AFTER language detection (possibly after reverse transliteration)
            unicode_result = self.unicode_service.normalize_text(
                text_for_processing, aggressive=False
            )
            normalized_text = unicode_result["normalized"]

            # 3. Advanced text normalization with token_variants generation
            try:
                advanced_norm_result = await self.advanced_normalization_service.normalize_advanced(
                    normalized_text,
                    language="auto",  # Let AdvancedNormalizationService detect language
                    enable_morphology=True,
                    enable_transliterations=True,
                    enable_phonetic_variants=True,
                    preserve_names=True,
                    clean_unicode=False,  # Already normalized by unicode_service
                )

                # Defensive coding: check normalization result
                if advanced_norm_result is None:
                    self.logger.error(
                        f"Advanced normalization service returned None for text: {normalized_text[:50]}..."
                    )

                    return ProcessingResult(
                        original_text=text,
                        normalized_text=normalized_text,
                        language=language,
                        language_confidence=language_confidence,
                        variants=[],
                        token_variants={},
                        processing_time=(datetime.now() - start_time).total_seconds(),
                        success=False,
                        errors=["Advanced normalization service returned None"],
                    )

                final_normalized = advanced_norm_result.get("normalized", normalized_text)
                token_variants = advanced_norm_result.get("token_variants", {})
                
                # Convert structured token_variants to simple format for ProcessingResult
                simple_token_variants = {}
                for token, structured_variants in token_variants.items():
                    if isinstance(structured_variants, dict) and "all_variants" in structured_variants:
                        simple_token_variants[token] = structured_variants["all_variants"]
                    else:
                        simple_token_variants[token] = list(structured_variants) if isinstance(structured_variants, (list, set)) else []

                self.logger.info(
                    f"Advanced normalization completed: {len(simple_token_variants)} tokens with variants"
                )

            except Exception as e:
                self.logger.warning(f"Advanced normalization failed, falling back to basic: {e}")
                
                # Fallback to basic normalization
                norm_result = await self.normalization_service.normalize_async(
                    normalized_text,
                    language=language,
                    preserve_names=True,
                    apply_lemmatization=True,
                    apply_stemming=False,
                    remove_stop_words=False,
                )

                if norm_result is None:
                    self.logger.error(
                        f"Both advanced and basic normalization failed for text: {normalized_text[:50]}..."
                    )

                    return ProcessingResult(
                        original_text=text,
                        normalized_text=normalized_text,
                        language=language,
                        language_confidence=language_confidence,
                        variants=[],
                        token_variants={},
                        processing_time=(datetime.now() - start_time).total_seconds(),
                        success=False,
                        errors=["Both normalization services failed"],
                    )

                final_normalized = getattr(norm_result, "normalized", normalized_text)
                simple_token_variants = {}

            # 3.1 SmartFilter-guided normalization strategy
            if smart_filter_result is not None and smart_filter_result.detected_signals:
                detected_signals = smart_filter_result.detected_signals
                self.logger.info(
                    f"SmartFilter detected signals: {detected_signals}, confidence: {smart_filter_result.confidence:.3f}"
                )

                # Prioritize processing based on SmartFilter signals
                if "name" in detected_signals and smart_filter_result.confidence > 0.5:
                    # High confidence name detected - prioritize name extraction
                    self.logger.info(
                        "SmartFilter prioritizing name extraction based on signal analysis"
                    )

                elif (
                    "company" in detected_signals
                    and smart_filter_result.confidence > 0.5
                ):
                    # High confidence company detected - prioritize company extraction
                    self.logger.info(
                        "SmartFilter prioritizing company extraction based on signal analysis"
                    )

                # Use SmartFilter complexity estimate to adjust processing depth
                if smart_filter_result.estimated_complexity in ["high", "very_high"]:
                    self.logger.info(
                        "SmartFilter detected high complexity - enabling enhanced processing"
                    )

            # 3.2 Domain-specific: extract and canonicalize names from payment context
            # Try extracting a name candidate directly
            candidate = self._extract_payment_context_name(
                text_for_processing, language
            )
            # If not found, try again after stripping stop words
            if not candidate:
                stripped = self._strip_stop_words(text_for_processing, language)
                if stripped and stripped != text:
                    candidate = self._extract_payment_context_name(stripped, language)
            # If still not found, try single initial + surname fallbacks (non-payment context)
            if not candidate:
                candidate = self._extract_initial_surname(text_for_processing, language)
                if not candidate and stripped and stripped != text_for_processing:
                    candidate = self._extract_initial_surname(stripped, language)
            if candidate:
                try:
                    # Try canonicalization with detected language
                    canonical_primary = self._canonicalize_name_phrase(
                        candidate, language
                    )
                    # Heuristic force to 'uk' if surname looks Ukrainian
                    import re as __re

                    parts = __re.findall(r"[A-Za-zА-Яа-яІіЇїЄєҐґ\'-]+", candidate)
                    last_tok = parts[-1] if len(parts) > 1 else ""
                    uk_force = False
                    if last_tok:
                        last_low = last_tok.lower()
                        if last_low.endswith(self._uk_surname_suffixes):
                            uk_force = True
                    canonical_uk = (
                        self._canonicalize_name_phrase(candidate, "uk")
                        if uk_force
                        else None
                    )
                    canonical = canonical_uk or canonical_primary
                    if canonical:
                        final_normalized = canonical
                        self.logger.info(
                            f"Canonicalized payment name: '{candidate}' -> '{final_normalized}'"
                        )
                except Exception as e:
                    self.logger.debug(f"Name canonicalization skipped: {e}")

            # 3.2 Companies and FOP/IP cases
            # If text mentions individual entrepreneur (FOP/IP), treat as person: strip marker and canonicalize
            import re as _re

            if _re.search(r"\b(фоп|ип|fop|ip)\b", text_for_processing, _re.IGNORECASE):
                # Take the tail after marker
                m = _re.search(
                    r"\b(?:фоп|ип|fop|ip)\b\s*(.+)$",
                    text_for_processing,
                    _re.IGNORECASE,
                )
                if m:
                    fop_tail = m.group(1).strip()
                    # Keep order Surname Given Patronymic; filter out non-name tokens (e.g., 'rent', dates)
                    tokens = _re.findall(
                        r"[A-Za-zА-Яа-яІіЇїЄєҐґ\'\u02BC\u2019\-]+", fop_tail
                    )
                    name_like = []
                    for t in tokens:
                        if len(t) < 2:
                            continue
                        # Heuristic: first letter uppercase, contains letters/apostrophes
                        if _re.match(
                            r"^[A-ZА-ЯІЇЄ][a-zA-Zа-яіїєґ\'\u02BC\u2019\-]+$", t
                        ):
                            name_like.append(t)
                        # Patronymic endings (ru/uk)
                        elif _re.search(
                            r"(вич|вна|івна|йович|ьович|ич)$", t, _re.IGNORECASE
                        ):
                            name_like.append(t)
                    # Keep up to first three plausible name tokens
                    if name_like:
                        final_normalized = " ".join(name_like[:3])
                        self.logger.info(
                            f"FOP/IP person extracted: '{fop_tail}' -> '{final_normalized}'"
                        )
            else:
                # Try to extract a company name if no FOP/IP
                comp = self._extract_company_context_name(text_for_processing, language)
                if not comp:
                    stripped = self._strip_stop_words(text_for_processing, language)
                    if stripped and stripped != text_for_processing:
                        comp = self._extract_company_context_name(stripped, language)
                if comp:
                    company_norm = self._normalize_company_name(comp, language)
                    if company_norm and len(company_norm) > 1:
                        # SmartFilter routing: if both person and company exist, choose per config
                        if candidate and SERVICE_CONFIG.smart_filter_routing:
                            if SERVICE_CONFIG.prefer_company_when_both:
                                final_normalized = company_norm
                                self.logger.info(
                                    f"SmartFilter routed to COMPANY: '{comp}' -> '{final_normalized}'"
                                )
                            else:
                                self.logger.info(
                                    f"SmartFilter kept PERSON over COMPANY: '{candidate}' vs '{company_norm}'"
                                )
                        else:
                            final_normalized = company_norm
                            self.logger.info(
                                f"Detected company: '{comp}' -> '{final_normalized}'"
                            )

            # 4. Variant generation (optimized logic)
            variants = []
            if generate_variants:
                if len(final_normalized.strip()) > 2:
                    # Get variants for the entire normalized text ONCE
                    variant_result = self.variant_service.generate_variants(
                        text=final_normalized,
                        language=language,
                        max_variants=50,  # Limit total number of variants
                    )
                    if variant_result and "variants" in variant_result:
                        variants = variant_result["variants"]

                    # Remove duplicates and empty strings
                    variants = list(
                        set(v for v in variants if v and len(v.strip()) > 0)
                    )

                # Fallback if no variants
                if not variants:
                    variants = [final_normalized]

            # 6. Generate embeddings (if needed)
            embeddings = None
            if generate_embeddings:
                try:
                    embedding_result = self.embedding_service.get_embeddings(
                        [final_normalized], normalize=True
                    )
                    if embedding_result.get("success"):
                        embeddings = embedding_result["embeddings"]
                except Exception as ee:
                    # Do not fail entire pipeline if embeddings unavailable
                    self.logger.warning(f"Embedding generation skipped: {ee}")
                    embeddings = None

            # Form result
            processing_time = (datetime.now() - start_time).total_seconds()

            result = ProcessingResult(
                original_text=text,
                normalized_text=final_normalized,
                language=language,
                language_confidence=language_confidence,
                variants=variants,
                token_variants=simple_token_variants,
                embeddings=embeddings,
                processing_time=processing_time,
                success=True,
            )

            # Add SmartFilter information to result
            if smart_filter_result is not None:
                result.smart_filter = {
                    "should_process": smart_filter_result.should_process,
                    "confidence": smart_filter_result.confidence,
                    "reason": f"SmartFilter analysis: {smart_filter_result.processing_recommendation}",
                    "detected_signals": smart_filter_result.detected_signals,
                    "complexity": smart_filter_result.estimated_complexity,
                    "signal_details": smart_filter_result.signal_details,
                }
            else:
                result.smart_filter = {
                    "should_process": True,
                    "confidence": 1.0,
                    "reason": "SmartFilter not available",
                    "detected_signals": [],
                    "complexity": "unknown",
                    "signal_details": {},
                }

            # Cache result (skip caching heavy results with embeddings)
            if cache_result and not generate_embeddings:
                self.cache_service.set(cache_key, result, ttl=3600)

            # Update statistics
            self._update_stats(processing_time, True)

            # Optional memory logging
            if self._memlog_interval and self._memlog_interval > 0:
                self._processed_since_memlog += 1
                if self._processed_since_memlog % self._memlog_interval == 0:
                    self._log_memory_snapshot()

            return result

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Error processing text: {e}")

            # Update statistics
            self._update_stats(processing_time, False)

            return ProcessingResult(
                original_text=text,
                normalized_text="",
                language="unknown",
                language_confidence=0.0,
                variants=[],
                token_variants={},
                processing_time=processing_time,
                success=False,
                errors=[str(e)],
            )

    async def process_batch(
        self,
        texts: List[str],
        generate_variants: bool = True,
        generate_embeddings: bool = False,
        max_concurrent: int = 10,
    ) -> List[ProcessingResult]:
        """
        Batch text processing

        Args:
            texts: List of texts
            generate_variants: Generate variants
            generate_embeddings: Generate embeddings
            max_concurrent: Maximum number of concurrent tasks

        Returns:
            List of processing results
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_single(text: str) -> ProcessingResult:
            async with semaphore:
                return await self.process_text(
                    text=text,
                    generate_variants=generate_variants,
                    generate_embeddings=generate_embeddings,
                )

        # Create tasks for all texts
        tasks = [process_single(text) for text in texts]

        # Execute tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process errors
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Error processing text {i}: {result}")
                processed_results.append(
                    ProcessingResult(
                        original_text=texts[i],
                        normalized_text="",
                        language="unknown",
                        language_confidence=0.0,
                        variants=[],
                        token_variants={},
                        processing_time=0.0,
                        success=False,
                        errors=[str(result)],
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    async def search_similar_names(
        self,
        query: str,
        candidates: List[str],
        threshold: float = 0.7,
        top_k: int = 10,
        use_embeddings: bool = True,
    ) -> Dict:
        """
        Search for similar names among candidates

        Args:
            query: Search query
            candidates: List of candidates
            threshold: Similarity threshold
            top_k: Number of best results
            use_embeddings: Use embeddings for search

        Returns:
            Search results
        """
        try:
            if use_embeddings:
                # Use embeddings for search
                search_result = self.embedding_service.find_similar_texts(
                    query=query, candidates=candidates, threshold=threshold, top_k=top_k
                )

                if search_result.get("success"):
                    return {
                        "method": "embeddings",
                        "query": query,
                        "results": search_result["results"],
                        "total_candidates": search_result["total_candidates"],
                        "threshold": threshold,
                    }

            # Fallback to simpler search
            variant_result = self.variant_service.find_best_matches(
                query=query,
                candidates=candidates,
                threshold=threshold,
                max_results=top_k,
            )

            return {
                "method": "variants",
                "query": query,
                "results": variant_result,
                "total_candidates": len(candidates),
                "threshold": threshold,
            }

        except Exception as e:
            self.logger.error(f"Error in name search: {e}")
            return {"method": "error", "query": query, "results": [], "error": str(e)}

    async def analyze_text_complexity(self, text: str) -> Dict:
        """
        Analyze text complexity

        Args:
            text: Input text

        Returns:
            Complexity analysis
        """
        try:
            # Unicode complexity
            unicode_result = self.unicode_service.normalize_text(text, aggressive=False)
            unicode_complexity = {
                "confidence": unicode_result["confidence"],
                "changes": unicode_result["changes"],
                "issues": unicode_result.get("issues", []),
            }

            # Language complexity
            language_result = self.language_service.detect_language(text)
            language_complexity = {
                "detected_language": language_result["language"],
                "confidence": language_result["confidence"],
                "method": language_result.get("method", "unknown"),
            }

            # Name signals
            signal_result = self.signal_service.get_name_signals(text)
            name_complexity = {
                "signal_type": "name_signal",
                "total_score": signal_result["count"],
                "confidence": signal_result["confidence"],
            }

            # Overall complexity score
            complexity_score = self._calculate_complexity_score(
                unicode_complexity, language_complexity, name_complexity
            )

            return {
                "text": text,
                "complexity_score": complexity_score,
                "unicode": unicode_complexity,
                "language": language_complexity,
                "names": name_complexity,
                "recommendations": self._generate_complexity_recommendations(
                    complexity_score
                ),
            }

        except Exception as e:
            self.logger.error(f"Error analyzing text complexity: {e}")
            return {"text": text, "error": str(e), "complexity_score": 0.0}

    def get_processing_stats(self) -> Dict[str, Any]:
        """
        Retrieves the current processing statistics for the service.

        This includes metrics like total requests, success/failure rates,
        average processing time, and detailed cache statistics.

        Returns:
            Dict[str, Any]: A dictionary containing comprehensive statistics
                            about the service's operation.
        """
        stats = self.processing_stats.copy()

        # Add cache statistics
        cache_stats = self.cache_service.get_stats()
        stats["cache"] = cache_stats

        # Add service statistics
        stats["services"] = {
            "unicode": "active",
            "language": "active",
            "normalization": "active",
            "variants": "active",
            "patterns": "active",
            "templates": "active",
            "embeddings": "active",
        }

        return stats

    def clear_cache(self):
        """
        Clears all cached data from the cache service.

        This method removes all stored processing results and resets
        the cache to its initial state. Useful for freeing memory
        or when cache consistency is required.

        Note:
            This operation is irreversible and will affect all cached data.
        """
        self.cache_service.clear()
        self.logger.info("Cache cleared")

    def reset_stats(self):
        """
        Resets all processing statistics to their initial values.

        This method clears all accumulated metrics including total processed
        requests, success/failure counts, timing information, and cache
        performance data. Useful for starting fresh measurements or
        troubleshooting performance issues.

        Note:
            This operation is irreversible and will reset all historical data.
        """
        self.processing_stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "total_time": 0.0,
            "average_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
        }
        self.logger.info("Statistics reset")

    def _generate_cache_key(
        self, text: str, generate_variants: bool, generate_embeddings: bool
    ) -> str:
        """
        Generates a unique cache key for text processing requests.

        Creates a deterministic hash-based key that uniquely identifies
        a processing request based on the input text and processing options.
        This ensures that identical requests with the same parameters
        will use the same cache entry.

        Args:
            text (str): The input text to be processed.
            generate_variants (bool): Whether to generate text variants.
            generate_embeddings (bool): Whether to generate embeddings.

        Returns:
            str: A unique MD5 hash-based cache key prefixed with 'orchestrator_'.
        """
        import hashlib

        key_data = f"{text}_{generate_variants}_{generate_embeddings}"
        return f"orchestrator_{hashlib.md5(key_data.encode()).hexdigest()}"

    def _update_stats(self, processing_time: float, success: bool):
        """
        Updates internal processing statistics with new request data.

        This method maintains running totals and calculates averages for
        processing performance metrics. It updates both request counts
        and timing information to provide real-time service performance
        insights.

        Args:
            processing_time (float): The time taken to process the request in seconds.
            success (bool): Whether the request was processed successfully.
        """
        self.processing_stats["total_processed"] += 1
        self.processing_stats["total_time"] += processing_time

        if success:
            self.processing_stats["successful"] += 1
        else:
            self.processing_stats["failed"] += 1

        # Update average time
        if self.processing_stats["total_processed"] > 0:
            self.processing_stats["average_time"] = (
                self.processing_stats["total_time"]
                / self.processing_stats["total_processed"]
            )

    def _calculate_complexity_score(
        self, unicode_complexity: Dict, language_complexity: Dict, name_complexity: Dict
    ) -> float:
        """
        Calculates an overall complexity score for text processing.

        Combines multiple complexity factors into a single normalized score
        that indicates how challenging a text will be to process. The score
        ranges from 0.0 (simple) to 1.0 (very complex).

        Args:
            unicode_complexity (Dict): Unicode normalization complexity metrics.
            language_complexity (Dict): Language detection complexity metrics.
            name_complexity (Dict): Name signal detection complexity metrics.

        Returns:
            float: A normalized complexity score between 0.0 and 1.0,
                   where higher values indicate more complex processing requirements.
        """
        score = 0.0

        # Unicode complexity (0-1)
        unicode_score = 1.0 - unicode_complexity["confidence"]
        score += unicode_score * 0.3

        # Language complexity (0-1)
        language_score = 1.0 - language_complexity["confidence"]
        score += language_score * 0.3

        # Name complexity (0-1)
        name_score = 1.0 - name_complexity["confidence"]
        score += name_score * 0.4

        return min(score, 1.0)

    def _generate_complexity_recommendations(
        self, complexity_score: float
    ) -> List[str]:
        """
        Generates processing recommendations based on complexity score.

        Provides actionable advice for handling texts of different complexity
        levels. Recommendations help users understand what to expect and
        suggest appropriate processing strategies.

        Args:
            complexity_score (float): The calculated complexity score (0.0 to 1.0).

        Returns:
            List[str]: A list of recommendation strings providing guidance
                       for processing the text based on its complexity level.
        """
        recommendations = []

        if complexity_score < 0.3:
            recommendations.append("Text has low complexity for processing")
        elif complexity_score < 0.6:
            recommendations.append("Text has medium complexity for processing")
            recommendations.append("It is recommended to check Unicode normalization")
        else:
            recommendations.append("Text has high complexity for processing")
            recommendations.append(
                "It is recommended to perform a detailed analysis and manual verification"
            )
            recommendations.append("Possible issues with encoding or language")

        return recommendations

    async def process_text_with_smart_filter(
        self,
        text: str,
        generate_variants: bool = True,
        use_embeddings: bool = True,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Process text with smart filter optimization

        Args:
            text: Text to process
            generate_variants: Whether to generate variants
            use_embeddings: Whether to generate embeddings
            use_cache: Whether to use cache

        Returns:
            Processing result with smart filter information
        """
        start_time = datetime.now()

        try:
            # Use smart filter if available
            if self.smart_filter is not None:
                filter_result = self.smart_filter.should_process_text(text)

                # If smart filter says skip processing
                if not filter_result.should_process:
                    self.processing_stats["smart_filter_skipped"] += 1

                    # Return minimal result without full processing
                    result = ProcessingResult(
                        original_text=text,
                        normalized_text=text,
                        language="en",  # Default language
                        language_confidence=0.0,
                        variants=[],
                        token_variants={},
                        embeddings=None,
                        processing_time=(datetime.now() - start_time).total_seconds(),
                        success=True,
                        errors=[],
                    )

                    # Add smart filter info
                    result.smart_filter = {
                        "should_process": False,
                        "confidence": filter_result.confidence,
                        "reason": f"Smart filter skipped: {filter_result.processing_recommendation}",
                        "detected_signals": filter_result.detected_signals,
                        "complexity": filter_result.estimated_complexity,
                    }

                    return (
                        result.to_dict()
                        if isinstance(result, ProcessingResult)
                        else result
                    )

                self.processing_stats["smart_filter_processed"] += 1
            else:
                # Fallback when smart filter is not available
                filter_result = None
                self.processing_stats["smart_filter_processed"] += 1

            # Proceed with full processing
            result = await self.process_text(
                text=text,
                generate_variants=generate_variants,
                generate_embeddings=use_embeddings,
                cache_result=use_cache,
                smart_filter_result=filter_result,
            )

            # Add smart filter information to result
            if self.smart_filter is not None:
                smart_filter_info = {
                    "should_process": True,
                    "confidence": filter_result.confidence,
                    "reason": f"Smart filter approved: {filter_result.processing_recommendation}",
                    "detected_signals": filter_result.detected_signals,
                    "complexity": filter_result.estimated_complexity,
                }
            else:
                smart_filter_info = {
                    "should_process": True,
                    "confidence": 1.0,
                    "reason": "Smart filter unavailable - processing all texts",
                    "detected_signals": [],
                    "complexity": "unknown",
                }

            if isinstance(result, dict):
                result["smart_filter"] = smart_filter_info
            else:
                # If result is ProcessingResult object
                result.smart_filter = smart_filter_info

            return result

        except Exception as e:
            self.logger.error(f"Error in process_text_with_smart_filter: {e}")
            self.processing_stats["failed"] += 1

            return {
                "original_text": text,
                "normalized_text": text,
                "language": "unknown",
                "language_confidence": 0.0,
                "variants": [],
                "embeddings": None,
                "processing_time": (datetime.now() - start_time).total_seconds(),
                "success": False,
                "errors": [str(e)],
                "smart_filter": {
                    "should_process": False,
                    "confidence": 0.0,
                    "reason": f"Error in processing: {str(e)}",
                    "detected_signals": [],
                    "complexity": "unknown",
                },
            }

    def get_smart_filter_stats(self) -> Dict[str, Any]:
        """
        Get smart filter statistics
        DISABLED: Smart filter is temporarily disabled

        Returns:
            Dictionary with smart filter statistics (disabled status)
        """
        total_processed = self.processing_stats["total_processed"]
        processed = self.processing_stats["smart_filter_processed"]

        return {
            "total_texts_analyzed": total_processed,
            "skipped_by_filter": 0,  # No texts skipped since filter is disabled
            "processed_fully": processed,
            "efficiency_percentage": 0.0,  # No efficiency since filter is disabled
            "status": "disabled",
            "message": "Smart filter is temporarily disabled - all texts are processed",
            "filter_effectiveness": {
                "skipped_ratio": 0.0,
                "processed_ratio": 1.0 if total_processed > 0 else 0.0,
            },
        }

    def update_processing_stats(self, processing_time: float, success: bool = True):
        """Update processing statistics (alias for _update_stats)"""
        self._update_stats(processing_time, success)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics (alias for get_processing_stats)"""
        return self.get_processing_stats()

    def cache_result(self, key: str, result: Any, ttl: int = 3600) -> bool:
        """Cache result (alias for cache_service.set)"""
        return self.cache_service.set(key, result, ttl)

    def get_cached_result(self, key: str) -> Any:
        """Get cached result (alias for cache_service.get)"""
        return self.cache_service.get(key)


    # clear_cache method already defined above

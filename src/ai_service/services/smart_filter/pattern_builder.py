"""
Smart Filter Pattern Builder

Builds compact Aho-Corasick-ready pattern lists for Smart Filter
by leveraging existing detectors and pattern/variant services.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from ..services.language_detection_service import LanguageDetectionService
from ..services.pattern_service import PatternService
from ..services.unicode_service import UnicodeService
from ..services.variant_generation_service import VariantGenerationService
from ..utils import get_logger
from .company_detector import CompanyDetector
from .name_detector import NameDetector


@dataclass
class SmartFilterPatternResult:
    language: str
    confidence: float
    patterns: List[str]
    names: List[str]
    companies: List[str]
    context_names: List[str]
    details: Dict[str, Any]


class SmartFilterPatternBuilder:
    """Aggregates patterns from existing services for Smart Filter."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.pattern_service = PatternService()
        self.variant_service = VariantGenerationService()
        self.language_service = LanguageDetectionService()
        self.unicode_service = UnicodeService()
        self.name_detector = NameDetector()
        self.company_detector = CompanyDetector()

    def build_patterns(
        self,
        text: str,
        language: str = "auto",
        include_variants: bool = True,
        max_per_type: int = 50,
    ) -> SmartFilterPatternResult:
        if not text or not text.strip():
            return SmartFilterPatternResult(
                language="unknown",
                confidence=0.0,
                patterns=[],
                names=[],
                companies=[],
                context_names=[],
                details={"message": "empty text"},
            )

        # Normalize unicode lightly (do not fold Cyrillic)
        uni = self.unicode_service.normalize_text(text, aggressive=False)

        # Language detection (explicit before any case transformations)
        if language == "auto":
            lang_res = self.language_service.detect_language(uni)
            language = lang_res.get("language", "uk")
            lang_conf = lang_res.get("confidence", 0.0)
        else:
            lang_conf = 1.0

        # Name and company signals
        name_signals = self.name_detector.detect_name_signals(uni)
        company_signals = self.company_detector.detect_company_signals(uni)

        names: Set[str] = set(name_signals.get("detected_names", []))
        companies: Set[str] = set(company_signals.get("detected_keywords", []))

        # Patterns from PatternService (name-focused + payment context)
        ps_patterns = self.pattern_service.generate_patterns(uni, language)
        context_names = [
            p.pattern
            for p in ps_patterns
            if getattr(p, "pattern_type", "") == "payment_context"
        ]
        for p in ps_patterns:
            if getattr(p, "pattern_type", "") in (
                "full_name",
                "surname_only",
                "name_only",
            ):
                names.add(p.pattern)

        # Build variant patterns for detected names (controlled size)
        patterns: Set[str] = set()
        context: List[str] = []
        context.extend(context_names)

        def add_trimmed(items: List[str], cap: int):
            added = 0
            for it in items:
                if it and len(it.strip()) > 1 and it not in patterns:
                    patterns.add(it.strip())
                    added += 1
                    if added >= cap:
                        break

        # Base names and context names
        add_trimmed(list(names), max_per_type)
        add_trimmed(context_names, max_per_type)

        # Variants per name (transliteration/morphology) with cap
        if include_variants:
            per_name_cap = max(5, max_per_type // 5)
            for n in list(names)[:max_per_type]:
                try:
                    var_res = self.variant_service.generate_variants(
                        n, language=language, max_variants=per_name_cap
                    )
                    add_trimmed(
                        var_res.get("variants", [])[:per_name_cap], per_name_cap
                    )
                except Exception:
                    continue

        # Also include simple company keywords (kept minimal)
        add_trimmed(list(companies), max_per_type)

        # Aggregate confidence from signals
        total_conf = min(
            (name_signals.get("confidence", 0.0) * 0.6)
            + (company_signals.get("confidence", 0.0) * 0.4),
            1.0,
        )

        return SmartFilterPatternResult(
            language=language,
            confidence=max(lang_conf, total_conf),
            patterns=list(patterns),
            names=list(names),
            companies=list(companies),
            context_names=context_names,
            details={
                "name_signals": name_signals,
                "company_signals": company_signals,
                "pattern_service_count": len(ps_patterns),
            },
        )

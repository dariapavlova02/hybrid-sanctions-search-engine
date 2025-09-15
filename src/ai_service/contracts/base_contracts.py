"""
Base contracts and interfaces for the unified AI service architecture.
Implements the layered processing model as specified in CLAUDE.md.
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TYPE_CHECKING

from pydantic import BaseModel

# ============================================================================
# API Response Models
# ============================================================================


class NormalizationResponse(BaseModel):
    """Response model for normalization endpoint"""
    
    normalized_text: str
    tokens: List[str]
    trace: List["TokenTrace"]
    language: str
    success: bool
    errors: List[str] = []
    processing_time: float = 0.0


class ProcessResponse(BaseModel):
    """Response model for process endpoint with full processing pipeline"""
    
    # Core fields
    normalized_text: str
    tokens: List[str]
    trace: List["TokenTrace"]
    language: str
    success: bool
    errors: List[str] = []
    processing_time: float = 0.0
    
    # Additional sections for /process endpoint
    signals: Optional[Dict[str, Any]] = None
    decision: Optional[Dict[str, Any]] = None
    embedding: Optional[List[float]] = None


# ============================================================================
# Core Processing Contracts
# ============================================================================


class TokenTrace(BaseModel):
    """Trace for a single token's normalization process"""

    token: str
    role: str  # initial | patronymic | given | surname | unknown
    rule: str
    morph_lang: Optional[str] = None
    normal_form: Optional[str] = None
    output: str
    fallback: bool = False
    notes: Optional[str] = None


class NormalizationResult(BaseModel):
    """Contract for normalization service output"""

    model_config = {"extra": "allow"}

    # Core output
    normalized: str  # clean names only (person tokens)
    tokens: List[str]
    trace: List["TokenTrace"]
    errors: List[str] = []

    # Metadata
    language: Optional[str] = None
    confidence: Optional[float] = None
    original_length: Optional[int] = None
    normalized_length: Optional[int] = None
    token_count: Optional[int] = None
    processing_time: Optional[float] = None
    success: bool = True

    # Organizations core (NOT in normalized text)
    persons_core: Optional[List[List[str]]] = None  # [[given, surname], ...]
    organizations_core: Optional[List[str]] = None  # ["GAZPROM", ...]
    
    # Persons data with gender and confidence
    persons: List[Dict[str, Any]] = []
    
    # Overall gender information (for single person cases)
    person_gender: Optional[str] = None  # "masc", "femn", or None
    gender_confidence: Optional[float] = None  # 0.0 to 1.0
    
    # Integration test compatibility fields
    original_text: Optional[str] = None
    token_variants: Optional[Dict[str, List[str]]] = None
    total_variants: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return self.model_dump()

    def to_json(self) -> str:
        """Convert to JSON string"""
        return self.model_dump_json()

    def __getitem__(self, k):
        """Enable dict-like access using square brackets"""
        return self.model_dump().get(k)
    
    def get(self, k, default=None):
        """Enable dict-like access with default value"""
        return self.model_dump().get(k, default)
    
    def __contains__(self, k):
        """Enable 'in' operator for dict-like access"""
        return k in self.model_dump()


@dataclass
class SignalsPerson:
    """Person entity from signals extraction"""

    core: List[str]  # from normalization [given, surname, patronymic]
    full_name: str  # reconstructed full name
    dob: Optional[str] = None  # ISO date YYYY-MM-DD
    ids: List[Dict[str, str]] = field(
        default_factory=list
    )  # [{type: "inn", value: "123", valid: true}]
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)  # reasoning steps


@dataclass
class SignalsOrganization:
    """Organization entity from signals extraction"""

    core: str  # core name from normalization
    legal_form: Optional[str] = None  # ООО, ТОВ, LLC, etc.
    full_name: str = ""  # legal_form + core (properly formatted)
    ids: List[Dict[str, str]] = field(default_factory=list)
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)


@dataclass
class SignalsExtras:
    """Additional signals not tied to persons/orgs"""

    dates: List[Dict[str, Any]] = field(
        default_factory=list
    )  # [{value, precision, context}]
    amounts: List[Dict[str, Any]] = field(default_factory=list)  # [{value, currency}]


@dataclass
class SignalsResult:
    """Contract for signals service output"""

    persons: List[SignalsPerson] = field(default_factory=list)
    organizations: List[SignalsOrganization] = field(default_factory=list)
    extras: SignalsExtras = field(default_factory=SignalsExtras)
    confidence: float = 0.0


@dataclass
class ProcessingContext:
    """Context passed through processing pipeline"""

    original_text: str
    sanitized_text: Optional[str] = None
    language: Optional[str] = None
    language_confidence: Optional[float] = None
    should_process: bool = True
    processing_flags: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnifiedProcessingResult:
    """Final unified result matching the layer specification"""

    # Input
    original_text: str

    # Language detection
    language: str
    language_confidence: float

    # Normalization
    normalized_text: str
    tokens: List[str]
    trace: List["TokenTrace"]

    # Signals
    signals: SignalsResult

    # Optional stages
    variants: Optional[List[str]] = None
    embeddings: Optional[List[float]] = None

    # Decision engine result (Layer 9)
    decision: Optional["DecisionResult"] = None

    # Metadata
    processing_time: float = 0.0
    success: bool = True
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "original_text": self.original_text,
            "language": self.language,
            "language_confidence": self.language_confidence,
            "normalized_text": self.normalized_text,
            "tokens": self.tokens,
            "trace": [
                trace.model_dump() if hasattr(trace, "model_dump") else trace.__dict__
                for trace in self.trace
            ],
            "signals": {
                "persons": [
                    {
                        "core": p.core,
                        "full_name": p.full_name,
                        "dob": p.dob,
                        "ids": p.ids,
                        "confidence": p.confidence,
                        "evidence": p.evidence,
                    }
                    for p in self.signals.persons
                ],
                "organizations": [
                    {
                        "core": o.core,
                        "legal_form": o.legal_form,
                        "full_name": o.full_name,
                        "ids": o.ids,
                        "confidence": o.confidence,
                        "evidence": o.evidence,
                    }
                    for o in self.signals.organizations
                ],
                "numbers": {},  # Legacy compatibility
                "dates": self.signals.extras.dates,
                "confidence": self.signals.confidence,
            },
            "variants": self.variants,
            "embeddings": self.embeddings,
            "decision": self.decision.model_dump() if self.decision else None,
            "processing_time": self.processing_time,
            "success": self.success,
            "errors": self.errors,
        }
        return result


# ============================================================================
# Service Interfaces
# ============================================================================


class ProcessingStage(ABC):
    """Base interface for all processing stages"""

    @abstractmethod
    async def process(self, context: ProcessingContext) -> ProcessingContext:
        """Process the context through this stage"""
        pass

    @abstractmethod
    def get_stage_name(self) -> str:
        """Get human-readable stage name"""
        pass


class ValidationServiceInterface(ABC):
    """Input validation and sanitization"""

    @abstractmethod
    async def validate_and_sanitize(self, text: str) -> Dict[str, Any]:
        """Basic validation and safe cleanup"""
        pass


@dataclass
class SmartFilterResult:
    """Smart filter result with detailed classification"""

    should_process: bool
    confidence: float
    classification: str  # must_process | recommend | maybe | skip
    detected_signals: List[str]
    details: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0


class SmartFilterInterface(ABC):
    """
    Layer 2: Smart Filter for pre-processing decision.

    Responsibilities per CLAUDE.md:
    - Quick decision on expensive processing worthiness
    - NameDetector: capitals, initials, patronymic endings, nicknames/diminutives
    - CompanyDetector: legal forms, banking triggers, quoted cores
    - Payment context: payment/oplata/v pol'zu triggers
    - Signal weighting -> confidence + classification
    - Does NOT: normalize/lemmatize text
    """

    @abstractmethod
    async def should_process(self, text: str) -> SmartFilterResult:
        """
        Determine if expensive processing is worthwhile.

        Args:
            text: Sanitized input text (original form)

        Returns:
            SmartFilterResult with classification and confidence
        """
        pass


class LanguageDetectionInterface(ABC):
    """Language detection service"""

    @abstractmethod
    async def detect_language(self, text: str) -> Dict[str, Any]:
        """Detect primary language with confidence"""
        pass


class UnicodeServiceInterface(ABC):
    """Unicode normalization service"""

    @abstractmethod
    async def normalize_unicode(self, text: str) -> str:
        """Canonical unicode normalization"""
        pass


class NormalizationServiceInterface(ABC):
    """Core name normalization service"""

    @abstractmethod
    async def normalize_async(
        self,
        text: str,
        *,
        language: Optional[str] = None,
        remove_stop_words: bool = True,
        preserve_names: bool = True,
        enable_advanced_features: bool = True,
    ) -> NormalizationResult:
        """Normalize names with full traceability"""
        pass


class SignalsServiceInterface(ABC):
    """Signals extraction and enrichment service"""

    @abstractmethod
    async def extract_signals(
        self, original_text: str, normalization_result: NormalizationResult
    ) -> SignalsResult:
        """Extract structured signals from text + normalization trace"""
        pass


class VariantsServiceInterface(ABC):
    """Variant generation service"""

    @abstractmethod
    async def generate_variants(self, normalized_text: str, language: str) -> List[str]:
        """Generate morphological and typographic variants"""
        pass


class EmbeddingsServiceInterface(ABC):
    """Embeddings generation service"""

    @abstractmethod
    async def generate_embeddings(self, text: str) -> List[float]:
        """Generate semantic embeddings"""
        pass

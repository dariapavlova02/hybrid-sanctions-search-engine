"""
Tracing utilities for normalization pipeline
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class TokenTrace(BaseModel):
    """Trace for a single token's normalization"""

    token: str
    role: str
    rule: str
    morph_lang: Optional[str] = None
    normal_form: Optional[str] = None
    output: str
    fallback: bool = False
    notes: Optional[str] = None


class NormalizationResult(BaseModel):
    """Result of text normalization with full traceability"""

    model_config = {"extra": "allow"}

    normalized: str
    tokens: List[str]
    trace: List[TokenTrace]
    errors: List[str] = []

    # Required metadata fields
    language: Optional[str] = None
    confidence: Optional[float] = None
    original_length: Optional[int] = None
    normalized_length: Optional[int] = None
    token_count: Optional[int] = None
    processing_time: Optional[float] = None
    success: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return self.model_dump()

    def to_json(self) -> str:
        """Convert to JSON string"""
        return self.model_dump_json()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NormalizationResult":
        """Create from dictionary"""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "NormalizationResult":
        """Create from JSON string"""
        return cls.model_validate_json(json_str)


class TraceCollector:
    """Collects and manages normalization traces"""

    def __init__(self):
        self.traces: List[TokenTrace] = []
        self.errors: List[str] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def start_trace(self) -> None:
        """Start timing the normalization process"""
        self.start_time = datetime.now()

    def end_trace(self) -> None:
        """End timing the normalization process"""
        self.end_time = datetime.now()

    def add_token_trace(
        self,
        token: str,
        role: str,
        rule: str,
        output: str,
        morph_lang: Optional[str] = None,
        normal_form: Optional[str] = None,
        fallback: bool = False,
        notes: Optional[str] = None,
    ) -> None:
        """Add a token trace to the collection"""
        trace = TokenTrace(
            token=token,
            role=role,
            rule=rule,
            morph_lang=morph_lang,
            normal_form=normal_form,
            output=output,
            fallback=fallback,
            notes=notes,
        )
        self.traces.append(trace)

    def add_error(self, error: str) -> None:
        """Add an error to the collection"""
        self.errors.append(error)

    def get_processing_time(self) -> Optional[float]:
        """Get processing time in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def create_result(
        self,
        normalized: str,
        tokens: List[str],
        language: Optional[str] = None,
        confidence: Optional[float] = None,
        original_length: Optional[int] = None,
    ) -> NormalizationResult:
        """Create a NormalizationResult from collected traces"""
        return NormalizationResult(
            normalized=normalized,
            tokens=tokens,
            trace=self.traces.copy(),
            errors=self.errors.copy(),
            language=language,
            confidence=confidence,
            original_length=original_length or len(" ".join(tokens)) if tokens else 0,
            normalized_length=len(normalized),
            token_count=len(tokens),
            processing_time=self.get_processing_time(),
            success=len(self.errors) == 0,
        )

    def reset(self) -> None:
        """Reset the collector for reuse"""
        self.traces.clear()
        self.errors.clear()
        self.start_time = None
        self.end_time = None

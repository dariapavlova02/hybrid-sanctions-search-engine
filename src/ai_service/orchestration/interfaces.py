"""
Clean interfaces for orchestration system following SOLID principles.
Interface Segregation: Small, focused interfaces for specific responsibilities.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class ProcessingStage(str, Enum):
    """Processing pipeline stages"""

    VALIDATION = "validation"
    UNICODE_NORMALIZATION = "unicode_normalization"
    LANGUAGE_DETECTION = "language_detection"
    TEXT_NORMALIZATION = "text_normalization"
    VARIANT_GENERATION = "variant_generation"
    EMBEDDING_GENERATION = "embedding_generation"
    CACHING = "caching"
    SMART_FILTERING = "smart_filtering"


@dataclass
class ProcessingContext:
    """Processing context passed between stages"""

    original_text: str
    current_text: str
    language: Optional[str] = None
    language_confidence: float = 0.0
    variants: List[str] = None
    embeddings: Optional[List[float]] = None
    metadata: Dict[str, Any] = None
    stage_results: Dict[ProcessingStage, Any] = None

    def __post_init__(self):
        if self.variants is None:
            self.variants = []
        if self.metadata is None:
            self.metadata = {}
        if self.stage_results is None:
            self.stage_results = {}


@dataclass
class ProcessingResult:
    """Final processing result"""

    success: bool
    context: ProcessingContext
    processing_time_ms: float
    errors: List[str] = None
    performance_metrics: Dict[str, float] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.performance_metrics is None:
            self.performance_metrics = {}

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "success": self.success,
            "original_text": self.context.original_text,
            "normalized_text": self.context.current_text,
            "language": self.context.language,
            "language_confidence": self.context.language_confidence,
            "variants": self.context.variants,
            "embeddings": self.context.embeddings,
            "processing_time_ms": self.processing_time_ms,
            "errors": self.errors,
            "performance_metrics": self.performance_metrics,
            "metadata": self.context.metadata,
        }


class ProcessingStageInterface(ABC):
    """
    Interface for processing stages.
    Single Responsibility: Each stage handles one specific processing task.
    """

    @abstractmethod
    async def process(self, context: ProcessingContext) -> ProcessingContext:
        """Process the context and return updated context"""
        pass

    @abstractmethod
    def get_stage_name(self) -> ProcessingStage:
        """Get stage identifier"""
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if stage is enabled"""
        pass


class PipelineInterface(ABC):
    """
    Interface for processing pipeline.
    Open/Closed: New stages can be added without modifying pipeline.
    """

    @abstractmethod
    async def execute(
        self, text: str, config: Optional[Dict] = None
    ) -> ProcessingResult:
        """Execute full processing pipeline"""
        pass

    @abstractmethod
    def add_stage(
        self, stage: ProcessingStageInterface, position: Optional[int] = None
    ) -> None:
        """Add processing stage to pipeline"""
        pass

    @abstractmethod
    def remove_stage(self, stage_name: ProcessingStage) -> bool:
        """Remove processing stage from pipeline"""
        pass

    @abstractmethod
    def get_stages(self) -> List[ProcessingStageInterface]:
        """Get all pipeline stages"""
        pass


class CacheInterface(ABC):
    """Interface for caching functionality"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value"""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache"""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        pass


class MetricsInterface(ABC):
    """Interface for performance metrics"""

    @abstractmethod
    def record_processing_time(self, stage: ProcessingStage, time_ms: float) -> None:
        """Record processing time for stage"""
        pass

    @abstractmethod
    def increment_counter(self, metric_name: str, value: int = 1) -> None:
        """Increment counter metric"""
        pass

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics"""
        pass

    @abstractmethod
    def reset_metrics(self) -> None:
        """Reset all metrics"""
        pass


class ConfigurationInterface(ABC):
    """Interface for configuration management"""

    @abstractmethod
    def get_stage_config(self, stage: ProcessingStage) -> Dict[str, Any]:
        """Get configuration for specific stage"""
        pass

    @abstractmethod
    def get_pipeline_config(self) -> Dict[str, Any]:
        """Get pipeline configuration"""
        pass

    @abstractmethod
    def is_stage_enabled(self, stage: ProcessingStage) -> bool:
        """Check if stage is enabled"""
        pass


class ErrorHandlerInterface(ABC):
    """Interface for error handling"""

    @abstractmethod
    async def handle_stage_error(
        self, stage: ProcessingStage, error: Exception, context: ProcessingContext
    ) -> ProcessingContext:
        """Handle error in processing stage"""
        pass

    @abstractmethod
    def should_continue_on_error(
        self, stage: ProcessingStage, error: Exception
    ) -> bool:
        """Determine if processing should continue after error"""
        pass

    @abstractmethod
    def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics"""
        pass

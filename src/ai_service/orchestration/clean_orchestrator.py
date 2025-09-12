"""
Clean Orchestrator Service implementing SOLID principles.
Replaces the monolithic orchestrator_service.py with proper separation of concerns.
"""

import asyncio
from typing import Any, Dict, List, Optional

# Import interfaces
try:
    from .config_manager import CentralizedConfigManager
    from .error_handler import AdvancedErrorHandler
    from .interfaces import (
        CacheInterface,
        ConfigurationInterface,
        ErrorHandlerInterface,
        MetricsInterface,
        PipelineInterface,
        ProcessingResult,
    )
    from .metrics import PerformanceMetrics
    from .pipeline import AsyncBatchPipeline, ProcessingPipeline

    # Import processing stages
    from .stages import (
        EmbeddingGenerationStage,
        LanguageDetectionStage,
        NormalizationServiceStage,
        SmartFilterStage,
        UnicodeNormalizationStage,
        ValidationStage,
        VariantGenerationStage,
    )
except ImportError:
    # Fallback for when loaded via importlib
    import sys
    from pathlib import Path

    orchestration_path = Path(__file__).parent
    sys.path.insert(0, str(orchestration_path))

    from interfaces import (
        PipelineInterface,
        ProcessingResult,
        CacheInterface,
        MetricsInterface,
        ErrorHandlerInterface,
        ConfigurationInterface,
    )
    from pipeline import ProcessingPipeline, AsyncBatchPipeline
    from config_manager import CentralizedConfigManager
    from error_handler import AdvancedErrorHandler
    from metrics import PerformanceMetrics

    # Import processing stages
    from stages import (
        ValidationStage,
        UnicodeNormalizationStage,
        LanguageDetectionStage,
        NormalizationServiceStage,
        VariantGenerationStage,
        EmbeddingGenerationStage,
        SmartFilterStage,
    )

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from ..config.settings import ServiceConfig
from ..exceptions import ValidationError


class ValidatedService:
    """Base class for validated services"""
    
    def __init__(self, config: Optional[ServiceConfig] = None, **kwargs):
        """Initialize validated service"""
        self.config = config
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def validate_input(self, data: Any) -> None:
        """Validate input data - to be overridden by subclasses"""
        pass


class CacheService(CacheInterface):
    """Simple in-memory cache implementation"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.cache: Dict[str, Any] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.stats = {"hits": 0, "misses": 0}

    async def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            self.stats["hits"] += 1
            return self.cache[key]
        self.stats["misses"] += 1
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        if len(self.cache) >= self.max_size:
            # Simple LRU: remove first item
            first_key = next(iter(self.cache))
            del self.cache[first_key]

        self.cache[key] = value

    async def clear(self) -> None:
        self.cache.clear()

    def get_stats(self) -> Dict[str, int]:
        return self.stats.copy()


class CleanOrchestratorService(ValidatedService):
    """
    Clean orchestrator service implementing SOLID principles.

    Single Responsibility: Coordinates text processing pipeline
    Open/Closed: New stages can be added without modifying orchestrator
    Liskov Substitution: Can be used wherever ValidatedService is expected
    Interface Segregation: Uses focused interfaces for each component
    Dependency Inversion: Depends on abstractions, not concrete implementations
    """

    def __init__(
        self,
        config: ServiceConfig,
        config_file: Optional[str] = None,
        cache: Optional[CacheInterface] = None,
        metrics: Optional[MetricsInterface] = None,
        error_handler: Optional[ErrorHandlerInterface] = None,
        config_manager: Optional[ConfigurationInterface] = None,
    ):
        super().__init__(config)

        # Initialize logger
        from ..utils.logging_config import get_logger
        self.logger = get_logger(__name__)

        # Initialize components with dependency injection
        self.config_manager = config_manager or CentralizedConfigManager(config_file)
        self.cache = cache or CacheService()
        self.metrics = metrics or PerformanceMetrics()
        self.error_handler = error_handler or AdvancedErrorHandler()

        # Initialize processing pipeline
        self.pipeline = ProcessingPipeline(
            cache=self.cache, metrics=self.metrics, error_handler=self.error_handler
        )

        # Initialize batch processor
        pipeline_config = self.config_manager.get_pipeline_config()
        max_concurrent = pipeline_config.get("max_concurrent_stages", 10)
        self.batch_pipeline = AsyncBatchPipeline(self.pipeline, max_concurrent)

        # Setup processing stages
        self._setup_pipeline_stages()

        self.logger.info("Clean orchestrator service initialized")

    def _setup_pipeline_stages(self):
        """Setup processing pipeline stages based on configuration"""
        # Get stage configurations
        validation_config = self.config_manager.get_stage_config("validation")
        language_config = self.config_manager.get_stage_config("language_detection")
        normalization_config = self.config_manager.get_stage_config(
            "text_normalization"
        )
        variant_config = self.config_manager.get_stage_config("variant_generation")
        embedding_config = self.config_manager.get_stage_config("embedding_generation")
        smart_filter_config = self.config_manager.get_stage_config("smart_filtering")

        # Add stages in order (pipeline will only execute enabled stages)
        self.pipeline.add_stage(ValidationStage(validation_config))

        # Unicode normalization (always enabled, lightweight)
        self.pipeline.add_stage(UnicodeNormalizationStage())

        self.pipeline.add_stage(LanguageDetectionStage(config=language_config))
        self.pipeline.add_stage(NormalizationServiceStage(config=normalization_config))

        # Optional expensive stages
        if variant_config.get("enabled", False):
            self.pipeline.add_stage(VariantGenerationStage(config=variant_config))

        if embedding_config.get("enabled", False):
            self.pipeline.add_stage(EmbeddingGenerationStage(config=embedding_config))

        if smart_filter_config.get("enabled", False):
            self.pipeline.add_stage(SmartFilterStage(config=smart_filter_config))

        self.logger.info(
            f"Pipeline configured with {len(self.pipeline.get_stages())} stages"
        )

    def validate_input(self, data: Any) -> None:
        """Validate orchestrator input"""
        if not data:
            raise ValidationError("Input data cannot be empty")

        if isinstance(data, dict):
            if "text" not in data:
                raise ValidationError("Text field is required")

            text = data["text"]
            if not isinstance(text, str):
                raise ValidationError("Text must be a string")

            if not text.strip():
                raise ValidationError("Text cannot be empty")

        elif isinstance(data, str):
            if not data.strip():
                raise ValidationError("Text cannot be empty")

        else:
            raise ValidationError(
                "Input must be string or dictionary with 'text' field"
            )

    async def process(self, data: Any) -> ProcessingResult:
        """Process single text through pipeline"""
        # Extract text and config
        if isinstance(data, dict):
            text = data["text"]
            config = data.get("config", {})
        else:
            text = str(data)
            config = {}

        # Execute pipeline
        result = await self.pipeline.execute(text, config)
        return result

    def process_text(self, text: str) -> ProcessingResult:
        """Process single text synchronously"""
        import asyncio
        return asyncio.run(self.process(text))

    async def process_batch(
        self, texts: List[str], config: Optional[Dict] = None
    ) -> List[ProcessingResult]:
        """Process multiple texts concurrently"""
        return await self.batch_pipeline.process_batch(texts, config)

    async def start(self) -> None:
        """Start orchestrator service"""
        self.status = "healthy"
        self.logger.info("Clean orchestrator service started")

    async def stop(self) -> None:
        """Stop orchestrator service"""
        self.status = "stopping"
        await self.cache.clear()
        self.logger.info("Clean orchestrator service stopped")

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        pipeline_info = self.pipeline.get_pipeline_info()
        cache_stats = self.cache.get_stats()
        metrics = self.metrics.get_health_score()
        error_stats = self.error_handler.get_error_stats()

        return {
            "status": self.status,
            "uptime_seconds": self.get_uptime(),
            "pipeline": pipeline_info,
            "cache": cache_stats,
            "performance": metrics,
            "errors": error_stats,
            "configuration": self.config_manager.get_configuration_info(),
        }

    def get_service_info(self) -> Dict[str, str]:
        """Get service information"""
        return {
            "name": self.config.service_name,
            "version": self.config.version,
            "description": "Clean orchestrator service with SOLID principles",
            "architecture": "microservice",
            "pipeline_stages": str(len(self.pipeline.get_stages())),
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        return self.metrics.get_metrics()

    def get_top_slow_stages(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get slowest processing stages"""
        return self.metrics.get_top_slow_stages(limit)

    def reset_metrics(self) -> None:
        """Reset all performance metrics"""
        self.metrics.reset_metrics()
        self.error_handler.reset_stats()
        self.logger.info("All metrics reset")

    def reload_configuration(self) -> None:
        """Reload configuration and reconfigure pipeline"""
        self.config_manager.reload_configuration()

        # Clear and recreate pipeline stages
        for stage in self.pipeline.get_stages():
            self.pipeline.remove_stage(stage.get_stage_name())

        self._setup_pipeline_stages()
        self.logger.info("Configuration reloaded and pipeline reconfigured")

    def add_custom_stage(self, stage, position: Optional[int] = None) -> None:
        """Add custom processing stage (Open/Closed Principle)"""
        self.pipeline.add_stage(stage, position)
        self.logger.info(f"Added custom stage: {stage.get_stage_name().value}")

    def get_error_analysis(self) -> Dict[str, Any]:
        """Get comprehensive error analysis"""
        error_stats = self.error_handler.get_error_stats()
        error_rules = self.error_handler.get_error_rules_info()

        return {
            "statistics": error_stats,
            "error_rules": error_rules,
            "recommendations": self._generate_error_recommendations(error_stats),
        }

    def _generate_error_recommendations(self, error_stats: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on error patterns"""
        recommendations = []

        total_errors = error_stats.get("total_errors", 0)
        if total_errors == 0:
            return ["System operating normally with no errors"]

        # Check error rates by stage
        errors_by_stage = error_stats.get("errors_by_stage", {})
        for stage, count in errors_by_stage.items():
            error_rate = (count / total_errors) * 100
            if error_rate > 50:
                recommendations.append(
                    f"High error rate in {stage} stage ({error_rate:.1f}%) - review configuration"
                )

        # Check recovery success rates
        recovery_rates = error_stats.get("recovery_success_rate", {})
        for strategy, rate in recovery_rates.items():
            if rate < 50:
                recommendations.append(
                    f"Low recovery success rate for {strategy} ({rate:.1f}%) - review error handling"
                )

        return recommendations


def create_clean_orchestrator(
    config_file: Optional[str] = None,
) -> CleanOrchestratorService:
    """Factory function to create clean orchestrator service"""
    service_config = ServiceConfig(
        service_name="clean-orchestrator", version="2.0.0", host="localhost", port=8002
    )

    return CleanOrchestratorService(config=service_config, config_file=config_file)


# Example usage
if __name__ == "__main__":

    async def main():
        # Create orchestrator
        orchestrator = create_clean_orchestrator()

        # Start service
        await orchestrator.start()

        # Process sample text
        result = await orchestrator.process("Hello, World!")
        print("Processing result:", result.to_dict())

        # Get metrics
        metrics = orchestrator.get_performance_metrics()
        print("Performance metrics:", metrics["summary"])

        # Stop service
        await orchestrator.stop()

    asyncio.run(main())

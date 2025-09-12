"""
Clean processing pipeline implementing SOLID principles.
Single Responsibility: Coordinates stage execution without knowing stage internals.
Open/Closed: Extensible with new stages without modification.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

# Import interfaces
try:
    from .interfaces import (
        CacheInterface,
        ErrorHandlerInterface,
        MetricsInterface,
        PipelineInterface,
        ProcessingContext,
        ProcessingResult,
        ProcessingStage,
        ProcessingStageInterface,
    )
except ImportError:
    # Fallback for when loaded via importlib
    import sys
    from pathlib import Path

    orchestration_path = Path(__file__).parent
    sys.path.insert(0, str(orchestration_path))

    from interfaces import (
        CacheInterface,
        ErrorHandlerInterface,
        MetricsInterface,
        PipelineInterface,
        ProcessingContext,
        ProcessingResult,
        ProcessingStage,
        ProcessingStageInterface,
    )

logger = logging.getLogger(__name__)


class ProcessingPipeline(PipelineInterface):
    """
    Clean processing pipeline with SOLID principles.
    Dependency Inversion: Depends on interfaces, not concrete implementations.
    """

    def __init__(
        self,
        cache: Optional[CacheInterface] = None,
        metrics: Optional[MetricsInterface] = None,
        error_handler: Optional[ErrorHandlerInterface] = None,
    ):
        self.stages: List[ProcessingStageInterface] = []
        self.cache = cache
        self.metrics = metrics
        self.error_handler = error_handler
        self.logger = logging.getLogger(f"{__name__}.ProcessingPipeline")

    async def execute(
        self, text: str, config: Optional[Dict] = None
    ) -> ProcessingResult:
        """
        Execute processing pipeline.
        Single Responsibility: Only coordinates stage execution.
        """
        start_time = time.time()

        # Initialize context
        context = ProcessingContext(
            original_text=text, current_text=text, metadata=config or {}
        )

        errors = []
        stage_performance = {}

        try:
            # Check cache first
            cache_key = self._generate_cache_key(text, config)
            if self.cache:
                cached_result = await self.cache.get(cache_key)
                if cached_result:
                    if self.metrics:
                        self.metrics.increment_counter("cache_hits")
                    return cached_result

                if self.metrics:
                    self.metrics.increment_counter("cache_misses")

            # Execute each stage
            for stage in self.stages:
                if not stage.is_enabled():
                    continue

                stage_start = time.time()

                try:
                    context = await stage.process(context)
                    stage_time = (time.time() - stage_start) * 1000  # Convert to ms
                    stage_performance[stage.get_stage_name().value] = stage_time

                    if self.metrics:
                        self.metrics.record_processing_time(
                            stage.get_stage_name(), stage_time
                        )

                    # Check if smart filter recommended skipping further processing
                    if (
                        stage.get_stage_name().value == "smart_filtering"
                        and context.metadata.get("smart_filter_skip", False)
                    ):
                        self.logger.info(
                            f"Smart filter recommended skipping further processing: {context.metadata.get('skip_reason', 'Unknown reason')}"
                        )
                        # Mark context as processed but with smart filter recommendation
                        context.metadata["processing_skipped_by_smart_filter"] = True
                        break

                except Exception as e:
                    stage_error = (
                        f"Stage {stage.get_stage_name().value} failed: {str(e)}"
                    )
                    errors.append(stage_error)
                    self.logger.error(stage_error, exc_info=True)

                    # Handle error
                    if self.error_handler:
                        try:
                            context = await self.error_handler.handle_stage_error(
                                stage.get_stage_name(), e, context
                            )
                            # Continue processing if error handler allows
                            if not self.error_handler.should_continue_on_error(
                                stage.get_stage_name(), e
                            ):
                                break
                        except Exception as handler_error:
                            self.logger.error(f"Error handler failed: {handler_error}")
                            break
                    else:
                        # No error handler, stop processing
                        break

            # Create result
            total_time = (time.time() - start_time) * 1000
            result = ProcessingResult(
                success=len(errors) == 0,
                context=context,
                processing_time_ms=total_time,
                errors=errors,
                performance_metrics=stage_performance,
            )

            # Cache successful results
            if self.cache and result.success:
                await self.cache.set(cache_key, result)

            if self.metrics:
                self.metrics.record_processing_time(
                    ProcessingStage.VALIDATION, total_time
                )
                if result.success:
                    self.metrics.increment_counter("successful_processing")
                else:
                    self.metrics.increment_counter("failed_processing")

            return result

        except Exception as e:
            # Pipeline-level error
            total_time = (time.time() - start_time) * 1000
            pipeline_error = f"Pipeline execution failed: {str(e)}"
            self.logger.error(pipeline_error, exc_info=True)

            if self.metrics:
                self.metrics.increment_counter("pipeline_errors")

            return ProcessingResult(
                success=False,
                context=context,
                processing_time_ms=total_time,
                errors=[pipeline_error],
                performance_metrics=stage_performance,
            )

    def add_stage(
        self, stage: ProcessingStageInterface, position: Optional[int] = None
    ) -> None:
        """
        Add processing stage.
        Open/Closed: New stages can be added without modifying pipeline.
        """
        if position is None:
            self.stages.append(stage)
        else:
            self.stages.insert(position, stage)

        self.logger.info(f"Added stage: {stage.get_stage_name().value}")

    def remove_stage(self, stage_name: ProcessingStage) -> bool:
        """Remove processing stage"""
        for i, stage in enumerate(self.stages):
            if stage.get_stage_name() == stage_name:
                del self.stages[i]
                self.logger.info(f"Removed stage: {stage_name.value}")
                return True
        return False

    def get_stages(self) -> List[ProcessingStageInterface]:
        """Get all pipeline stages"""
        return self.stages.copy()

    def _generate_cache_key(self, text: str, config: Optional[Dict]) -> str:
        """Generate cache key for text and configuration"""
        import hashlib

        # Create deterministic key from text and config
        key_data = f"{text}"
        if config:
            # Sort config keys for deterministic hashing
            sorted_config = sorted(config.items())
            key_data += f":{str(sorted_config)}"

        return hashlib.md5(key_data.encode()).hexdigest()

    def get_pipeline_info(self) -> Dict[str, Any]:
        """Get pipeline information"""
        return {
            "total_stages": len(self.stages),
            "enabled_stages": [
                stage.get_stage_name().value
                for stage in self.stages
                if stage.is_enabled()
            ],
            "disabled_stages": [
                stage.get_stage_name().value
                for stage in self.stages
                if not stage.is_enabled()
            ],
            "cache_enabled": self.cache is not None,
            "metrics_enabled": self.metrics is not None,
            "error_handler_enabled": self.error_handler is not None,
        }


class AsyncBatchPipeline:
    """
    Batch processing pipeline for multiple texts.
    Single Responsibility: Handles batch operations efficiently.
    """

    def __init__(self, pipeline: ProcessingPipeline, max_concurrent: int = 10):
        self.pipeline = pipeline
        self.max_concurrent = max_concurrent
        self.logger = logging.getLogger(f"{__name__}.AsyncBatchPipeline")

    async def process_batch(
        self, texts: List[str], config: Optional[Dict] = None
    ) -> List[ProcessingResult]:
        """Process multiple texts concurrently"""
        if not texts:
            return []

        self.logger.info(
            f"Processing batch of {len(texts)} texts with max concurrency {self.max_concurrent}"
        )

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def process_single(text: str) -> ProcessingResult:
            async with semaphore:
                return await self.pipeline.execute(text, config)

        # Execute all texts concurrently
        tasks = [process_single(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Batch processing failed for text {i}: {result}")
                # Create error result
                error_result = ProcessingResult(
                    success=False,
                    context=ProcessingContext(
                        original_text=texts[i], current_text=texts[i]
                    ),
                    processing_time_ms=0.0,
                    errors=[f"Batch processing error: {str(result)}"],
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)

        return processed_results

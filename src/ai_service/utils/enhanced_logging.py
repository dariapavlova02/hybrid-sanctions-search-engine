"""
Enhanced logging system with structured logs, trace IDs, and performance monitoring.
Provides comprehensive observability for the AI Service application.
"""

import logging
import json
import time
import uuid
import threading
from typing import Any, Dict, Optional, List, Union
from datetime import datetime
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from enum import Enum
import traceback
import sys
import os

# Try to import optional dependencies
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False


class LogLevel(Enum):
    """Enhanced log levels with custom levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    AUDIT = "AUDIT"      # For audit trail
    SECURITY = "SECURITY"  # For security events
    PERFORMANCE = "PERFORMANCE"  # For performance metrics


class LogCategory(Enum):
    """Log categories for better organization."""
    SEARCH = "search"
    NORMALIZATION = "normalization"
    VALIDATION = "validation"
    API = "api"
    SYSTEM = "system"
    SECURITY = "security"
    PERFORMANCE = "performance"
    ELASTICSEARCH = "elasticsearch"
    MONITORING = "monitoring"


@dataclass
class LogContext:
    """Context information for structured logging."""
    trace_id: str
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    operation: Optional[str] = None
    component: Optional[str] = None
    version: Optional[str] = None
    environment: Optional[str] = None
    additional_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                result[key] = value
        return result


@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: str
    level: str
    message: str
    category: str
    logger_name: str
    context: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    error_details: Optional[Dict[str, Any]] = None
    performance_data: Optional[Dict[str, Any]] = None


class TraceManager:
    """Thread-safe trace ID management."""

    def __init__(self):
        self._local = threading.local()

    def generate_trace_id(self) -> str:
        """Generate new trace ID."""
        return str(uuid.uuid4())

    def set_trace_id(self, trace_id: str) -> None:
        """Set trace ID for current thread."""
        self._local.trace_id = trace_id

    def get_trace_id(self) -> Optional[str]:
        """Get trace ID for current thread."""
        return getattr(self._local, 'trace_id', None)

    def set_context(self, context: LogContext) -> None:
        """Set full context for current thread."""
        self._local.context = context

    def get_context(self) -> Optional[LogContext]:
        """Get context for current thread."""
        return getattr(self._local, 'context', None)

    def clear_context(self) -> None:
        """Clear context for current thread."""
        if hasattr(self._local, 'context'):
            delattr(self._local, 'context')
        if hasattr(self._local, 'trace_id'):
            delattr(self._local, 'trace_id')


class PerformanceTracker:
    """Track performance metrics during logging."""

    def __init__(self):
        self._start_times: Dict[str, float] = {}

    def start_operation(self, operation_id: str) -> None:
        """Start tracking operation performance."""
        self._start_times[operation_id] = time.time()

    def end_operation(self, operation_id: str) -> Optional[float]:
        """End tracking operation and return duration."""
        start_time = self._start_times.pop(operation_id, None)
        if start_time:
            return time.time() - start_time
        return None

    @contextmanager
    def track_operation(self, operation_id: str):
        """Context manager for tracking operation performance."""
        self.start_operation(operation_id)
        try:
            yield
        finally:
            duration = self.end_operation(operation_id)
            if duration:
                # Could emit metrics here
                pass

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system performance metrics."""
        metrics = {
            "timestamp": time.time(),
        }

        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process()
                metrics.update({
                    "memory_rss_mb": process.memory_info().rss / 1024 / 1024,
                    "memory_vms_mb": process.memory_info().vms / 1024 / 1024,
                    "cpu_percent": process.cpu_percent(),
                    "num_threads": process.num_threads(),
                    "open_files": len(process.open_files()),
                    "connections": len(process.connections()),
                })

                # System-wide metrics
                system_memory = psutil.virtual_memory()
                metrics.update({
                    "system_memory_percent": system_memory.percent,
                    "system_cpu_percent": psutil.cpu_percent(),
                    "system_load_avg": os.getloadavg() if hasattr(os, 'getloadavg') else None,
                })
            except Exception as e:
                metrics["psutil_error"] = str(e)

        return metrics


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for logs."""

    def __init__(self, include_system_metrics: bool = False):
        super().__init__()
        self.include_system_metrics = include_system_metrics
        self.performance_tracker = PerformanceTracker()

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Get context from trace manager
        trace_manager = get_trace_manager()
        context = trace_manager.get_context()

        # Build log entry
        log_entry = LogEntry(
            timestamp=datetime.fromtimestamp(record.created).isoformat(),
            level=record.levelname,
            message=record.getMessage(),
            category=getattr(record, 'category', LogCategory.SYSTEM.value),
            logger_name=record.name,
        )

        # Add context information
        if context:
            log_entry.context = context.to_dict()
        elif trace_manager.get_trace_id():
            log_entry.context = {"trace_id": trace_manager.get_trace_id()}

        # Add custom fields from record
        custom_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'stack_info', 'exc_info',
                          'exc_text', 'category']:
                custom_fields[key] = value

        if custom_fields:
            log_entry.context.update(custom_fields)

        # Add error details if exception occurred
        if record.exc_info:
            log_entry.error_details = {
                "exception_type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "exception_message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "stack_trace": traceback.format_exception(*record.exc_info),
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName
            }

        # Add performance metrics if requested
        if self.include_system_metrics:
            log_entry.performance_data = self.performance_tracker.get_system_metrics()

        # Add any metrics from the record
        if hasattr(record, 'metrics'):
            log_entry.metrics = record.metrics

        # Convert to JSON
        try:
            return json.dumps(asdict(log_entry), ensure_ascii=False, separators=(',', ':'))
        except (TypeError, ValueError) as e:
            # Fallback to simple format if JSON serialization fails
            fallback_entry = {
                "timestamp": log_entry.timestamp,
                "level": log_entry.level,
                "message": log_entry.message,
                "logger": log_entry.logger_name,
                "json_error": str(e)
            }
            return json.dumps(fallback_entry)


class EnhancedLogger:
    """Enhanced logger with structured logging and tracing."""

    def __init__(self, name: str, category: LogCategory = LogCategory.SYSTEM):
        self.name = name
        self.category = category
        self.logger = logging.getLogger(name)
        self.trace_manager = get_trace_manager()
        self.performance_tracker = PerformanceTracker()

    def _log_with_context(
        self,
        level: LogLevel,
        message: str,
        *,
        context: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
        extra_fields: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log message with enhanced context."""
        # Determine logging level
        log_level = getattr(logging, level.value)

        # Prepare extra fields
        extra = {
            'category': self.category.value,
        }

        if context:
            extra.update(context)

        if metrics:
            extra['metrics'] = metrics

        if extra_fields:
            extra.update(extra_fields)

        # Log with or without exception
        if error:
            self.logger.log(log_level, message, exc_info=error, extra=extra)
        else:
            self.logger.log(log_level, message, extra=extra)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._log_with_context(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._log_with_context(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._log_with_context(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self._log_with_context(LogLevel.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self._log_with_context(LogLevel.CRITICAL, message, **kwargs)

    def audit(self, message: str, **kwargs) -> None:
        """Log audit message."""
        self._log_with_context(LogLevel.AUDIT, message, **kwargs)

    def security(self, message: str, **kwargs) -> None:
        """Log security message."""
        self._log_with_context(LogLevel.SECURITY, message, **kwargs)

    def performance(self, message: str, **kwargs) -> None:
        """Log performance message."""
        # Include system metrics for performance logs
        if 'metrics' not in kwargs:
            kwargs['metrics'] = self.performance_tracker.get_system_metrics()
        self._log_with_context(LogLevel.PERFORMANCE, message, **kwargs)

    def log_operation_start(self, operation: str, **kwargs) -> str:
        """Log operation start and return operation ID for tracking."""
        operation_id = str(uuid.uuid4())
        self.performance_tracker.start_operation(operation_id)

        self.info(
            f"Operation started: {operation}",
            context={
                "operation": operation,
                "operation_id": operation_id,
                "operation_phase": "start"
            },
            **kwargs
        )

        return operation_id

    def log_operation_end(
        self,
        operation_id: str,
        operation: str,
        success: bool = True,
        **kwargs
    ) -> None:
        """Log operation completion."""
        duration = self.performance_tracker.end_operation(operation_id)

        self.info(
            f"Operation {'completed' if success else 'failed'}: {operation}",
            context={
                "operation": operation,
                "operation_id": operation_id,
                "operation_phase": "end",
                "success": success,
                "duration_ms": duration * 1000 if duration else None
            },
            metrics={
                "operation_duration_ms": duration * 1000 if duration else None,
                "operation_success": success
            },
            **kwargs
        )

    def log_api_request(
        self,
        method: str,
        path: str,
        status_code: int,
        response_time_ms: float,
        user_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log API request with standard fields."""
        success = 200 <= status_code < 400

        self.info(
            f"API Request: {method} {path} -> {status_code}",
            context={
                "http_method": method,
                "http_path": path,
                "http_status_code": status_code,
                "user_id": user_id,
                "api_request": True
            },
            metrics={
                "response_time_ms": response_time_ms,
                "api_success": success
            },
            **kwargs
        )

    def log_search_operation(
        self,
        query: str,
        strategy: str,
        result_count: int,
        latency_ms: float,
        success: bool = True,
        **kwargs
    ) -> None:
        """Log search operation with standard fields."""
        self.info(
            f"Search operation: {strategy} query",
            context={
                "search_query_length": len(query),
                "search_strategy": strategy,
                "search_result_count": result_count,
                "search_success": success
            },
            metrics={
                "search_latency_ms": latency_ms,
                "search_results": result_count
            },
            **kwargs
        )

    @contextmanager
    def trace_operation(self, operation: str, **context_fields):
        """Context manager for tracing operations."""
        operation_id = self.log_operation_start(operation, **context_fields)

        try:
            yield operation_id
            self.log_operation_end(operation_id, operation, success=True)
        except Exception as e:
            self.log_operation_end(
                operation_id,
                operation,
                success=False,
                error=e,
                extra_fields={"error_type": type(e).__name__}
            )
            raise

    def with_trace_id(self, trace_id: Optional[str] = None) -> 'EnhancedLogger':
        """Create logger copy with specific trace ID."""
        if trace_id is None:
            trace_id = self.trace_manager.generate_trace_id()

        # Create context with trace ID
        context = LogContext(trace_id=trace_id)
        self.trace_manager.set_context(context)

        return self


# Global trace manager
_trace_manager: Optional[TraceManager] = None


def get_trace_manager() -> TraceManager:
    """Get global trace manager."""
    global _trace_manager
    if _trace_manager is None:
        _trace_manager = TraceManager()
    return _trace_manager


def create_enhanced_logger(
    name: str,
    category: LogCategory = LogCategory.SYSTEM,
    level: LogLevel = LogLevel.INFO,
    structured: bool = True,
    include_system_metrics: bool = False
) -> EnhancedLogger:
    """Create enhanced logger with structured formatting."""
    logger = EnhancedLogger(name, category)

    # Configure logging level
    logger.logger.setLevel(getattr(logging, level.value))

    # Add structured handler if not already present
    if structured and not any(isinstance(h, logging.StreamHandler) for h in logger.logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter(include_system_metrics=include_system_metrics))
        logger.logger.addHandler(handler)

    return logger


@contextmanager
def trace_context(
    trace_id: Optional[str] = None,
    operation: Optional[str] = None,
    component: Optional[str] = None,
    **additional_fields
):
    """Context manager for setting trace context."""
    trace_manager = get_trace_manager()

    if trace_id is None:
        trace_id = trace_manager.generate_trace_id()

    context = LogContext(
        trace_id=trace_id,
        operation=operation,
        component=component,
        additional_fields=additional_fields
    )

    # Set context
    trace_manager.set_context(context)

    try:
        yield trace_id
    finally:
        # Clear context
        trace_manager.clear_context()


def get_logger_for_component(component_name: str, category: LogCategory = LogCategory.SYSTEM) -> EnhancedLogger:
    """Get enhanced logger for specific component."""
    return create_enhanced_logger(
        name=f"ai_service.{component_name}",
        category=category,
        structured=True,
        include_system_metrics=False
    )


# Specialized loggers for common use cases
def get_api_logger() -> EnhancedLogger:
    """Get logger for API operations."""
    return get_logger_for_component("api", LogCategory.API)


def get_search_logger() -> EnhancedLogger:
    """Get logger for search operations."""
    return get_logger_for_component("search", LogCategory.SEARCH)


def get_security_logger() -> EnhancedLogger:
    """Get logger for security events."""
    return get_logger_for_component("security", LogCategory.SECURITY)


def get_performance_logger() -> EnhancedLogger:
    """Get logger for performance monitoring."""
    return create_enhanced_logger(
        name="ai_service.performance",
        category=LogCategory.PERFORMANCE,
        include_system_metrics=True
    )


# Integration with existing logging
def configure_enhanced_logging(
    level: str = "INFO",
    structured: bool = True,
    include_system_metrics: bool = False
) -> None:
    """Configure enhanced logging for entire application."""
    # Set root logger level
    logging.getLogger().setLevel(getattr(logging, level.upper()))

    if structured:
        # Remove existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Add structured handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter(include_system_metrics=include_system_metrics))
        root_logger.addHandler(handler)

        # Configure specific loggers
        for logger_name in ['ai_service', 'uvicorn', 'fastapi']:
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
            logger.addHandler(handler)
            logger.propagate = False


# OpenTelemetry integration (if available)
if OPENTELEMETRY_AVAILABLE:
    def get_current_span_context() -> Optional[Dict[str, str]]:
        """Get current OpenTelemetry span context."""
        try:
            span = trace.get_current_span()
            if span.is_recording():
                span_context = span.get_span_context()
                return {
                    "trace_id": format(span_context.trace_id, "032x"),
                    "span_id": format(span_context.span_id, "016x"),
                }
        except Exception:
            pass
        return None

    def create_logger_with_otel_context(name: str, category: LogCategory = LogCategory.SYSTEM) -> EnhancedLogger:
        """Create logger that automatically includes OpenTelemetry context."""
        logger = create_enhanced_logger(name, category)

        # Override _log_with_context to include OpenTelemetry context
        original_log = logger._log_with_context

        def enhanced_log_with_context(*args, **kwargs):
            # Get OpenTelemetry context
            otel_context = get_current_span_context()
            if otel_context:
                if 'context' not in kwargs:
                    kwargs['context'] = {}
                kwargs['context'].update(otel_context)

            return original_log(*args, **kwargs)

        logger._log_with_context = enhanced_log_with_context
        return logger


# Example usage and testing
def demo_enhanced_logging():
    """Demonstrate enhanced logging capabilities."""
    # Configure logging
    configure_enhanced_logging(level="DEBUG", structured=True)

    # Create loggers
    api_logger = get_api_logger()
    search_logger = get_search_logger()
    perf_logger = get_performance_logger()

    # Basic logging
    with trace_context(operation="demo", component="logging_demo"):
        api_logger.info("API server started", context={"port": 8000, "version": "1.0.0"})

        # Search operation logging
        search_logger.log_search_operation(
            query="John Doe",
            strategy="hybrid",
            result_count=5,
            latency_ms=150.0
        )

        # Performance logging
        perf_logger.performance(
            "System performance check",
            metrics={"custom_metric": 42}
        )

        # Error logging
        try:
            raise ValueError("Demo error")
        except Exception as e:
            api_logger.error("Demo error occurred", error=e)

        # Operation tracing
        with api_logger.trace_operation("demo_operation", user_id="user123"):
            time.sleep(0.1)  # Simulate work


if __name__ == "__main__":
    demo_enhanced_logging()
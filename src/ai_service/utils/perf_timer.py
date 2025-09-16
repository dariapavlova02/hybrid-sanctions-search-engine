"""
Performance timing utilities
"""

import time
from contextlib import contextmanager
from typing import Generator


class PerfTimer:
    """Performance timer class for measuring execution time."""

    def __init__(self):
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()

    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.end_time is None or self.start_time is None:
            return 0.0
        return self.end_time - self.start_time

    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        return self.elapsed * 1000


@contextmanager
def perf_timer(operation_name: str = "operation") -> Generator[None, None, None]:
    """
    Context manager for timing operations
    
    Args:
        operation_name: Name of the operation being timed
        
    Yields:
        None
        
    Example:
        with perf_timer("encode_batch"):
            result = service.encode_batch(texts)
    """
    start_time = time.perf_counter()
    try:
        yield
    finally:
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000
        print(f"⏱️  {operation_name}: {duration_ms:.2f}ms")


def time_function(func):
    """
    Decorator to time function execution
    
    Args:
        func: Function to time
        
    Returns:
        Decorated function that logs execution time
    """
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000
        print(f"⏱️  {func.__name__}: {duration_ms:.2f}ms")
        return result
    return wrapper


def measure_latency(func, *args, **kwargs):
    """
    Measure latency of a function call
    
    Args:
        func: Function to measure
        *args: Function arguments
        **kwargs: Function keyword arguments
        
    Returns:
        Tuple of (result, duration_ms)
    """
    start_time = time.perf_counter()
    result = func(*args, **kwargs)
    end_time = time.perf_counter()
    duration_ms = (end_time - start_time) * 1000
    return result, duration_ms

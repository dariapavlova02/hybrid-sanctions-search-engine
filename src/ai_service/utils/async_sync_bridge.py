"""
Async/Sync bridge utilities to eliminate blocking operations and mixing patterns.
Provides seamless integration between async and sync code without blocking.
"""

import asyncio
import functools
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Any, Callable, Coroutine, Optional, TypeVar, Union
from contextlib import contextmanager

from .logging_config import get_logger

T = TypeVar('T')

logger = get_logger(__name__)


class AsyncSyncBridge:
    """
    Bridge for seamless async/sync integration without blocking the event loop.

    Strategies:
    1. Thread Pool Execution: Run sync code in threads
    2. Event Loop Detection: Automatically choose appropriate execution
    3. Lazy Async Wrappers: Convert sync functions to async on demand
    4. Non-blocking Sync: Use queue-based communication
    """

    def __init__(self, max_workers: int = 8):
        """Initialize async/sync bridge."""
        self.max_workers = max_workers
        self._thread_pool: Optional[ThreadPoolExecutor] = None
        self._thread_pool_lock = threading.Lock()

        # Event loop tracking
        self._event_loops: set = set()
        self._main_thread_id = threading.get_ident()

    @property
    def thread_pool(self) -> ThreadPoolExecutor:
        """Get thread pool, creating if necessary."""
        if self._thread_pool is None:
            with self._thread_pool_lock:
                if self._thread_pool is None:
                    self._thread_pool = ThreadPoolExecutor(
                        max_workers=self.max_workers,
                        thread_name_prefix="async_sync_bridge"
                    )
        return self._thread_pool

    def run_sync_in_thread(self, func: Callable[..., T], *args, **kwargs) -> Coroutine[Any, Any, T]:
        """
        Run synchronous function in thread pool to avoid blocking event loop.

        Args:
            func: Synchronous function to run
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Coroutine that yields the result
        """
        async def _async_wrapper():
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self.thread_pool, functools.partial(func, *args, **kwargs))

        return _async_wrapper()

    def make_async(self, func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
        """
        Convert synchronous function to async function.

        Args:
            func: Synchronous function to convert

        Returns:
            Async version of the function
        """
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await self.run_sync_in_thread(func, *args, **kwargs)

        return async_wrapper

    def run_async_in_sync(self, coro: Coroutine[Any, Any, T], timeout: Optional[float] = None) -> T:
        """
        Run async coroutine from synchronous context safely.

        Args:
            coro: Coroutine to run
            timeout: Optional timeout in seconds

        Returns:
            Result of the coroutine
        """
        try:
            # Try to get current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, use asyncio.create_task
                # But we need to run it in a new thread to avoid blocking
                return self._run_coro_in_new_thread(coro, timeout)
            else:
                # Event loop exists but not running, we can use it
                return loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))
        except RuntimeError:
            # No event loop, create a new one
            return asyncio.run(asyncio.wait_for(coro, timeout=timeout))

    def _run_coro_in_new_thread(self, coro: Coroutine[Any, Any, T], timeout: Optional[float]) -> T:
        """Run coroutine in a new thread with its own event loop."""
        import queue

        result_queue = queue.Queue()
        exception_queue = queue.Queue()

        def run_in_thread():
            try:
                # Create new event loop for this thread
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)

                try:
                    if timeout:
                        result = new_loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))
                    else:
                        result = new_loop.run_until_complete(coro)
                    result_queue.put(result)
                finally:
                    new_loop.close()

            except Exception as e:
                exception_queue.put(e)

        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join(timeout=timeout)

        if not exception_queue.empty():
            raise exception_queue.get()

        if not result_queue.empty():
            return result_queue.get()

        raise TimeoutError(f"Coroutine timed out after {timeout} seconds")

    def adaptive_call(self, func: Union[Callable[..., T], Callable[..., Coroutine[Any, Any, T]]], *args, **kwargs) -> Union[T, Coroutine[Any, Any, T]]:
        """
        Adaptively call function based on current context.

        Args:
            func: Function that may be sync or async
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result or coroutine depending on context
        """
        try:
            # Check if we're in an async context
            loop = asyncio.get_event_loop()
            is_async_context = loop.is_running()
        except RuntimeError:
            is_async_context = False

        # Call the function
        result = func(*args, **kwargs)

        # Handle the result based on context
        if asyncio.iscoroutine(result):
            if is_async_context:
                # We're in async context and got a coroutine - return it
                return result
            else:
                # We're in sync context and got a coroutine - run it
                return self.run_async_in_sync(result)
        else:
            if is_async_context and not asyncio.iscoroutine(result):
                # We're in async context but got sync result - wrap it
                async def _async_result():
                    return result
                return _async_result()
            else:
                # Sync context with sync result - return as-is
                return result

    @contextmanager
    def sync_context(self):
        """Context manager that ensures sync execution."""
        original_loop = None
        try:
            original_loop = asyncio.get_event_loop()
        except RuntimeError:
            pass

        try:
            # Temporarily disable async context
            if original_loop and original_loop.is_running():
                # We're in an async context, but we want sync behavior
                yield SyncContextManager(self)
            else:
                yield SyncContextManager(self)
        finally:
            # Restore original context
            pass

    async def batch_sync_operations(self, operations: list, batch_size: int = 10) -> list:
        """
        Run multiple sync operations in batches to avoid overwhelming thread pool.

        Args:
            operations: List of (func, args, kwargs) tuples
            batch_size: Number of operations to run concurrently

        Returns:
            List of results in same order as input
        """
        results = []

        for i in range(0, len(operations), batch_size):
            batch = operations[i:i + batch_size]
            batch_tasks = []

            for func, args, kwargs in batch:
                task = self.run_sync_in_thread(func, *args, **kwargs)
                batch_tasks.append(task)

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            results.extend(batch_results)

            # Small delay between batches to avoid overwhelming the system
            if i + batch_size < len(operations):
                await asyncio.sleep(0.01)

        return results

    def cleanup(self):
        """Cleanup resources."""
        if self._thread_pool:
            self._thread_pool.shutdown(wait=True)
            self._thread_pool = None


class SyncContextManager:
    """Context manager for sync operations within async context."""

    def __init__(self, bridge: AsyncSyncBridge):
        self.bridge = bridge

    def run(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Run function in sync context."""
        return func(*args, **kwargs)

    def run_async(self, coro: Coroutine[Any, Any, T], timeout: Optional[float] = None) -> T:
        """Run coroutine in sync context."""
        return self.bridge.run_async_in_sync(coro, timeout)


class AsyncDataLoader:
    """
    Async-aware data loader that prevents blocking operations.
    Specifically designed for dictionary and model loading.
    """

    def __init__(self, bridge: Optional[AsyncSyncBridge] = None):
        """Initialize async data loader."""
        self.bridge = bridge or AsyncSyncBridge()
        self._loading_cache: dict = {}
        self._loading_locks: dict = {}
        self._cache_lock = asyncio.Lock()

    async def load_with_fallback(self,
                                loader_func: Callable[..., T],
                                fallback_func: Optional[Callable[..., T]] = None,
                                cache_key: Optional[str] = None,
                                *args, **kwargs) -> T:
        """
        Load data with async safety and fallback.

        Args:
            loader_func: Primary loading function (may be sync or async)
            fallback_func: Fallback function if primary fails
            cache_key: Optional cache key for deduplication
            *args: Arguments for loader functions
            **kwargs: Keyword arguments for loader functions
        """
        # Check cache if key provided
        if cache_key:
            async with self._cache_lock:
                if cache_key in self._loading_cache:
                    return self._loading_cache[cache_key]

                # Check if already loading
                if cache_key in self._loading_locks:
                    # Wait for existing load to complete
                    await self._loading_locks[cache_key]
                    if cache_key in self._loading_cache:
                        return self._loading_cache[cache_key]

                # Create loading lock
                self._loading_locks[cache_key] = asyncio.Event()

        try:
            # Try primary loader
            if asyncio.iscoroutinefunction(loader_func):
                result = await loader_func(*args, **kwargs)
            else:
                result = await self.bridge.run_sync_in_thread(loader_func, *args, **kwargs)

            # Cache result
            if cache_key:
                async with self._cache_lock:
                    self._loading_cache[cache_key] = result

            return result

        except Exception as e:
            logger.warning(f"Primary loader failed: {e}")

            # Try fallback
            if fallback_func:
                try:
                    if asyncio.iscoroutinefunction(fallback_func):
                        result = await fallback_func(*args, **kwargs)
                    else:
                        result = await self.bridge.run_sync_in_thread(fallback_func, *args, **kwargs)

                    # Cache fallback result
                    if cache_key:
                        async with self._cache_lock:
                            self._loading_cache[cache_key] = result

                    return result

                except Exception as fallback_error:
                    logger.error(f"Fallback loader also failed: {fallback_error}")
                    raise fallback_error
            else:
                raise e

        finally:
            # Release loading lock
            if cache_key and cache_key in self._loading_locks:
                async with self._cache_lock:
                    self._loading_locks[cache_key].set()
                    del self._loading_locks[cache_key]


# Global instances
_global_bridge: Optional[AsyncSyncBridge] = None
_global_loader: Optional[AsyncDataLoader] = None


def get_async_sync_bridge() -> AsyncSyncBridge:
    """Get global async/sync bridge instance."""
    global _global_bridge
    if _global_bridge is None:
        _global_bridge = AsyncSyncBridge()
    return _global_bridge


def get_async_data_loader() -> AsyncDataLoader:
    """Get global async data loader instance."""
    global _global_loader
    if _global_loader is None:
        _global_loader = AsyncDataLoader(get_async_sync_bridge())
    return _global_loader


# Decorators for easy usage
def async_safe(func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
    """Decorator to make sync function async-safe."""
    bridge = get_async_sync_bridge()
    return bridge.make_async(func)


def adaptive_async(func: Callable[..., Union[T, Coroutine[Any, Any, T]]]) -> Callable[..., Union[T, Coroutine[Any, Any, T]]]:
    """Decorator for adaptive async/sync behavior."""
    bridge = get_async_sync_bridge()

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return bridge.adaptive_call(func, *args, **kwargs)

    return wrapper


# Utility functions
async def safe_sync_call(func: Callable[..., T], *args, **kwargs) -> T:
    """Safely call sync function from async context."""
    bridge = get_async_sync_bridge()
    return await bridge.run_sync_in_thread(func, *args, **kwargs)


def safe_async_call(coro: Coroutine[Any, Any, T], timeout: Optional[float] = None) -> T:
    """Safely call async function from sync context."""
    bridge = get_async_sync_bridge()
    return bridge.run_async_in_sync(coro, timeout)
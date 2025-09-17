#!/usr/bin/env python3
"""
Утилиты для профилирования производительности.

Этот модуль предоставляет дешёвые счётчики, таймеры и контекстные менеджеры
для профилирования производительности без влияния на основную логику.
"""

import time
import tracemalloc
import functools
from contextlib import contextmanager
from typing import Dict, Any, Optional, Callable, List
from collections import defaultdict, deque
import threading
import statistics


class PerformanceCounter:
    """Дешёвый счётчик производительности."""
    
    def __init__(self, name: str, max_samples: int = 1000):
        self.name = name
        self.max_samples = max_samples
        self.times: deque = deque(maxlen=max_samples)
        self.calls = 0
        self.total_time = 0.0
        self.min_time = float('inf')
        self.max_time = 0.0
        self._lock = threading.Lock()
    
    def add_sample(self, duration: float):
        """Добавить образец времени."""
        with self._lock:
            self.calls += 1
            self.total_time += duration
            self.min_time = min(self.min_time, duration)
            self.max_time = max(self.max_time, duration)
            self.times.append(duration)
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику."""
        with self._lock:
            if not self.times:
                return {
                    'name': self.name,
                    'calls': 0,
                    'total_time': 0.0,
                    'avg_time': 0.0,
                    'min_time': 0.0,
                    'max_time': 0.0,
                    'p50_time': 0.0,
                    'p95_time': 0.0,
                    'p99_time': 0.0
                }
            
            times_list = list(self.times)
            return {
                'name': self.name,
                'calls': self.calls,
                'total_time': self.total_time,
                'avg_time': self.total_time / self.calls,
                'min_time': self.min_time,
                'max_time': self.max_time,
                'p50_time': statistics.median(times_list),
                'p95_time': statistics.quantiles(times_list, n=20)[18] if len(times_list) > 1 else times_list[0],
                'p99_time': statistics.quantiles(times_list, n=100)[98] if len(times_list) > 1 else times_list[0]
            }


class MemoryTracker:
    """Трекер памяти с использованием tracemalloc."""
    
    def __init__(self, name: str):
        self.name = name
        self.snapshots: List[tracemalloc.Snapshot] = []
        self.peak_memory = 0
        self.total_allocations = 0
        self._lock = threading.Lock()
    
    def start_tracking(self):
        """Начать отслеживание памяти."""
        if not tracemalloc.is_tracing():
            tracemalloc.start()
    
    def take_snapshot(self):
        """Сделать снимок памяти."""
        if tracemalloc.is_tracing():
            snapshot = tracemalloc.take_snapshot()
            with self._lock:
                self.snapshots.append(snapshot)
                current_memory = sum(stat.size for stat in snapshot.statistics('lineno'))
                self.peak_memory = max(self.peak_memory, current_memory)
                self.total_allocations += len(snapshot.traces)
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику памяти."""
        with self._lock:
            if not self.snapshots:
                return {
                    'name': self.name,
                    'snapshots': 0,
                    'peak_memory': 0,
                    'total_allocations': 0,
                    'avg_memory': 0.0
                }
            
            total_memory = sum(
                sum(stat.size for stat in snapshot.statistics('lineno'))
                for snapshot in self.snapshots
            )
            
            return {
                'name': self.name,
                'snapshots': len(self.snapshots),
                'peak_memory': self.peak_memory,
                'total_allocations': self.total_allocations,
                'avg_memory': total_memory / len(self.snapshots)
            }


class ProfilingManager:
    """Менеджер профилирования для сбора метрик."""
    
    def __init__(self):
        self.counters: Dict[str, PerformanceCounter] = {}
        self.memory_trackers: Dict[str, MemoryTracker] = {}
        self._lock = threading.Lock()
    
    def get_counter(self, name: str) -> PerformanceCounter:
        """Получить или создать счётчик."""
        with self._lock:
            if name not in self.counters:
                self.counters[name] = PerformanceCounter(name)
            return self.counters[name]
    
    def get_memory_tracker(self, name: str) -> MemoryTracker:
        """Получить или создать трекер памяти."""
        with self._lock:
            if name not in self.memory_trackers:
                self.memory_trackers[name] = MemoryTracker(name)
            return self.memory_trackers[name]
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Получить все статистики."""
        with self._lock:
            return {
                'counters': {name: counter.get_stats() for name, counter in self.counters.items()},
                'memory_trackers': {name: tracker.get_stats() for name, tracker in self.memory_trackers.items()}
            }
    
    def clear_stats(self):
        """Очистить все статистики."""
        with self._lock:
            self.counters.clear()
            self.memory_trackers.clear()


# Глобальный менеджер профилирования
_profiling_manager = ProfilingManager()


@contextmanager
def profile_time(name: str, enable: bool = True):
    """Контекстный менеджер для профилирования времени."""
    if not enable:
        yield
        return
    
    counter = _profiling_manager.get_counter(name)
    start_time = time.perf_counter()
    
    try:
        yield counter
    finally:
        end_time = time.perf_counter()
        counter.add_sample(end_time - start_time)


@contextmanager
def profile_memory(name: str, enable: bool = True):
    """Контекстный менеджер для профилирования памяти."""
    if not enable:
        yield
        return
    
    tracker = _profiling_manager.get_memory_tracker(name)
    tracker.start_tracking()
    
    try:
        yield tracker
    finally:
        tracker.take_snapshot()


def profile_function(name: Optional[str] = None, enable: bool = True):
    """Декоратор для профилирования функций."""
    def decorator(func: Callable) -> Callable:
        if not enable:
            return func
        
        counter_name = name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with profile_time(counter_name, enable):
                return func(*args, **kwargs)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with profile_time(counter_name, enable):
                return await func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
    
    return decorator


def get_profiling_stats() -> Dict[str, Any]:
    """Получить статистики профилирования."""
    return _profiling_manager.get_all_stats()


def clear_profiling_stats():
    """Очистить статистики профилирования."""
    _profiling_manager.clear_stats()


def print_profiling_report():
    """Вывести отчёт профилирования."""
    stats = get_profiling_stats()
    
    print("\n" + "="*80)
    print("ОТЧЁТ ПРОФИЛИРОВАНИЯ ПРОИЗВОДИТЕЛЬНОСТИ")
    print("="*80)
    
    # Счётчики времени
    if stats['counters']:
        print("\nСЧЁТЧИКИ ВРЕМЕНИ:")
        print("-" * 80)
        print(f"{'Название':<40} {'Вызовы':<8} {'Общее время':<12} {'Среднее':<10} {'P50':<10} {'P95':<10}")
        print("-" * 80)
        
        sorted_counters = sorted(
            stats['counters'].items(),
            key=lambda x: x[1]['total_time'],
            reverse=True
        )
        
        for name, counter_stats in sorted_counters:
            print(f"{name:<40} {counter_stats['calls']:<8} {counter_stats['total_time']:<12.4f} "
                  f"{counter_stats['avg_time']:<10.6f} {counter_stats['p50_time']:<10.6f} "
                  f"{counter_stats['p95_time']:<10.6f}")
    
    # Трекеры памяти
    if stats['memory_trackers']:
        print("\nТРЕКЕРЫ ПАМЯТИ:")
        print("-" * 80)
        print(f"{'Название':<40} {'Снимки':<8} {'Пик памяти':<12} {'Аллокации':<12}")
        print("-" * 80)
        
        for name, memory_stats in stats['memory_trackers'].items():
            print(f"{name:<40} {memory_stats['snapshots']:<8} {memory_stats['peak_memory']:<12} "
                  f"{memory_stats['total_allocations']:<12}")


# Импорт asyncio для проверки корутин
import asyncio

#!/usr/bin/env python3
"""
Morphology adapter with caching support.

This adapter provides morphology analysis functionality with LRU caching
for improved performance on repeated token patterns.
"""

import time
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass

from ai_service.utils.logging_config import get_logger
from ai_service.utils.lru_cache_ttl import LruTtlCache, create_cache_key, create_flags_hash
from .processors.morphology_processor import MorphologyProcessor


@dataclass
class ParseResult:
    """Result of morphology parsing."""
    normal_form: str
    lemma: str
    pos: str
    gender: Optional[str] = None
    number: Optional[str] = None
    case: Optional[str] = None


@dataclass
class MorphologyResult:
    """Result of morphology analysis."""
    normalized: str
    fallback: bool
    traces: List[str]
    parses: List[ParseResult]
    processing_time: float
    cache_hit: bool = False


class MorphologyAdapter:
    """
    Morphology adapter with caching support.
    
    Provides morphology analysis functionality with LRU caching for improved
    performance on repeated token patterns. Caches both parse results and
    normalization outcomes.
    """
    
    def __init__(
        self,
        cache: Optional[LruTtlCache] = None,
        diminutive_maps: Optional[Dict[str, Dict[str, str]]] = None
    ):
        """
        Initialize morphology adapter.
        
        Args:
            cache: Optional LRU cache instance
            diminutive_maps: Diminutive name mappings
        """
        self.logger = get_logger(__name__)
        self.morphology_processor = MorphologyProcessor(diminutive_maps)
        self.cache = cache
        
        # Metrics
        self._total_requests = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_processing_time = 0.0
    
    def parse(
        self,
        token: str,
        language: str,
        role: Optional[str] = None,
        feature_flags: Optional[Dict[str, Any]] = None
    ) -> MorphologyResult:
        """
        Parse token with morphology analysis and caching.
        
        Args:
            token: Token to parse
            language: Language code
            role: Token role (given, surname, patronymic, etc.)
            feature_flags: Feature flags for cache key
            
        Returns:
            MorphologyResult with normalized form and metadata
        """
        start_time = time.perf_counter()
        self._total_requests += 1
        
        # Create cache key
        cache_key = None
        if self.cache:
            flags = feature_flags or {}
            flags_hash = create_flags_hash(flags)
            cache_key = create_cache_key(
                f"{language}_morph",
                f"{token}_{role or 'unknown'}",
                flags_hash
            )
            
            # Try to get from cache
            hit, cached_result = self.cache.get(cache_key)
            if hit:
                self._cache_hits += 1
                processing_time = time.perf_counter() - start_time
                self._total_processing_time += processing_time
                
                # Return cached result with updated timing
                return MorphologyResult(
                    normalized=cached_result['normalized'],
                    fallback=cached_result['fallback'],
                    traces=cached_result['traces'],
                    parses=cached_result['parses'],
                    processing_time=processing_time,
                    cache_hit=True
                )
        
        # Cache miss - perform morphology analysis
        self._cache_misses += 1
        
        # Perform actual morphology analysis
        normalized, fallback, traces = self.morphology_processor._normalize_token(
            token, language, role
        )
        
        # Create parse results (simplified)
        parses = self._create_parse_results(token, normalized, language)
        
        processing_time = time.perf_counter() - start_time
        self._total_processing_time += processing_time
        
        # Prepare result
        result = MorphologyResult(
            normalized=normalized,
            fallback=fallback,
            traces=traces,
            parses=parses,
            processing_time=processing_time,
            cache_hit=False
        )
        
        # Cache the result
        if self.cache and cache_key:
            cache_value = {
                'normalized': normalized,
                'fallback': fallback,
                'traces': traces,
                'parses': parses
            }
            self.cache.set(cache_key, cache_value)
        
        return result
    
    async def normalize_slavic_token(
        self,
        token: str,
        role: Optional[str],
        language: str,
        enable_morphology: bool = True,
        preserve_feminine_suffix_uk: bool = False,
        feature_flags: Optional[Dict[str, Any]] = None
    ) -> MorphologyResult:
        """
        Normalize Slavic token with caching.
        
        Args:
            token: Token to normalize
            role: Token role
            language: Language code
            enable_morphology: Whether to enable morphology
            preserve_feminine_suffix_uk: Whether to preserve Ukrainian feminine suffixes
            feature_flags: Feature flags for cache key
            
        Returns:
            MorphologyResult with normalized form and metadata
        """
        start_time = time.perf_counter()
        self._total_requests += 1
        
        # Create cache key
        cache_key = None
        if self.cache:
            flags = feature_flags or {}
            flags['enable_morphology'] = enable_morphology
            flags['preserve_feminine_suffix_uk'] = preserve_feminine_suffix_uk
            flags_hash = create_flags_hash(flags)
            cache_key = create_cache_key(
                f"{language}_slavic",
                f"{token}_{role or 'unknown'}",
                flags_hash
            )
            
            # Try to get from cache
            hit, cached_result = self.cache.get(cache_key)
            if hit:
                self._cache_hits += 1
                processing_time = time.perf_counter() - start_time
                self._total_processing_time += processing_time
                
                # Return cached result with updated timing
                return MorphologyResult(
                    normalized=cached_result['normalized'],
                    fallback=cached_result['fallback'],
                    traces=cached_result['traces'],
                    parses=cached_result['parses'],
                    processing_time=processing_time,
                    cache_hit=True
                )
        
        # Cache miss - perform normalization
        self._cache_misses += 1
        
        # Perform actual normalization
        normalized, traces = await self.morphology_processor.normalize_slavic_token(
            token, role, language, enable_morphology, preserve_feminine_suffix_uk
        )
        
        # Create parse results
        parses = self._create_parse_results(token, normalized, language)
        
        processing_time = time.perf_counter() - start_time
        self._total_processing_time += processing_time
        
        # Prepare result
        result = MorphologyResult(
            normalized=normalized,
            fallback=normalized.lower() == token.lower(),
            traces=traces,
            parses=parses,
            processing_time=processing_time,
            cache_hit=False
        )
        
        # Cache the result
        if self.cache and cache_key:
            cache_value = {
                'normalized': normalized,
                'fallback': result.fallback,
                'traces': traces,
                'parses': parses
            }
            self.cache.set(cache_key, cache_value)
        
        return result
    
    def _create_parse_results(
        self,
        token: str,
        normalized: str,
        language: str
    ) -> List[ParseResult]:
        """
        Create parse results from token and normalized form.
        
        Args:
            token: Original token
            normalized: Normalized form
            language: Language code
            
        Returns:
            List of ParseResult objects
        """
        # Simplified parse result creation
        # In a real implementation, this would use actual morphology analysis
        parse_result = ParseResult(
            normal_form=normalized,
            lemma=normalized.lower(),
            pos="NOUN",  # Default to noun
            gender=None,
            number="sing",
            case="nom"
        )
        
        return [parse_result]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get morphology adapter statistics.
        
        Returns:
            Dictionary with adapter statistics
        """
        avg_processing_time = (
            self._total_processing_time / self._total_requests
            if self._total_requests > 0 else 0.0
        )
        
        hit_rate = (
            self._cache_hits / self._total_requests * 100
            if self._total_requests > 0 else 0.0
        )
        
        stats = {
            'total_requests': self._total_requests,
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate': hit_rate,
            'avg_processing_time': avg_processing_time,
            'total_processing_time': self._total_processing_time
        }
        
        # Add cache stats if available
        if self.cache:
            cache_stats = self.cache.get_stats()
            stats['cache'] = cache_stats
        
        return stats
    
    def clear_cache(self) -> None:
        """Clear morphology cache."""
        if self.cache:
            self.cache.clear()
    
    def reset_stats(self) -> None:
        """Reset adapter statistics."""
        self._total_requests = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_processing_time = 0.0

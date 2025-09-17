#!/usr/bin/env python3
"""
Tokenizer service with caching support.

This service provides tokenization functionality with LRU caching
for improved performance on repeated patterns.
"""

import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from ...utils.logging_config import get_logger
from ...utils.lru_cache_ttl import LruTtlCache, create_cache_key, create_flags_hash
from .processors.token_processor import TokenProcessor


@dataclass
class TokenizationResult:
    """Result of tokenization operation."""
    tokens: List[str]
    traces: List[str]
    metadata: Dict[str, Any]
    processing_time: float
    cache_hit: bool = False
    success: bool = True


class TokenizerService:
    """
    Tokenizer service with caching support.
    
    Provides tokenization functionality with LRU caching for improved
    performance on repeated patterns. Caches both tokenization results
    and token classification.
    
    Features:
    - Collapse double dots in initials (И.. → И.)
    - Preserve hyphenated names with has_hyphen flag
    - NFKC normalization and bidi cleaning
    - Remove invisible characters while preserving .-' as valid
    """
    
    def __init__(
        self, 
        cache: Optional[LruTtlCache] = None,
        fix_initials_double_dot: bool = False,
        preserve_hyphenated_case: bool = True
    ):
        """
        Initialize tokenizer service.
        
        Args:
            cache: Optional LRU cache instance
            fix_initials_double_dot: Whether to collapse double dots in initials
            preserve_hyphenated_case: Whether to preserve hyphenated names
        """
        self.logger = get_logger(__name__)
        self.token_processor = TokenProcessor()
        self.cache = cache
        
        # Feature flags
        self.fix_initials_double_dot = fix_initials_double_dot
        self.preserve_hyphenated_case = preserve_hyphenated_case
        
        # Metrics
        self._total_requests = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_processing_time = 0.0
    
    def tokenize(
        self,
        text: str,
        language: str = "uk",
        remove_stop_words: bool = True,
        preserve_names: bool = True,
        stop_words: Optional[set] = None,
        feature_flags: Optional[Dict[str, Any]] = None
    ) -> TokenizationResult:
        """
        Tokenize text with caching support.
        
        Args:
            text: Input text to tokenize
            language: Language code
            remove_stop_words: Whether to remove stop words
            preserve_names: Whether to preserve name-specific punctuation
            stop_words: Custom stop words set
            feature_flags: Feature flags for cache key
            
        Returns:
            TokenizationResult with tokens and metadata
        """
        start_time = time.perf_counter()
        self._total_requests += 1
        
        # Create cache key
        cache_key = None
        if self.cache:
            flags = feature_flags or {}
            flags_hash = create_flags_hash(flags)
            cache_key = create_cache_key(language, text, flags_hash)
            
            # Try to get from cache
            hit, cached_result = self.cache.get(cache_key)
            if hit:
                self._cache_hits += 1
                processing_time = time.perf_counter() - start_time
                self._total_processing_time += processing_time
                
                # Return cached result with updated timing
                return TokenizationResult(
                    tokens=cached_result['tokens'],
                    traces=cached_result['traces'],
                    metadata=cached_result['metadata'],
                    processing_time=processing_time,
                    cache_hit=True
                )
        
        # Cache miss - perform tokenization
        self._cache_misses += 1
        
        # Perform actual tokenization
        tokens, traces, metadata = self.token_processor.strip_noise_and_tokenize(
            text,
            language=language,
            remove_stop_words=remove_stop_words,
            preserve_names=preserve_names,
            stop_words=stop_words,
            feature_flags=feature_flags
        )
        
        # Apply post-processing rules
        tokens, post_traces = self._apply_post_processing_rules(tokens)
        traces.extend(post_traces)
        
        processing_time = time.perf_counter() - start_time
        self._total_processing_time += processing_time
        
        # Prepare result
        result = TokenizationResult(
            tokens=tokens,
            traces=traces,
            metadata=metadata,
            processing_time=processing_time,
            cache_hit=False
        )
        
        # Cache the result
        if self.cache and cache_key:
            cache_value = {
                'tokens': tokens,
                'traces': traces,
                'metadata': metadata
            }
            self.cache.set(cache_key, cache_value)
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get tokenizer service statistics.
        
        Returns:
            Dictionary with service statistics
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
        """Clear tokenizer cache."""
        if self.cache:
            self.cache.clear()
    
    def reset_stats(self) -> None:
        """Reset service statistics."""
        self._total_requests = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_processing_time = 0.0
    
    def _apply_post_processing_rules(self, tokens: List[str]) -> Tuple[List[str], List[str]]:
        """
        Apply post-processing rules to tokens.
        
        Args:
            tokens: List of tokens to process
            
        Returns:
            Tuple of (processed_tokens, traces)
        """
        processed_tokens = []
        traces = []
        
        for token in tokens:
            original_token = token
            processed_token = token
            
            # Rule 1: Collapse double dots in initials (И.. → И.)
            if self.fix_initials_double_dot:
                processed_token = self.collapse_double_dots(processed_token)
                if processed_token != original_token:
                    trace_entry = {
                        "rule": "collapse_double_dots",
                        "before": original_token,
                        "after": processed_token,
                        "evidence": "initials"
                    }
                    traces.append(trace_entry)
            
            # Rule 2: Preserve hyphenated names (add has_hyphen flag to metadata)
            if self.preserve_hyphenated_case:
                if self._has_hyphen(token):
                    traces.append({
                        "type": "tokenize",
                        "action": "preserve_hyphenated_name",
                        "token": processed_token,
                        "has_hyphen": True
                    })
            
            processed_tokens.append(processed_token)
        
        return processed_tokens, traces
    
    def collapse_double_dots(self, token: str) -> str:
        """
        Collapse double dots in initials according to pattern ^([A-Za-zА-Яа-яІЇЄҐїєґ])\.+$ → normalize to X.
        
        Args:
            token: Input token to process
            
        Returns:
            Processed token with collapsed double dots
            
        Examples:
            "И.." → "И."
            "A.." → "A."
            "І.." → "І."
            "ООО" → "ООО" (no change for abbreviations)
            "ТОВ" → "ТОВ" (no change for abbreviations)
        """
        import re
        
        # Pattern for initials: single letter followed by one or more dots
        # This covers: И., И.., A., A.., І., І.., etc.
        # Pattern: ^([A-Za-zА-Яа-яІЇЄҐїєґ])\.+$
        initial_pattern = r'^([A-Za-zА-Яа-яІЇЄҐїєґ])\.+$'
        match = re.match(initial_pattern, token)
        if match:
            # Collapse to single dot
            letter = match.group(1)
            return f"{letter}."
            
        # No changes needed
        return token
    
    def _looks_like_initial_with_double_dot(self, token: str) -> bool:
        """
        Check if token looks like an initial with double dots.
        
        Args:
            token: Token to check
            
        Returns:
            True if token looks like initial with double dots
        """
        # Pattern: single letter followed by two or more dots
        import re
        pattern = r'^[А-Яа-яA-Za-zІіЇїЄєҐґёЁ]\.{2,}$'
        return bool(re.match(pattern, token))
    
    def _collapse_double_dot(self, token: str) -> str:
        """
        Collapse double dots in initial to single dot.
        
        Args:
            token: Token with double dots
            
        Returns:
            Token with single dot
        """
        import re
        # Replace multiple dots with single dot
        return re.sub(r'\.{2,}', '.', token)
    
    def _has_hyphen(self, token: str) -> bool:
        """
        Check if token contains hyphen.
        
        Args:
            token: Token to check
            
        Returns:
            True if token contains hyphen
        """
        # Check for various hyphen types
        hyphen_chars = ['-', '–', '—', '−', '‐']
        return any(char in token for char in hyphen_chars)


class CachedTokenizerService:
    """
    Cached tokenizer service with enhanced caching capabilities.
    
    This service provides additional caching for token classification
    and other tokenization-related operations.
    """
    
    def __init__(self, cache: Optional[LruTtlCache] = None):
        """
        Initialize cached tokenizer service.
        
        Args:
            cache: Optional LRU cache instance
        """
        self.logger = get_logger(__name__)
        self.tokenizer_service = TokenizerService(cache)
        self._classification_cache = cache  # Reuse same cache for classification
        
        # Classification metrics
        self._classification_requests = 0
        self._classification_hits = 0
        self._classification_misses = 0
    
    def tokenize(
        self,
        text: str,
        language: str = "uk",
        remove_stop_words: bool = True,
        preserve_names: bool = True,
        stop_words: Optional[set] = None,
        feature_flags: Optional[Dict[str, Any]] = None
    ) -> TokenizationResult:
        """
        Tokenize text with caching support.
        
        Args:
            text: Input text to tokenize
            language: Language code
            remove_stop_words: Whether to remove stop words
            preserve_names: Whether to preserve name-specific punctuation
            stop_words: Custom stop words set
            feature_flags: Feature flags for cache key
            
        Returns:
            TokenizationResult with tokens and metadata
        """
        return self.tokenizer_service.tokenize(
            text, language, remove_stop_words, preserve_names, stop_words, feature_flags
        )
    
    def tokenize_with_classification(
        self,
        text: str,
        language: str = "uk",
        remove_stop_words: bool = True,
        preserve_names: bool = True,
        stop_words: Optional[set] = None,
        feature_flags: Optional[Dict[str, Any]] = None
    ) -> Tuple[TokenizationResult, List[str]]:
        """
        Tokenize text and classify tokens with caching.
        
        Args:
            text: Input text to tokenize
            language: Language code
            remove_stop_words: Whether to remove stop words
            preserve_names: Whether to preserve name-specific punctuation
            stop_words: Custom stop words set
            feature_flags: Feature flags for cache key
            
        Returns:
            Tuple of (TokenizationResult, token_classes)
        """
        # Get tokenization result
        tokenization_result = self.tokenize(
            text, language, remove_stop_words, preserve_names, stop_words, feature_flags
        )
        
        # Classify tokens with caching
        token_classes = self._classify_tokens_cached(
            tokenization_result.tokens,
            language,
            feature_flags
        )
        
        return tokenization_result, token_classes
    
    def _classify_tokens_cached(
        self,
        tokens: List[str],
        language: str,
        feature_flags: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Classify tokens with caching.
        
        Args:
            tokens: List of tokens to classify
            language: Language code
            feature_flags: Feature flags for cache key
            
        Returns:
            List of token classes
        """
        if not self._classification_cache:
            # No cache - perform classification directly
            return self._classify_tokens_direct(tokens, language)
        
        self._classification_requests += 1
        
        # Create cache key for classification
        flags = feature_flags or {}
        flags_hash = create_flags_hash(flags)
        classification_key = create_cache_key(
            f"{language}_classification",
            "|".join(tokens),  # Join tokens for key
            flags_hash
        )
        
        # Try to get from cache
        hit, cached_classes = self._classification_cache.get(classification_key)
        if hit:
            self._classification_hits += 1
            return cached_classes
        
        # Cache miss - perform classification
        self._classification_misses += 1
        token_classes = self._classify_tokens_direct(tokens, language)
        
        # Cache the result
        self._classification_cache.set(classification_key, token_classes)
        
        return token_classes
    
    def _classify_tokens_direct(self, tokens: List[str], language: str) -> List[str]:
        """
        Perform direct token classification without caching.
        
        Args:
            tokens: List of tokens to classify
            language: Language code
            
        Returns:
            List of token classes
        """
        # Simple classification logic - can be enhanced
        classes = []
        for token in tokens:
            if len(token) == 1 and token.isalpha():
                classes.append("initial")
            elif token.isupper():
                classes.append("acronym")
            elif token.istitle():
                classes.append("name")
            else:
                classes.append("word")
        
        return classes
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cached tokenizer service statistics.
        
        Returns:
            Dictionary with service statistics
        """
        stats = self.tokenizer_service.get_stats()
        
        # Add classification stats
        classification_hit_rate = (
            self._classification_hits / self._classification_requests * 100
            if self._classification_requests > 0 else 0.0
        )
        
        stats.update({
            'classification_requests': self._classification_requests,
            'classification_hits': self._classification_hits,
            'classification_misses': self._classification_misses,
            'classification_hit_rate': classification_hit_rate
        })
        
        return stats
    
    def clear_cache(self) -> None:
        """Clear all caches."""
        self.tokenizer_service.clear_cache()
        if self._classification_cache:
            self._classification_cache.clear()
    
    def reset_stats(self) -> None:
        """Reset all statistics."""
        self.tokenizer_service.reset_stats()
        self._classification_requests = 0
        self._classification_hits = 0
        self._classification_misses = 0

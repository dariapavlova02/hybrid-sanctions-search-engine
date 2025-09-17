#!/usr/bin/env python3
"""
Decomposed normalization service with clear component separation.

This service orchestrates the normalization pipeline using separate
components: TokenizerService, RoleTaggerService, MorphologyAdapter,
and NameAssembler. Each component has a single responsibility and
can be easily replaced or tested independently.
"""

import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from ...contracts.base_contracts import NormalizationResult, TokenTrace
from ...utils.logging_config import get_logger
from ...utils.feature_flags import FeatureFlags
from ...utils.lru_cache_ttl import LruTtlCache
from .tokenizer_service import TokenizerService
from .role_tagger_service import RoleTaggerService, Token, TokenRole
from .morphology_adapter import MorphologyAdapter
from .name_assembler import NameAssembler, TokenWithRole, AssembledNames
from .lexicon_loader import Lexicons, load_lexicons


@dataclass
class PipelineMetrics:
    """Metrics for normalization pipeline stages."""
    tokenize_time: float = 0.0
    role_tag_time: float = 0.0
    morphology_time: float = 0.0
    assemble_time: float = 0.0
    total_time: float = 0.0


class NormalizationServiceDecomposed:
    """
    Decomposed normalization service with clear component separation.
    
    Responsibilities:
    - Orchestrate tokenize → role_tag → morph → assemble pipeline
    - Pass feature flags through all components
    - Log durations for each stage and p95 metrics
    - Maintain external NormalizationResult contract
    """
    
    def __init__(
        self,
        cache: Optional[LruTtlCache] = None,
        *,
        fix_initials_double_dot: bool = True,
        preserve_hyphenated_case: bool = True,
        org_context_window: int = 3,
        strict_stopwords: bool = False,
        prefer_surname_first: bool = False
    ):
        """
        Initialize decomposed normalization service.
        
        Args:
            cache: Optional LRU cache for performance
            fix_initials_double_dot: Whether to collapse double dots in initials
            preserve_hyphenated_case: Whether to preserve hyphenated names
            org_context_window: Window size for organization context detection
            strict_stopwords: Whether to use strict stopword filtering
            prefer_surname_first: Whether to prefer surname-first order
        """
        self.logger = get_logger(__name__)
        
        # Initialize components
        self.tokenizer = TokenizerService(
            cache=cache,
            fix_initials_double_dot=fix_initials_double_dot,
            preserve_hyphenated_case=preserve_hyphenated_case
        )
        
        # Load lexicons for role tagger
        self.lexicons = load_lexicons()
        
        self.role_tagger = RoleTaggerService(
            lexicons=self.lexicons,
            window=org_context_window
        )
        
        self.morphology = MorphologyAdapter()
        self.name_assembler = NameAssembler()
        
        # Statistics
        self._total_requests = 0
        self._total_processing_time = 0.0
        self._stage_times = {
            'tokenize': [],
            'role_tag': [],
            'morphology': [],
            'assemble': []
        }
        
        self.logger.info("NormalizationServiceDecomposed initialized with separate components")
    
    async def normalize_async(
        self,
        text: str,
        *,
        language: str = "uk",
        remove_stop_words: bool = True,
        preserve_names: bool = True,
        enable_advanced_features: bool = True,
        feature_flags: Optional[FeatureFlags] = None,
        **kwargs
    ) -> NormalizationResult:
        """
        Normalize text using decomposed pipeline.
        
        Args:
            text: Input text to normalize
            language: Language code
            remove_stop_words: Whether to remove stop words
            preserve_names: Whether to preserve name-specific punctuation
            enable_advanced_features: Whether to enable morphology
            feature_flags: Feature flags for behavior control
            **kwargs: Additional arguments (ignored for compatibility)
            
        Returns:
            NormalizationResult with normalized text and metadata
        """
        start_time = time.perf_counter()
        self._total_requests += 1
        
        try:
            # Input validation
            if not text or not isinstance(text, str):
                return NormalizationResult(
                    normalized="",
                    tokens=[],
                    trace=[],
                    errors=["Invalid input: text must be a non-empty string"],
                    language=language,
                    confidence=0.0,
                    original_length=0,
                    normalized_length=0,
                    token_count=0,
                    processing_time=0.0,
                    success=False
                )
            
            # Stage 1: Tokenization
            tokenize_start = time.perf_counter()
            tokenization_result = self.tokenizer.tokenize(
                text=text,
                language=language,
                remove_stop_words=remove_stop_words,
                preserve_names=preserve_names,
                feature_flags=feature_flags.to_dict() if feature_flags else None
            )
            tokenize_time = time.perf_counter() - tokenize_start
            self._stage_times['tokenize'].append(tokenize_time)
            
            # Stage 2: Role Tagging
            role_tag_start = time.perf_counter()
            role_tags = self.role_tagger.tag(
                tokens=tokenization_result.tokens,
                lang=language
            )
            role_tag_time = time.perf_counter() - role_tag_start
            self._stage_times['role_tag'].append(role_tag_time)
            
            # Stage 3: Morphology (if enabled)
            morphology_time = 0.0
            if enable_advanced_features:
                morphology_start = time.perf_counter()
                normalized_tokens = []
                morphology_traces = []
                
                for i, token in enumerate(tokenization_result.tokens):
                    role_tag = role_tags[i] if i < len(role_tags) else None
                    
                    # Only process person tokens
                    if role_tag and role_tag.role in {TokenRole.GIVEN, TokenRole.SURNAME, TokenRole.PATRONYMIC}:
                        # Use MorphologyAdapter's to_nominative method
                        normalized_token = self.morphology.to_nominative(token, language)
                        normalized_tokens.append(normalized_token)
                        morphology_traces.append(f"normalized_{role_tag.role.value}: {token} -> {normalized_token}")
                    else:
                        normalized_tokens.append(token)
                
                morphology_time = time.perf_counter() - morphology_start
                self._stage_times['morphology'].append(morphology_time)
            else:
                normalized_tokens = tokenization_result.tokens
                morphology_traces = []
            
            # Stage 4: Name Assembly
            assemble_start = time.perf_counter()
            
            # Convert role tags to TokenWithRole objects
            tagged_tokens = []
            for i, token in enumerate(tokenization_result.tokens):
                role_tag = role_tags[i] if i < len(role_tags) else None
                if role_tag:
                    tagged_token = TokenWithRole(
                        text=token,
                        normalized=normalized_tokens[i] if i < len(normalized_tokens) else token,
                        role=role_tag.role,
                        confidence=role_tag.confidence,
                        reason=role_tag.reason,
                        evidence=role_tag.evidence,
                        state_from=role_tag.state_from,
                        state_to=role_tag.state_to,
                        window_context=role_tag.window_context
                    )
                    tagged_tokens.append(tagged_token)
            
            assembled_names = self.name_assembler.assemble(
                tagged_tokens=tagged_tokens,
                language=language,
                flags=feature_flags.to_dict() if feature_flags else None
            )
            assemble_time = time.perf_counter() - assemble_start
            self._stage_times['assemble'].append(assemble_time)
            
            # Calculate total processing time
            total_time = time.perf_counter() - start_time
            self._total_processing_time += total_time
            
            # Build final result
            normalized_text = self.person_separator.join(
                person.full_name for person in assembled_names.persons
            )
            
            # Collect all traces as TokenTrace objects
            all_traces = []
            # Add basic trace information
            all_traces.append(TokenTrace(
                token="pipeline",
                role="info",
                rule="decomposed_processing",
                output=f"processed {len(tokenization_result.tokens)} tokens, found {len(assembled_names.persons)} persons"
            ))
            all_traces.append(TokenTrace(
                token="timing",
                role="metrics",
                rule="performance",
                output=f"total: {total_time:.4f}s, stages: tokenize={tokenize_time:.4f}s, role_tag={role_tag_time:.4f}s, morphology={morphology_time:.4f}s, assemble={assemble_time:.4f}s"
            ))
            
            return NormalizationResult(
                normalized=normalized_text,
                tokens=tokenization_result.tokens,
                trace=all_traces,
                errors=[],
                language=language,
                confidence=self._calculate_overall_confidence(assembled_names.persons),
                original_length=len(text),
                normalized_length=len(normalized_text),
                token_count=len(tokenization_result.tokens),
                processing_time=total_time,
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"Decomposed normalization failed: {e}")
            processing_time = time.perf_counter() - start_time
            
            return NormalizationResult(
                normalized="",
                tokens=[],
                trace=[],
                errors=[str(e)],
                language=language,
                confidence=0.0,
                original_length=len(text),
                normalized_length=0,
                token_count=0,
                processing_time=processing_time,
                success=False
            )
    
    def _get_p95_time(self, stage: str) -> float:
        """Calculate p95 time for a stage."""
        times = self._stage_times.get(stage, [])
        if not times:
            return 0.0
        
        sorted_times = sorted(times)
        p95_index = int(len(sorted_times) * 0.95)
        return sorted_times[p95_index] if p95_index < len(sorted_times) else sorted_times[-1]
    
    def _calculate_overall_confidence(self, persons: List) -> float:
        """Calculate overall confidence from assembled persons."""
        if not persons:
            return 0.0
        
        total_confidence = sum(person.confidence for person in persons)
        return total_confidence / len(persons)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        avg_processing_time = (
            self._total_processing_time / self._total_requests
            if self._total_requests > 0 else 0.0
        )
        
        stats = {
            'total_requests': self._total_requests,
            'avg_processing_time': avg_processing_time,
            'total_processing_time': self._total_processing_time,
            'stage_stats': {}
        }
        
        # Add stage statistics
        for stage, times in self._stage_times.items():
            if times:
                stats['stage_stats'][stage] = {
                    'avg_time': sum(times) / len(times),
                    'p95_time': self._get_p95_time(stage),
                    'min_time': min(times),
                    'max_time': max(times),
                    'count': len(times)
                }
        
        # Add component stats
        stats['tokenizer_stats'] = self.tokenizer.get_stats()
        stats['morphology_stats'] = self.morphology.get_cache_stats()
        stats['assembler_stats'] = self.name_assembler.get_stats()
        
        return stats
    
    def reset_stats(self) -> None:
        """Reset all statistics."""
        self._total_requests = 0
        self._total_processing_time = 0.0
        self._stage_times = {
            'tokenize': [],
            'role_tag': [],
            'morphology': [],
            'assemble': []
        }
        
        self.tokenizer.reset_stats()
        self.morphology.clear_cache()
        self.name_assembler.reset_stats()
    
    @property
    def person_separator(self) -> str:
        """Multi-person separator."""
        return " | "

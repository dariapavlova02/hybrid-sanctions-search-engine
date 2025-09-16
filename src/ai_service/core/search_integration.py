"""
Search Integration for UnifiedOrchestrator

Provides integration functions for adding HybridSearchService to the existing pipeline
without breaking existing layer contracts.
"""

import time
from typing import Any, Dict, List, Optional

from ..contracts.base_contracts import NormalizationResult, SignalsResult
from ..contracts.search_contracts import (
    SearchOpts, SearchMode, SearchResult, SearchInfo, 
    extract_search_candidates, create_search_info
)
from ..contracts.decision_contracts import DecisionInput
from ..exceptions import SearchServiceError, ElasticsearchConnectionError, SearchTimeoutError
from ..utils import get_logger

logger = get_logger(__name__)


class SearchIntegration:
    """Integration helper for search services in the pipeline"""
    
    def __init__(self, hybrid_search_service: Optional[Any] = None):
        """
        Initialize search integration
        
        Args:
            hybrid_search_service: HybridSearchService instance
        """
        self.hybrid_search_service = hybrid_search_service
        self.logger = get_logger(__name__)
    
    async def extract_and_search(
        self,
        text: str,
        normalization_result: NormalizationResult,
        signals_result: SignalsResult,
        search_opts: Optional[SearchOpts] = None
    ) -> Optional[SearchInfo]:
        """
        Extract candidates from Signals and perform hybrid search
        
        Args:
            text: Original text
            normalization_result: Result from normalization layer
            signals_result: Result from signals layer
            search_opts: Search options
            
        Returns:
            SearchInfo for Decision layer, or None if search failed/disabled
        """
        if not self.hybrid_search_service:
            self.logger.debug("Hybrid search service not available, skipping search")
            return None
        
        try:
            # Extract candidate strings from Signals result
            search_candidates = extract_search_candidates(signals_result)
            
            if not search_candidates:
                self.logger.debug("No search candidates found in Signals result")
                return None
            
            self.logger.debug(f"Found {len(search_candidates)} search candidates: {search_candidates[:5]}...")
            
            # Set default search options
            if search_opts is None:
                search_opts = SearchOpts(
                    top_k=50,
                    threshold=0.7,
                    search_mode=SearchMode.HYBRID,
                    enable_escalation=True
                )
            
            # Perform hybrid search
            search_start = time.time()
            
            search_result = await self.hybrid_search_service.find_candidates(
                normalized=normalization_result,
                text=text,
                opts=search_opts
            )
            
            search_time = time.time() - search_start
            
            # Create SearchResult for processing
            search_result_obj = SearchResult(
                candidates=search_result,
                ac_results=[],  # Will be filled by HybridSearchService
                vector_results=[],  # Will be filled by HybridSearchService
                search_metadata={
                    "candidates_count": len(search_candidates),
                    "search_time": search_time,
                    "search_mode": search_opts.search_mode.value
                },
                processing_time=search_time,
                success=True
            )
            
            # Convert to SearchInfo for Decision layer
            search_info = create_search_info(search_result_obj)
            
            self.logger.debug(
                f"Search completed: {len(search_result)} candidates found in {search_time:.3f}s"
            )
            
            return search_info
            
        except ElasticsearchConnectionError as e:
            self.logger.warning(f"Elasticsearch unavailable, skipping search: {e}")
            return None
            
        except SearchTimeoutError as e:
            self.logger.warning(f"Search timeout, skipping search: {e}")
            return None
            
        except SearchServiceError as e:
            self.logger.error(f"Search service error: {e}")
            return None
            
        except Exception as e:
            self.logger.error(f"Unexpected search error: {e}")
            return None
    
    def create_decision_input_with_search(
        self,
        original_decision_input: DecisionInput,
        search_info: Optional[SearchInfo]
    ) -> DecisionInput:
        """
        Create DecisionInput with search information
        
        Args:
            original_decision_input: Original DecisionInput from pipeline
            search_info: Search information to add
            
        Returns:
            Updated DecisionInput with search info
        """
        return DecisionInput(
            text=original_decision_input.text,
            language=original_decision_input.language,
            smartfilter=original_decision_input.smartfilter,
            signals=original_decision_input.signals,
            similarity=original_decision_input.similarity,
            search=search_info
        )
    
    def should_enable_search(self, signals_result: SignalsResult) -> bool:
        """
        Determine if search should be enabled based on Signals result
        
        Args:
            signals_result: Result from Signals layer
            
        Returns:
            True if search should be enabled
        """
        # Enable search if we have persons or organizations
        has_persons = hasattr(signals_result, 'persons') and signals_result.persons
        has_organizations = hasattr(signals_result, 'organizations') and signals_result.organizations
        
        return has_persons or has_organizations
    
    def get_search_metrics(self) -> Dict[str, Any]:
        """
        Get search metrics if available
        
        Returns:
            Dictionary with search metrics
        """
        if not self.hybrid_search_service or not hasattr(self.hybrid_search_service, 'get_metrics'):
            return {}
        
        try:
            metrics = self.hybrid_search_service.get_metrics()
            return {
                "ac_attempts": metrics.ac_attempts,
                "vector_attempts": metrics.vector_attempts,
                "ac_success": metrics.ac_success,
                "vector_success": metrics.vector_success,
                "ac_latency_p95": metrics.ac_latency_p95,
                "vector_latency_p95": metrics.vector_latency_p95,
                "hit_rate": metrics.hit_rate,
                "escalation_rate": metrics.escalation_rate
            }
        except Exception as e:
            self.logger.warning(f"Failed to get search metrics: {e}")
            return {}


def create_search_integration(hybrid_search_service: Optional[Any] = None) -> SearchIntegration:
    """
    Factory function to create SearchIntegration
    
    Args:
        hybrid_search_service: HybridSearchService instance
        
    Returns:
        SearchIntegration instance
    """
    return SearchIntegration(hybrid_search_service)

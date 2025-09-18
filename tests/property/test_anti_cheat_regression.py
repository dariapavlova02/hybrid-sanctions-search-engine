#!/usr/bin/env python3
"""
Anti-Cheat Regression Tests for Hybrid Search System

Property-based tests using Hypothesis to prevent test overfitting and ensure
system invariants are maintained across all possible inputs.

These tests verify that the hybrid search system behaves correctly according
 to fundamental invariants, regardless of input variations.
"""

import asyncio
import json
import random
import string
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import pytest
from hypothesis import given, strategies as st, settings, assume, example
from hypothesis.strategies import text, lists, integers, floats, booleans, sampled_from
import httpx


class SearchType(str, Enum):
    """Search result types"""
    EXACT = "exact"
    PHRASE = "phrase"
    NGRAM = "ngram"
    VECTOR = "vector"
    FUSION = "fusion"


@dataclass
class SearchResult:
    """Search result with scores and metadata"""
    entity_id: str
    entity_type: str
    normalized_name: str
    aliases: List[str]
    country: str
    dob: Optional[str]
    meta: Dict[str, Any]
    ac_score: float
    vector_score: float
    final_score: float
    search_type: SearchType
    matched_field: str
    matched_text: str


@dataclass
class SearchConfig:
    """Search configuration for testing"""
    exact_threshold: float = 1.0
    phrase_threshold: float = 0.8
    ngram_threshold: float = 0.6
    vector_threshold: float = 0.5
    fusion_weights: Dict[str, float] = None
    
    def __post_init__(self):
        if self.fusion_weights is None:
            self.fusion_weights = {
                "ac_weight": 0.55,
                "vector_weight": 0.45,
                "dob_bonus": 0.05,
                "context_penalty": 0.1
            }


class HybridSearchTester:
    """Test harness for hybrid search system"""
    
    def __init__(self, es_url: str = "http://localhost:9200"):
        self.es_url = es_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)
        self.normalizer_cache = {}
    
    async def normalize_text(self, text: str) -> str:
        """Normalize text for consistent comparison"""
        if text in self.normalizer_cache:
            return self.normalizer_cache[text]
        
        # Simple normalization: lowercase, remove diacritics, strip whitespace
        normalized = text.lower().strip()
        
        # Remove common diacritics (simplified)
        diacritics_map = {
            'а': 'a', 'е': 'e', 'ё': 'e', 'и': 'i', 'о': 'o', 'у': 'u', 'ы': 'y', 'э': 'e', 'ю': 'u', 'я': 'ya',
            'А': 'A', 'Е': 'E', 'Ё': 'E', 'И': 'I', 'О': 'O', 'У': 'U', 'Ы': 'Y', 'Э': 'E', 'Ю': 'U', 'Я': 'YA',
            'і': 'i', 'ї': 'i', 'є': 'e', 'ґ': 'g',
            'І': 'I', 'Ї': 'I', 'Є': 'E', 'Ґ': 'G',
            'ß': 'ss', 'ẞ': 'SS',  # German eszett
            'µ': 'μ', 'Μ': 'Μ'  # Normalize micro sign to Greek mu
        }
        
        for old, new in diacritics_map.items():
            normalized = normalized.replace(old, new)
        
        self.normalizer_cache[text] = normalized
        return normalized
    
    async def ac_search(self, query: str, entity_type: str = "person") -> List[SearchResult]:
        """Perform AC search"""
        index_name = f"watchlist_{entity_type}s_current"
        
        # Exact match query
        exact_query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"entity_type": entity_type}},
                        {"terms": {"normalized_name": [query]}}
                    ]
                }
            },
            "size": 50
        }
        
        try:
            response = await self.client.get(
                f"{self.es_url}/{index_name}/_search",
                json=exact_query
            )
            
            if response.status_code != 200:
                return []
            
            result = response.json()
            hits = result.get("hits", {}).get("hits", [])
            
            search_results = []
            for hit in hits:
                source = hit.get("_source", {})
                score = hit.get("_score", 0.0)
                
                search_result = SearchResult(
                    entity_id=source.get("entity_id", ""),
                    entity_type=source.get("entity_type", ""),
                    normalized_name=source.get("normalized_name", ""),
                    aliases=source.get("aliases", []),
                    country=source.get("country", ""),
                    dob=source.get("dob"),
                    meta=source.get("meta", {}),
                    ac_score=score,
                    vector_score=0.0,
                    final_score=score,
                    search_type=SearchType.EXACT,
                    matched_field="normalized_name",
                    matched_text=source.get("normalized_name", "")
                )
                search_results.append(search_result)
            
            return search_results
            
        except Exception:
            return []
    
    async def vector_search(self, query: str, entity_type: str = "person") -> List[SearchResult]:
        """Perform vector search"""
        index_name = f"watchlist_{entity_type}s_current"
        
        # Generate mock query vector (384 dimensions)
        query_vector = [random.random() for _ in range(384)]
        
        vector_query = {
            "knn": {
                "field": "name_vector",
                "query_vector": query_vector,
                "k": 50,
                "similarity": "cosine"
            },
            "size": 50
        }
        
        try:
            response = await self.client.get(
                f"{self.es_url}/{index_name}/_search",
                json=vector_query
            )
            
            if response.status_code != 200:
                return []
            
            result = response.json()
            hits = result.get("hits", {}).get("hits", [])
            
            search_results = []
            for hit in hits:
                source = hit.get("_source", {})
                score = hit.get("_score", 0.0)
                
                search_result = SearchResult(
                    entity_id=source.get("entity_id", ""),
                    entity_type=source.get("entity_type", ""),
                    normalized_name=source.get("normalized_name", ""),
                    aliases=source.get("aliases", []),
                    country=source.get("country", ""),
                    dob=source.get("dob"),
                    meta=source.get("meta", {}),
                    ac_score=0.0,
                    vector_score=score,
                    final_score=score,
                    search_type=SearchType.VECTOR,
                    matched_field="name_vector",
                    matched_text=source.get("normalized_name", "")
                )
                search_results.append(search_result)
            
            return search_results
            
        except Exception:
            return []
    
    async def hybrid_search(self, query: str, config: SearchConfig, entity_type: str = "person") -> List[SearchResult]:
        """Perform hybrid search with fusion"""
        # Get AC results
        ac_results = await self.ac_search(query, entity_type)
        
        # Get Vector results
        vector_results = await self.vector_search(query, entity_type)
        
        # Fuse results
        fused_results = self._fuse_results(ac_results, vector_results, config)
        
        return fused_results
    
    def _fuse_results(self, ac_results: List[SearchResult], vector_results: List[SearchResult], config: SearchConfig) -> List[SearchResult]:
        """Fuse AC and Vector results"""
        # Create entity lookup maps
        ac_map = {result.entity_id: result for result in ac_results}
        vector_map = {result.entity_id: result for result in vector_results}
        
        # Get all unique entity IDs
        all_entity_ids = set(ac_map.keys()) | set(vector_map.keys())
        
        fused_results = []
        
        for entity_id in all_entity_ids:
            ac_result = ac_map.get(entity_id)
            vector_result = vector_map.get(entity_id)
            
            # Calculate fusion score
            ac_score = ac_result.ac_score if ac_result else 0.0
            vector_score = vector_result.vector_score if vector_result else 0.0
            
            fusion_score = (
                config.fusion_weights["ac_weight"] * ac_score +
                config.fusion_weights["vector_weight"] * vector_score
            )
            
            # Use the result with more complete information
            primary_result = ac_result if ac_result else vector_result
            
            if not primary_result:
                continue
            
            # Determine search type
            if ac_result and vector_result:
                search_type = SearchType.FUSION
            elif ac_result:
                search_type = SearchType.AC
            else:
                search_type = SearchType.VECTOR
            
            fused_result = SearchResult(
                entity_id=primary_result.entity_id,
                entity_type=primary_result.entity_type,
                normalized_name=primary_result.normalized_name,
                aliases=primary_result.aliases,
                country=primary_result.country,
                dob=primary_result.dob,
                meta=primary_result.meta,
                ac_score=ac_score,
                vector_score=vector_score,
                final_score=fusion_score,
                search_type=search_type,
                matched_field=primary_result.matched_field,
                matched_text=primary_result.matched_text
            )
            
            fused_results.append(fused_result)
        
        # Sort by final score (descending)
        fused_results.sort(key=lambda x: x.final_score, reverse=True)
        
        return fused_results
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.client.aclose()


# Test strategies
def search_queries() -> st.SearchStrategy[str]:
    """Generate search query strings"""
    return st.one_of(
        st.text(min_size=1, max_size=50, alphabet=string.ascii_letters + string.digits + " "),
        st.text(min_size=1, max_size=50, alphabet="абвгдеёжзийклмнопрстуфхцчшщъыьэюяіїєґ "),
        st.text(min_size=1, max_size=50, alphabet="АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯІЇЄҐ ")
    )

def search_configs() -> st.SearchStrategy[SearchConfig]:
    """Generate search configurations"""
    return st.builds(
        SearchConfig,
        exact_threshold=st.floats(min_value=0.5, max_value=1.0),
        phrase_threshold=st.floats(min_value=0.3, max_value=0.9),
        ngram_threshold=st.floats(min_value=0.2, max_value=0.8),
        vector_threshold=st.floats(min_value=0.1, max_value=0.7),
        fusion_weights=st.dictionaries(
            keys=st.sampled_from(["ac_weight", "vector_weight", "dob_bonus", "context_penalty"]),
            values=st.floats(min_value=0.0, max_value=1.0),
            min_size=4,
            max_size=4
        )
    )

def case_variations(text: str) -> st.SearchStrategy[str]:
    """Generate case variations of text"""
    return st.one_of(
        st.just(text.lower()),
        st.just(text.upper()),
        st.just(text.title()),
        st.just(text.swapcase()),
        st.just(text.capitalize())
    )

def diacritic_variations(text: str) -> st.SearchStrategy[str]:
    """Generate diacritic variations of text"""
    # Simple diacritic variations for testing
    variations = [
        text.replace('а', 'а').replace('е', 'ё'),
        text.replace('и', 'і').replace('е', 'є'),
        text.replace('о', 'о').replace('у', 'у'),
    ]
    return st.one_of([st.just(var) for var in variations if var != text] + [st.just(text)])


class TestAntiCheatRegression:
    """Anti-cheat regression tests for hybrid search"""
    
    @pytest.fixture(scope="class")
    async def search_tester(self):
        """Create search tester instance"""
        tester = HybridSearchTester()
        yield tester
        await tester.cleanup()
    
    @pytest.mark.asyncio
    @given(
        query=search_queries(),
        config=search_configs(),
        entity_type=st.sampled_from(["person", "org"])
    )
    @settings(max_examples=50, deadline=5000)
    async def test_exact_match_invariant(self, search_tester, query, config, entity_type):
        """
        INVARIANT: Exact matches always have score >= any non-exact matches for the same text.
        
        This test ensures that exact matches are never scored lower than
        approximate matches for the same normalized text.
        """
        assume(len(query.strip()) > 0)
        
        # Normalize query for consistent comparison
        normalized_query = await search_tester.normalize_text(query)
        assume(len(normalized_query) > 0)
        
        # Perform hybrid search
        results = await search_tester.hybrid_search(query, config, entity_type)
        
        if not results:
            return  # No results to compare
        
        # Find exact matches
        exact_matches = [r for r in results if r.search_type == SearchType.EXACT]
        non_exact_matches = [r for r in results if r.search_type != SearchType.EXACT]
        
        if not exact_matches or not non_exact_matches:
            return  # No comparison possible
        
        # Check invariant: exact matches should have higher scores
        max_exact_score = max(r.final_score for r in exact_matches)
        max_non_exact_score = max(r.final_score for r in non_exact_matches)
        
        assert max_exact_score >= max_non_exact_score, (
            f"Exact match invariant violated: "
            f"max_exact_score={max_exact_score} < max_non_exact_score={max_non_exact_score} "
            f"for query='{query}', normalized='{normalized_query}'"
        )
    
    @pytest.mark.asyncio
    @given(
        query=search_queries(),
        config=search_configs(),
        entity_type=st.sampled_from(["person", "org"])
    )
    @settings(max_examples=50, deadline=5000)
    async def test_fusion_score_invariant(self, search_tester, query, config, entity_type):
        """
        INVARIANT: If both AC and kNN found the same entity, fusion score >= max(ac_score, vector_score).
        
        This test ensures that fusion never reduces the score below the best
        individual component score.
        """
        assume(len(query.strip()) > 0)
        
        # Perform hybrid search
        results = await search_tester.hybrid_search(query, config, entity_type)
        
        if not results:
            return  # No results to check
        
        # Find fusion results (both AC and Vector found the same entity)
        fusion_results = [r for r in results if r.search_type == SearchType.FUSION]
        
        for result in fusion_results:
            ac_score = result.ac_score
            vector_score = result.vector_score
            fusion_score = result.final_score
            
            max_individual_score = max(ac_score, vector_score)
            
            assert fusion_score >= max_individual_score, (
                f"Fusion score invariant violated: "
                f"fusion_score={fusion_score} < max_individual_score={max_individual_score} "
                f"for entity_id='{result.entity_id}', query='{query}'"
            )
    
    @pytest.mark.asyncio
    @given(
        base_query=search_queries(),
        config=search_configs(),
        entity_type=st.sampled_from(["person", "org"])
    )
    @settings(max_examples=30, deadline=5000)
    async def test_case_stability_invariant(self, search_tester, base_query, config, entity_type):
        """
        INVARIANT: AC search results are stable across case variations.
        
        This test ensures that case variations of the same query produce
        consistent AC search results through normalization.
        """
        assume(len(base_query.strip()) > 0)
        
        # Generate case variations
        case_variants = [
            base_query.lower(),
            base_query.upper(),
            base_query.title(),
            base_query.swapcase(),
            base_query.capitalize()
        ]
        
        # Remove duplicates
        case_variants = list(set(case_variants))
        
        if len(case_variants) < 2:
            return  # Not enough variations to test
        
        # Perform searches for each variation
        results_by_variant = {}
        for variant in case_variants:
            results = await search_tester.hybrid_search(variant, config, entity_type)
            # Filter for AC results only
            ac_results = [r for r in results if r.search_type in [SearchType.EXACT, SearchType.PHRASE, SearchType.NGRAM]]
            results_by_variant[variant] = ac_results
        
        # Check stability: same entities should be found across variations
        all_entity_ids = set()
        for results in results_by_variant.values():
            all_entity_ids.update(r.entity_id for r in results)
        
        if not all_entity_ids:
            return  # No results to compare
        
        # For each entity found, check it appears consistently
        for entity_id in all_entity_ids:
            entity_scores = []
            for variant, results in results_by_variant.items():
                entity_results = [r for r in results if r.entity_id == entity_id]
                if entity_results:
                    # Take the best score for this entity in this variant
                    best_score = max(r.final_score for r in entity_results)
                    entity_scores.append((variant, best_score))
            
            # Entity should appear in most variations (allowing for some noise)
            appearance_rate = len(entity_scores) / len(case_variants)
            assert appearance_rate >= 0.8, (
                f"Case stability violated: entity '{entity_id}' appears in only "
                f"{len(entity_scores)}/{len(case_variants)} case variations "
                f"for base_query='{base_query}'"
            )
    
    @pytest.mark.asyncio
    @given(
        base_query=search_queries(),
        config=search_configs(),
        entity_type=st.sampled_from(["person", "org"])
    )
    @settings(max_examples=30, deadline=5000)
    async def test_diacritic_stability_invariant(self, search_tester, base_query, config, entity_type):
        """
        INVARIANT: AC search results are stable across diacritic variations.
        
        This test ensures that diacritic variations of the same query produce
        consistent AC search results through normalization.
        """
        assume(len(base_query.strip()) > 0)
        
        # Generate diacritic variations
        diacritic_variants = [
            base_query,
            base_query.replace('а', 'а').replace('е', 'ё'),
            base_query.replace('и', 'і').replace('е', 'є'),
            base_query.replace('о', 'о').replace('у', 'у'),
        ]
        
        # Remove duplicates
        diacritic_variants = list(set(diacritic_variants))
        
        if len(diacritic_variants) < 2:
            return  # Not enough variations to test
        
        # Perform searches for each variation
        results_by_variant = {}
        for variant in diacritic_variants:
            results = await search_tester.hybrid_search(variant, config, entity_type)
            # Filter for AC results only
            ac_results = [r for r in results if r.search_type in [SearchType.EXACT, SearchType.PHRASE, SearchType.NGRAM]]
            results_by_variant[variant] = ac_results
        
        # Check stability: same entities should be found across variations
        all_entity_ids = set()
        for results in results_by_variant.values():
            all_entity_ids.update(r.entity_id for r in results)
        
        if not all_entity_ids:
            return  # No results to compare
        
        # For each entity found, check it appears consistently
        for entity_id in all_entity_ids:
            entity_scores = []
            for variant, results in results_by_variant.items():
                entity_results = [r for r in results if r.entity_id == entity_id]
                if entity_results:
                    # Take the best score for this entity in this variant
                    best_score = max(r.final_score for r in entity_results)
                    entity_scores.append((variant, best_score))
            
            # Entity should appear in most variations (allowing for some noise)
            appearance_rate = len(entity_scores) / len(diacritic_variants)
            assert appearance_rate >= 0.8, (
                f"Diacritic stability violated: entity '{entity_id}' appears in only "
                f"{len(entity_scores)}/{len(diacritic_variants)} diacritic variations "
                f"for base_query='{base_query}'"
            )
    
    @pytest.mark.asyncio
    @given(
        queries=lists(search_queries(), min_size=2, max_size=5),
        config=search_configs(),
        entity_type=st.sampled_from(["person", "org"])
    )
    @settings(max_examples=20, deadline=10000)
    async def test_no_cross_contamination_invariant(self, search_tester, queries, config, entity_type):
        """
        INVARIANT: Disabling AC with threshold should not cause kNN to "overwrite" 
        explicit exact hits from other queries (no cross-contamination).
        
        This test ensures that search results are isolated between different queries
        and that disabling one component doesn't affect others.
        """
        assume(len(queries) >= 2)
        assume(all(len(q.strip()) > 0 for q in queries))
        
        # Create config with AC disabled (very high threshold)
        disabled_ac_config = SearchConfig(
            exact_threshold=999.0,  # Effectively disables AC
            phrase_threshold=999.0,
            ngram_threshold=999.0,
            vector_threshold=config.vector_threshold,
            fusion_weights=config.fusion_weights
        )
        
        # Perform searches with both normal and disabled AC configs
        normal_results = {}
        disabled_ac_results = {}
        
        for query in queries:
            normal_results[query] = await search_tester.hybrid_search(query, config, entity_type)
            disabled_ac_results[query] = await search_tester.hybrid_search(query, disabled_ac_config, entity_type)
        
        # Check that exact matches from normal config are not "overwritten" by disabled AC config
        for query in queries:
            normal_exact = [r for r in normal_results[query] if r.search_type == SearchType.EXACT]
            disabled_exact = [r for r in disabled_ac_results[query] if r.search_type == SearchType.EXACT]
            
            # Normal config should have more or equal exact matches
            assert len(normal_exact) >= len(disabled_exact), (
                f"Cross-contamination detected: normal config has {len(normal_exact)} exact matches, "
                f"disabled AC config has {len(disabled_exact)} exact matches for query='{query}'"
            )
            
            # Check that exact matches from normal config are preserved in disabled AC config
            normal_exact_ids = {r.entity_id for r in normal_exact}
            disabled_exact_ids = {r.entity_id for r in disabled_exact}
            
            # All exact matches from normal config should be present in disabled AC config
            missing_exact = normal_exact_ids - disabled_exact_ids
            assert len(missing_exact) == 0, (
                f"Exact matches lost when AC disabled: {missing_exact} "
                f"for query='{query}'"
            )
    
    @pytest.mark.asyncio
    @given(
        query=search_queries(),
        config=search_configs(),
        entity_type=st.sampled_from(["person", "org"])
    )
    @settings(max_examples=50, deadline=5000)
    async def test_score_monotonicity_invariant(self, search_tester, query, config, entity_type):
        """
        INVARIANT: Search scores should be monotonically decreasing for ranked results.
        
        This test ensures that search results are properly ranked by score.
        """
        assume(len(query.strip()) > 0)
        
        # Perform hybrid search
        results = await search_tester.hybrid_search(query, config, entity_type)
        
        if len(results) < 2:
            return  # Not enough results to check monotonicity
        
        # Check that scores are monotonically decreasing
        scores = [r.final_score for r in results]
        
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], (
                f"Score monotonicity violated: score[{i}]={scores[i]} < score[{i+1}]={scores[i+1]} "
                f"for query='{query}'"
            )
    
    @pytest.mark.asyncio
    @given(
        query=search_queries(),
        config=search_configs(),
        entity_type=st.sampled_from(["person", "org"])
    )
    @settings(max_examples=50, deadline=5000)
    async def test_result_consistency_invariant(self, search_tester, query, config, entity_type):
        """
        INVARIANT: Multiple searches with the same query should return consistent results.
        
        This test ensures that search results are deterministic and reproducible.
        """
        assume(len(query.strip()) > 0)
        
        # Perform multiple searches with the same query
        results1 = await search_tester.hybrid_search(query, config, entity_type)
        results2 = await search_tester.hybrid_search(query, config, entity_type)
        
        # Results should be identical
        assert len(results1) == len(results2), (
            f"Result count inconsistency: {len(results1)} vs {len(results2)} "
            f"for query='{query}'"
        )
        
        for i, (r1, r2) in enumerate(zip(results1, results2)):
            assert r1.entity_id == r2.entity_id, (
                f"Entity ID mismatch at position {i}: '{r1.entity_id}' vs '{r2.entity_id}' "
                f"for query='{query}'"
            )
            
            assert abs(r1.final_score - r2.final_score) < 1e-6, (
                f"Score mismatch at position {i}: {r1.final_score} vs {r2.final_score} "
                f"for query='{query}'"
            )
    
    @pytest.mark.asyncio
    @given(
        query=search_queries(),
        config=search_configs(),
        entity_type=st.sampled_from(["person", "org"])
    )
    @settings(max_examples=30, deadline=5000)
    async def test_threshold_filtering_invariant(self, search_tester, query, config, entity_type):
        """
        INVARIANT: Results should respect configured thresholds.
        
        This test ensures that only results above the configured thresholds are returned.
        """
        assume(len(query.strip()) > 0)
        
        # Perform hybrid search
        results = await search_tester.hybrid_search(query, config, entity_type)
        
        if not results:
            return  # No results to check
        
        # Check that all results meet their respective thresholds
        for result in results:
            if result.search_type == SearchType.EXACT:
                assert result.ac_score >= config.exact_threshold, (
                    f"Exact result below threshold: {result.ac_score} < {config.exact_threshold} "
                    f"for entity_id='{result.entity_id}'"
                )
            elif result.search_type == SearchType.PHRASE:
                assert result.ac_score >= config.phrase_threshold, (
                    f"Phrase result below threshold: {result.ac_score} < {config.phrase_threshold} "
                    f"for entity_id='{result.entity_id}'"
                )
            elif result.search_type == SearchType.NGRAM:
                assert result.ac_score >= config.ngram_threshold, (
                    f"Ngram result below threshold: {result.ac_score} < {config.ngram_threshold} "
                    f"for entity_id='{result.entity_id}'"
                )
            elif result.search_type == SearchType.VECTOR:
                assert result.vector_score >= config.vector_threshold, (
                    f"Vector result below threshold: {result.vector_score} < {config.vector_threshold} "
                    f"for entity_id='{result.entity_id}'"
                )
            elif result.search_type == SearchType.FUSION:
                # Fusion results should meet the higher of AC or Vector thresholds
                ac_threshold = max(config.exact_threshold, config.phrase_threshold, config.ngram_threshold)
                vector_threshold = config.vector_threshold
                min_threshold = min(ac_threshold, vector_threshold)
                
                assert result.final_score >= min_threshold, (
                    f"Fusion result below threshold: {result.final_score} < {min_threshold} "
                    f"for entity_id='{result.entity_id}'"
                )


# Additional utility tests
class TestSearchUtilities:
    """Utility tests for search system components"""
    
    @pytest.mark.asyncio
    @given(
        text_input=st.text(min_size=1, max_size=100),
        case_variation=st.sampled_from(["lower", "upper", "title", "swapcase", "capitalize"])
    )
    @settings(max_examples=20, deadline=1000)
    async def test_text_normalization_consistency(self, text_input, case_variation):
        """
        Test that text normalization is consistent across case variations.
        """
        tester = HybridSearchTester()
        
        try:
            # Apply case variation
            if case_variation == "lower":
                varied_text = text_input.lower()
            elif case_variation == "upper":
                varied_text = text_input.upper()
            elif case_variation == "title":
                varied_text = text_input.title()
            elif case_variation == "swapcase":
                varied_text = text_input.swapcase()
            elif case_variation == "capitalize":
                varied_text = text_input.capitalize()
            
            # Normalize both versions
            normalized_original = await tester.normalize_text(text_input)
            normalized_varied = await tester.normalize_text(varied_text)
            
            # They should be identical
            assert normalized_original == normalized_varied, (
                f"Normalization inconsistency: '{normalized_original}' vs '{normalized_varied}' "
                f"for input='{text_input}', variation='{case_variation}'"
            )
            
        finally:
            await tester.cleanup()
    
    @pytest.mark.asyncio
    @given(
        config1=search_configs(),
        config2=search_configs()
    )
    @settings(max_examples=10, deadline=1000)
    async def test_config_equality(self, config1, config2):
        """
        Test that SearchConfig objects can be compared for equality.
        """
        # Test equality
        if (config1.exact_threshold == config2.exact_threshold and
            config1.phrase_threshold == config2.phrase_threshold and
            config1.ngram_threshold == config2.ngram_threshold and
            config1.vector_threshold == config2.vector_threshold and
            config1.fusion_weights == config2.fusion_weights):
            assert config1 == config2
        else:
            assert config1 != config2


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])

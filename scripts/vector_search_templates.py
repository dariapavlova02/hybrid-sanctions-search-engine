#!/usr/bin/env python3
"""
Vector Search Templates for Elasticsearch

Provides kNN search templates and fusion formulas for combining AC and Vector results.
Includes ranking algorithms and candidate selection logic.
"""

import json
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class SearchType(str, Enum):
    """Search result types"""
    AC = "ac"
    VECTOR = "vector"
    FUSION = "fusion"


@dataclass
class VectorHit:
    """Vector search hit from Elasticsearch"""
    entity_id: str
    entity_type: str
    normalized_name: str
    aliases: List[str]
    country: str
    dob: Optional[str]
    meta: Dict[str, Any]
    vector_score: float
    matched_field: str = "name_vector"


@dataclass
class ACHit:
    """AC search hit from Elasticsearch"""
    entity_id: str
    entity_type: str
    normalized_name: str
    aliases: List[str]
    country: str
    dob: Optional[str]
    meta: Dict[str, Any]
    ac_score: float
    ac_type: str  # exact, phrase, ngram, weak
    matched_field: str


@dataclass
class Candidate:
    """Final candidate with fusion score"""
    entity_id: str
    entity_type: str
    normalized_name: str
    aliases: List[str]
    country: str
    dob: Optional[str]
    meta: Dict[str, Any]
    final_score: float
    ac_score: float
    vector_score: float
    features: Dict[str, Any]  # DOB_match, need_context, etc.
    search_type: SearchType


class VectorSearchTemplates:
    """Vector search query templates for Elasticsearch"""
    
    def __init__(self, 
                 min_semantic_similarity: float = 0.7,
                 k: int = 50,
                 fusion_weights: Dict[str, float] = None):
        """
        Initialize vector search templates
        
        Args:
            min_semantic_similarity: Minimum semantic similarity threshold
            k: Number of kNN results to retrieve
            fusion_weights: Weights for fusion formula
        """
        self.min_semantic_similarity = min_semantic_similarity
        self.k = k
        
        # Fusion formula weights
        self.fusion_weights = fusion_weights or {
            "ac_weight": 0.55,
            "vector_weight": 0.45,
            "dob_bonus": 0.05,
            "context_penalty": 0.1
        }
    
    def create_knn_query(self, 
                        query_vector: List[float],
                        entity_type: str,
                        country_filter: Optional[str] = None,
                        additional_filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create kNN query for dense_vector with filters
        
        Args:
            query_vector: 384-dimensional query vector
            entity_type: Entity type filter (person/org)
            country_filter: Optional country filter
            additional_filters: Additional filters (e.g., meta fields)
            
        Returns:
            Elasticsearch kNN query DSL
        """
        # Base kNN query
        knn_query = {
            "knn": {
                "field": "name_vector",
                "query_vector": query_vector,
                "k": self.k,
                "num_candidates": self.k * 2,  # Retrieve more candidates for filtering
                "similarity": "cosine"
            },
            "size": self.k,
            "_source": [
                "entity_id", "entity_type", "normalized_name", "aliases", 
                "country", "dob", "meta"
            ]
        }
        
        # Add filters
        filters = []
        
        # Entity type filter
        filters.append({
            "term": {
                "entity_type": entity_type
            }
        })
        
        # Country filter
        if country_filter:
            filters.append({
                "term": {
                    "country": country_filter
                }
            })
        
        # Additional filters
        if additional_filters:
            for field, value in additional_filters.items():
                if isinstance(value, list):
                    filters.append({
                        "terms": {
                            field: value
                        }
                    })
                else:
                    filters.append({
                        "term": {
                            field: value
                        }
                    })
        
        # Apply filters
        if filters:
            knn_query["knn"]["filter"] = {
                "bool": {
                    "must": filters
                }
            }
        
        return knn_query
    
    def create_filtered_knn_query(self,
                                 query_vector: List[float],
                                 entity_type: str,
                                 country_filter: Optional[str] = None,
                                 meta_filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create kNN query with post-filtering for better performance
        
        Args:
            query_vector: 384-dimensional query vector
            entity_type: Entity type filter
            country_filter: Optional country filter
            meta_filters: Meta field filters
            
        Returns:
            Elasticsearch kNN query with post-filtering
        """
        # Build post-filter
        post_filter = {
            "bool": {
                "must": [
                    {"term": {"entity_type": entity_type}}
                ]
            }
        }
        
        if country_filter:
            post_filter["bool"]["must"].append({
                "term": {"country": country_filter}
            })
        
        if meta_filters:
            for field, value in meta_filters.items():
                if isinstance(value, list):
                    post_filter["bool"]["must"].append({
                        "terms": {f"meta.{field}": value}
                    })
                else:
                    post_filter["bool"]["must"].append({
                        "term": {f"meta.{field}": value}
                    })
        
        return {
            "knn": {
                "field": "name_vector",
                "query_vector": query_vector,
                "k": self.k,
                "num_candidates": self.k * 3,  # More candidates for post-filtering
                "similarity": "cosine"
            },
            "post_filter": post_filter,
            "size": self.k,
            "_source": [
                "entity_id", "entity_type", "normalized_name", "aliases", 
                "country", "dob", "meta"
            ]
        }
    
    def parse_vector_hits(self, response: Dict[str, Any]) -> List[VectorHit]:
        """
        Parse vector search response into VectorHit objects
        
        Args:
            response: Elasticsearch search response
            
        Returns:
            List of VectorHit objects
        """
        hits = response.get("hits", {}).get("hits", [])
        vector_hits = []
        
        for hit in hits:
            source = hit.get("_source", {})
            score = hit.get("_score", 0.0)
            
            # Filter by semantic similarity threshold
            if score < self.min_semantic_similarity:
                continue
            
            vector_hit = VectorHit(
                entity_id=source.get("entity_id", ""),
                entity_type=source.get("entity_type", ""),
                normalized_name=source.get("normalized_name", ""),
                aliases=source.get("aliases", []),
                country=source.get("country", ""),
                dob=source.get("dob"),
                meta=source.get("meta", {}),
                vector_score=score,
                matched_field="name_vector"
            )
            
            vector_hits.append(vector_hit)
        
        return vector_hits
    
    def parse_ac_hits(self, response: Dict[str, Any], ac_type: str) -> List[ACHit]:
        """
        Parse AC search response into ACHit objects
        
        Args:
            response: Elasticsearch search response
            ac_type: AC search type (exact, phrase, ngram, weak)
            
        Returns:
            List of ACHit objects
        """
        hits = response.get("hits", {}).get("hits", [])
        ac_hits = []
        
        for hit in hits:
            source = hit.get("_source", {})
            score = hit.get("_score", 0.0)
            
            ac_hit = ACHit(
                entity_id=source.get("entity_id", ""),
                entity_type=source.get("entity_type", ""),
                normalized_name=source.get("normalized_name", ""),
                aliases=source.get("aliases", []),
                country=source.get("country", ""),
                dob=source.get("dob"),
                meta=source.get("meta", {}),
                ac_score=score,
                ac_type=ac_type,
                matched_field=self._get_matched_field(ac_type)
            )
            
            ac_hits.append(ac_hit)
        
        return ac_hits
    
    def _get_matched_field(self, ac_type: str) -> str:
        """Get matched field name for AC type"""
        field_mapping = {
            "exact": "normalized_name",
            "phrase": "name_text.shingle",
            "ngram": "name_ngrams",
            "weak": "name_ngrams"
        }
        return field_mapping.get(ac_type, "unknown")
    
    def calculate_fusion_score(self, 
                              ac_score: float, 
                              vector_score: float, 
                              features: Dict[str, Any]) -> float:
        """
        Calculate fusion score using the formula:
        final = 0.55*ac_score + 0.45*vec_sim + bonus(DOB_match +0.05) - penalty(need_context -0.1)
        
        Args:
            ac_score: AC search score
            vector_score: Vector similarity score
            features: Additional features (DOB_match, need_context, etc.)
            
        Returns:
            Fusion score
        """
        # Base fusion score
        fusion_score = (
            self.fusion_weights["ac_weight"] * ac_score +
            self.fusion_weights["vector_weight"] * vector_score
        )
        
        # DOB match bonus
        dob_match = features.get("DOB_match", False)
        if dob_match:
            fusion_score += self.fusion_weights["dob_bonus"]
        
        # Context penalty
        need_context = features.get("need_context", False)
        if need_context:
            fusion_score -= self.fusion_weights["context_penalty"]
        
        return max(0.0, fusion_score)  # Ensure non-negative score
    
    def extract_features(self, 
                        ac_hit: Optional[ACHit], 
                        vector_hit: Optional[VectorHit],
                        query_dob: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract features for fusion scoring
        
        Args:
            ac_hit: AC search hit (optional)
            vector_hit: Vector search hit (optional)
            query_dob: Query DOB for matching (optional)
            
        Returns:
            Dictionary of features
        """
        features = {}
        
        # DOB match feature
        if query_dob and ac_hit and ac_hit.dob:
            features["DOB_match"] = (query_dob == ac_hit.dob)
        elif query_dob and vector_hit and vector_hit.dob:
            features["DOB_match"] = (query_dob == vector_hit.dob)
        else:
            features["DOB_match"] = False
        
        # Context need feature (simplified heuristic)
        if ac_hit and vector_hit:
            # If both AC and vector found the same entity, context might be needed
            features["need_context"] = (ac_hit.entity_id == vector_hit.entity_id)
        else:
            features["need_context"] = False
        
        # Additional features can be added here
        features["has_aliases"] = bool((ac_hit and ac_hit.aliases) or (vector_hit and vector_hit.aliases))
        features["has_meta"] = bool((ac_hit and ac_hit.meta) or (vector_hit and vector_hit.meta))
        
        return features
    
    def fuse_results(self, 
                    ac_hits: List[ACHit], 
                    vector_hits: List[VectorHit],
                    query_dob: Optional[str] = None) -> List[Candidate]:
        """
        Fuse AC and Vector results into final candidates
        
        Args:
            ac_hits: List of AC search hits
            vector_hits: List of Vector search hits
            query_dob: Query DOB for matching (optional)
            
        Returns:
            List of fused Candidate objects
        """
        # Create entity lookup maps
        ac_map = {hit.entity_id: hit for hit in ac_hits}
        vector_map = {hit.entity_id: hit for hit in vector_hits}
        
        # Get all unique entity IDs
        all_entity_ids = set(ac_map.keys()) | set(vector_map.keys())
        
        candidates = []
        
        for entity_id in all_entity_ids:
            ac_hit = ac_map.get(entity_id)
            vector_hit = vector_map.get(entity_id)
            
            # Extract features
            features = self.extract_features(ac_hit, vector_hit, query_dob)
            
            # Calculate fusion score
            ac_score = ac_hit.ac_score if ac_hit else 0.0
            vector_score = vector_hit.vector_score if vector_hit else 0.0
            fusion_score = self.calculate_fusion_score(ac_score, vector_score, features)
            
            # Use the hit with more complete information
            primary_hit = ac_hit if ac_hit else vector_hit
            
            if not primary_hit:
                continue
            
            # Determine search type
            if ac_hit and vector_hit:
                search_type = SearchType.FUSION
            elif ac_hit:
                search_type = SearchType.AC
            else:
                search_type = SearchType.VECTOR
            
            candidate = Candidate(
                entity_id=primary_hit.entity_id,
                entity_type=primary_hit.entity_type,
                normalized_name=primary_hit.normalized_name,
                aliases=primary_hit.aliases,
                country=primary_hit.country,
                dob=primary_hit.dob,
                meta=primary_hit.meta,
                final_score=fusion_score,
                ac_score=ac_score,
                vector_score=vector_score,
                features=features,
                search_type=search_type
            )
            
            candidates.append(candidate)
        
        return candidates
    
    def rank_and_select_top_n(self, 
                             candidates: List[Candidate], 
                             top_n: int = 10) -> List[Candidate]:
        """
        Rank candidates and select top N
        
        Args:
            candidates: List of candidates to rank
            top_n: Number of top candidates to return
            
        Returns:
            Top N ranked candidates
        """
        # Sort by final score (descending)
        ranked_candidates = sorted(candidates, key=lambda c: c.final_score, reverse=True)
        
        # Select top N
        return ranked_candidates[:top_n]
    
    def create_hybrid_search_query(self,
                                  query_vector: List[float],
                                  ac_queries: List[Dict[str, Any]],
                                  entity_type: str,
                                  country_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Create hybrid search query combining AC and Vector search
        
        Args:
            query_vector: 384-dimensional query vector
            ac_queries: List of AC search queries
            entity_type: Entity type filter
            country_filter: Optional country filter
            
        Returns:
            List of multi-search requests
        """
        requests = []
        
        # Add AC queries
        for ac_query in ac_queries:
            requests.append({
                "index": f"watchlist_{entity_type}s_current",
                "search_type": "query_then_fetch"
            })
            requests.append(ac_query)
        
        # Add Vector query
        requests.append({
            "index": f"watchlist_{entity_type}s_current",
            "search_type": "query_then_fetch"
        })
        requests.append(self.create_knn_query(query_vector, entity_type, country_filter))
        
        return requests


def create_sample_queries():
    """Create sample queries for testing"""
    templates = VectorSearchTemplates()
    
    # Sample query vector (384 dimensions)
    query_vector = [0.1] * 384
    
    print("=== Vector Search Templates ===\n")
    
    # 1. Basic kNN query
    print("1. BASIC kNN QUERY:")
    knn_query = templates.create_knn_query(query_vector, "person")
    print(json.dumps(knn_query, indent=2))
    print()
    
    # 2. Filtered kNN query
    print("2. FILTERED kNN QUERY:")
    filtered_query = templates.create_filtered_knn_query(
        query_vector, "person", country_filter="RU"
    )
    print(json.dumps(filtered_query, indent=2))
    print()
    
    # 3. Fusion example
    print("3. FUSION EXAMPLE:")
    
    # Sample AC hit
    ac_hit = ACHit(
        entity_id="person_001",
        entity_type="person",
        normalized_name="иван петров",
        aliases=["и. петров"],
        country="RU",
        dob="1980-05-15",
        meta={"source": "sanctions"},
        ac_score=2.0,
        ac_type="exact",
        matched_field="normalized_name"
    )
    
    # Sample Vector hit
    vector_hit = VectorHit(
        entity_id="person_001",
        entity_type="person",
        normalized_name="иван петров",
        aliases=["и. петров"],
        country="RU",
        dob="1980-05-15",
        meta={"source": "sanctions"},
        vector_score=0.85,
        matched_field="name_vector"
    )
    
    # Fuse results
    candidates = templates.fuse_results([ac_hit], [vector_hit], "1980-05-15")
    
    print("AC Hit:", ac_hit.ac_score, ac_hit.ac_type)
    print("Vector Hit:", vector_hit.vector_score)
    print("Fusion Score:", candidates[0].final_score)
    print("Features:", candidates[0].features)
    print()
    
    # 4. Ranking example
    print("4. RANKING EXAMPLE:")
    
    # Create multiple candidates
    candidates = [
        Candidate(
            entity_id="person_001",
            entity_type="person",
            normalized_name="иван петров",
            aliases=[],
            country="RU",
            dob="1980-05-15",
            meta={},
            final_score=1.2,
            ac_score=2.0,
            vector_score=0.8,
            features={"DOB_match": True, "need_context": False},
            search_type=SearchType.FUSION
        ),
        Candidate(
            entity_id="person_002",
            entity_type="person",
            normalized_name="мария сидорова",
            aliases=[],
            country="RU",
            dob="1975-12-03",
            meta={},
            final_score=0.9,
            ac_score=1.5,
            vector_score=0.7,
            features={"DOB_match": False, "need_context": True},
            search_type=SearchType.AC
        ),
        Candidate(
            entity_id="person_003",
            entity_type="person",
            normalized_name="алексей козлов",
            aliases=[],
            country="RU",
            dob=None,
            meta={},
            final_score=0.6,
            ac_score=0.0,
            vector_score=0.6,
            features={"DOB_match": False, "need_context": False},
            search_type=SearchType.VECTOR
        )
    ]
    
    # Rank and select top 2
    top_candidates = templates.rank_and_select_top_n(candidates, top_n=2)
    
    print("Top 2 Candidates:")
    for i, candidate in enumerate(top_candidates, 1):
        print(f"{i}. {candidate.normalized_name} - Score: {candidate.final_score:.2f}")
        print(f"   AC: {candidate.ac_score:.2f}, Vector: {candidate.vector_score:.2f}")
        print(f"   Features: {candidate.features}")
        print()


if __name__ == "__main__":
    create_sample_queries()

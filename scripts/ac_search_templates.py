#!/usr/bin/env python3
"""
AC Search Templates for Elasticsearch

Provides DSL query templates for AC (Aho-Corasick) search stage with multiple
search patterns in order of decreasing strictness:
1. Exact: terms on normalized_name/aliases (case-insensitive)
2. Phrase: match_phrase on name_text (slop=0..1)
3. Char-ngram: match on name_ngrams (operator=AND, minimum_should_match=100%)

Includes multi-search templates with thresholds and "weak signal" detection.
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ACSearchType(str, Enum):
    """AC search result types"""
    EXACT = "exact"
    PHRASE = "phrase"
    NGRAM = "ngram"
    WEAK = "weak"


@dataclass
class ACScore:
    """AC search score result"""
    type: ACSearchType
    score: float
    matched_field: str
    matched_text: str
    entity_id: str
    entity_type: str


class ACSearchTemplates:
    """AC search query templates for Elasticsearch"""
    
    def __init__(self, 
                 exact_threshold: float = 1.0,
                 phrase_threshold: float = 0.8,
                 ngram_threshold: float = 0.6,
                 weak_threshold: float = 0.4):
        """
        Initialize AC search templates
        
        Args:
            exact_threshold: Minimum score for exact matches
            phrase_threshold: Minimum score for phrase matches
            ngram_threshold: Minimum score for ngram matches
            weak_threshold: Minimum score for weak signals
        """
        self.exact_threshold = exact_threshold
        self.phrase_threshold = phrase_threshold
        self.ngram_threshold = ngram_threshold
        self.weak_threshold = weak_threshold
    
    def create_exact_query(self, search_terms: List[str], entity_type: str) -> Dict[str, Any]:
        """
        Create exact match query using terms on normalized_name/aliases
        
        Args:
            search_terms: List of normalized search terms
            entity_type: Entity type (person/org)
            
        Returns:
            Elasticsearch query DSL
        """
        return {
            "query": {
                "bool": {
                    "must": [
                        {
                            "term": {
                                "entity_type": entity_type
                            }
                        },
                        {
                            "bool": {
                                "should": [
                                    {
                                        "terms": {
                                            "normalized_name": search_terms,
                                            "boost": 2.0
                                        }
                                    },
                                    {
                                        "terms": {
                                            "aliases": search_terms,
                                            "boost": 1.5
                                        }
                                    }
                                ],
                                "minimum_should_match": 1
                            }
                        }
                    ]
                }
            },
            "size": 50,
            "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "meta"]
        }
    
    def create_phrase_query(self, search_terms: List[str], entity_type: str, slop: int = 1) -> Dict[str, Any]:
        """
        Create phrase match query on name_text with shingles
        
        Args:
            search_terms: List of search terms
            entity_type: Entity type (person/org)
            slop: Maximum word distance for phrase matching
            
        Returns:
            Elasticsearch query DSL
        """
        # Join terms for phrase search
        phrase_text = " ".join(search_terms)
        
        return {
            "query": {
                "bool": {
                    "must": [
                        {
                            "term": {
                                "entity_type": entity_type
                            }
                        },
                        {
                            "match_phrase": {
                                "name_text.shingle": {
                                    "query": phrase_text,
                                    "slop": slop,
                                    "boost": 1.8
                                }
                            }
                        }
                    ]
                }
            },
            "size": 50,
            "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "meta"]
        }
    
    def create_ngram_query(self, search_terms: List[str], entity_type: str) -> Dict[str, Any]:
        """
        Create ngram match query with AND operator and 100% minimum_should_match
        
        Args:
            search_terms: List of search terms
            entity_type: Entity type (person/org)
            
        Returns:
            Elasticsearch query DSL
        """
        # Join terms for ngram search
        ngram_text = " ".join(search_terms)
        
        return {
            "query": {
                "bool": {
                    "must": [
                        {
                            "term": {
                                "entity_type": entity_type
                            }
                        },
                        {
                            "match": {
                                "name_ngrams": {
                                    "query": ngram_text,
                                    "operator": "AND",
                                    "minimum_should_match": "100%",
                                    "boost": 1.0
                                }
                            }
                        }
                    ]
                }
            },
            "size": 50,
            "_source": ["entity_id", "entity_type", "normalized_name", "aliases", "country", "meta"]
        }
    
    def create_multi_search_template(self, 
                                   search_terms: List[str], 
                                   entity_type: str,
                                   include_exact: bool = True,
                                   include_phrase: bool = True,
                                   include_ngram: bool = True) -> List[Dict[str, Any]]:
        """
        Create multi-search template with all query types
        
        Args:
            search_terms: List of search terms
            entity_type: Entity type (person/org)
            include_exact: Include exact match query
            include_phrase: Include phrase match query
            include_ngram: Include ngram match query
            
        Returns:
            List of multi-search requests
        """
        requests = []
        
        if include_exact:
            requests.append({
                "index": f"watchlist_{entity_type}s_current",
                "search_type": "query_then_fetch"
            })
            requests.append(self.create_exact_query(search_terms, entity_type))
        
        if include_phrase:
            requests.append({
                "index": f"watchlist_{entity_type}s_current",
                "search_type": "query_then_fetch"
            })
            requests.append(self.create_phrase_query(search_terms, entity_type))
        
        if include_ngram:
            requests.append({
                "index": f"watchlist_{entity_type}s_current",
                "search_type": "query_then_fetch"
            })
            requests.append(self.create_ngram_query(search_terms, entity_type))
        
        return requests
    
    def parse_ac_results(self, msearch_response: Dict[str, Any]) -> List[ACScore]:
        """
        Parse multi-search response and extract AC scores
        
        Args:
            msearch_response: Elasticsearch multi-search response
            
        Returns:
            List of ACScore objects
        """
        ac_scores = []
        
        if "responses" not in msearch_response:
            return ac_scores
        
        responses = msearch_response["responses"]
        
        # Process each response type
        for i, response in enumerate(responses):
            if "error" in response:
                continue
            
            hits = response.get("hits", {}).get("hits", [])
            search_type = self._get_search_type(i)
            
            for hit in hits:
                score = hit.get("_score", 0.0)
                source = hit.get("_source", {})
                
                # Determine if this is a valid match based on thresholds
                if self._is_valid_match(search_type, score):
                    ac_score = ACScore(
                        type=search_type,
                        score=score,
                        matched_field=self._get_matched_field(hit),
                        matched_text=self._get_matched_text(source, search_type),
                        entity_id=source.get("entity_id", ""),
                        entity_type=source.get("entity_type", "")
                    )
                    ac_scores.append(ac_score)
        
        return ac_scores
    
    def _get_search_type(self, response_index: int) -> ACSearchType:
        """Get search type based on response index"""
        if response_index == 0:
            return ACSearchType.EXACT
        elif response_index == 1:
            return ACSearchType.PHRASE
        elif response_index == 2:
            return ACSearchType.NGRAM
        else:
            return ACSearchType.WEAK
    
    def _is_valid_match(self, search_type: ACSearchType, score: float) -> bool:
        """Check if match meets threshold requirements"""
        if search_type == ACSearchType.EXACT:
            return score >= self.exact_threshold
        elif search_type == ACSearchType.PHRASE:
            return score >= self.phrase_threshold
        elif search_type == ACSearchType.NGRAM:
            return score >= self.ngram_threshold
        else:
            return score >= self.weak_threshold
    
    def _get_matched_field(self, hit: Dict[str, Any]) -> str:
        """Extract matched field from hit"""
        # This would need to be implemented based on actual hit structure
        # For now, return a placeholder
        return "normalized_name"
    
    def _get_matched_text(self, source: Dict[str, Any], search_type: ACSearchType) -> str:
        """Extract matched text from source"""
        if search_type == ACSearchType.EXACT:
            return source.get("normalized_name", "")
        else:
            return source.get("normalized_name", "")
    
    def find_best_hit(self, ac_scores: List[ACScore]) -> Optional[ACScore]:
        """
        Find the best hit from AC scores
        
        Args:
            ac_scores: List of AC scores
            
        Returns:
            Best AC score or None
        """
        if not ac_scores:
            return None
        
        # Sort by type priority (exact > phrase > ngram > weak) then by score
        type_priority = {
            ACSearchType.EXACT: 4,
            ACSearchType.PHRASE: 3,
            ACSearchType.NGRAM: 2,
            ACSearchType.WEAK: 1
        }
        
        def sort_key(score: ACScore) -> Tuple[int, float]:
            return (type_priority.get(score.type, 0), score.score)
        
        return max(ac_scores, key=sort_key)
    
    def detect_weak_signal(self, ac_scores: List[ACScore]) -> bool:
        """
        Detect if there's only weak signal (no exact/phrase, but ngram with score >= T_ng)
        
        Args:
            ac_scores: List of AC scores
            
        Returns:
            True if weak signal detected
        """
        has_exact = any(score.type == ACSearchType.EXACT for score in ac_scores)
        has_phrase = any(score.type == ACSearchType.PHRASE for score in ac_scores)
        has_strong_ngram = any(
            score.type == ACSearchType.NGRAM and score.score >= self.ngram_threshold 
            for score in ac_scores
        )
        
        return not (has_exact or has_phrase) and has_strong_ngram
    
    def create_parameterized_queries(self, 
                                   candidate_strings: List[str], 
                                   entity_type: str) -> Dict[str, Any]:
        """
        Create parameterized queries for multiple candidate strings
        
        Args:
            candidate_strings: List of candidate search strings
            entity_type: Entity type (person/org)
            
        Returns:
            Dictionary with query templates and parameters
        """
        queries = {}
        
        for i, candidate in enumerate(candidate_strings):
            # Normalize candidate string (this would use actual normalization)
            normalized_terms = candidate.lower().split()
            
            queries[f"candidate_{i}"] = {
                "search_terms": normalized_terms,
                "original_text": candidate,
                "exact_query": self.create_exact_query(normalized_terms, entity_type),
                "phrase_query": self.create_phrase_query(normalized_terms, entity_type),
                "ngram_query": self.create_ngram_query(normalized_terms, entity_type),
                "multi_search": self.create_multi_search_template(normalized_terms, entity_type)
            }
        
        return queries


def create_sample_queries():
    """Create sample queries for testing"""
    templates = ACSearchTemplates()
    
    # Sample search terms
    search_terms = ["иван", "петров"]
    entity_type = "person"
    
    print("=== AC Search Templates ===\n")
    
    # 1. Exact query
    print("1. EXACT QUERY:")
    exact_query = templates.create_exact_query(search_terms, entity_type)
    print(json.dumps(exact_query, indent=2, ensure_ascii=False))
    print()
    
    # 2. Phrase query
    print("2. PHRASE QUERY:")
    phrase_query = templates.create_phrase_query(search_terms, entity_type)
    print(json.dumps(phrase_query, indent=2, ensure_ascii=False))
    print()
    
    # 3. Ngram query
    print("3. NGRAM QUERY:")
    ngram_query = templates.create_ngram_query(search_terms, entity_type)
    print(json.dumps(ngram_query, indent=2, ensure_ascii=False))
    print()
    
    # 4. Multi-search template
    print("4. MULTI-SEARCH TEMPLATE:")
    multi_search = templates.create_multi_search_template(search_terms, entity_type)
    print(json.dumps(multi_search, indent=2, ensure_ascii=False))
    print()
    
    # 5. Sample response parsing
    print("5. SAMPLE RESPONSE PARSING:")
    sample_response = {
        "responses": [
            {
                "hits": {
                    "total": {"value": 1},
                    "hits": [
                        {
                            "_score": 2.0,
                            "_source": {
                                "entity_id": "person_001",
                                "entity_type": "person",
                                "normalized_name": "иван петров",
                                "aliases": ["и. петров"],
                                "country": "RU"
                            }
                        }
                    ]
                }
            },
            {
                "hits": {
                    "total": {"value": 0},
                    "hits": []
                }
            },
            {
                "hits": {
                    "total": {"value": 1},
                    "hits": [
                        {
                            "_score": 0.8,
                            "_source": {
                                "entity_id": "person_002",
                                "entity_type": "person",
                                "normalized_name": "иван петрович",
                                "aliases": [],
                                "country": "RU"
                            }
                        }
                    ]
                }
            }
        ]
    }
    
    ac_scores = templates.parse_ac_results(sample_response)
    print("AC Scores:")
    for score in ac_scores:
        print(f"  {score.type.value}: {score.score:.2f} - {score.matched_text} ({score.entity_id})")
    
    best_hit = templates.find_best_hit(ac_scores)
    if best_hit:
        print(f"\nBest Hit: {best_hit.type.value} - {best_hit.score:.2f} - {best_hit.matched_text}")
    
    weak_signal = templates.detect_weak_signal(ac_scores)
    print(f"Weak Signal Detected: {weak_signal}")
    print()
    
    # 6. Parameterized queries
    print("6. PARAMETERIZED QUERIES:")
    candidate_strings = ["Иван Петров", "Мария Сидорова", "ООО Газпром"]
    param_queries = templates.create_parameterized_queries(candidate_strings, "person")
    print(f"Created {len(param_queries)} parameterized query sets")
    print()


if __name__ == "__main__":
    create_sample_queries()

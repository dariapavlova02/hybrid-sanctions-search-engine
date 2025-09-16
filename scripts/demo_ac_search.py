#!/usr/bin/env python3
"""
AC Search Demo Script

Demonstrates AC search functionality with Elasticsearch templates.
Shows how to use the search templates and process results.
"""

import json
import asyncio
import httpx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from ac_search_templates import ACSearchTemplates, ACScore, ACSearchType


@dataclass
class SearchResult:
    """Search result with AC score information"""
    entity_id: str
    entity_type: str
    normalized_name: str
    aliases: List[str]
    country: str
    meta: Dict[str, Any]
    ac_score: ACScore
    search_type: str


class ACSearchDemo:
    """Demo class for AC search functionality"""
    
    def __init__(self, es_url: str = "http://localhost:9200"):
        self.es_url = es_url.rstrip("/")
        self.templates = ACSearchTemplates()
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search_exact(self, search_terms: List[str], entity_type: str) -> List[SearchResult]:
        """Perform exact search"""
        print(f"🔍 Exact search: {search_terms} ({entity_type})")
        
        query = self.templates.create_exact_query(search_terms, entity_type)
        index_name = f"watchlist_{entity_type}s_current"
        
        try:
            response = await self.client.post(
                f"{self.es_url}/{index_name}/_search",
                json=query
            )
            
            if response.status_code == 200:
                return self._parse_search_response(response.json(), ACSearchType.EXACT)
            else:
                print(f"❌ Search failed: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    async def search_phrase(self, search_terms: List[str], entity_type: str, slop: int = 1) -> List[SearchResult]:
        """Perform phrase search"""
        print(f"🔍 Phrase search: {' '.join(search_terms)} ({entity_type}, slop={slop})")
        
        query = self.templates.create_phrase_query(search_terms, entity_type, slop)
        index_name = f"watchlist_{entity_type}s_current"
        
        try:
            response = await self.client.post(
                f"{self.es_url}/{index_name}/_search",
                json=query
            )
            
            if response.status_code == 200:
                return self._parse_search_response(response.json(), ACSearchType.PHRASE)
            else:
                print(f"❌ Search failed: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    async def search_ngram(self, search_terms: List[str], entity_type: str) -> List[SearchResult]:
        """Perform ngram search"""
        print(f"🔍 N-gram search: {' '.join(search_terms)} ({entity_type})")
        
        query = self.templates.create_ngram_query(search_terms, entity_type)
        index_name = f"watchlist_{entity_type}s_current"
        
        try:
            response = await self.client.post(
                f"{self.es_url}/{index_name}/_search",
                json=query
            )
            
            if response.status_code == 200:
                return self._parse_search_response(response.json(), ACSearchType.NGRAM)
            else:
                print(f"❌ Search failed: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    async def search_multi(self, search_terms: List[str], entity_type: str) -> List[SearchResult]:
        """Perform multi-search (all types)"""
        print(f"🔍 Multi-search: {search_terms} ({entity_type})")
        
        multi_search_requests = self.templates.create_multi_search_template(search_terms, entity_type)
        
        try:
            # Prepare multi-search request body
            body_lines = []
            for request in multi_search_requests:
                if "index" in request:
                    body_lines.append(json.dumps(request))
                else:
                    body_lines.append(json.dumps(request))
            
            body = "\n".join(body_lines) + "\n"
            
            response = await self.client.post(
                f"{self.es_url}/_msearch",
                content=body,
                headers={"Content-Type": "application/x-ndjson"}
            )
            
            if response.status_code == 200:
                return self._parse_multi_search_response(response.json())
            else:
                print(f"❌ Multi-search failed: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ Multi-search error: {e}")
            return []
    
    def _parse_search_response(self, response: Dict[str, Any], search_type: ACSearchType) -> List[SearchResult]:
        """Parse single search response"""
        results = []
        
        hits = response.get("hits", {}).get("hits", [])
        
        for hit in hits:
            source = hit.get("_source", {})
            score = hit.get("_score", 0.0)
            
            ac_score = ACScore(
                type=search_type,
                score=score,
                matched_field=self._get_matched_field(hit, search_type),
                matched_text=source.get("normalized_name", ""),
                entity_id=source.get("entity_id", ""),
                entity_type=source.get("entity_type", "")
            )
            
            result = SearchResult(
                entity_id=source.get("entity_id", ""),
                entity_type=source.get("entity_type", ""),
                normalized_name=source.get("normalized_name", ""),
                aliases=source.get("aliases", []),
                country=source.get("country", ""),
                meta=source.get("meta", {}),
                ac_score=ac_score,
                search_type=search_type.value
            )
            
            results.append(result)
        
        return results
    
    def _parse_multi_search_response(self, response: Dict[str, Any]) -> List[SearchResult]:
        """Parse multi-search response"""
        all_results = []
        
        responses = response.get("responses", [])
        search_types = [ACSearchType.EXACT, ACSearchType.PHRASE, ACSearchType.NGRAM]
        
        for i, sub_response in enumerate(responses):
            if "error" in sub_response:
                print(f"⚠️  Search {i} error: {sub_response['error']}")
                continue
            
            search_type = search_types[i] if i < len(search_types) else ACSearchType.WEAK
            results = self._parse_search_response(sub_response, search_type)
            all_results.extend(results)
        
        return all_results
    
    def _get_matched_field(self, hit: Dict[str, Any], search_type: ACSearchType) -> str:
        """Get matched field name"""
        if search_type == ACSearchType.EXACT:
            return "normalized_name"
        elif search_type == ACSearchType.PHRASE:
            return "name_text.shingle"
        elif search_type == ACSearchType.NGRAM:
            return "name_ngrams"
        else:
            return "unknown"
    
    def find_best_hit(self, results: List[SearchResult]) -> Optional[SearchResult]:
        """Find best hit from results"""
        if not results:
            return None
        
        # Sort by type priority (exact > phrase > ngram > weak) then by score
        type_priority = {
            ACSearchType.EXACT: 4,
            ACSearchType.PHRASE: 3,
            ACSearchType.NGRAM: 2,
            ACSearchType.WEAK: 1
        }
        
        def sort_key(result: SearchResult) -> tuple:
            return (type_priority.get(result.ac_score.type, 0), result.ac_score.score)
        
        return max(results, key=sort_key)
    
    def detect_weak_signal(self, results: List[SearchResult]) -> bool:
        """Detect weak signal in results"""
        has_exact = any(result.ac_score.type == ACSearchType.EXACT for result in results)
        has_phrase = any(result.ac_score.type == ACSearchType.PHRASE for result in results)
        has_strong_ngram = any(
            result.ac_score.type == ACSearchType.NGRAM and result.ac_score.score >= self.templates.ngram_threshold
            for result in results
        )
        
        return not (has_exact or has_phrase) and has_strong_ngram
    
    def print_results(self, results: List[SearchResult], title: str = "Search Results"):
        """Print search results"""
        print(f"\n📊 {title}")
        print("=" * 60)
        
        if not results:
            print("No results found")
            return
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.normalized_name} ({result.entity_id})")
            print(f"   Type: {result.search_type} | Score: {result.ac_score.score:.2f}")
            print(f"   Matched Field: {result.ac_score.matched_field}")
            print(f"   Country: {result.country}")
            if result.aliases:
                print(f"   Aliases: {', '.join(result.aliases)}")
            if result.meta:
                print(f"   Meta: {result.meta}")
            print()
        
        # Find and show best hit
        best_hit = self.find_best_hit(results)
        if best_hit:
            print(f"🏆 Best Hit: {best_hit.normalized_name} ({best_hit.search_type}, {best_hit.ac_score.score:.2f})")
        
        # Check for weak signal
        weak_signal = self.detect_weak_signal(results)
        if weak_signal:
            print("⚠️  Weak Signal Detected: No exact/phrase matches, but ngram with score >= T_ng")
    
    async def run_demo(self):
        """Run complete demo"""
        print("🚀 AC Search Demo")
        print("=" * 60)
        
        # Test cases
        test_cases = [
            {
                "name": "Person - Exact Match",
                "search_terms": ["иван", "петров"],
                "entity_type": "person",
                "search_type": "exact"
            },
            {
                "name": "Person - Phrase Match",
                "search_terms": ["иван", "петрович"],
                "entity_type": "person",
                "search_type": "phrase"
            },
            {
                "name": "Person - N-gram Match",
                "search_terms": ["иван"],
                "entity_type": "person",
                "search_type": "ngram"
            },
            {
                "name": "Organization - Exact Match",
                "search_terms": ["газпром"],
                "entity_type": "org",
                "search_type": "exact"
            },
            {
                "name": "Person - Multi Search",
                "search_terms": ["мария", "сидорова"],
                "entity_type": "person",
                "search_type": "multi"
            }
        ]
        
        for test_case in test_cases:
            print(f"\n🧪 {test_case['name']}")
            print("-" * 40)
            
            if test_case["search_type"] == "exact":
                results = await self.search_exact(test_case["search_terms"], test_case["entity_type"])
            elif test_case["search_type"] == "phrase":
                results = await self.search_phrase(test_case["search_terms"], test_case["entity_type"])
            elif test_case["search_type"] == "ngram":
                results = await self.search_ngram(test_case["search_terms"], test_case["entity_type"])
            elif test_case["search_type"] == "multi":
                results = await self.search_multi(test_case["search_terms"], test_case["entity_type"])
            else:
                continue
            
            self.print_results(results, test_case["name"])
        
        await self.client.aclose()
        print("\n✅ Demo completed!")


async def main():
    """Main function"""
    demo = ACSearchDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())

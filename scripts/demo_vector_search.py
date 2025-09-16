#!/usr/bin/env python3
"""
Vector Search Demo Script

Demonstrates kNN search functionality and fusion scoring.
Shows how to combine AC and Vector results into final candidates.
"""

import json
import asyncio
import httpx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from vector_search_templates import (
    VectorSearchTemplates, VectorHit, ACHit, Candidate, SearchType
)


class VectorSearchDemo:
    """Demo class for vector search functionality"""
    
    def __init__(self, es_url: str = "http://localhost:9200"):
        self.es_url = es_url.rstrip("/")
        self.templates = VectorSearchTemplates()
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search_knn(self, 
                        query_vector: List[float], 
                        entity_type: str,
                        country_filter: Optional[str] = None) -> List[VectorHit]:
        """Perform kNN search"""
        print(f"🔍 kNN search: {entity_type} (k={self.templates.k})")
        
        query = self.templates.create_knn_query(query_vector, entity_type, country_filter)
        index_name = f"watchlist_{entity_type}s_current"
        
        try:
            response = await self.client.post(
                f"{self.es_url}/{index_name}/_search",
                json=query
            )
            
            if response.status_code == 200:
                return self.templates.parse_vector_hits(response.json())
            else:
                print(f"❌ kNN search failed: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ kNN search error: {e}")
            return []
    
    async def search_hybrid(self, 
                           query_vector: List[float],
                           ac_queries: List[Dict[str, Any]],
                           entity_type: str) -> List[Candidate]:
        """Perform hybrid search (AC + Vector)"""
        print(f"🔍 Hybrid search: {entity_type}")
        
        hybrid_requests = self.templates.create_hybrid_search_query(
            query_vector, ac_queries, entity_type
        )
        
        try:
            # Prepare multi-search request body
            body_lines = []
            for request in hybrid_requests:
                body_lines.append(json.dumps(request))
            
            body = "\n".join(body_lines) + "\n"
            
            response = await self.client.post(
                f"{self.es_url}/_msearch",
                content=body,
                headers={"Content-Type": "application/x-ndjson"}
            )
            
            if response.status_code == 200:
                return self._parse_hybrid_response(response.json())
            else:
                print(f"❌ Hybrid search failed: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ Hybrid search error: {e}")
            return []
    
    def _parse_hybrid_response(self, response: Dict[str, Any]) -> List[Candidate]:
        """Parse hybrid search response"""
        responses = response.get("responses", [])
        
        if len(responses) < 2:
            return []
        
        # Parse AC results (first response)
        ac_hits = self.templates.parse_ac_hits(responses[0], "exact")
        
        # Parse Vector results (second response)
        vector_hits = self.templates.parse_vector_hits(responses[1])
        
        # Fuse results
        return self.templates.fuse_results(ac_hits, vector_hits)
    
    def print_vector_hits(self, hits: List[VectorHit], title: str = "Vector Search Results"):
        """Print vector search results"""
        print(f"\n📊 {title}")
        print("=" * 60)
        
        if not hits:
            print("No results found")
            return
        
        for i, hit in enumerate(hits, 1):
            print(f"{i}. {hit.normalized_name} ({hit.entity_id})")
            print(f"   Vector Score: {hit.vector_score:.3f}")
            print(f"   Country: {hit.country}")
            if hit.dob:
                print(f"   DOB: {hit.dob}")
            if hit.aliases:
                print(f"   Aliases: {', '.join(hit.aliases)}")
            if hit.meta:
                print(f"   Meta: {hit.meta}")
            print()
    
    def print_candidates(self, candidates: List[Candidate], title: str = "Fusion Results"):
        """Print fusion candidates"""
        print(f"\n📊 {title}")
        print("=" * 60)
        
        if not candidates:
            print("No candidates found")
            return
        
        for i, candidate in enumerate(candidates, 1):
            print(f"{i}. {candidate.normalized_name} ({candidate.entity_id})")
            print(f"   Final Score: {candidate.final_score:.3f}")
            print(f"   AC Score: {candidate.ac_score:.3f} | Vector Score: {candidate.vector_score:.3f}")
            print(f"   Search Type: {candidate.search_type.value}")
            print(f"   Features: {candidate.features}")
            print(f"   Country: {candidate.country}")
            if candidate.dob:
                print(f"   DOB: {candidate.dob}")
            print()
    
    def demonstrate_fusion_formula(self):
        """Demonstrate fusion formula calculation"""
        print("\n🧮 Fusion Formula Demonstration")
        print("=" * 60)
        print("Formula: final = 0.55*ac_score + 0.45*vec_sim + bonus(DOB_match +0.05) - penalty(need_context -0.1)")
        print()
        
        examples = [
            {
                "name": "Perfect Match with DOB",
                "ac_score": 2.0,
                "vector_score": 0.9,
                "features": {"DOB_match": True, "need_context": False}
            },
            {
                "name": "Good Match with Context Penalty",
                "ac_score": 1.5,
                "vector_score": 0.8,
                "features": {"DOB_match": False, "need_context": True}
            },
            {
                "name": "Vector-Only Match",
                "ac_score": 0.0,
                "vector_score": 0.7,
                "features": {"DOB_match": False, "need_context": False}
            }
        ]
        
        for example in examples:
            fusion_score = self.templates.calculate_fusion_score(
                example["ac_score"],
                example["vector_score"],
                example["features"]
            )
            
            print(f"📝 {example['name']}:")
            print(f"   AC Score: {example['ac_score']}")
            print(f"   Vector Score: {example['vector_score']}")
            print(f"   Features: {example['features']}")
            
            # Manual calculation
            base_score = 0.55 * example["ac_score"] + 0.45 * example["vector_score"]
            bonus = 0.05 if example["features"]["DOB_match"] else 0.0
            penalty = 0.1 if example["features"]["need_context"] else 0.0
            manual_score = base_score + bonus - penalty
            
            print(f"   Calculation: 0.55*{example['ac_score']} + 0.45*{example['vector_score']} + {bonus} - {penalty} = {manual_score:.3f}")
            print(f"   Final Score: {fusion_score:.3f}")
            print()
    
    async def run_demo(self):
        """Run complete demo"""
        print("🚀 Vector Search Demo")
        print("=" * 60)
        
        # Generate sample query vector (384 dimensions)
        query_vector = [0.1 + (i * 0.01) for i in range(384)]
        
        # Demo 1: Basic kNN search
        print("\n🧪 Demo 1: Basic kNN Search")
        print("-" * 40)
        
        vector_hits = await self.search_knn(query_vector, "person")
        self.print_vector_hits(vector_hits, "kNN Results")
        
        # Demo 2: Filtered kNN search
        print("\n🧪 Demo 2: Filtered kNN Search (RU only)")
        print("-" * 40)
        
        filtered_hits = await self.search_knn(query_vector, "person", country_filter="RU")
        self.print_vector_hits(filtered_hits, "Filtered kNN Results")
        
        # Demo 3: Fusion formula demonstration
        print("\n🧪 Demo 3: Fusion Formula")
        print("-" * 40)
        self.demonstrate_fusion_formula()
        
        # Demo 4: Mock hybrid search
        print("\n🧪 Demo 4: Mock Hybrid Search")
        print("-" * 40)
        
        # Create mock AC and Vector hits
        ac_hits = [
            ACHit(
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
            ),
            ACHit(
                entity_id="person_002",
                entity_type="person",
                normalized_name="мария сидорова",
                aliases=["м. сидорова"],
                country="RU",
                dob="1975-12-03",
                meta={"source": "sanctions"},
                ac_score=1.5,
                ac_type="phrase",
                matched_field="name_text.shingle"
            )
        ]
        
        vector_hits = [
            VectorHit(
                entity_id="person_001",
                entity_type="person",
                normalized_name="иван петров",
                aliases=["и. петров"],
                country="RU",
                dob="1980-05-15",
                meta={"source": "sanctions"},
                vector_score=0.95,
                matched_field="name_vector"
            ),
            VectorHit(
                entity_id="person_003",
                entity_type="person",
                normalized_name="алексей козлов",
                aliases=[],
                country="RU",
                dob=None,
                meta={"source": "watchlist"},
                vector_score=0.8,
                matched_field="name_vector"
            )
        ]
        
        # Fuse results
        candidates = self.templates.fuse_results(ac_hits, vector_hits, "1980-05-15")
        
        # Rank and select top 3
        top_candidates = self.templates.rank_and_select_top_n(candidates, top_n=3)
        
        self.print_candidates(top_candidates, "Top 3 Fusion Candidates")
        
        # Demo 5: Ranking algorithm
        print("\n🧪 Demo 5: Ranking Algorithm")
        print("-" * 40)
        
        print("Ranking Steps:")
        print("1. Calculate fusion score for each candidate")
        print("2. Sort by final_score (descending)")
        print("3. Select top N candidates")
        print()
        
        print("Ranked Candidates:")
        for i, candidate in enumerate(top_candidates, 1):
            print(f"{i}. {candidate.normalized_name} - Score: {candidate.final_score:.3f}")
            print(f"   Type: {candidate.search_type.value} | AC: {candidate.ac_score:.3f} | Vector: {candidate.vector_score:.3f}")
        
        await self.client.aclose()
        print("\n✅ Demo completed!")


async def main():
    """Main function"""
    demo = VectorSearchDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())

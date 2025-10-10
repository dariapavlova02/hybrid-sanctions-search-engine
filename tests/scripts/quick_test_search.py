#!/usr/bin/env python3
"""
Quick Search Test Script

Provides quick testing capabilities for AC and Vector search functionality.
Useful for SRE and developers to verify search system health.
"""

import argparse
import asyncio
import json
import sys
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin

import httpx


class QuickSearchTester:
    """Quick search tester for hybrid search system"""
    
    def __init__(self, es_url: str = "http://localhost:9200"):
        self.es_url = es_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test_elasticsearch_health(self) -> bool:
        """Test Elasticsearch cluster health"""
        try:
            response = await self.client.get(f"{self.es_url}/_cluster/health")
            if response.status_code == 200:
                health = response.json()
                print(f"[OK] Elasticsearch Health: {health['status']}")
                print(f"   Nodes: {health['number_of_nodes']}")
                print(f"   Active Shards: {health['active_shards']}")
                return health['status'] in ['green', 'yellow']
            else:
                print(f"[ERROR] Elasticsearch Health Check Failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"[ERROR] Elasticsearch Connection Error: {e}")
            return False
    
    async def test_indices_exist(self) -> bool:
        """Test if required indices exist"""
        try:
            response = await self.client.get(f"{self.es_url}/_cat/indices?format=json")
            if response.status_code == 200:
                indices = response.json()
                index_names = [idx['index'] for idx in indices]
                
                required_indices = ['watchlist_persons_current', 'watchlist_orgs_current']
                missing_indices = []
                
                for required in required_indices:
                    if not any(required in name for name in index_names):
                        missing_indices.append(required)
                
                if missing_indices:
                    print(f"[ERROR] Missing Indices: {missing_indices}")
                    return False
                else:
                    print("[OK] All required indices exist")
                    return True
            else:
                print(f"[ERROR] Failed to get indices: {response.status_code}")
                return False
        except Exception as e:
            print(f"[ERROR] Error checking indices: {e}")
            return False
    
    async def test_ac_search(self, entity_type: str = "person") -> bool:
        """Test AC search functionality"""
        try:
            index_name = f"watchlist_{entity_type}s_current"
            
            # Test exact match
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"entity_type": entity_type}},
                            {"terms": {"normalized_name": ["test"]}}
                        ]
                    }
                },
                "size": 1
            }
            
            response = await self.client.get(
                f"{self.es_url}/{index_name}/_search",
                json=query
            )
            
            if response.status_code == 200:
                result = response.json()
                hits = result.get('hits', {}).get('total', {}).get('value', 0)
                print(f"[OK] AC Search Test: {hits} hits found")
                return True
            else:
                print(f"[ERROR] AC Search Test Failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"[ERROR] AC Search Error: {e}")
            return False
    
    async def test_vector_search(self, entity_type: str = "person") -> bool:
        """Test Vector search functionality"""
        try:
            index_name = f"watchlist_{entity_type}s_current"
            
            # Test kNN search with dummy vector
            query = {
                "knn": {
                    "field": "name_vector",
                    "query_vector": [0.1] * 384,  # 384-dim dummy vector
                    "k": 5,
                    "similarity": "cosine"
                },
                "size": 1
            }
            
            response = await self.client.get(
                f"{self.es_url}/{index_name}/_search",
                json=query
            )
            
            if response.status_code == 200:
                result = response.json()
                hits = result.get('hits', {}).get('total', {}).get('value', 0)
                print(f"[OK] Vector Search Test: {hits} hits found")
                return True
            else:
                print(f"[ERROR] Vector Search Test Failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"[ERROR] Vector Search Error: {e}")
            return False
    
    async def test_multi_search(self, entity_type: str = "person") -> bool:
        """Test multi-search functionality"""
        try:
            index_name = f"watchlist_{entity_type}s_current"
            
            # Create multi-search request
            msearch_body = []
            
            # AC query
            msearch_body.append({"index": index_name})
            msearch_body.append({
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"entity_type": entity_type}},
                            {"match_all": {}}
                        ]
                    }
                },
                "size": 1
            })
            
            # Vector query
            msearch_body.append({"index": index_name})
            msearch_body.append({
                "knn": {
                    "field": "name_vector",
                    "query_vector": [0.1] * 384,
                    "k": 5,
                    "similarity": "cosine"
                },
                "size": 1
            })
            
            # Send multi-search request
            msearch_text = "\n".join(json.dumps(item) for item in msearch_body) + "\n"
            
            response = await self.client.post(
                f"{self.es_url}/_msearch",
                content=msearch_text,
                headers={"Content-Type": "application/x-ndjson"}
            )
            
            if response.status_code == 200:
                result = response.json()
                responses = result.get('responses', [])
                print(f"[OK] Multi-Search Test: {len(responses)} responses received")
                return True
            else:
                print(f"[ERROR] Multi-Search Test Failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"[ERROR] Multi-Search Error: {e}")
            return False
    
    async def test_search_performance(self, entity_type: str = "person") -> Dict[str, float]:
        """Test search performance and return timing metrics"""
        import time
        
        index_name = f"watchlist_{entity_type}s_current"
        metrics = {}
        
        try:
            # Test AC search performance
            start_time = time.time()
            ac_query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"entity_type": entity_type}},
                            {"match_all": {}}
                        ]
                    }
                },
                "size": 10
            }
            
            response = await self.client.get(
                f"{self.es_url}/{index_name}/_search",
                json=ac_query
            )
            
            if response.status_code == 200:
                ac_time = time.time() - start_time
                metrics['ac_latency_ms'] = ac_time * 1000
                print(f"[OK] AC Search Latency: {ac_time*1000:.2f}ms")
            else:
                print(f"[ERROR] AC Search Performance Test Failed: {response.status_code}")
                metrics['ac_latency_ms'] = -1
            
            # Test Vector search performance
            start_time = time.time()
            vector_query = {
                "knn": {
                    "field": "name_vector",
                    "query_vector": [0.1] * 384,
                    "k": 10,
                    "similarity": "cosine"
                },
                "size": 10
            }
            
            response = await self.client.get(
                f"{self.es_url}/{index_name}/_search",
                json=vector_query
            )
            
            if response.status_code == 200:
                vector_time = time.time() - start_time
                metrics['vector_latency_ms'] = vector_time * 1000
                print(f"[OK] Vector Search Latency: {vector_time*1000:.2f}ms")
            else:
                print(f"[ERROR] Vector Search Performance Test Failed: {response.status_code}")
                metrics['vector_latency_ms'] = -1
            
            return metrics
            
        except Exception as e:
            print(f"[ERROR] Performance Test Error: {e}")
            return {'ac_latency_ms': -1, 'vector_latency_ms': -1}
    
    async def run_comprehensive_test(self) -> bool:
        """Run comprehensive test suite"""
        print("[CHECK] Starting Comprehensive Search Test...\n")
        
        tests_passed = 0
        total_tests = 6
        
        # Test 1: Elasticsearch Health
        print("1. Testing Elasticsearch Health...")
        if await self.test_elasticsearch_health():
            tests_passed += 1
        print()
        
        # Test 2: Indices Exist
        print("2. Testing Indices...")
        if await self.test_indices_exist():
            tests_passed += 1
        print()
        
        # Test 3: AC Search
        print("3. Testing AC Search...")
        if await self.test_ac_search("person"):
            tests_passed += 1
        print()
        
        # Test 4: Vector Search
        print("4. Testing Vector Search...")
        if await self.test_vector_search("person"):
            tests_passed += 1
        print()
        
        # Test 5: Multi-Search
        print("5. Testing Multi-Search...")
        if await self.test_multi_search("person"):
            tests_passed += 1
        print()
        
        # Test 6: Performance
        print("6. Testing Performance...")
        metrics = await self.test_search_performance("person")
        if metrics['ac_latency_ms'] > 0 and metrics['vector_latency_ms'] > 0:
            tests_passed += 1
        print()
        
        # Summary
        print("="*50)
        print(f"Test Results: {tests_passed}/{total_tests} tests passed")
        
        if tests_passed == total_tests:
            print("[OK] All tests passed! Search system is healthy.")
            return True
        else:
            print("[ERROR] Some tests failed. Check the output above for details.")
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.client.aclose()


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Quick Search Test Script")
    
    parser.add_argument("--es-url", default="http://localhost:9200", 
                       help="Elasticsearch URL")
    parser.add_argument("--entity-type", choices=["person", "org"], default="person",
                       help="Entity type to test")
    parser.add_argument("--test", choices=["health", "indices", "ac", "vector", "multi", "performance", "all"],
                       default="all", help="Specific test to run")
    
    args = parser.parse_args()
    
    tester = QuickSearchTester(args.es_url)
    
    try:
        if args.test == "health":
            success = await tester.test_elasticsearch_health()
        elif args.test == "indices":
            success = await tester.test_indices_exist()
        elif args.test == "ac":
            success = await tester.test_ac_search(args.entity_type)
        elif args.test == "vector":
            success = await tester.test_vector_search(args.entity_type)
        elif args.test == "multi":
            success = await tester.test_multi_search(args.entity_type)
        elif args.test == "performance":
            metrics = await tester.test_search_performance(args.entity_type)
            success = metrics['ac_latency_ms'] > 0 and metrics['vector_latency_ms'] > 0
        else:  # all
            success = await tester.run_comprehensive_test()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n[WARN]  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] Test failed with error: {e}")
        sys.exit(1)
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

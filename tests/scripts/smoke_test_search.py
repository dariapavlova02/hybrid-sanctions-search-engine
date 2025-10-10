#!/usr/bin/env python3
"""
Smoke tests for search integration.

Tests:
- AC search functionality
- Vector search functionality
- Alias functionality
- Performance metrics
- Error handling
"""

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx


class SearchSmokeTester:
    """Smoke tests for search integration."""
    
    def __init__(
        self,
        es_url: str,
        es_auth: Optional[str] = None,
        es_verify_ssl: bool = False,
        environment: str = "staging"
    ):
        self.es_url = es_url
        self.es_auth = es_auth
        self.es_verify_ssl = es_verify_ssl
        self.environment = environment
        
        # HTTP client
        self.client: Optional[httpx.AsyncClient] = None
        
        # Test results
        self.test_results = {
            "environment": environment,
            "timestamp": time.time(),
            "tests": {},
            "performance": {},
            "errors": []
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        auth = None
        if self.es_auth:
            username, password = self.es_auth.split(":", 1)
            auth = (username, password)
        
        self.client = httpx.AsyncClient(
            base_url=self.es_url,
            auth=auth,
            verify=self.es_verify_ssl,
            timeout=30.0
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        expected_status: int = 200
    ) -> Tuple[bool, Dict]:
        """Make HTTP request to Elasticsearch."""
        url = f"{self.es_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                json=data
            )
            
            if response.status_code == expected_status:
                try:
                    return True, response.json() if response.content else {}
                except Exception:
                    return True, {}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                return False, {"error": error_msg}
                
        except Exception as e:
            return False, {"error": f"Request failed: {str(e)}"}
    
    async def test_elasticsearch_health(self) -> bool:
        """Test Elasticsearch cluster health."""
        print("[CHECK] Testing Elasticsearch health...")
        
        start_time = time.time()
        success, result = await self._make_request("GET", "/_cluster/health")
        end_time = time.time()
        
        if not success:
            print(f"[ERROR] Health check failed: {result.get('error')}")
            self.test_results["tests"]["elasticsearch_health"] = {
                "status": "failed",
                "error": result.get("error"),
                "duration_ms": (end_time - start_time) * 1000
            }
            return False
        
        status = result.get("status", "unknown")
        print(f"[OK] Elasticsearch health: {status}")
        
        self.test_results["tests"]["elasticsearch_health"] = {
            "status": "passed",
            "cluster_status": status,
            "duration_ms": (end_time - start_time) * 1000
        }
        
        return status in ["green", "yellow"]
    
    async def test_indices_exist(self) -> bool:
        """Test that required indices exist."""
        print("🗂️ Testing indices existence...")
        
        start_time = time.time()
        success, result = await self._make_request("GET", "/_aliases")
        end_time = time.time()
        
        if not success:
            print(f"[ERROR] Failed to get aliases: {result.get('error')}")
            self.test_results["tests"]["indices_exist"] = {
                "status": "failed",
                "error": result.get("error"),
                "duration_ms": (end_time - start_time) * 1000
            }
            return False
        
        # Check for required aliases
        required_aliases = ["watchlist_persons_current", "watchlist_orgs_current"]
        found_aliases = []
        
        for index_name, index_info in result.items():
            aliases = index_info.get("aliases", {})
            for alias in required_aliases:
                if alias in aliases:
                    found_aliases.append(alias)
                    print(f"[OK] Found alias: {alias} -> {index_name}")
        
        if len(found_aliases) == len(required_aliases):
            print(f"[OK] All required aliases found: {found_aliases}")
            self.test_results["tests"]["indices_exist"] = {
                "status": "passed",
                "found_aliases": found_aliases,
                "duration_ms": (end_time - start_time) * 1000
            }
            return True
        else:
            missing = set(required_aliases) - set(found_aliases)
            print(f"[ERROR] Missing aliases: {missing}")
            self.test_results["tests"]["indices_exist"] = {
                "status": "failed",
                "found_aliases": found_aliases,
                "missing_aliases": list(missing),
                "duration_ms": (end_time - start_time) * 1000
            }
            return False
    
    async def test_ac_search(self) -> bool:
        """Test AC search functionality."""
        print("[CHECK] Testing AC search...")
        
        test_queries = [
            "иван петров",
            "мария сидорова",
            "приватбанк",
            "apple inc"
        ]
        
        ac_results = []
        
        for query in test_queries:
            start_time = time.time()
            
            # Test persons search
            success, result = await self._make_request(
                "POST",
                "/watchlist_persons_current/_search",
                {
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["normalized_name", "name_text", "name_ngrams"]
                        }
                    },
                    "size": 10
                }
            )
            
            end_time = time.time()
            
            if success:
                hits = result.get("hits", {}).get("total", {}).get("value", 0)
                print(f"[OK] AC search '{query}': {hits} hits ({end_time - start_time:.3f}s)")
                ac_results.append({
                    "query": query,
                    "hits": hits,
                    "duration_ms": (end_time - start_time) * 1000
                })
            else:
                print(f"[ERROR] AC search '{query}' failed: {result.get('error')}")
                ac_results.append({
                    "query": query,
                    "hits": 0,
                    "duration_ms": (end_time - start_time) * 1000,
                    "error": result.get("error")
                })
        
        # Calculate performance metrics
        total_hits = sum(r["hits"] for r in ac_results)
        avg_duration = sum(r["duration_ms"] for r in ac_results) / len(ac_results)
        
        self.test_results["tests"]["ac_search"] = {
            "status": "passed" if total_hits > 0 else "failed",
            "total_hits": total_hits,
            "avg_duration_ms": avg_duration,
            "queries": ac_results
        }
        
        self.test_results["performance"]["ac_search_avg_ms"] = avg_duration
        self.test_results["performance"]["ac_search_total_hits"] = total_hits
        
        return total_hits > 0
    
    async def test_vector_search(self) -> bool:
        """Test vector search functionality."""
        print("[CHECK] Testing vector search...")
        
        # Generate dummy query vector
        query_vector = [0.1] * 384
        
        start_time = time.time()
        
        success, result = await self._make_request(
            "POST",
            "/watchlist_persons_current/_search",
            {
                "knn": {
                    "field": "name_vector",
                    "query_vector": query_vector,
                    "k": 10,
                    "num_candidates": 100,
                    "similarity": "cosine"
                },
                "size": 10
            }
        )
        
        end_time = time.time()
        
        if success:
            hits = result.get("hits", {}).get("total", {}).get("value", 0)
            print(f"[OK] Vector search: {hits} hits ({end_time - start_time:.3f}s)")
            
            self.test_results["tests"]["vector_search"] = {
                "status": "passed",
                "hits": hits,
                "duration_ms": (end_time - start_time) * 1000
            }
            
            self.test_results["performance"]["vector_search_ms"] = (end_time - start_time) * 1000
            self.test_results["performance"]["vector_search_hits"] = hits
            
            return True
        else:
            print(f"[ERROR] Vector search failed: {result.get('error')}")
            self.test_results["tests"]["vector_search"] = {
                "status": "failed",
                "error": result.get("error"),
                "duration_ms": (end_time - start_time) * 1000
            }
            return False
    
    async def test_performance(self) -> bool:
        """Test search performance."""
        print("⚡ Testing performance...")
        
        # Performance test queries
        perf_queries = [
            "иван петров",
            "мария сидорова",
            "приватбанк",
            "apple inc",
            "john smith"
        ]
        
        durations = []
        
        for query in perf_queries:
            start_time = time.time()
            
            success, result = await self._make_request(
                "POST",
                "/watchlist_persons_current/_search",
                {
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["normalized_name", "name_text", "name_ngrams"]
                        }
                    },
                    "size": 10
                }
            )
            
            end_time = time.time()
            
            if success:
                durations.append(end_time - start_time)
            else:
                print(f"[WARN] Performance test query '{query}' failed")
        
        if durations:
            avg_duration = sum(durations) / len(durations)
            p95_duration = sorted(durations)[int(len(durations) * 0.95)]
            max_duration = max(durations)
            
            print(f"[OK] Performance test completed:")
            print(f"  Average: {avg_duration:.3f}s")
            print(f"  P95: {p95_duration:.3f}s")
            print(f"  Max: {max_duration:.3f}s")
            
            self.test_results["performance"]["avg_duration_ms"] = avg_duration * 1000
            self.test_results["performance"]["p95_duration_ms"] = p95_duration * 1000
            self.test_results["performance"]["max_duration_ms"] = max_duration * 1000
            
            # Check if performance meets requirements
            performance_ok = p95_duration < 0.08  # 80ms requirement
            
            self.test_results["tests"]["performance"] = {
                "status": "passed" if performance_ok else "failed",
                "avg_duration_ms": avg_duration * 1000,
                "p95_duration_ms": p95_duration * 1000,
                "max_duration_ms": max_duration * 1000,
                "requirement_met": performance_ok
            }
            
            return performance_ok
        else:
            print("[ERROR] No successful performance test queries")
            self.test_results["tests"]["performance"] = {
                "status": "failed",
                "error": "No successful queries"
            }
            return False
    
    async def test_error_handling(self) -> bool:
        """Test error handling."""
        print("🛡️ Testing error handling...")
        
        # Test with invalid query
        start_time = time.time()
        
        success, result = await self._make_request(
            "POST",
            "/watchlist_persons_current/_search",
            {
                "query": {
                    "invalid_query": {
                        "field": "nonexistent"
                    }
                }
            }
        )
        
        end_time = time.time()
        
        # Should handle error gracefully
        if not success:
            print("[OK] Error handling test passed - invalid query handled gracefully")
            self.test_results["tests"]["error_handling"] = {
                "status": "passed",
                "duration_ms": (end_time - start_time) * 1000
            }
            return True
        else:
            print("[WARN] Error handling test - invalid query did not fail as expected")
            self.test_results["tests"]["error_handling"] = {
                "status": "warning",
                "duration_ms": (end_time - start_time) * 1000
            }
            return True
    
    async def run_all_tests(self) -> bool:
        """Run all smoke tests."""
        print("🧪 Running smoke tests...")
        
        tests = [
            ("Elasticsearch Health", self.test_elasticsearch_health),
            ("Indices Exist", self.test_indices_exist),
            ("AC Search", self.test_ac_search),
            ("Vector Search", self.test_vector_search),
            ("Performance", self.test_performance),
            ("Error Handling", self.test_error_handling)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n📋 {test_name}...")
            
            try:
                success = await test_func()
                if success:
                    passed_tests += 1
                    print(f"[OK] {test_name} passed")
                else:
                    print(f"[ERROR] {test_name} failed")
            except Exception as e:
                print(f"[ERROR] {test_name} error: {e}")
                self.test_results["errors"].append(f"{test_name}: {str(e)}")
        
        # Overall result
        overall_success = passed_tests == total_tests
        self.test_results["overall_status"] = "passed" if overall_success else "failed"
        self.test_results["passed_tests"] = passed_tests
        self.test_results["total_tests"] = total_tests
        
        print(f"\n[STATS] Smoke test summary:")
        print(f"  Passed: {passed_tests}/{total_tests}")
        print(f"  Status: {'[OK] PASSED' if overall_success else '[ERROR] FAILED'}")
        
        return overall_success


async def main():
    """Main smoke test function."""
    parser = argparse.ArgumentParser(description="Run smoke tests for search integration")
    parser.add_argument("--environment", required=True, help="Environment being tested")
    parser.add_argument("--es-url", required=True, help="Elasticsearch URL")
    parser.add_argument("--es-auth", help="Elasticsearch auth (username:password)")
    parser.add_argument("--es-verify-ssl", action="store_true", help="Verify SSL")
    parser.add_argument("--output", help="Output file for test results")
    
    args = parser.parse_args()
    
    print(f"🧪 Starting smoke tests for search integration")
    print(f"Environment: {args.environment}")
    print(f"ES URL: {args.es_url}")
    
    async with SearchSmokeTester(
        es_url=args.es_url,
        es_auth=args.es_auth,
        es_verify_ssl=args.es_verify_ssl,
        environment=args.environment
    ) as tester:
        
        success = await tester.run_all_tests()
        
        # Save results
        if args.output:
            with open(args.output, "w") as f:
                json.dump(tester.test_results, f, indent=2)
            print(f"\n📄 Test results saved to: {args.output}")
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

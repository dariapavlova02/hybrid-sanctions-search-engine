#!/usr/bin/env python3
"""
Generate deployment report for search integration.

Collects:
- Deployment metrics
- Performance data
- Error rates
- Index statistics
- Health status
"""

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx


class DeploymentReportGenerator:
    """Generates deployment reports for search integration."""
    
    def __init__(
        self,
        es_url: str,
        es_auth: Optional[str] = None,
        es_verify_ssl: bool = False,
        environment: str = "production"
    ):
        self.es_url = es_url
        self.es_auth = es_auth
        self.es_verify_ssl = es_verify_ssl
        self.environment = environment
        
        # HTTP client
        self.client: Optional[httpx.AsyncClient] = None
        
        # Report data
        self.report = {
            "environment": environment,
            "timestamp": time.time(),
            "elasticsearch": {},
            "indices": {},
            "performance": {},
            "health": {},
            "summary": {}
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
    
    async def collect_elasticsearch_info(self) -> bool:
        """Collect Elasticsearch cluster information."""
        print("📊 Collecting Elasticsearch information...")
        
        # Cluster health
        success, health = await self._make_request("GET", "/_cluster/health")
        if success:
            self.report["elasticsearch"]["health"] = health
            print(f"✅ Cluster health: {health.get('status', 'unknown')}")
        else:
            print(f"❌ Failed to get cluster health: {health.get('error')}")
            return False
        
        # Cluster stats
        success, stats = await self._make_request("GET", "/_cluster/stats")
        if success:
            self.report["elasticsearch"]["stats"] = stats
            print("✅ Cluster stats collected")
        else:
            print(f"⚠️ Failed to get cluster stats: {stats.get('error')}")
        
        # Node info
        success, nodes = await self._make_request("GET", "/_nodes")
        if success:
            self.report["elasticsearch"]["nodes"] = {
                "total": nodes.get("_nodes", {}).get("total", 0),
                "successful": nodes.get("_nodes", {}).get("successful", 0),
                "failed": nodes.get("_nodes", {}).get("failed", 0)
            }
            print("✅ Node information collected")
        else:
            print(f"⚠️ Failed to get node info: {nodes.get('error')}")
        
        return True
    
    async def collect_indices_info(self) -> bool:
        """Collect indices information."""
        print("📊 Collecting indices information...")
        
        # Get all indices
        success, indices = await self._make_request("GET", "/_cat/indices?format=json")
        if not success:
            print(f"❌ Failed to get indices: {indices.get('error')}")
            return False
        
        # Filter search-related indices
        search_indices = []
        for index in indices:
            index_name = index.get("index", "")
            if "watchlist" in index_name:
                search_indices.append({
                    "name": index_name,
                    "status": index.get("status", "unknown"),
                    "health": index.get("health", "unknown"),
                    "docs_count": int(index.get("docs.count", 0)),
                    "store_size": index.get("store.size", "0b"),
                    "pri_store_size": index.get("pri.store.size", "0b")
                })
        
        self.report["indices"]["search_indices"] = search_indices
        print(f"✅ Found {len(search_indices)} search indices")
        
        # Get aliases
        success, aliases = await self._make_request("GET", "/_aliases")
        if success:
            search_aliases = {}
            for index_name, index_info in aliases.items():
                if "watchlist" in index_name:
                    search_aliases[index_name] = index_info.get("aliases", {})
            
            self.report["indices"]["aliases"] = search_aliases
            print("✅ Aliases information collected")
        else:
            print(f"⚠️ Failed to get aliases: {aliases.get('error')}")
        
        return True
    
    async def collect_performance_data(self) -> bool:
        """Collect performance data."""
        print("📊 Collecting performance data...")
        
        # Test queries for performance measurement
        test_queries = [
            "иван петров",
            "мария сидорова",
            "приватбанк",
            "apple inc",
            "john smith"
        ]
        
        performance_data = []
        
        for query in test_queries:
            start_time = time.time()
            
            # AC search
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
                performance_data.append({
                    "query": query,
                    "type": "ac_search",
                    "duration_ms": (end_time - start_time) * 1000,
                    "hits": hits
                })
            else:
                performance_data.append({
                    "query": query,
                    "type": "ac_search",
                    "duration_ms": (end_time - start_time) * 1000,
                    "hits": 0,
                    "error": result.get("error")
                })
        
        # Calculate performance metrics
        if performance_data:
            durations = [p["duration_ms"] for p in performance_data if "error" not in p]
            if durations:
                durations.sort()
                p50 = durations[len(durations) // 2]
                p95 = durations[int(len(durations) * 0.95)]
                p99 = durations[int(len(durations) * 0.99)]
                
                self.report["performance"] = {
                    "queries": performance_data,
                    "p50_duration_ms": p50,
                    "p95_duration_ms": p95,
                    "p99_duration_ms": p99,
                    "avg_duration_ms": sum(durations) / len(durations),
                    "max_duration_ms": max(durations),
                    "min_duration_ms": min(durations)
                }
                
                print(f"✅ Performance data collected:")
                print(f"  P50: {p50:.2f}ms")
                print(f"  P95: {p95:.2f}ms")
                print(f"  P99: {p99:.2f}ms")
                print(f"  Avg: {sum(durations) / len(durations):.2f}ms")
        
        return True
    
    async def collect_health_metrics(self) -> bool:
        """Collect health metrics."""
        print("📊 Collecting health metrics...")
        
        # Cluster health
        success, health = await self._make_request("GET", "/_cluster/health")
        if not success:
            print(f"❌ Failed to get cluster health: {health.get('error')}")
            return False
        
        # Index health
        success, indices = await self._make_request("GET", "/_cat/indices?format=json&health=red,yellow,green")
        if not success:
            print(f"❌ Failed to get index health: {indices.get('error')}")
            return False
        
        # Count healthy indices
        healthy_indices = sum(1 for idx in indices if idx.get("health") == "green")
        yellow_indices = sum(1 for idx in indices if idx.get("health") == "yellow")
        red_indices = sum(1 for idx in indices if idx.get("health") == "red")
        
        self.report["health"] = {
            "cluster_status": health.get("status", "unknown"),
            "cluster_number_of_nodes": health.get("number_of_nodes", 0),
            "cluster_data_nodes": health.get("data_nodes", 0),
            "cluster_active_shards": health.get("active_shards", 0),
            "cluster_relocating_shards": health.get("relocating_shards", 0),
            "cluster_initializing_shards": health.get("initializing_shards", 0),
            "cluster_unassigned_shards": health.get("unassigned_shards", 0),
            "indices_healthy": healthy_indices,
            "indices_yellow": yellow_indices,
            "indices_red": red_indices,
            "total_indices": len(indices)
        }
        
        print(f"✅ Health metrics collected:")
        print(f"  Cluster status: {health.get('status', 'unknown')}")
        print(f"  Healthy indices: {healthy_indices}")
        print(f"  Yellow indices: {yellow_indices}")
        print(f"  Red indices: {red_indices}")
        
        return True
    
    async def generate_summary(self) -> bool:
        """Generate deployment summary."""
        print("📊 Generating deployment summary...")
        
        # Overall health status
        cluster_status = self.report["elasticsearch"]["health"].get("status", "unknown")
        red_indices = self.report["health"].get("indices_red", 0)
        
        overall_health = "healthy"
        if cluster_status == "red" or red_indices > 0:
            overall_health = "unhealthy"
        elif cluster_status == "yellow":
            overall_health = "degraded"
        
        # Performance status
        p95_duration = self.report["performance"].get("p95_duration_ms", 0)
        performance_status = "good"
        if p95_duration > 100:  # 100ms threshold
            performance_status = "poor"
        elif p95_duration > 50:  # 50ms threshold
            performance_status = "acceptable"
        
        # Document count
        total_docs = sum(
            idx.get("docs_count", 0) 
            for idx in self.report["indices"].get("search_indices", [])
        )
        
        self.report["summary"] = {
            "overall_health": overall_health,
            "performance_status": performance_status,
            "total_documents": total_docs,
            "search_indices_count": len(self.report["indices"].get("search_indices", [])),
            "p95_latency_ms": p95_duration,
            "cluster_status": cluster_status,
            "deployment_successful": overall_health in ["healthy", "degraded"] and performance_status in ["good", "acceptable"]
        }
        
        print(f"✅ Deployment summary generated:")
        print(f"  Overall health: {overall_health}")
        print(f"  Performance: {performance_status}")
        print(f"  Total documents: {total_docs}")
        print(f"  P95 latency: {p95_duration:.2f}ms")
        print(f"  Deployment successful: {self.report['summary']['deployment_successful']}")
        
        return True
    
    async def generate_report(self) -> Dict:
        """Generate complete deployment report."""
        print("📊 Generating deployment report...")
        
        # Collect all data
        steps = [
            ("Elasticsearch info", self.collect_elasticsearch_info),
            ("Indices info", self.collect_indices_info),
            ("Performance data", self.collect_performance_data),
            ("Health metrics", self.collect_health_metrics),
            ("Summary", self.generate_summary)
        ]
        
        for step_name, step_func in steps:
            print(f"\n📋 {step_name}...")
            try:
                success = await step_func()
                if not success:
                    print(f"❌ {step_name} failed")
                    return self.report
                print(f"✅ {step_name} completed")
            except Exception as e:
                print(f"❌ {step_name} error: {e}")
                return self.report
        
        return self.report


async def main():
    """Main report generation function."""
    parser = argparse.ArgumentParser(description="Generate deployment report")
    parser.add_argument("--environment", required=True, help="Environment")
    parser.add_argument("--es-url", required=True, help="Elasticsearch URL")
    parser.add_argument("--es-auth", help="Elasticsearch auth (username:password)")
    parser.add_argument("--es-verify-ssl", action="store_true", help="Verify SSL")
    parser.add_argument("--output", required=True, help="Output file for report")
    
    args = parser.parse_args()
    
    print(f"📊 Generating deployment report")
    print(f"Environment: {args.environment}")
    print(f"ES URL: {args.es_url}")
    print(f"Output: {args.output}")
    
    async with DeploymentReportGenerator(
        es_url=args.es_url,
        es_auth=args.es_auth,
        es_verify_ssl=args.es_verify_ssl,
        environment=args.environment
    ) as generator:
        
        report = await generator.generate_report()
        
        # Save report
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Deployment report saved to: {args.output}")
        
        # Print summary
        summary = report.get("summary", {})
        print(f"\n📊 Deployment Summary:")
        print(f"  Overall health: {summary.get('overall_health', 'unknown')}")
        print(f"  Performance: {summary.get('performance_status', 'unknown')}")
        print(f"  Total documents: {summary.get('total_documents', 0)}")
        print(f"  P95 latency: {summary.get('p95_latency_ms', 0):.2f}ms")
        print(f"  Deployment successful: {summary.get('deployment_successful', False)}")


if __name__ == "__main__":
    asyncio.run(main())

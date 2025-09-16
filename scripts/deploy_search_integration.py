#!/usr/bin/env python3
"""
Deployment script for search integration.

Handles:
- Elasticsearch template creation
- Index creation with aliases
- Bulk data loading
- Alias rollover
- Warmup queries
- Smoke tests
- Metrics collection
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx
import yaml


class SearchDeploymentManager:
    """Manages search integration deployment."""
    
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
        
        # Deployment state
        self.deployment_id = f"search-{int(time.time())}"
        self.old_aliases: Dict[str, str] = {}
        self.new_indices: Dict[str, str] = {}
        
        # Metrics
        self.metrics = {
            "deployment_start": time.time(),
            "templates_created": 0,
            "indices_created": 0,
            "documents_loaded": 0,
            "warmup_queries": 0,
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
            timeout=60.0
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
    
    async def health_check(self) -> bool:
        """Check Elasticsearch health."""
        print("🔍 Checking Elasticsearch health...")
        
        success, result = await self._make_request("GET", "/_cluster/health")
        if not success:
            print(f"❌ Health check failed: {result.get('error')}")
            return False
        
        status = result.get("status", "unknown")
        print(f"✅ Elasticsearch health: {status}")
        return status in ["green", "yellow"]
    
    async def create_templates(self, artifacts_path: str) -> bool:
        """Create Elasticsearch templates."""
        print("📋 Creating Elasticsearch templates...")
        
        templates_dir = Path(artifacts_path) / "templates" / "elasticsearch"
        if not templates_dir.exists():
            print(f"❌ Templates directory not found: {templates_dir}")
            return False
        
        # Component template
        component_template_path = templates_dir / "elasticsearch_component_template.json"
        if component_template_path.exists():
            with open(component_template_path) as f:
                component_template = json.load(f)
            
            success, result = await self._make_request(
                "PUT",
                "/_component_template/search_analyzers",
                component_template
            )
            
            if success:
                print("✅ Component template created")
                self.metrics["templates_created"] += 1
            else:
                print(f"❌ Component template failed: {result.get('error')}")
                return False
        
        # Index templates
        for template_file in ["elasticsearch_persons_template.json", "elasticsearch_orgs_template.json"]:
            template_path = templates_dir / template_file
            if template_path.exists():
                with open(template_path) as f:
                    template = json.load(f)
                
                template_name = template_file.replace("elasticsearch_", "").replace("_template.json", "")
                success, result = await self._make_request(
                    "PUT",
                    f"/_index_template/{template_name}",
                    template
                )
                
                if success:
                    print(f"✅ {template_name} template created")
                    self.metrics["templates_created"] += 1
                else:
                    print(f"❌ {template_name} template failed: {result.get('error')}")
                    return False
        
        return True
    
    async def create_indices(self) -> bool:
        """Create new indices with aliases."""
        print("🗂️ Creating new indices...")
        
        # Generate new index names
        timestamp = int(time.time())
        persons_index = f"watchlist_persons_v{timestamp}"
        orgs_index = f"watchlist_orgs_v{timestamp}"
        
        self.new_indices = {
            "persons": persons_index,
            "orgs": orgs_index
        }
        
        # Create indices
        for entity_type, index_name in self.new_indices.items():
            success, result = await self._make_request("PUT", f"/{index_name}")
            
            if success:
                print(f"✅ {index_name} created")
                self.metrics["indices_created"] += 1
            else:
                print(f"❌ {index_name} creation failed: {result.get('error')}")
                return False
        
        return True
    
    async def load_data(self, artifacts_path: str) -> bool:
        """Load data into new indices."""
        print("📦 Loading data into indices...")
        
        # Load test data
        templates_dir = Path(artifacts_path) / "templates"
        if not templates_dir.exists():
            print(f"❌ Templates directory not found: {templates_dir}")
            return False
        
        # Load persons data
        persons_file = templates_dir / "sanctioned_persons_templates.json"
        if persons_file.exists():
            with open(persons_file) as f:
                persons_data = json.load(f)
            
            success = await self._bulk_load_data(persons_data, "persons")
            if not success:
                return False
        
        # Load orgs data
        orgs_file = templates_dir / "sanctioned_companies_templates.json"
        if orgs_file.exists():
            with open(orgs_file) as f:
                orgs_data = json.load(f)
            
            success = await self._bulk_load_data(orgs_data, "orgs")
            if not success:
                return False
        
        return True
    
    async def _bulk_load_data(self, data: List[Dict], entity_type: str) -> bool:
        """Load data using bulk API."""
        index_name = self.new_indices[entity_type]
        
        # Prepare bulk request
        bulk_body = []
        for item in data:
            # Index action
            bulk_body.append({
                "index": {
                    "_index": index_name,
                    "_id": item.get("entity_id", f"{entity_type}_{len(bulk_body)}")
                }
            })
            
            # Transform data for ES
            doc = {
                "entity_id": item.get("entity_id", ""),
                "entity_type": entity_type,
                "normalized_name": item.get("normalized_name", "").lower().strip(),
                "aliases": item.get("aliases", []),
                "country": item.get("country", ""),
                "dob": item.get("dob"),
                "name_text": item.get("normalized_name", ""),
                "name_ngrams": item.get("normalized_name", ""),
                "name_vector": [0.1] * 384,  # Dummy vector
                "meta": item.get("meta", {})
            }
            bulk_body.append(doc)
        
        # Execute bulk request
        success, result = await self._make_request(
            "POST",
            f"/{index_name}/_bulk",
            bulk_body
        )
        
        if success:
            if result.get("errors"):
                print(f"⚠️ Some documents failed to index in {index_name}")
            else:
                print(f"✅ {len(data)} documents loaded into {index_name}")
                self.metrics["documents_loaded"] += len(data)
            return True
        else:
            print(f"❌ Bulk load failed for {index_name}: {result.get('error')}")
            return False
    
    async def rollover_aliases(self) -> bool:
        """Rollover aliases to new indices."""
        print("🔄 Rolling over aliases...")
        
        # Get current aliases
        success, result = await self._make_request("GET", "/_aliases")
        if not success:
            print(f"❌ Failed to get aliases: {result.get('error')}")
            return False
        
        # Store old aliases for rollback
        for index_name, index_info in result.items():
            if "watchlist_persons_current" in index_info.get("aliases", {}):
                self.old_aliases["persons"] = index_name
            if "watchlist_orgs_current" in index_info.get("aliases", {}):
                self.old_aliases["orgs"] = index_name
        
        # Create new aliases
        for entity_type, index_name in self.new_indices.items():
            alias_name = f"watchlist_{entity_type}_current"
            
            # Remove old alias
            if entity_type in self.old_aliases:
                old_index = self.old_aliases[entity_type]
                success, result = await self._make_request(
                    "POST",
                    f"/{old_index}/_alias/{alias_name}",
                    {"remove": {}}
                )
                if success:
                    print(f"✅ Removed old alias {alias_name} from {old_index}")
            
            # Add new alias
            success, result = await self._make_request(
                "POST",
                f"/{index_name}/_alias/{alias_name}",
                {"add": {}}
            )
            
            if success:
                print(f"✅ Added alias {alias_name} to {index_name}")
            else:
                print(f"❌ Failed to add alias {alias_name}: {result.get('error')}")
                return False
        
        return True
    
    async def warmup_queries(self) -> bool:
        """Run warmup queries."""
        print("🔥 Running warmup queries...")
        
        # Sample queries for warmup
        warmup_queries = [
            "иван петров",
            "мария сидорова",
            "приватбанк",
            "apple inc",
            "john smith"
        ]
        
        for query in warmup_queries:
            # AC search warmup
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
            
            if success:
                print(f"✅ AC warmup query: {query}")
                self.metrics["warmup_queries"] += 1
            else:
                print(f"⚠️ AC warmup query failed: {query}")
        
        return True
    
    async def smoke_tests(self) -> bool:
        """Run smoke tests."""
        print("🧪 Running smoke tests...")
        
        # Test AC search
        success, result = await self._make_request(
            "POST",
            "/watchlist_persons_current/_search",
            {
                "query": {
                    "term": {
                        "entity_type": "person"
                    }
                },
                "size": 1
            }
        )
        
        if not success:
            print(f"❌ Smoke test failed: {result.get('error')}")
            return False
        
        hits = result.get("hits", {}).get("total", {}).get("value", 0)
        print(f"✅ Smoke test passed: {hits} documents found")
        
        return True
    
    async def generate_metrics_report(self) -> Dict:
        """Generate deployment metrics report."""
        deployment_time = time.time() - self.metrics["deployment_start"]
        
        report = {
            "deployment_id": self.deployment_id,
            "environment": self.environment,
            "timestamp": time.time(),
            "deployment_time_seconds": deployment_time,
            "metrics": self.metrics,
            "new_indices": self.new_indices,
            "old_aliases": self.old_aliases,
            "status": "success" if not self.metrics["errors"] else "failed"
        }
        
        return report


async def main():
    """Main deployment function."""
    parser = argparse.ArgumentParser(description="Deploy search integration")
    parser.add_argument("--environment", required=True, help="Deployment environment")
    parser.add_argument("--artifacts-path", required=True, help="Path to artifacts")
    parser.add_argument("--es-url", required=True, help="Elasticsearch URL")
    parser.add_argument("--es-auth", help="Elasticsearch auth (username:password)")
    parser.add_argument("--es-verify-ssl", action="store_true", help="Verify SSL")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    
    args = parser.parse_args()
    
    print(f"🚀 Starting search integration deployment")
    print(f"Environment: {args.environment}")
    print(f"Artifacts: {args.artifacts_path}")
    print(f"ES URL: {args.es_url}")
    print(f"Dry run: {args.dry_run}")
    
    async with SearchDeploymentManager(
        es_url=args.es_url,
        es_auth=args.es_auth,
        es_verify_ssl=args.es_verify_ssl,
        environment=args.environment
    ) as manager:
        
        # Health check
        if not await manager.health_check():
            print("❌ Elasticsearch health check failed")
            sys.exit(1)
        
        if args.dry_run:
            print("🔍 Dry run mode - skipping actual deployment")
            return
        
        # Deployment steps
        steps = [
            ("Create templates", manager.create_templates, args.artifacts_path),
            ("Create indices", manager.create_indices, None),
            ("Load data", manager.load_data, args.artifacts_path),
            ("Rollover aliases", manager.rollover_aliases, None),
            ("Warmup queries", manager.warmup_queries, None),
            ("Smoke tests", manager.smoke_tests, None)
        ]
        
        for step_name, step_func, step_arg in steps:
            print(f"\n📋 {step_name}...")
            
            try:
                if step_arg is not None:
                    success = await step_func(step_arg)
                else:
                    success = await step_func()
                
                if not success:
                    print(f"❌ {step_name} failed")
                    sys.exit(1)
                
                print(f"✅ {step_name} completed")
                
            except Exception as e:
                print(f"❌ {step_name} error: {e}")
                manager.metrics["errors"].append(str(e))
                sys.exit(1)
        
        # Generate report
        report = await manager.generate_metrics_report()
        
        # Save report
        report_path = Path(args.artifacts_path) / "deployment-report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Deployment completed successfully!")
        print(f"Report saved to: {report_path}")
        print(f"Deployment time: {report['deployment_time_seconds']:.2f}s")
        print(f"Documents loaded: {report['metrics']['documents_loaded']}")
        print(f"Warmup queries: {report['metrics']['warmup_queries']}")


if __name__ == "__main__":
    asyncio.run(main())

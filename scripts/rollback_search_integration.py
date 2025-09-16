#!/usr/bin/env python3
"""
Rollback script for search integration.

Handles:
- Alias rollback to previous indices
- Cleanup of new indices
- Verification of rollback
- Metrics collection
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx


class SearchRollbackManager:
    """Manages search integration rollback."""
    
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
        
        # Rollback state
        self.rollback_id = f"rollback-{int(time.time())}"
        self.old_aliases: Dict[str, str] = {}
        self.new_indices: Dict[str, str] = {}
        
        # Metrics
        self.metrics = {
            "rollback_start": time.time(),
            "aliases_rolled_back": 0,
            "indices_cleaned": 0,
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
    
    async def discover_current_state(self) -> bool:
        """Discover current aliases and indices."""
        print("🔍 Discovering current state...")
        
        # Get current aliases
        success, result = await self._make_request("GET", "/_aliases")
        if not success:
            print(f"❌ Failed to get aliases: {result.get('error')}")
            return False
        
        # Find current aliases
        for index_name, index_info in result.items():
            aliases = index_info.get("aliases", {})
            
            if "watchlist_persons_current" in aliases:
                self.old_aliases["persons"] = index_name
                print(f"✅ Found persons alias: {index_name}")
            
            if "watchlist_orgs_current" in aliases:
                self.old_aliases["orgs"] = index_name
                print(f"✅ Found orgs alias: {index_name}")
        
        # Find new indices (not in old aliases)
        for index_name in result.keys():
            if (index_name.startswith("watchlist_persons_v") and 
                index_name not in self.old_aliases.values()):
                self.new_indices["persons"] = index_name
                print(f"✅ Found new persons index: {index_name}")
            
            if (index_name.startswith("watchlist_orgs_v") and 
                index_name not in self.old_aliases.values()):
                self.new_indices["orgs"] = index_name
                print(f"✅ Found new orgs index: {index_name}")
        
        return True
    
    async def rollback_aliases(self) -> bool:
        """Rollback aliases to previous indices."""
        print("🔄 Rolling back aliases...")
        
        if not self.old_aliases:
            print("⚠️ No old aliases found to rollback to")
            return True
        
        # Rollback persons alias
        if "persons" in self.old_aliases:
            old_persons_index = self.old_aliases["persons"]
            
            # Remove alias from new index
            if "persons" in self.new_indices:
                new_persons_index = self.new_indices["persons"]
                success, result = await self._make_request(
                    "POST",
                    f"/{new_persons_index}/_alias/watchlist_persons_current",
                    {"remove": {}}
                )
                if success:
                    print(f"✅ Removed alias from {new_persons_index}")
                else:
                    print(f"⚠️ Failed to remove alias from {new_persons_index}")
            
            # Add alias to old index
            success, result = await self._make_request(
                "POST",
                f"/{old_persons_index}/_alias/watchlist_persons_current",
                {"add": {}}
            )
            
            if success:
                print(f"✅ Rolled back persons alias to {old_persons_index}")
                self.metrics["aliases_rolled_back"] += 1
            else:
                print(f"❌ Failed to rollback persons alias: {result.get('error')}")
                return False
        
        # Rollback orgs alias
        if "orgs" in self.old_aliases:
            old_orgs_index = self.old_aliases["orgs"]
            
            # Remove alias from new index
            if "orgs" in self.new_indices:
                new_orgs_index = self.new_indices["orgs"]
                success, result = await self._make_request(
                    "POST",
                    f"/{new_orgs_index}/_alias/watchlist_orgs_current",
                    {"remove": {}}
                )
                if success:
                    print(f"✅ Removed alias from {new_orgs_index}")
                else:
                    print(f"⚠️ Failed to remove alias from {new_orgs_index}")
            
            # Add alias to old index
            success, result = await self._make_request(
                "POST",
                f"/{old_orgs_index}/_alias/watchlist_orgs_current",
                {"add": {}}
            )
            
            if success:
                print(f"✅ Rolled back orgs alias to {old_orgs_index}")
                self.metrics["aliases_rolled_back"] += 1
            else:
                print(f"❌ Failed to rollback orgs alias: {result.get('error')}")
                return False
        
        return True
    
    async def cleanup_new_indices(self) -> bool:
        """Clean up new indices."""
        print("🧹 Cleaning up new indices...")
        
        for entity_type, index_name in self.new_indices.items():
            success, result = await self._make_request("DELETE", f"/{index_name}")
            
            if success:
                print(f"✅ Deleted {index_name}")
                self.metrics["indices_cleaned"] += 1
            else:
                print(f"⚠️ Failed to delete {index_name}: {result.get('error')}")
                # Don't fail rollback for cleanup errors
        
        return True
    
    async def verify_rollback(self) -> bool:
        """Verify rollback was successful."""
        print("✅ Verifying rollback...")
        
        # Check aliases
        success, result = await self._make_request("GET", "/_aliases")
        if not success:
            print(f"❌ Failed to verify aliases: {result.get('error')}")
            return False
        
        # Verify persons alias
        persons_alias_found = False
        for index_name, index_info in result.items():
            if "watchlist_persons_current" in index_info.get("aliases", {}):
                persons_alias_found = True
                print(f"✅ Persons alias verified: {index_name}")
                break
        
        if not persons_alias_found:
            print("❌ Persons alias not found after rollback")
            return False
        
        # Verify orgs alias
        orgs_alias_found = False
        for index_name, index_info in result.items():
            if "watchlist_orgs_current" in index_info.get("aliases", {}):
                orgs_alias_found = True
                print(f"✅ Orgs alias verified: {index_name}")
                break
        
        if not orgs_alias_found:
            print("❌ Orgs alias not found after rollback")
            return False
        
        return True
    
    async def run_smoke_tests(self) -> bool:
        """Run smoke tests after rollback."""
        print("🧪 Running smoke tests...")
        
        # Test persons search
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
            print(f"❌ Persons smoke test failed: {result.get('error')}")
            return False
        
        persons_hits = result.get("hits", {}).get("total", {}).get("value", 0)
        print(f"✅ Persons smoke test passed: {persons_hits} documents")
        
        # Test orgs search
        success, result = await self._make_request(
            "POST",
            "/watchlist_orgs_current/_search",
            {
                "query": {
                    "term": {
                        "entity_type": "org"
                    }
                },
                "size": 1
            }
        )
        
        if not success:
            print(f"❌ Orgs smoke test failed: {result.get('error')}")
            return False
        
        orgs_hits = result.get("hits", {}).get("total", {}).get("value", 0)
        print(f"✅ Orgs smoke test passed: {orgs_hits} documents")
        
        return True
    
    async def generate_rollback_report(self) -> Dict:
        """Generate rollback metrics report."""
        rollback_time = time.time() - self.metrics["rollback_start"]
        
        report = {
            "rollback_id": self.rollback_id,
            "environment": self.environment,
            "timestamp": time.time(),
            "rollback_time_seconds": rollback_time,
            "metrics": self.metrics,
            "old_aliases": self.old_aliases,
            "new_indices": self.new_indices,
            "status": "success" if not self.metrics["errors"] else "failed"
        }
        
        return report


async def main():
    """Main rollback function."""
    parser = argparse.ArgumentParser(description="Rollback search integration")
    parser.add_argument("--environment", required=True, help="Deployment environment")
    parser.add_argument("--es-url", required=True, help="Elasticsearch URL")
    parser.add_argument("--es-auth", help="Elasticsearch auth (username:password)")
    parser.add_argument("--es-verify-ssl", action="store_true", help="Verify SSL")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    
    args = parser.parse_args()
    
    print(f"🔄 Starting search integration rollback")
    print(f"Environment: {args.environment}")
    print(f"ES URL: {args.es_url}")
    print(f"Dry run: {args.dry_run}")
    
    async with SearchRollbackManager(
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
            print("🔍 Dry run mode - discovering state only")
            await manager.discover_current_state()
            return
        
        # Rollback steps
        steps = [
            ("Discover current state", manager.discover_current_state, None),
            ("Rollback aliases", manager.rollback_aliases, None),
            ("Cleanup new indices", manager.cleanup_new_indices, None),
            ("Verify rollback", manager.verify_rollback, None),
            ("Run smoke tests", manager.run_smoke_tests, None)
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
        report = await manager.generate_rollback_report()
        
        # Save report
        report_path = f"rollback-report-{manager.rollback_id}.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Rollback completed successfully!")
        print(f"Report saved to: {report_path}")
        print(f"Rollback time: {report['rollback_time_seconds']:.2f}s")
        print(f"Aliases rolled back: {report['metrics']['aliases_rolled_back']}")
        print(f"Indices cleaned: {report['metrics']['indices_cleaned']}")


if __name__ == "__main__":
    asyncio.run(main())

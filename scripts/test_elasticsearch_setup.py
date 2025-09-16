#!/usr/bin/env python3
"""
Test script for Elasticsearch setup

Tests the setup script with mock Elasticsearch responses.
"""

import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, patch

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from elasticsearch_setup_and_warmup import ElasticsearchSetup


async def test_elasticsearch_setup():
    """Test Elasticsearch setup with mocked responses"""
    
    # Mock responses
    mock_responses = {
        "/_cluster/health": {
            "status": "green",
            "number_of_nodes": 1,
            "active_primary_shards": 0
        },
        "/_component_template/watchlist_analyzers": {
            "acknowledged": True
        },
        "/_index_template/watchlist_persons_v1": {
            "acknowledged": True
        },
        "/_index_template/watchlist_orgs_v1": {
            "acknowledged": True
        },
        "/watchlist_persons_v1_001": {
            "acknowledged": True
        },
        "/watchlist_orgs_v1_001": {
            "acknowledged": True
        },
        "/_aliases": {
            "acknowledged": True
        },
        "/watchlist_persons_v1_001/_search": {
            "hits": {"total": {"value": 0}},
            "took": 5
        },
        "/watchlist_orgs_v1_001/_search": {
            "hits": {"total": {"value": 0}},
            "took": 3
        }
    }
    
    # Mock httpx client
    async def mock_request(method, url, json=None, **kwargs):
        # Extract endpoint from URL
        endpoint = url.split("/", 3)[-1] if len(url.split("/")) > 3 else url
        
        # Find matching response
        response_data = None
        for key, value in mock_responses.items():
            if key in endpoint:
                response_data = value
                break
        
        if response_data is None:
            response_data = {"error": f"No mock response for {endpoint}"}
        
        # Create mock response
        response = AsyncMock()
        response.status_code = 200
        response.json = AsyncMock(return_value=response_data)
        response.content = b""
        response.text = json.dumps(response_data)
        
        return response
    
    # Patch httpx client
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.request = mock_request
        mock_client.aclose = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Test setup
        setup = ElasticsearchSetup()
        setup.es_url = "http://localhost:9200"
        
        print("Testing Elasticsearch setup...")
        
        # Test health check
        health_ok = await setup.health_check()
        print(f"Health check: {'PASS' if health_ok else 'FAIL'}")
        
        # Test component template creation
        template_ok = await setup.create_component_template()
        print(f"Component template: {'PASS' if template_ok else 'FAIL'}")
        
        # Test index template creation
        persons_template_ok = await setup.create_index_template(
            "watchlist_persons_v1", "watchlist_persons_v1*", "person"
        )
        print(f"Persons template: {'PASS' if persons_template_ok else 'FAIL'}")
        
        orgs_template_ok = await setup.create_index_template(
            "watchlist_orgs_v1", "watchlist_orgs_v1*", "org"
        )
        print(f"Orgs template: {'PASS' if orgs_template_ok else 'FAIL'}")
        
        # Test index creation
        persons_index_ok = await setup.create_index_with_alias(
            "watchlist_persons_v1_001", "watchlist_persons_current"
        )
        print(f"Persons index: {'PASS' if persons_index_ok else 'FAIL'}")
        
        orgs_index_ok = await setup.create_index_with_alias(
            "watchlist_orgs_v1_001", "watchlist_orgs_current"
        )
        print(f"Orgs index: {'PASS' if orgs_index_ok else 'FAIL'}")
        
        # Test warmup
        warmup_queries = await setup.get_warmup_queries()
        print(f"Warmup queries generated: {len(warmup_queries['persons'])} persons, {len(warmup_queries['orgs'])} orgs")
        
        # Test warmup search
        warmup_ok = await setup.warmup_search("watchlist_persons_v1_001", warmup_queries["persons"][:2])
        print(f"Warmup search: {'PASS' if warmup_ok else 'FAIL'}")
        
        # Cleanup
        await setup.cleanup()
        
        # Overall result
        all_tests = [
            health_ok, template_ok, persons_template_ok, orgs_template_ok,
            persons_index_ok, orgs_index_ok, warmup_ok
        ]
        
        if all(all_tests):
            print("\n✅ All tests PASSED!")
            return True
        else:
            print("\n❌ Some tests FAILED!")
            return False


async def main():
    """Main test function"""
    try:
        success = await test_elasticsearch_setup()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Test failed with exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

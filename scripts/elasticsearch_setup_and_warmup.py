#!/usr/bin/env python3
"""
Elasticsearch Setup and Warmup Script

Creates component/index templates, indices with aliases, and performs warmup.
Uses httpx + asyncio for async operations.

Usage:
    python elasticsearch_setup_and_warmup.py

Environment Variables:
    ES_URL: Elasticsearch URL (default: http://localhost:9200)
    ES_USER: Username for authentication (optional)
    ES_PASS: Password for authentication (optional)
    ES_VERIFY_SSL: Verify SSL certificates (default: true)
    ES_TIMEOUT: Request timeout in seconds (default: 30)
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import httpx


class ElasticsearchSetupError(Exception):
    """Custom exception for Elasticsearch setup errors"""
    pass


class ElasticsearchSetup:
    """Elasticsearch setup and warmup manager"""
    
    def __init__(self):
        self.es_url = os.getenv("ES_URL", "http://localhost:9200").rstrip("/")
        self.es_user = os.getenv("ES_USER")
        self.es_pass = os.getenv("ES_PASS")
        self.es_verify_ssl = os.getenv("ES_VERIFY_SSL", "true").lower() == "true"
        self.es_timeout = int(os.getenv("ES_TIMEOUT", "30"))
        
        # Setup httpx client
        auth = None
        if self.es_user and self.es_pass:
            auth = (self.es_user, self.es_pass)
        
        self.client = httpx.AsyncClient(
            auth=auth,
            verify=self.es_verify_ssl,
            timeout=self.es_timeout,
            headers={"Content-Type": "application/json"}
        )
        
        self.log_prefix = "[ES-SETUP]"
    
    async def log(self, message: str, level: str = "INFO") -> None:
        """Log message with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} {self.log_prefix} [{level}] {message}")
    
    async def make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        expected_status: int = 200
    ) -> Tuple[bool, Dict]:
        """
        Make HTTP request to Elasticsearch
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body data
            expected_status: Expected HTTP status code
            
        Returns:
            Tuple of (success, response_data)
        """
        url = urljoin(self.es_url + "/", endpoint.lstrip("/"))
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                json=data
            )
            
            if response.status_code == expected_status:
                try:
                    response_data = response.json() if response.content else {}
                    return True, response_data
                except Exception:
                    return True, {}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                return False, {"error": error_msg}
                
        except httpx.RequestError as e:
            return False, {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            return False, {"error": f"Unexpected error: {str(e)}"}
    
    async def health_check(self) -> bool:
        """Check Elasticsearch cluster health"""
        await self.log("Checking Elasticsearch health...")
        
        success, response = await self.make_request("GET", "/_cluster/health")
        if not success:
            await self.log(f"Health check failed: {response.get('error')}", "ERROR")
            return False
        
        status = response.get("status", "unknown")
        await self.log(f"Cluster status: {status}")
        
        if status in ["red", "yellow"]:
            await self.log(f"Warning: Cluster status is {status}", "WARN")
        
        return True
    
    async def create_component_template(self) -> bool:
        """Create component template with analyzers and normalizers"""
        await self.log("Creating component template: watchlist_analyzers")
        
        template_data = {
            "template": {
                "settings": {
                    "analysis": {
                        "normalizer": {
                            "case_insensitive_normalizer": {
                                "type": "custom",
                                "filter": ["lowercase", "asciifolding", "icu_folding"]
                            }
                        },
                        "analyzer": {
                            "icu_text_analyzer": {
                                "type": "custom",
                                "tokenizer": "icu_tokenizer",
                                "filter": ["icu_normalizer", "icu_folding", "lowercase"]
                            },
                            "shingle_analyzer": {
                                "type": "custom",
                                "tokenizer": "icu_tokenizer",
                                "filter": [
                                    "icu_normalizer",
                                    "icu_folding", 
                                    "lowercase",
                                    "shingle"
                                ]
                            },
                            "char_ngram_analyzer": {
                                "type": "custom",
                                "tokenizer": "keyword",
                                "filter": [
                                    "lowercase",
                                    "asciifolding",
                                    "char_ngram_filter"
                                ]
                            }
                        },
                        "filter": {
                            "char_ngram_filter": {
                                "type": "ngram",
                                "min_gram": 3,
                                "max_gram": 5,
                                "token_chars": ["letter", "digit"]
                            },
                            "shingle": {
                                "type": "shingle",
                                "min_shingle_size": 2,
                                "max_shingle_size": 3,
                                "output_unigrams": True
                            }
                        }
                    }
                }
            }
        }
        
        success, response = await self.make_request(
            "PUT", 
            "/_component_template/watchlist_analyzers",
            template_data
        )
        
        if success:
            await self.log("Component template created successfully")
            return True
        else:
            await self.log(f"Failed to create component template: {response.get('error')}", "ERROR")
            return False
    
    async def create_index_template(self, template_name: str, index_pattern: str, entity_type: str) -> bool:
        """Create index template for persons or organizations"""
        await self.log(f"Creating index template: {template_name}")
        
        template_data = {
            "index_patterns": [index_pattern],
            "template": {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 1,
                    "index": {
                        "knn": True,
                        "knn.algo_param.ef_search": 100
                    }
                },
                "mappings": {
                    "properties": {
                        "entity_id": {"type": "keyword"},
                        "entity_type": {"type": "keyword"},
                        "dob": {
                            "type": "date",
                            "format": "yyyy-MM-dd||yyyy-MM||yyyy"
                        },
                        "country": {"type": "keyword"},
                        "normalized_name": {
                            "type": "keyword",
                            "normalizer": "case_insensitive_normalizer"
                        },
                        "aliases": {
                            "type": "keyword",
                            "normalizer": "case_insensitive_normalizer"
                        },
                        "name_text": {
                            "type": "text",
                            "analyzer": "icu_text_analyzer",
                            "fields": {
                                "shingle": {
                                    "type": "text",
                                    "analyzer": "shingle_analyzer"
                                }
                            }
                        },
                        "name_ngrams": {
                            "type": "text",
                            "analyzer": "char_ngram_analyzer"
                        },
                        "name_vector": {
                            "type": "dense_vector",
                            "dims": 384,
                            "index": True,
                            "similarity": "cosine"
                        },
                        "meta": {
                            "type": "object",
                            "enabled": True
                        }
                    }
                }
            },
            "composed_of": ["watchlist_analyzers"],
            "priority": 200
        }
        
        success, response = await self.make_request(
            "PUT",
            f"/_index_template/{template_name}",
            template_data
        )
        
        if success:
            await self.log(f"Index template {template_name} created successfully")
            return True
        else:
            await self.log(f"Failed to create index template {template_name}: {response.get('error')}", "ERROR")
            return False
    
    async def create_index_with_alias(self, index_name: str, alias_name: str) -> bool:
        """Create index with alias"""
        await self.log(f"Creating index {index_name} with alias {alias_name}")
        
        # Create index
        success, response = await self.make_request(
            "PUT",
            f"/{index_name}",
            {},
            expected_status=200
        )
        
        if not success:
            await self.log(f"Failed to create index {index_name}: {response.get('error')}", "ERROR")
            return False
        
        # Create alias
        alias_data = {
            "actions": [
                {
                    "add": {
                        "index": index_name,
                        "alias": alias_name
                    }
                }
            ]
        }
        
        success, response = await self.make_request(
            "POST",
            "/_aliases",
            alias_data
        )
        
        if success:
            await self.log(f"Index {index_name} created with alias {alias_name}")
            return True
        else:
            await self.log(f"Failed to create alias {alias_name}: {response.get('error')}", "ERROR")
            return False
    
    async def warmup_search(self, index_name: str, search_queries: List[Dict]) -> bool:
        """Perform warmup searches on index"""
        await self.log(f"Warming up index {index_name}")
        
        for i, query in enumerate(search_queries, 1):
            await self.log(f"Running warmup query {i}/{len(search_queries)}")
            
            success, response = await self.make_request(
                "POST",
                f"/{index_name}/_search",
                query
            )
            
            if success:
                hits = response.get("hits", {}).get("total", {}).get("value", 0)
                took = response.get("took", 0)
                await self.log(f"Query {i} completed: {hits} hits in {took}ms")
            else:
                await self.log(f"Query {i} failed: {response.get('error')}", "WARN")
        
        return True
    
    async def get_warmup_queries(self) -> Dict[str, List[Dict]]:
        """Get warmup queries for different search types"""
        return {
            "persons": [
                # Empty search
                {"query": {"match_all": {}}, "size": 0},
                
                # AC search - exact match
                {
                    "query": {
                        "multi_match": {
                            "query": "Иван Петров",
                            "fields": ["normalized_name^2.0", "aliases^1.5"],
                            "type": "best_fields",
                            "fuzziness": 1
                        }
                    },
                    "size": 10
                },
                
                # AC search - fuzzy match
                {
                    "query": {
                        "multi_match": {
                            "query": "иван петров",
                            "fields": ["normalized_name", "aliases"],
                            "type": "best_fields",
                            "fuzziness": 2
                        }
                    },
                    "size": 10
                },
                
                # Phrase search
                {
                    "query": {
                        "match_phrase": {
                            "name_text.shingle": {
                                "query": "Иван Петров",
                                "boost": 2.0
                            }
                        }
                    },
                    "size": 10
                },
                
                # N-gram search
                {
                    "query": {
                        "match": {
                            "name_ngrams": {
                                "query": "иван",
                                "operator": "and"
                            }
                        }
                    },
                    "size": 10
                },
                
                # Vector search (mock vector)
                {
                    "knn": {
                        "field": "name_vector",
                        "query_vector": [0.1] * 384,  # Mock 384-dim vector
                        "k": 10,
                        "num_candidates": 100
                    },
                    "size": 10
                }
            ],
            "orgs": [
                # Empty search
                {"query": {"match_all": {}}, "size": 0},
                
                # AC search - company name
                {
                    "query": {
                        "multi_match": {
                            "query": "Газпром",
                            "fields": ["normalized_name^2.0", "aliases^1.5"],
                            "type": "best_fields",
                            "fuzziness": 1
                        }
                    },
                    "size": 10
                },
                
                # Fuzzy company search
                {
                    "query": {
                        "multi_match": {
                            "query": "газпром",
                            "fields": ["normalized_name", "aliases"],
                            "type": "best_fields",
                            "fuzziness": 2
                        }
                    },
                    "size": 10
                },
                
                # Phrase search
                {
                    "query": {
                        "match_phrase": {
                            "name_text.shingle": {
                                "query": "Газпром Нефть",
                                "boost": 2.0
                            }
                        }
                    },
                    "size": 10
                },
                
                # N-gram search
                {
                    "query": {
                        "match": {
                            "name_ngrams": {
                                "query": "газпром",
                                "operator": "and"
                            }
                        }
                    },
                    "size": 10
                },
                
                # Vector search (mock vector)
                {
                    "knn": {
                        "field": "name_vector",
                        "query_vector": [0.2] * 384,  # Mock 384-dim vector
                        "k": 10,
                        "num_candidates": 100
                    },
                    "size": 10
                }
            ]
        }
    
    async def run_setup(self) -> bool:
        """Run complete setup process"""
        start_time = time.time()
        
        try:
            # 1. Health check
            if not await self.health_check():
                return False
            
            # 2. Create component template
            if not await self.create_component_template():
                return False
            
            # 3. Create index templates
            if not await self.create_index_template("watchlist_persons_v1", "watchlist_persons_v1*", "person"):
                return False
            
            if not await self.create_index_template("watchlist_orgs_v1", "watchlist_orgs_v1*", "org"):
                return False
            
            # 4. Create indices with aliases
            if not await self.create_index_with_alias("watchlist_persons_v1_001", "watchlist_persons_current"):
                return False
            
            if not await self.create_index_with_alias("watchlist_orgs_v1_001", "watchlist_orgs_current"):
                return False
            
            # 5. Warmup searches
            warmup_queries = await self.get_warmup_queries()
            
            if not await self.warmup_search("watchlist_persons_v1_001", warmup_queries["persons"]):
                await self.log("Warmup for persons index failed", "WARN")
            
            if not await self.warmup_search("watchlist_orgs_v1_001", warmup_queries["orgs"]):
                await self.log("Warmup for orgs index failed", "WARN")
            
            # 6. Final health check
            await self.log("Performing final health check...")
            if not await self.health_check():
                await self.log("Final health check failed", "WARN")
            
            elapsed_time = time.time() - start_time
            await self.log(f"Setup completed successfully in {elapsed_time:.2f} seconds")
            return True
            
        except Exception as e:
            await self.log(f"Setup failed with exception: {str(e)}", "ERROR")
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.client.aclose()


async def main():
    """Main function"""
    setup = ElasticsearchSetup()
    
    try:
        success = await setup.run_setup()
        exit_code = 0 if success else 1
        sys.exit(exit_code)
    except KeyboardInterrupt:
        await setup.log("Setup interrupted by user", "WARN")
        sys.exit(130)
    except Exception as e:
        await setup.log(f"Unexpected error: {str(e)}", "ERROR")
        sys.exit(1)
    finally:
        await setup.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

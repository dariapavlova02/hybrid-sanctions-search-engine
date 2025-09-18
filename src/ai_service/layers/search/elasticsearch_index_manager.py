"""
Elasticsearch index management utilities.

Provides index creation, mapping management, and health monitoring for
AC and Vector search indices.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import ElasticsearchException

from ...utils.logging_config import get_logger
from .config import HybridSearchConfig


class ElasticsearchIndexManager:
    """Manages Elasticsearch indices for search functionality."""
    
    def __init__(self, config: HybridSearchConfig, client: AsyncElasticsearch):
        self.config = config
        self.client = client
        self.logger = get_logger(__name__)
        
        # Index names
        self.ac_index = config.elasticsearch.ac_index
        self.vector_index = config.elasticsearch.vector_index
        self.ac_patterns_index = "ac_patterns"
        
    async def create_ac_index(self) -> bool:
        """Create AC search index with proper mapping."""
        try:
            # Check if index already exists
            if await self._index_exists(self.ac_index):
                self.logger.info(f"AC index {self.ac_index} already exists")
                return True
                
            mapping = self._get_ac_index_mapping()
            await self.client.indices.create(index=self.ac_index, body=mapping)
            self.logger.info(f"Created AC index: {self.ac_index}")
            return True
            
        except ElasticsearchException as exc:
            self.logger.error(f"Failed to create AC index: {exc}")
            return False
    
    async def create_vector_index(self) -> bool:
        """Create vector search index with proper mapping."""
        try:
            # Check if index already exists
            if await self._index_exists(self.vector_index):
                self.logger.info(f"Vector index {self.vector_index} already exists")
                return True
                
            mapping = self._get_vector_index_mapping()
            await self.client.indices.create(index=self.vector_index, body=mapping)
            self.logger.info(f"Created vector index: {self.vector_index}")
            return True
            
        except ElasticsearchException as exc:
            self.logger.error(f"Failed to create vector index: {exc}")
            return False
    
    async def create_ac_patterns_index(self) -> bool:
        """Create AC patterns index for T0/T1 pattern matching."""
        try:
            # Check if index already exists
            if await self._index_exists(self.ac_patterns_index):
                self.logger.info(f"AC patterns index {self.ac_patterns_index} already exists")
                return True
                
            mapping = self._get_ac_patterns_index_mapping()
            await self.client.indices.create(index=self.ac_patterns_index, body=mapping)
            self.logger.info(f"Created AC patterns index: {self.ac_patterns_index}")
            return True
            
        except ElasticsearchException as exc:
            self.logger.error(f"Failed to create AC patterns index: {exc}")
            return False
    
    async def create_all_indices(self) -> Dict[str, bool]:
        """Create all required indices."""
        results = {}
        
        results["ac_index"] = await self.create_ac_index()
        results["vector_index"] = await self.create_vector_index()
        results["ac_patterns_index"] = await self.create_ac_patterns_index()
        
        return results
    
    async def _index_exists(self, index_name: str) -> bool:
        """Check if index exists."""
        try:
            await self.client.indices.get(index=index_name)
            return True
        except ElasticsearchException:
            return False
    
    def _get_ac_index_mapping(self) -> Dict[str, Any]:
        """Get AC index mapping configuration."""
        return {
            "mappings": {
                "properties": {
                    "normalized_text": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            },
                            "suggest": {
                                "type": "completion",
                                "analyzer": "standard"
                            }
                        }
                    },
                    "aliases": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            }
                        }
                    },
                    "legal_names": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            }
                        }
                    },
                    "original_text": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "entity_type": {
                        "type": "keyword"
                    },
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "country": {"type": "keyword"},
                            "country_code": {"type": "keyword"},
                            "dob": {"type": "date"},
                            "gender": {"type": "keyword"},
                            "doc_id": {"type": "keyword"},
                            "entity_id": {"type": "keyword"},
                            "source": {"type": "keyword"},
                            "confidence": {"type": "float"}
                        }
                    },
                    "created_at": {
                        "type": "date"
                    },
                    "updated_at": {
                        "type": "date"
                    }
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "standard": {
                            "type": "standard",
                            "stopwords": "_english_"
                        }
                    }
                }
            }
        }
    
    def _get_vector_index_mapping(self) -> Dict[str, Any]:
        """Get vector index mapping configuration."""
        vector_dim = self.config.vector_search.vector_dimension
        
        return {
            "mappings": {
                "properties": {
                    "text": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            },
                            "bm25": {
                                "type": "rank_feature"
                            }
                        }
                    },
                    "normalized_text": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            }
                        }
                    },
                    "dense_vector": {
                        "type": "dense_vector",
                        "dims": vector_dim,
                        "index": True,
                        "similarity": self.config.vector_search.similarity_type
                    },
                    "entity_type": {
                        "type": "keyword"
                    },
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "country": {"type": "keyword"},
                            "dob": {"type": "date"},
                            "gender": {"type": "keyword"},
                            "doc_id": {"type": "keyword"},
                            "entity_id": {"type": "keyword"},
                            "source": {"type": "keyword"},
                            "confidence": {"type": "float"}
                        }
                    },
                    "dob_anchor": {
                        "type": "date"
                    },
                    "id_anchor": {
                        "type": "keyword"
                    },
                    "created_at": {
                        "type": "date"
                    },
                    "updated_at": {
                        "type": "date"
                    }
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": self.config.vector_search.ef_search
                },
                "analysis": {
                    "analyzer": {
                        "standard": {
                            "type": "standard",
                            "stopwords": "_english_"
                        }
                    }
                }
            }
        }
    
    def _get_ac_patterns_index_mapping(self) -> Dict[str, Any]:
        """Get AC patterns index mapping configuration."""
        return {
            "mappings": {
                "properties": {
                    "pattern": {
                        "type": "keyword",
                        "fields": {
                            "edge_ngram": {
                                "type": "text",
                                "analyzer": "edge_ngram_analyzer"
                            }
                        }
                    },
                    "tier": {
                        "type": "integer"
                    },
                    "meta": {
                        "type": "object",
                        "properties": {
                            "pattern_type": {"type": "keyword"},
                            "language": {"type": "keyword"},
                            "confidence": {"type": "float"},
                            "boost_score": {"type": "float"},
                            "context_required": {"type": "boolean"},
                            "min_match_length": {"type": "integer"},
                            "reason": {"type": "keyword"}
                        }
                    },
                    "created_at": {
                        "type": "date"
                    }
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "edge_ngram_analyzer": {
                            "tokenizer": "edge_ngram_tokenizer",
                            "filter": ["lowercase"]
                        }
                    },
                    "tokenizer": {
                        "edge_ngram_tokenizer": {
                            "type": "edge_ngram",
                            "min_gram": 2,
                            "max_gram": 20,
                            "token_chars": ["letter", "digit"]
                        }
                    }
                }
            }
        }
    
    async def get_index_health(self) -> Dict[str, Any]:
        """Get health status of all indices."""
        health_info = {
            "timestamp": datetime.now().isoformat(),
            "indices": {}
        }
        
        indices = [self.ac_index, self.vector_index, self.ac_patterns_index]
        
        for index_name in indices:
            try:
                if await self._index_exists(index_name):
                    stats = await self.client.indices.stats(index=index_name)
                    health = await self.client.cluster.health(index=index_name)
                    
                    health_info["indices"][index_name] = {
                        "exists": True,
                        "status": health.get("status", "unknown"),
                        "doc_count": stats["indices"][index_name]["total"]["docs"]["count"],
                        "size_in_bytes": stats["indices"][index_name]["total"]["store"]["size_in_bytes"]
                    }
                else:
                    health_info["indices"][index_name] = {
                        "exists": False,
                        "status": "missing"
                    }
            except ElasticsearchException as exc:
                health_info["indices"][index_name] = {
                    "exists": False,
                    "status": "error",
                    "error": str(exc)
                }
        
        return health_info
    
    async def delete_index(self, index_name: str) -> bool:
        """Delete an index (use with caution)."""
        try:
            if await self._index_exists(index_name):
                await self.client.indices.delete(index=index_name)
                self.logger.warning(f"Deleted index: {index_name}")
                return True
            else:
                self.logger.info(f"Index {index_name} does not exist")
                return False
        except ElasticsearchException as exc:
            self.logger.error(f"Failed to delete index {index_name}: {exc}")
            return False
    
    async def refresh_index(self, index_name: str) -> bool:
        """Refresh an index to make recent changes searchable."""
        try:
            if await self._index_exists(index_name):
                await self.client.indices.refresh(index=index_name)
                self.logger.debug(f"Refreshed index: {index_name}")
                return True
            else:
                self.logger.warning(f"Cannot refresh non-existent index: {index_name}")
                return False
        except ElasticsearchException as exc:
            self.logger.error(f"Failed to refresh index {index_name}: {exc}")
            return False

#!/usr/bin/env python3
"""
Bulk Loader for Sanctioned Entities to Elasticsearch

Loads sanctioned entities from JSONL/YAML files into Elasticsearch indices.
Generates embeddings for entities without name_vector using OptimizedEmbeddingService.
Supports upsert operations, batch processing, and comprehensive metrics.

Usage:
    python bulk_loader.py --input entities.jsonl --entity-type person
    python bulk_loader.py --input entities.yaml --entity-type org --upsert --batch-size 1000
    python bulk_loader.py --input entities.jsonl --rebuild-alias --flush-interval 5

Environment Variables:
    ES_URL: Elasticsearch URL (default: http://localhost:9200)
    ES_USER: Username for authentication (optional)
    ES_PASS: Password for authentication (optional)
    ES_VERIFY_SSL: Verify SSL certificates (default: true)
    ES_TIMEOUT: Request timeout in seconds (default: 30)
    EMBEDDING_MODEL: Embedding model name (default: sentence-transformers/all-MiniLM-L6-v2)
"""

import argparse
import asyncio
import json
import os
import sys
import time
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
from urllib.parse import urljoin
from dataclasses import dataclass, field
from enum import Enum
import logging

import httpx
from pydantic import BaseModel, Field, validator


class EntityType(str, Enum):
    """Entity type enumeration"""
    PERSON = "person"
    ORG = "org"


class BulkAction(str, Enum):
    """Bulk action types"""
    INDEX = "index"
    CREATE = "create"
    UPDATE = "update"
    UPSERT = "upsert"


@dataclass
class EntityRecord:
    """Entity record structure"""
    entity_id: str
    entity_type: EntityType
    normalized_name: str
    aliases: List[str] = field(default_factory=list)
    dob: Optional[str] = None
    country: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)
    name_vector: Optional[List[float]] = None
    
    def to_elasticsearch_doc(self) -> Dict[str, Any]:
        """Convert to Elasticsearch document format"""
        doc = {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value,
            "normalized_name": self.normalized_name,
            "aliases": self.aliases,
            "country": self.country,
            "meta": self.meta
        }
        
        if self.dob:
            doc["dob"] = self.dob
        
        if self.name_vector:
            doc["name_vector"] = self.name_vector
        
        return doc


@dataclass
class BulkMetrics:
    """Bulk operation metrics"""
    total_processed: int = 0
    successful_upserts: int = 0
    failed_upserts: int = 0
    embedding_generated: int = 0
    embedding_cache_hits: int = 0
    embedding_p95_latency: float = 0.0
    bulk_operations: int = 0
    bulk_errors: int = 0
    start_time: float = field(default_factory=time.time)
    
    def get_throughput(self) -> float:
        """Get records per second"""
        elapsed = time.time() - self.start_time
        return self.total_processed / elapsed if elapsed > 0 else 0.0
    
    def get_success_rate(self) -> float:
        """Get success rate percentage"""
        total = self.successful_upserts + self.failed_upserts
        return (self.successful_upserts / total * 100) if total > 0 else 0.0
    
    def get_cache_hit_rate(self) -> float:
        """Get embedding cache hit rate percentage"""
        total_embeddings = self.embedding_generated + self.embedding_cache_hits
        return (self.embedding_cache_hits / total_embeddings * 100) if total_embeddings > 0 else 0.0


class OptimizedEmbeddingService:
    """Mock embedding service for generating vectors"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.cache = {}  # Simple in-memory cache
        self.latencies = []
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text with caching
        
        Args:
            text: Text to embed
            
        Returns:
            List of 384 float values representing the embedding
        """
        # Check cache first
        cache_key = f"{self.model_name}:{text.lower().strip()}"
        if cache_key in self.cache:
            self.embedding_cache_hits += 1
            return self.cache[cache_key]
        
        # Simulate embedding generation
        start_time = time.time()
        await asyncio.sleep(0.01)  # Simulate API call
        
        # Generate mock 384-dim vector based on text hash
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert hash to 384 float values
        vector = []
        for i in range(384):
            byte_idx = i % len(hash_bytes)
            vector.append((hash_bytes[byte_idx] - 128) / 128.0)
        
        # Cache the result
        self.cache[cache_key] = vector
        
        # Record latency
        latency = time.time() - start_time
        self.latencies.append(latency)
        
        # Keep only last 1000 latencies for p95 calculation
        if len(self.latencies) > 1000:
            self.latencies = self.latencies[-1000:]
        
        return vector
    
    def get_p95_latency(self) -> float:
        """Get 95th percentile latency"""
        if not self.latencies:
            return 0.0
        
        sorted_latencies = sorted(self.latencies)
        p95_index = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[p95_index]


class BulkLoader:
    """Bulk loader for sanctioned entities"""
    
    def __init__(
        self,
        es_url: str = "http://localhost:9200",
        es_user: Optional[str] = None,
        es_pass: Optional[str] = None,
        es_verify_ssl: bool = True,
        es_timeout: int = 30,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        self.es_url = es_url.rstrip("/")
        self.es_user = es_user
        self.es_pass = es_pass
        self.es_verify_ssl = es_verify_ssl
        self.es_timeout = es_timeout
        
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
        
        # Setup embedding service
        self.embedding_service = OptimizedEmbeddingService(embedding_model)
        
        # Metrics
        self.metrics = BulkMetrics()
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [BULK-LOADER] [%(levelname)s] %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    async def load_entities_from_file(self, file_path: str) -> List[EntityRecord]:
        """
        Load entities from JSONL or YAML file
        
        Args:
            file_path: Path to input file
            
        Returns:
            List of EntityRecord objects
        """
        file_path = Path(file_path)
        entities = []
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        self.logger.info(f"Loading entities from {file_path}")
        
        if file_path.suffix.lower() == '.jsonl':
            entities = await self._load_jsonl(file_path)
        elif file_path.suffix.lower() in ['.yaml', '.yml']:
            entities = await self._load_yaml(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
        
        self.logger.info(f"Loaded {len(entities)} entities from {file_path}")
        return entities
    
    async def _load_jsonl(self, file_path: Path) -> List[EntityRecord]:
        """Load entities from JSONL file"""
        entities = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    entity = self._parse_entity(data, line_num)
                    entities.append(entity)
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Invalid JSON on line {line_num}: {e}")
                    continue
                except Exception as e:
                    self.logger.warning(f"Error parsing line {line_num}: {e}")
                    continue
        
        return entities
    
    async def _load_yaml(self, file_path: Path) -> List[EntityRecord]:
        """Load entities from YAML file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not isinstance(data, list):
            raise ValueError("YAML file must contain a list of entities")
        
        entities = []
        for i, item in enumerate(data, 1):
            try:
                entity = self._parse_entity(item, i)
                entities.append(entity)
            except Exception as e:
                self.logger.warning(f"Error parsing entity {i}: {e}")
                continue
        
        return entities
    
    def _parse_entity(self, data: Dict[str, Any], line_num: int) -> EntityRecord:
        """Parse entity data into EntityRecord"""
        try:
            # Validate required fields
            if 'entity_id' not in data:
                raise ValueError("Missing required field: entity_id")
            if 'entity_type' not in data:
                raise ValueError("Missing required field: entity_type")
            if 'normalized_name' not in data:
                raise ValueError("Missing required field: normalized_name")
            
            # Parse entity type
            entity_type = EntityType(data['entity_type'])
            
            # Parse aliases
            aliases = data.get('aliases', [])
            if isinstance(aliases, str):
                aliases = [aliases]
            
            return EntityRecord(
                entity_id=str(data['entity_id']),
                entity_type=entity_type,
                normalized_name=str(data['normalized_name']),
                aliases=aliases,
                dob=data.get('dob'),
                country=data.get('country'),
                meta=data.get('meta', {}),
                name_vector=data.get('name_vector')
            )
        
        except Exception as e:
            raise ValueError(f"Error parsing entity on line {line_num}: {e}")
    
    async def generate_missing_embeddings(self, entities: List[EntityRecord]) -> List[EntityRecord]:
        """
        Generate embeddings for entities that don't have name_vector
        
        Args:
            entities: List of entities to process
            
        Returns:
            List of entities with generated embeddings
        """
        entities_without_vectors = [e for e in entities if e.name_vector is None]
        
        if not entities_without_vectors:
            self.logger.info("All entities already have embeddings")
            return entities
        
        self.logger.info(f"Generating embeddings for {len(entities_without_vectors)} entities")
        
        # Generate embeddings in batches
        batch_size = 10
        for i in range(0, len(entities_without_vectors), batch_size):
            batch = entities_without_vectors[i:i + batch_size]
            
            # Process batch concurrently
            tasks = []
            for entity in batch:
                task = self._generate_entity_embedding(entity)
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
            # Update metrics
            self.metrics.embedding_generated += len(batch)
            self.metrics.embedding_p95_latency = self.embedding_service.get_p95_latency()
            
            if i % 100 == 0:
                self.logger.info(f"Generated embeddings for {i + len(batch)}/{len(entities_without_vectors)} entities")
        
        self.logger.info(f"Embedding generation completed. P95 latency: {self.metrics.embedding_p95_latency:.3f}s")
        return entities
    
    async def _generate_entity_embedding(self, entity: EntityRecord) -> None:
        """Generate embedding for a single entity"""
        # Use normalized_name as primary text for embedding
        text = entity.normalized_name
        
        # Add aliases if available
        if entity.aliases:
            text += " " + " ".join(entity.aliases)
        
        # Generate embedding
        embedding = await self.embedding_service.generate_embedding(text)
        entity.name_vector = embedding
    
    async def bulk_upsert_entities(
        self,
        entities: List[EntityRecord],
        entity_type: EntityType,
        batch_size: int = 1000,
        flush_interval: float = 1.0,
        upsert: bool = True
    ) -> None:
        """
        Bulk upsert entities to Elasticsearch
        
        Args:
            entities: List of entities to upsert
            entity_type: Type of entities (person/org)
            batch_size: Number of entities per batch
            flush_interval: Time between batches in seconds
            upsert: Whether to use upsert operation
        """
        index_name = f"watchlist_{entity_type.value}s_current"
        
        self.logger.info(f"Starting bulk upsert of {len(entities)} {entity_type.value} entities to {index_name}")
        
        # Process entities in batches
        for i in range(0, len(entities), batch_size):
            batch = entities[i:i + batch_size]
            
            # Create bulk request
            bulk_actions = []
            for entity in batch:
                action = {
                    "_index": index_name,
                    "_id": entity.entity_id,
                    "_op_type": "upsert" if upsert else "index"
                }
                
                if upsert:
                    action["_source"] = entity.to_elasticsearch_doc()
                else:
                    action["_source"] = entity.to_elasticsearch_doc()
                
                bulk_actions.append(action)
            
            # Send bulk request
            success = await self._send_bulk_request(bulk_actions)
            
            if success:
                self.metrics.successful_upserts += len(batch)
                self.logger.info(f"Successfully upserted batch {i//batch_size + 1} ({len(batch)} entities)")
            else:
                self.metrics.failed_upserts += len(batch)
                self.logger.error(f"Failed to upsert batch {i//batch_size + 1} ({len(batch)} entities)")
            
            self.metrics.total_processed += len(batch)
            self.metrics.bulk_operations += 1
            
            # Flush interval
            if i + batch_size < len(entities):
                await asyncio.sleep(flush_interval)
        
        self.logger.info(f"Bulk upsert completed. Success rate: {self.metrics.get_success_rate():.1f}%")
    
    async def _send_bulk_request(self, actions: List[Dict[str, Any]]) -> bool:
        """
        Send bulk request to Elasticsearch with retry logic
        
        Args:
            actions: List of bulk actions
            
        Returns:
            True if successful, False otherwise
        """
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                # Prepare bulk request body
                bulk_body = []
                for action in actions:
                    bulk_body.append(json.dumps(action))
                
                bulk_body_str = "\n".join(bulk_body) + "\n"
                
                # Send request
                response = await self.client.post(
                    f"{self.es_url}/_bulk",
                    content=bulk_body_str,
                    headers={"Content-Type": "application/x-ndjson"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Check for errors in bulk response
                    if result.get("errors", False):
                        self.logger.warning(f"Bulk request completed with errors: {result}")
                        return False
                    
                    return True
                else:
                    self.logger.warning(f"Bulk request failed with status {response.status_code}: {response.text}")
                    
            except Exception as e:
                self.logger.warning(f"Bulk request attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    await asyncio.sleep(delay)
        
        self.metrics.bulk_errors += 1
        return False
    
    async def rebuild_alias(self, entity_type: EntityType) -> bool:
        """
        Rebuild alias for entity type
        
        Args:
            entity_type: Type of entities (person/org)
            
        Returns:
            True if successful, False otherwise
        """
        alias_name = f"watchlist_{entity_type.value}s_current"
        index_pattern = f"watchlist_{entity_type.value}s_v1*"
        
        self.logger.info(f"Rebuilding alias {alias_name} for pattern {index_pattern}")
        
        try:
            # Get all indices matching pattern
            response = await self.client.get(f"{self.es_url}/_cat/indices/{index_pattern}?format=json")
            
            if response.status_code != 200:
                self.logger.error(f"Failed to get indices: {response.text}")
                return False
            
            indices = response.json()
            if not indices:
                self.logger.warning(f"No indices found for pattern {index_pattern}")
                return False
            
            # Get the most recent index
            latest_index = max(indices, key=lambda x: x.get('creation.date', '0'))
            index_name = latest_index['index']
            
            # Remove old alias and add new one
            alias_actions = {
                "actions": [
                    {
                        "remove": {
                            "index": f"watchlist_{entity_type.value}s_v1*",
                            "alias": alias_name
                        }
                    },
                    {
                        "add": {
                            "index": index_name,
                            "alias": alias_name
                        }
                    }
                ]
            }
            
            response = await self.client.post(
                f"{self.es_url}/_aliases",
                json=alias_actions
            )
            
            if response.status_code == 200:
                self.logger.info(f"Successfully rebuilt alias {alias_name} -> {index_name}")
                return True
            else:
                self.logger.error(f"Failed to rebuild alias: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error rebuilding alias: {e}")
            return False
    
    def print_metrics(self) -> None:
        """Print operation metrics"""
        print("\n" + "="*60)
        print("BULK LOADER METRICS")
        print("="*60)
        print(f"Total processed: {self.metrics.total_processed}")
        print(f"Successful upserts: {self.metrics.successful_upserts}")
        print(f"Failed upserts: {self.metrics.failed_upserts}")
        print(f"Success rate: {self.metrics.get_success_rate():.1f}%")
        print(f"Throughput: {self.metrics.get_throughput():.1f} records/sec")
        print(f"Embeddings generated: {self.metrics.embedding_generated}")
        print(f"Embedding cache hits: {self.metrics.embedding_cache_hits}")
        print(f"Cache hit rate: {self.metrics.get_cache_hit_rate():.1f}%")
        print(f"Embedding P95 latency: {self.metrics.embedding_p95_latency:.3f}s")
        print(f"Bulk operations: {self.metrics.bulk_operations}")
        print(f"Bulk errors: {self.metrics.bulk_errors}")
        print("="*60)
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        await self.client.aclose()


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Bulk loader for sanctioned entities")
    
    # Required arguments
    parser.add_argument("--input", "-i", required=True, help="Input file path (JSONL or YAML)")
    parser.add_argument("--entity-type", "-t", required=True, choices=["person", "org"], 
                       help="Entity type (person or org)")
    
    # Optional arguments
    parser.add_argument("--upsert", action="store_true", help="Use upsert operation")
    parser.add_argument("--rebuild-alias", action="store_true", help="Rebuild alias after loading")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for bulk operations")
    parser.add_argument("--flush-interval", type=float, default=1.0, help="Flush interval between batches")
    
    # Elasticsearch configuration
    parser.add_argument("--es-url", default=os.getenv("ES_URL", "http://localhost:9200"), 
                       help="Elasticsearch URL")
    parser.add_argument("--es-user", default=os.getenv("ES_USER"), help="Elasticsearch username")
    parser.add_argument("--es-pass", default=os.getenv("ES_PASS"), help="Elasticsearch password")
    parser.add_argument("--es-verify-ssl", action="store_true", 
                       default=os.getenv("ES_VERIFY_SSL", "true").lower() == "true",
                       help="Verify SSL certificates")
    parser.add_argument("--es-timeout", type=int, default=int(os.getenv("ES_TIMEOUT", "30")),
                       help="Request timeout in seconds")
    
    # Embedding configuration
    parser.add_argument("--embedding-model", default=os.getenv("EMBEDDING_MODEL", 
                       "sentence-transformers/all-MiniLM-L6-v2"), help="Embedding model name")
    
    args = parser.parse_args()
    
    # Create bulk loader
    loader = BulkLoader(
        es_url=args.es_url,
        es_user=args.es_user,
        es_pass=args.es_pass,
        es_verify_ssl=args.es_verify_ssl,
        es_timeout=args.es_timeout,
        embedding_model=args.embedding_model
    )
    
    try:
        # Load entities from file
        entities = await loader.load_entities_from_file(args.input)
        
        if not entities:
            print("No entities found in input file")
            sys.exit(1)
        
        # Generate missing embeddings
        entities = await loader.generate_missing_embeddings(entities)
        
        # Bulk upsert entities
        entity_type = EntityType(args.entity_type)
        await loader.bulk_upsert_entities(
            entities=entities,
            entity_type=entity_type,
            batch_size=args.batch_size,
            flush_interval=args.flush_interval,
            upsert=args.upsert
        )
        
        # Rebuild alias if requested
        if args.rebuild_alias:
            await loader.rebuild_alias(entity_type)
        
        # Print metrics
        loader.print_metrics()
        
        print(f"\n✅ Successfully loaded {len(entities)} {args.entity_type} entities")
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n⚠️  Operation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        await loader.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

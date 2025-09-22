"""
Admin API endpoints for data loading and management.
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .elasticsearch_wrapper import ElasticsearchClient
from ..layers.embeddings.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# Request/Response models
class ACPatternsBulkRequest(BaseModel):
    """Request model for bulk AC patterns loading."""
    patterns: List[Dict[str, Any]] = Field(..., description="List of AC patterns to load")
    category: str = Field(..., description="Pattern category (person/company/terrorism)")
    tier: str = Field(..., description="Pattern tier (tier_0_exact, tier_1_high, etc.)")
    batch_size: int = Field(default=1000, description="Bulk indexing batch size")

class VectorsBulkRequest(BaseModel):
    """Request model for bulk vectors loading."""
    vectors: List[Dict[str, Any]] = Field(..., description="List of name-vector pairs")
    category: str = Field(..., description="Vector category (person/company)")
    model_name: str = Field(..., description="Embedding model name")
    batch_size: int = Field(default=500, description="Bulk indexing batch size")

class LoadingStatusResponse(BaseModel):
    """Response model for loading status."""
    success: bool
    message: str
    loaded_count: int
    errors: List[str] = []
    processing_time: float

# Global loading status tracking
loading_status = {
    "ac_patterns": {"status": "idle", "progress": 0, "total": 0},
    "vectors": {"status": "idle", "progress": 0, "total": 0}
}

@router.post("/ac-patterns/bulk", response_model=LoadingStatusResponse)
async def load_ac_patterns_bulk(
    background_tasks: BackgroundTasks,
    request: ACPatternsBulkRequest
):
    """
    Load AC patterns in bulk to Elasticsearch.

    Supports loading patterns by categories and tiers with configurable batch sizes.
    """
    try:
        # Validate category and tier
        valid_categories = ["person", "company", "terrorism"]
        valid_tiers = ["tier_0_exact", "tier_1_high", "tier_2_medium", "tier_3_low", "tier_4_experimental"]

        if request.category not in valid_categories:
            raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {valid_categories}")

        if request.tier not in valid_tiers:
            raise HTTPException(status_code=400, detail=f"Invalid tier. Must be one of: {valid_tiers}")

        # Start background loading
        background_tasks.add_task(
            _load_ac_patterns_background,
            request.patterns,
            request.category,
            request.tier,
            request.batch_size
        )

        return LoadingStatusResponse(
            success=True,
            message=f"Started loading {len(request.patterns)} AC patterns for {request.category}/{request.tier}",
            loaded_count=0,
            processing_time=0.0
        )

    except Exception as e:
        logger.error(f"Failed to start AC patterns loading: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start loading: {str(e)}")

@router.post("/vectors/bulk", response_model=LoadingStatusResponse)
async def load_vectors_bulk(
    background_tasks: BackgroundTasks,
    request: VectorsBulkRequest
):
    """
    Load name vectors in bulk to Elasticsearch.

    Supports loading pre-computed embeddings for semantic search.
    """
    try:
        # Validate category
        valid_categories = ["person", "company"]

        if request.category not in valid_categories:
            raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {valid_categories}")

        # Start background loading
        background_tasks.add_task(
            _load_vectors_background,
            request.vectors,
            request.category,
            request.model_name,
            request.batch_size
        )

        return LoadingStatusResponse(
            success=True,
            message=f"Started loading {len(request.vectors)} vectors for {request.category}",
            loaded_count=0,
            processing_time=0.0
        )

    except Exception as e:
        logger.error(f"Failed to start vectors loading: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start loading: {str(e)}")

@router.post("/ac-patterns/upload")
async def upload_ac_patterns_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: str = Form(...),
    batch_size: int = Form(default=1000)
):
    """
    Upload AC patterns file and load to Elasticsearch.

    Accepts JSON files with AC patterns structure.
    """
    try:
        # Validate file type
        if not file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="File must be a JSON file")

        # Read and parse file
        content = await file.read()
        patterns_data = json.loads(content)

        # Validate structure
        if not isinstance(patterns_data, dict):
            raise HTTPException(status_code=400, detail="File must contain a JSON object with tier data")

        total_patterns = sum(len(patterns) for patterns in patterns_data.values() if isinstance(patterns, list))

        # Start background loading for all tiers
        background_tasks.add_task(
            _load_ac_patterns_file_background,
            patterns_data,
            category,
            batch_size
        )

        return LoadingStatusResponse(
            success=True,
            message=f"Started loading {total_patterns} patterns from {file.filename}",
            loaded_count=0,
            processing_time=0.0
        )

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to upload AC patterns file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

@router.post("/vectors/upload")
async def upload_vectors_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: str = Form(...),
    model_name: str = Form(...),
    batch_size: int = Form(default=500)
):
    """
    Upload vectors file and load to Elasticsearch.

    Accepts JSON files with name-vector pairs.
    """
    try:
        # Validate file type
        if not file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="File must be a JSON file")

        # Read and parse file
        content = await file.read()
        vectors_data = json.loads(content)

        # Validate structure
        if not isinstance(vectors_data, list):
            raise HTTPException(status_code=400, detail="File must contain a JSON array of vectors")

        # Start background loading
        background_tasks.add_task(
            _load_vectors_file_background,
            vectors_data,
            category,
            model_name,
            batch_size
        )

        return LoadingStatusResponse(
            success=True,
            message=f"Started loading {len(vectors_data)} vectors from {file.filename}",
            loaded_count=0,
            processing_time=0.0
        )

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to upload vectors file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

@router.get("/loading-status")
async def get_loading_status():
    """Get current loading status for all operations."""
    return JSONResponse(content=loading_status)

@router.delete("/indices/{index_name}")
async def delete_index(index_name: str):
    """Delete an Elasticsearch index."""
    try:
        es_client = ElasticsearchClient()

        if await es_client.client.indices.exists(index=index_name):
            await es_client.client.indices.delete(index=index_name)
            await es_client.close()

            return {"success": True, "message": f"Deleted index: {index_name}"}
        else:
            await es_client.close()
            raise HTTPException(status_code=404, detail=f"Index '{index_name}' not found")

    except Exception as e:
        logger.error(f"Failed to delete index {index_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete index: {str(e)}")

@router.get("/indices")
async def list_indices():
    """List all Elasticsearch indices."""
    try:
        es_client = ElasticsearchClient()

        indices = await es_client.client.cat.indices(format="json")
        await es_client.close()

        return {"indices": [idx["index"] for idx in indices]}

    except Exception as e:
        logger.error(f"Failed to list indices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list indices: {str(e)}")

# Background task functions
async def _load_ac_patterns_background(
    patterns: List[Dict[str, Any]],
    category: str,
    tier: str,
    batch_size: int
):
    """Background task to load AC patterns."""
    loading_status["ac_patterns"]["status"] = "loading"
    loading_status["ac_patterns"]["progress"] = 0
    loading_status["ac_patterns"]["total"] = len(patterns)

    try:
        es_client = ElasticsearchClient()
        index_name = f"ac_patterns_{category}"

        # Create index if not exists
        await _ensure_ac_patterns_index(es_client, index_name)

        # Convert to confidence score
        confidence = _tier_to_confidence(tier)

        # Process in batches
        loaded_count = 0
        for i in range(0, len(patterns), batch_size):
            batch = patterns[i:i + batch_size]

            # Prepare bulk documents
            bulk_body = []
            for pattern_data in batch:
                doc = {
                    "pattern": pattern_data.get("pattern", ""),
                    "pattern_type": pattern_data.get("pattern_type", "unknown"),
                    "tier": tier,
                    "category": category,
                    "source_list": pattern_data.get("source_list", "api_upload"),
                    "confidence": confidence,
                    "metadata": {k: v for k, v in pattern_data.items()
                              if k not in ['pattern', 'pattern_type', 'source_list']}
                }
                bulk_body.append({"index": {"_index": index_name}})
                bulk_body.append(doc)

            # Execute bulk request
            await es_client.client.bulk(body=bulk_body)

            loaded_count += len(batch)
            loading_status["ac_patterns"]["progress"] = loaded_count

            logger.info(f"Loaded {loaded_count}/{len(patterns)} AC patterns")

        # Refresh index
        await es_client.client.indices.refresh(index=index_name)
        await es_client.close()

        loading_status["ac_patterns"]["status"] = "completed"
        logger.info(f"Successfully loaded {loaded_count} AC patterns")

    except Exception as e:
        loading_status["ac_patterns"]["status"] = "error"
        logger.error(f"Failed to load AC patterns: {e}")

async def _load_vectors_background(
    vectors: List[Dict[str, Any]],
    category: str,
    model_name: str,
    batch_size: int
):
    """Background task to load vectors."""
    loading_status["vectors"]["status"] = "loading"
    loading_status["vectors"]["progress"] = 0
    loading_status["vectors"]["total"] = len(vectors)

    try:
        es_client = ElasticsearchClient()
        index_name = f"vectors_{category}"

        # Create index if not exists
        await _ensure_vectors_index(es_client, index_name)

        # Process in batches
        loaded_count = 0
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]

            # Prepare bulk documents
            bulk_body = []
            for vector_data in batch:
                doc = {
                    "name": vector_data.get("name", ""),
                    "vector": vector_data.get("vector", []),
                    "category": category,
                    "model_name": model_name,
                    "metadata": vector_data.get("metadata", {})
                }
                bulk_body.append({"index": {"_index": index_name}})
                bulk_body.append(doc)

            # Execute bulk request
            await es_client.client.bulk(body=bulk_body)

            loaded_count += len(batch)
            loading_status["vectors"]["progress"] = loaded_count

            logger.info(f"Loaded {loaded_count}/{len(vectors)} vectors")

        # Refresh index
        await es_client.client.indices.refresh(index=index_name)
        await es_client.close()

        loading_status["vectors"]["status"] = "completed"
        logger.info(f"Successfully loaded {loaded_count} vectors")

    except Exception as e:
        loading_status["vectors"]["status"] = "error"
        logger.error(f"Failed to load vectors: {e}")

async def _load_ac_patterns_file_background(
    patterns_data: Dict[str, Any],
    category: str,
    batch_size: int
):
    """Background task to load AC patterns from file data."""
    total_patterns = sum(len(patterns) for patterns in patterns_data.values() if isinstance(patterns, list))

    loading_status["ac_patterns"]["status"] = "loading"
    loading_status["ac_patterns"]["progress"] = 0
    loading_status["ac_patterns"]["total"] = total_patterns

    loaded_count = 0

    # Load each tier
    for tier_name, patterns in patterns_data.items():
        if isinstance(patterns, list):
            await _load_ac_patterns_background(patterns, category, tier_name, batch_size)
            loaded_count += len(patterns)
            loading_status["ac_patterns"]["progress"] = loaded_count

async def _load_vectors_file_background(
    vectors_data: List[Dict[str, Any]],
    category: str,
    model_name: str,
    batch_size: int
):
    """Background task to load vectors from file data."""
    await _load_vectors_background(vectors_data, category, model_name, batch_size)

async def _ensure_ac_patterns_index(es_client: ElasticsearchClient, index_name: str):
    """Ensure AC patterns index exists with proper mapping."""
    if not await es_client.client.indices.exists(index=index_name):
        index_config = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "pattern_analyzer": {
                            "type": "custom",
                            "tokenizer": "keyword",
                            "filter": ["lowercase"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "pattern": {
                        "type": "text",
                        "analyzer": "pattern_analyzer",
                        "fields": {"exact": {"type": "keyword"}}
                    },
                    "pattern_type": {"type": "keyword"},
                    "tier": {"type": "keyword"},
                    "category": {"type": "keyword"},
                    "source_list": {"type": "keyword"},
                    "confidence": {"type": "float"},
                    "metadata": {"type": "object", "enabled": False}
                }
            }
        }
        await es_client.client.indices.create(index=index_name, body=index_config)

async def _ensure_vectors_index(es_client: ElasticsearchClient, index_name: str):
    """Ensure vectors index exists with proper mapping."""
    if not await es_client.client.indices.exists(index=index_name):
        index_config = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0
            },
            "mappings": {
                "properties": {
                    "name": {
                        "type": "text",
                        "fields": {"exact": {"type": "keyword"}}
                    },
                    "vector": {
                        "type": "dense_vector",
                        "dims": 384  # sentence-transformers default
                    },
                    "category": {"type": "keyword"},
                    "model_name": {"type": "keyword"},
                    "metadata": {"type": "object", "enabled": False}
                }
            }
        }
        await es_client.client.indices.create(index=index_name, body=index_config)

def _tier_to_confidence(tier_name: str) -> float:
    """Convert tier name to confidence score."""
    tier_mapping = {
        'tier_0_exact': 1.0,
        'tier_1_high': 0.9,
        'tier_2_medium': 0.7,
        'tier_3_low': 0.5,
        'tier_4_experimental': 0.3
    }
    return tier_mapping.get(tier_name, 0.5)
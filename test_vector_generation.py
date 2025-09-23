#!/usr/bin/env python3
"""
Quick test of vector generation with small dataset
"""

import json
import asyncio
import aiohttp
import time
from pathlib import Path

# Try to import sentence transformers
try:
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("⚠️  sentence-transformers not available, using mock vectors")

async def test_vector_upload():
    es_url = "http://95.217.84.234:9200"

    print("🧪 Testing vector generation...")

    # Load small sample
    persons_file = Path("src/ai_service/data/sanctioned_persons.json")
    if persons_file.exists():
        with open(persons_file, 'r', encoding='utf-8') as f:
            persons_data = json.load(f)
            print(f"📊 Loaded {len(persons_data):,} persons")
            # Take first 10 for testing
            sample_persons = persons_data[:10]
            print(f"🔬 Testing with {len(sample_persons)} sample persons")
    else:
        print("❌ No persons data found")
        return

    # Load model if available
    if TRANSFORMERS_AVAILABLE:
        print("🔧 Loading sentence-transformers model...")
        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        vector_dim = 384
        print("✅ Model loaded")
    else:
        model = None
        vector_dim = 384
        print("⚠️  Using mock vectors")

    # Generate vectors for sample
    vectors = []
    for i, person in enumerate(sample_persons):
        name = person.get('name', f'Person {i}')

        if model:
            vector = model.encode([name])[0].tolist()
        else:
            # Mock vector
            import hashlib
            import numpy as np
            hash_obj = hashlib.md5(name.encode())
            seed = int(hash_obj.hexdigest()[:8], 16)
            np.random.seed(seed)
            vector = np.random.normal(0, 1, vector_dim).tolist()

        vectors.append({
            "entity_id": str(person.get('id', i)),
            "entity_type": "person",
            "name": name,
            "vector": vector,
            "created_at": "2025-09-22T23:42:00Z"
        })

        print(f"  Generated vector {i+1}/{len(sample_persons)}: {name}")

    print(f"✅ Generated {len(vectors)} test vectors")

    # Test upload to ES
    async with aiohttp.ClientSession() as session:
        # Delete and recreate index
        print("🗑️  Deleting old vectors index...")
        async with session.delete(f"{es_url}/vectors") as resp:
            print(f"  Delete status: {resp.status}")

        # Create index
        print("🔧 Creating new vectors index...")
        index_config = {
            "settings": {"number_of_shards": 1, "number_of_replicas": 0},
            "mappings": {
                "properties": {
                    "entity_id": {"type": "keyword"},
                    "entity_type": {"type": "keyword"},
                    "name": {"type": "text"},
                    "vector": {"type": "dense_vector", "dims": vector_dim, "index": True, "similarity": "cosine"},
                    "created_at": {"type": "date"}
                }
            }
        }

        async with session.put(f"{es_url}/vectors", json=index_config) as resp:
            if resp.status in [200, 201]:
                print("✅ Index created")
            else:
                error = await resp.text()
                print(f"❌ Index creation failed: {error}")
                return

        # Upload vectors
        print("📤 Uploading test vectors...")
        bulk_body = []
        for vector_doc in vectors:
            bulk_body.append(json.dumps({"index": {"_index": "vectors"}}))
            bulk_body.append(json.dumps(vector_doc))

        bulk_data = "\n".join(bulk_body) + "\n"
        headers = {"Content-Type": "application/x-ndjson"}

        async with session.post(f"{es_url}/_bulk", data=bulk_data, headers=headers) as resp:
            if resp.status == 200:
                result = await resp.json()
                if not result.get("errors"):
                    print(f"✅ Successfully uploaded {len(vectors)} vectors")
                else:
                    print(f"⚠️  Some upload errors occurred")
            else:
                error = await resp.text()
                print(f"❌ Upload failed: {error}")
                return

        # Verify upload
        print("🔍 Verifying upload...")
        await asyncio.sleep(1)  # Wait for indexing
        async with session.get(f"{es_url}/vectors/_count") as resp:
            if resp.status == 200:
                result = await resp.json()
                count = result.get("count", 0)
                print(f"📊 Vectors in index: {count}")
            else:
                print("❌ Failed to verify upload")

if __name__ == "__main__":
    asyncio.run(test_vector_upload())
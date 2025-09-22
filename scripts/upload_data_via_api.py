#!/usr/bin/env python3
"""
Script to upload AC patterns and vectors via API.
"""

import json
import asyncio
import aiohttp
import time
import argparse
from pathlib import Path
from typing import Dict, List, Any

class DataUploader:
    """Upload data to AI service via API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def upload_ac_patterns_file(self, file_path: Path, category: str, batch_size: int = 1000) -> Dict[str, Any]:
        """Upload AC patterns file via API."""
        print(f"📤 Uploading AC patterns from {file_path.name}...")

        with open(file_path, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename=file_path.name, content_type='application/json')
            data.add_field('category', category)
            data.add_field('batch_size', str(batch_size))

            async with self.session.post(f"{self.base_url}/admin/ac-patterns/upload", data=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ {result['message']}")
                    return result
                else:
                    error_text = await resp.text()
                    print(f"❌ Upload failed: {error_text}")
                    return {"success": False, "error": error_text}

    async def upload_vectors_file(self, file_path: Path, category: str, model_name: str, batch_size: int = 500) -> Dict[str, Any]:
        """Upload vectors file via API."""
        print(f"📤 Uploading vectors from {file_path.name}...")

        with open(file_path, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename=file_path.name, content_type='application/json')
            data.add_field('category', category)
            data.add_field('model_name', model_name)
            data.add_field('batch_size', str(batch_size))

            async with self.session.post(f"{self.base_url}/admin/vectors/upload", data=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ {result['message']}")
                    return result
                else:
                    error_text = await resp.text()
                    print(f"❌ Upload failed: {error_text}")
                    return {"success": False, "error": error_text}

    async def upload_ac_patterns_bulk(self, patterns: List[Dict[str, Any]], category: str, tier: str, batch_size: int = 1000) -> Dict[str, Any]:
        """Upload AC patterns via bulk API."""
        print(f"📤 Uploading {len(patterns)} AC patterns for {category}/{tier}...")

        payload = {
            "patterns": patterns,
            "category": category,
            "tier": tier,
            "batch_size": batch_size
        }

        async with self.session.post(f"{self.base_url}/admin/ac-patterns/bulk", json=payload) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"✅ {result['message']}")
                return result
            else:
                error_text = await resp.text()
                print(f"❌ Upload failed: {error_text}")
                return {"success": False, "error": error_text}

    async def upload_vectors_bulk(self, vectors: List[Dict[str, Any]], category: str, model_name: str, batch_size: int = 500) -> Dict[str, Any]:
        """Upload vectors via bulk API."""
        print(f"📤 Uploading {len(vectors)} vectors for {category}...")

        payload = {
            "vectors": vectors,
            "category": category,
            "model_name": model_name,
            "batch_size": batch_size
        }

        async with self.session.post(f"{self.base_url}/admin/vectors/bulk", json=payload) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"✅ {result['message']}")
                return result
            else:
                error_text = await resp.text()
                print(f"❌ Upload failed: {error_text}")
                return {"success": False, "error": error_text}

    async def get_loading_status(self) -> Dict[str, Any]:
        """Get current loading status."""
        async with self.session.get(f"{self.base_url}/admin/loading-status") as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                return {"error": f"Failed to get status: {resp.status}"}

    async def wait_for_completion(self, operation_type: str = "ac_patterns", timeout: int = 300):
        """Wait for loading operation to complete."""
        print(f"⏳ Waiting for {operation_type} loading to complete...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            status = await self.get_loading_status()

            if operation_type in status:
                op_status = status[operation_type]
                current_status = op_status.get("status", "unknown")
                progress = op_status.get("progress", 0)
                total = op_status.get("total", 0)

                if current_status == "completed":
                    print(f"✅ {operation_type} loading completed! ({progress}/{total})")
                    return True
                elif current_status == "error":
                    print(f"❌ {operation_type} loading failed!")
                    return False
                elif current_status == "loading":
                    percentage = (progress / total * 100) if total > 0 else 0
                    print(f"📊 {operation_type}: {progress}/{total} ({percentage:.1f}%)")

            await asyncio.sleep(5)

        print(f"⏰ Timeout waiting for {operation_type} loading")
        return False

    async def list_indices(self) -> List[str]:
        """List all Elasticsearch indices."""
        async with self.session.get(f"{self.base_url}/admin/indices") as resp:
            if resp.status == 200:
                result = await resp.json()
                return result.get("indices", [])
            else:
                print(f"❌ Failed to list indices: {resp.status}")
                return []

    async def delete_index(self, index_name: str) -> bool:
        """Delete an Elasticsearch index."""
        async with self.session.delete(f"{self.base_url}/admin/indices/{index_name}") as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"✅ {result['message']}")
                return True
            else:
                error_text = await resp.text()
                print(f"❌ Failed to delete index: {error_text}")
                return False

async def upload_all_ac_patterns(uploader: DataUploader, data_dir: Path):
    """Upload all AC patterns files."""
    pattern_files = [
        ("person_ac_export.json", "person"),
        ("company_ac_export.json", "company"),
        ("terrorism_ac_export.json", "terrorism")
    ]

    for filename, category in pattern_files:
        file_path = data_dir / filename
        if file_path.exists():
            result = await uploader.upload_ac_patterns_file(file_path, category)
            if result.get("success"):
                await uploader.wait_for_completion("ac_patterns")
        else:
            print(f"⚠️ File not found: {file_path}")

async def generate_and_upload_vectors(uploader: DataUploader, data_dir: Path):
    """Generate vectors from names and upload them."""
    print("🧠 Generating vectors from name patterns...")

    # This would typically read from existing patterns and generate vectors
    # For now, we'll create a simple example

    sample_vectors = [
        {
            "name": "иванов",
            "vector": [0.1] * 384,  # Sample 384-dim vector
            "metadata": {"type": "surname", "language": "ru"}
        },
        {
            "name": "петров",
            "vector": [0.2] * 384,
            "metadata": {"type": "surname", "language": "ru"}
        },
        {
            "name": "сидоров",
            "vector": [0.3] * 384,
            "metadata": {"type": "surname", "language": "ru"}
        }
    ]

    result = await uploader.upload_vectors_bulk(
        sample_vectors,
        "person",
        "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    )

    if result.get("success"):
        await uploader.wait_for_completion("vectors")

async def main():
    parser = argparse.ArgumentParser(description="Upload data to AI service via API")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of AI service")
    parser.add_argument("--data-dir", type=Path, default="data/templates", help="Data directory path")
    parser.add_argument("--action", choices=["ac-patterns", "vectors", "all", "status", "list-indices"],
                       default="status", help="Action to perform")
    parser.add_argument("--delete-index", help="Index name to delete")

    args = parser.parse_args()

    async with DataUploader(args.url) as uploader:
        if args.delete_index:
            await uploader.delete_index(args.delete_index)
        elif args.action == "status":
            status = await uploader.get_loading_status()
            print(f"📊 Loading Status:")
            for op_type, op_status in status.items():
                print(f"  {op_type}: {op_status}")
        elif args.action == "list-indices":
            indices = await uploader.list_indices()
            print(f"📋 Elasticsearch Indices:")
            for index in indices:
                print(f"  - {index}")
        elif args.action == "ac-patterns":
            await upload_all_ac_patterns(uploader, args.data_dir)
        elif args.action == "vectors":
            await generate_and_upload_vectors(uploader, args.data_dir)
        elif args.action == "all":
            await upload_all_ac_patterns(uploader, args.data_dir)
            await generate_and_upload_vectors(uploader, args.data_dir)

if __name__ == "__main__":
    asyncio.run(main())
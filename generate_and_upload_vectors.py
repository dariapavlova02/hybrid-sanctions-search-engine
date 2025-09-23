#!/usr/bin/env python3
"""
Generate and upload vectors for all entities (persons, companies, terrorism blacklist)
"""

import json
import asyncio
import aiohttp
import time
import numpy as np
from typing import Dict, List, Any
from pathlib import Path

# Try to import sentence transformers
try:
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("⚠️  sentence-transformers not available, using mock vectors")

class VectorGenerator:
    def __init__(self, es_url="http://95.217.84.234:9200"):
        self.es_url = es_url.rstrip("/")
        self.session = None

        # Initialize sentence transformer model
        if TRANSFORMERS_AVAILABLE:
            print("🔧 Loading sentence-transformers model...")
            import sys
            sys.stdout.flush()
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')  # 384 dimensions
            self.vector_dim = 384
            print("✅ Model loaded successfully")
            sys.stdout.flush()
        else:
            self.model = None
            self.vector_dim = 384

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def generate_vector(self, text: str) -> List[float]:
        """Generate vector for text"""
        if self.model:
            vector = self.model.encode([text])[0]
            return vector.tolist()
        else:
            # Mock vector for testing
            import hashlib
            hash_obj = hashlib.md5(text.encode())
            seed = int(hash_obj.hexdigest()[:8], 16)
            np.random.seed(seed)
            return np.random.normal(0, 1, self.vector_dim).tolist()

    async def create_vectors_index(self):
        """Create vectors index with proper mapping"""
        print("🔧 Creating vectors index...")
        import sys
        sys.stdout.flush()

        # Check if index already exists
        async with self.session.head(f"{self.es_url}/vectors") as resp:
            if resp.status == 200:
                print("ℹ️  Vectors index already exists, deleting first...")
                sys.stdout.flush()
                # Delete existing index
                async with self.session.delete(f"{self.es_url}/vectors") as del_resp:
                    if del_resp.status in [200, 404]:
                        print("✅ Old vectors index deleted")
                        sys.stdout.flush()
                    else:
                        print(f"⚠️  Warning deleting vectors index: {del_resp.status}")
                        sys.stdout.flush()

        index_config = {
            "settings": {
                "number_of_shards": 2,
                "number_of_replicas": 0,
                "index.max_result_window": 100000
            },
            "mappings": {
                "properties": {
                    "entity_id": {"type": "keyword"},
                    "entity_type": {"type": "keyword"},  # person, company, terrorism
                    "name": {"type": "text"},
                    "name_variants": {"type": "text"},
                    "vector": {
                        "type": "dense_vector",
                        "dims": self.vector_dim,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "metadata": {"type": "object"},
                    "created_at": {"type": "date"}
                }
            }
        }

        async with self.session.put(f"{self.es_url}/vectors", json=index_config) as resp:
            if resp.status in [200, 201]:
                print("✅ Vectors index created")
                return True
            else:
                error = await resp.text()
                print(f"❌ Failed to create vectors index: {error}")
                return False

    def load_entities_data(self) -> Dict[str, List[Dict]]:
        """Load all entities data"""
        print("📂 Loading entities data...")
        import sys
        sys.stdout.flush()

        data = {}

        # Load sanctioned persons
        persons_file = Path("src/ai_service/data/sanctioned_persons.json")
        if persons_file.exists():
            with open(persons_file, 'r', encoding='utf-8') as f:
                data["persons"] = json.load(f)
                print(f"✅ Loaded {len(data['persons']):,} sanctioned persons")
        else:
            data["persons"] = []
            print("⚠️  Sanctioned persons file not found")

        # Load sanctioned companies
        companies_file = Path("src/ai_service/data/sanctioned_companies.json")
        if companies_file.exists():
            with open(companies_file, 'r', encoding='utf-8') as f:
                data["companies"] = json.load(f)
                print(f"✅ Loaded {len(data['companies']):,} sanctioned companies")
        else:
            data["companies"] = []
            print("⚠️  Sanctioned companies file not found")

        # Load terrorism blacklist
        terrorism_file = Path("src/ai_service/data/terrorism_black_list.json")
        if terrorism_file.exists():
            with open(terrorism_file, 'r', encoding='utf-8') as f:
                data["terrorism"] = json.load(f)
                print(f"✅ Loaded {len(data['terrorism']):,} terrorism blacklist entries")
        else:
            data["terrorism"] = []
            print("⚠️  Terrorism blacklist file not found")

        return data

    def generate_vectors_for_persons(self, persons: List[Dict]) -> List[Dict]:
        """Generate vectors for persons"""
        print("🔄 Generating vectors for persons...")

        vectors = []
        for i, person in enumerate(persons):
            # Extract name variants
            names = []
            if person.get('name'):
                names.append(person['name'])
            if person.get('name_ru'):
                names.append(person['name_ru'])
            if person.get('name_en'):
                names.append(person['name_en'])

            # Use primary name for vector generation
            primary_name = names[0] if names else f"Person {person.get('id', i)}"

            # Generate vector
            vector = self.generate_vector(primary_name)

            vectors.append({
                "entity_id": str(person.get('id', i)),
                "entity_type": "person",
                "name": primary_name,
                "name_variants": names,
                "vector": vector,
                "metadata": {
                    "birth_date": person.get('birth_date'),
                    "passport": person.get('passport'),
                    "inn": person.get('inn'),
                    "source": "sanctioned_persons"
                },
                "created_at": "2025-09-22T23:00:00Z"
            })

            if (i + 1) % 1000 == 0:
                print(f"  Generated {i + 1:,}/{len(persons):,} person vectors ({((i+1)/len(persons)*100):.1f}%)")

        print(f"✅ Generated {len(vectors):,} person vectors")
        return vectors

    def generate_vectors_for_companies(self, companies: List[Dict]) -> List[Dict]:
        """Generate vectors for companies"""
        print("🔄 Generating vectors for companies...")

        vectors = []
        for i, company in enumerate(companies):
            # Extract company name variants
            names = []
            if company.get('name'):
                names.append(company['name'])
            if company.get('name_ru'):
                names.append(company['name_ru'])
            if company.get('name_en'):
                names.append(company['name_en'])

            # Use primary name for vector generation
            primary_name = names[0] if names else f"Company {company.get('id', i)}"

            # Generate vector
            vector = self.generate_vector(primary_name)

            vectors.append({
                "entity_id": str(company.get('id', i)),
                "entity_type": "company",
                "name": primary_name,
                "name_variants": names,
                "vector": vector,
                "metadata": {
                    "edrpou": company.get('edrpou'),
                    "inn": company.get('inn'),
                    "address": company.get('address'),
                    "source": "sanctioned_companies"
                },
                "created_at": "2025-09-22T23:00:00Z"
            })

            if (i + 1) % 1000 == 0:
                print(f"  Generated {i + 1:,}/{len(companies):,} company vectors ({((i+1)/len(companies)*100):.1f}%)")

        print(f"✅ Generated {len(vectors):,} company vectors")
        return vectors

    def generate_vectors_for_terrorism(self, terrorism: List[Dict]) -> List[Dict]:
        """Generate vectors for terrorism blacklist"""
        print("🔄 Generating vectors for terrorism blacklist...")

        vectors = []
        for i, entry in enumerate(terrorism):
            # Extract name variants
            names = []
            if entry.get('name'):
                names.append(entry['name'])
            if entry.get('name_ru'):
                names.append(entry['name_ru'])
            if entry.get('name_en'):
                names.append(entry['name_en'])

            # Use primary name for vector generation
            primary_name = names[0] if names else f"Terrorism Entry {entry.get('id', i)}"

            # Generate vector
            vector = self.generate_vector(primary_name)

            vectors.append({
                "entity_id": str(entry.get('id', i)),
                "entity_type": "terrorism",
                "name": primary_name,
                "name_variants": names,
                "vector": vector,
                "metadata": {
                    "category": entry.get('category'),
                    "reason": entry.get('reason'),
                    "source": "terrorism_black_list"
                },
                "created_at": "2025-09-22T23:00:00Z"
            })

            if (i + 1) % 1000 == 0:
                print(f"  Generated {i + 1:,}/{len(terrorism):,} terrorism vectors ({((i+1)/len(terrorism)*100):.1f}%)")

        print(f"✅ Generated {len(vectors):,} terrorism vectors")
        return vectors

    async def bulk_upload_vectors(self, vectors: List[Dict], batch_size=500):
        """Upload vectors in batches"""
        total_vectors = len(vectors)
        uploaded = 0

        print(f"📤 Uploading {total_vectors:,} vectors in batches of {batch_size:,}...")

        for i in range(0, total_vectors, batch_size):
            batch = vectors[i:i + batch_size]

            # Prepare bulk request
            bulk_body = []
            for vector_doc in batch:
                # Index action
                bulk_body.append(json.dumps({"index": {"_index": "vectors"}}))
                # Document
                bulk_body.append(json.dumps(vector_doc))

            bulk_data = "\n".join(bulk_body) + "\n"

            # Upload batch
            headers = {"Content-Type": "application/x-ndjson"}
            async with self.session.post(f"{self.es_url}/_bulk", data=bulk_data, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if not result.get("errors"):
                        uploaded += len(batch)
                        progress = (uploaded / total_vectors) * 100
                        print(f"✅ Batch {i//batch_size + 1} uploaded: {uploaded:,}/{total_vectors:,} ({progress:.1f}%)")
                    else:
                        print(f"⚠️  Some errors in batch {i//batch_size + 1}")
                else:
                    error = await resp.text()
                    print(f"❌ Batch upload failed: {error}")
                    break

            # Small delay
            await asyncio.sleep(0.1)

        return uploaded

async def main():
    print("🚀 Starting vectors generation and upload...")
    print("=" * 60)

    async with VectorGenerator() as generator:
        # Create vectors index
        if not await generator.create_vectors_index():
            return

        # Load entities data
        entities_data = generator.load_entities_data()

        # Generate vectors for all entity types
        all_vectors = []

        if entities_data.get("persons"):
            person_vectors = generator.generate_vectors_for_persons(entities_data["persons"])
            all_vectors.extend(person_vectors)

        if entities_data.get("companies"):
            company_vectors = generator.generate_vectors_for_companies(entities_data["companies"])
            all_vectors.extend(company_vectors)

        if entities_data.get("terrorism"):
            terrorism_vectors = generator.generate_vectors_for_terrorism(entities_data["terrorism"])
            all_vectors.extend(terrorism_vectors)

        print(f"\n📊 Total vectors to upload: {len(all_vectors):,}")

        # Upload all vectors
        start_time = time.time()
        uploaded = await generator.bulk_upload_vectors(all_vectors)
        upload_time = time.time() - start_time

        print("=" * 60)
        print("🎉 Vector generation and upload completed!")
        print(f"📊 Uploaded: {uploaded:,} vectors")
        print(f"⏱️  Time: {upload_time:.2f}s")
        print(f"🚀 Rate: {uploaded/upload_time:.1f} vectors/sec")

        # Show entity type distribution
        entity_counts = {}
        for vector in all_vectors:
            entity_type = vector["entity_type"]
            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1

        print("\n📈 Entity type distribution:")
        for entity_type, count in entity_counts.items():
            print(f"  {entity_type}: {count:,} vectors")

if __name__ == "__main__":
    asyncio.run(main())
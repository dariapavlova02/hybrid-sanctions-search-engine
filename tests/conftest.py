"""
Pytest configuration for AI service tests
"""

import pytest
import sys
import os
import asyncio
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import httpx

# Add src to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Suppress warnings for cleaner test output
# pytest_plugins = ['pytest_warnings']  # Removed - plugin not available

# Set test environment for search tests
os.environ["ENABLE_HYBRID_SEARCH"] = "true"
os.environ["ES_URL"] = "http://localhost:9200"
os.environ["ES_AUTH"] = ""
os.environ["ES_VERIFY_SSL"] = "false"

# Search weights for testing
os.environ["AI_DECISION__W_SEARCH_EXACT"] = "0.3"
os.environ["AI_DECISION__W_SEARCH_PHRASE"] = "0.25"
os.environ["AI_DECISION__W_SEARCH_NGRAM"] = "0.2"
os.environ["AI_DECISION__W_SEARCH_VECTOR"] = "0.15"

# Search thresholds
os.environ["AI_DECISION__THR_SEARCH_EXACT"] = "0.8"
os.environ["AI_DECISION__THR_SEARCH_PHRASE"] = "0.7"
os.environ["AI_DECISION__THR_SEARCH_NGRAM"] = "0.6"
os.environ["AI_DECISION__THR_SEARCH_VECTOR"] = "0.5"

# Search bonuses
os.environ["AI_DECISION__BONUS_MULTIPLE_MATCHES"] = "0.1"
os.environ["AI_DECISION__BONUS_HIGH_CONFIDENCE"] = "0.05"


@pytest.fixture(scope="session")
def test_data_dir():
    """Provide test data directory path"""
    return Path(__file__).parent / 'data'


@pytest.fixture(scope="session")
def sample_texts():
    """Provide sample texts for testing"""
    return {
        'ukrainian': 'Привіт світ! Це тестовий текст українською мовою.',
        'russian': 'Привет мир! Это тестовый текст на русском языке.',
        'english': 'Hello world! This is a test text in English.',
        'mixed': 'Hello світ! Привет world!'
    }


@pytest.fixture(scope="session")
def sample_names():
    """Provide sample names for testing"""
    return {
        'ukrainian': ['Петро', 'Дарія', 'Володимир', 'Олена'],
        'russian': ['Сергей', 'Мария', 'Владимир', 'Анна'],
        'english': ['John', 'Mary', 'William', 'Elizabeth']
    }


@pytest.fixture(scope="function")
def mock_services():
    """Provide mocked services for testing"""
    from unittest.mock import Mock
    
    return {
        'language_service': Mock(),
        'normalization_service': Mock(),
        'variant_service': Mock(),
        'embedding_service': Mock(),
        'cache_service': Mock()
    }


@pytest.fixture(scope="function")
def orchestrator_service():
    """
    Provides a clean, isolated instance of OrchestratorService for each test.
    
    This ensures that each test gets a fresh instance with clean cache and statistics,
    preventing test contamination. Mocks heavy dependencies to avoid NLTK issues.
    """
    from unittest.mock import patch, MagicMock
    
    # Mock heavy dependencies to avoid initialization issues
    with patch('src.ai_service.data.dicts.stopwords.STOP_ALL') as mock_stopwords:
        
        # Configure mocks
        mock_stopwords.return_value = ['the', 'a', 'an']
        
        from src.ai_service.core.unified_orchestrator import UnifiedOrchestrator as OrchestratorService
        from unittest.mock import Mock
        
        # Create mock services for required dependencies
        from unittest.mock import AsyncMock, Mock
        
        mock_validation_service = AsyncMock()
        mock_language_service = Mock()
        mock_unicode_service = Mock()
        mock_normalization_service = AsyncMock()
        mock_signals_service = AsyncMock()
        
        # Configure mock responses
        async def mock_validation(text):
            return {"is_valid": True, "sanitized_text": text}
        
        def mock_language_config_driven(text, config=None):
            from src.ai_service.utils.types import LanguageDetectionResult
            return LanguageDetectionResult(language="uk", confidence=0.9, details={})
        
        def mock_unicode_normalize_text(text, aggressive=False):
            return {"normalized_text": text, "original_text": text}
        
        def mock_unicode_normalize_unicode(text):
            return text
        
        async def mock_normalization(text, **kwargs):
            return type('obj', (object,), {
                'normalized': text,
                'tokens': text.split(),
                'trace': [],
                'success': True,
                'errors': []
            })()
        
        async def mock_signals(text, normalization_result, language, **kwargs):
            return type('obj', (object,), {
                'persons': [],
                'organizations': [],
                'extras': type('obj', (object,), {'dates': [], 'amounts': []})(),
                'confidence': 0.0
            })()
        
        mock_validation_service.validate_and_sanitize.side_effect = mock_validation
        mock_language_service.detect_language_config_driven.side_effect = mock_language_config_driven
        mock_unicode_service.normalize_text.side_effect = mock_unicode_normalize_text
        mock_unicode_service.normalize_unicode.side_effect = mock_unicode_normalize_unicode
        mock_normalization_service.normalize_async.side_effect = mock_normalization
        mock_signals_service.extract_signals.side_effect = mock_signals
        
        # Create mock for variants service
        mock_variants_service = AsyncMock()
        mock_variants_service.generate_variants.return_value = [
            "Gnatuk Abdulaeva Zhorzha Rashida",
            "Gnatuk Abdulaev Zhorzha Rashid",
            "Gnatuk Abdulaev Zhorzha Rashidovich",
            "Gnatuk Abdulaev Zhorzha Rashidovich Freedom",
            "Jean-Baptiste Müller Олександр Петренко-Сміт",
            "Jean-Baptiste Muller Олександр Петренко-Сміт",
            "Jean-Baptiste Muller Олександр Петренко-Смит",
            "Jean-Baptiste Muller Олександр Петренко-Смит Zürcher Straße",
            "Jean-Baptiste Muller Олександр Петренко-Смит Zürcher Strasse",
            "Jean-Baptiste Muller Олександр Петренко-Смит Zürcher Strasse",
            "Jean-Baptiste Muller Олександр Петренко-Смит Zürcher Strasse",
            "Jean-Baptiste Muller Олександр Петренко-Смит Zürcher Strasse"
        ]
        
        # Create mock cache service
        from src.ai_service.core.cache_service import CacheService
        mock_cache_service = CacheService(max_size=100, default_ttl=60)
        
        # Create mock embeddings service
        mock_embeddings_service = AsyncMock()
        mock_embeddings_service.generate_embeddings.return_value = [0.1, 0.2, 0.3]
        mock_embeddings_service.find_similar_texts.return_value = []
        
        # Use small values for tests to speed them up
        service = OrchestratorService(
            validation_service=mock_validation_service,
            language_service=mock_language_service,
            unicode_service=mock_unicode_service,
            normalization_service=mock_normalization_service,
            signals_service=mock_signals_service,
            variants_service=mock_variants_service,
            embeddings_service=mock_embeddings_service
        )
        
        # Set the cache service for legacy compatibility
        service.cache_service = mock_cache_service
        
        # Set other legacy services for compatibility
        service.pattern_service = Mock()
        service.template_builder = Mock()
        
        # Ensure clean state before test
        # UnifiedOrchestrator doesn't have reset_stats/clear_cache methods
        
        yield service
        
        # Clean up after test to prevent state leakage
        # UnifiedOrchestrator doesn't have clear_cache/reset_stats methods


@pytest.fixture(scope="function")
def language_detection_service():
    """Provides a clean instance of LanguageDetectionService for each test"""
    from src.ai_service.layers.language.language_detection_service import LanguageDetectionService
    return LanguageDetectionService()


@pytest.fixture(scope="function")
def advanced_normalization_service():
    """Provides a clean instance of NormalizationService for each test"""
    from src.ai_service.layers.normalization.normalization_service import NormalizationService
    return NormalizationService()


@pytest.fixture(scope="function")
def variant_generation_service():
    """Provides a clean instance of VariantGenerationService for each test"""
    from src.ai_service.layers.variants.variant_generation_service import VariantGenerationService
    return VariantGenerationService()


@pytest.fixture(scope="function")
def unicode_service():
    """Provides a clean instance of UnicodeService for each test"""
    from src.ai_service.layers.unicode.unicode_service import UnicodeService
    return UnicodeService()


@pytest.fixture(scope="function")
def pattern_service():
    """Provides a clean instance of UnifiedPatternService for each test"""
    from src.ai_service.layers.patterns.unified_pattern_service import UnifiedPatternService
    return UnifiedPatternService()


@pytest.fixture(scope="function")
def cache_service():
    """Provides a clean instance of CacheService for each test"""
    from src.ai_service.core.cache_service import CacheService
    service = CacheService(max_size=3, default_ttl=5)  # Small size and TTL for tests
    yield service
    # Clean up after test
    service.clear()


@pytest.fixture(scope="function")
def template_builder():
    """Provides a clean instance of TemplateBuilder for each test"""
    from src.ai_service.layers.variants.template_builder import TemplateBuilder
    return TemplateBuilder()


# ============================================================================
# Search Integration Test Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def docker_client():
    """Docker client for managing containers."""
    try:
        from docker import DockerClient  # type: ignore
        client = DockerClient()
        client.ping()
        return client
    except Exception as e:
        pytest.skip(f"Docker not available: {e}")


@pytest.fixture(scope="session")
def elasticsearch_container(docker_client):
    """Elasticsearch container for integration tests."""
    container_name = "ai-service-test-es"
    
    # Remove existing container if any
    try:
        existing = docker_client.containers.get(container_name)
        existing.remove(force=True)
    except:
        pass
    
    try:
        # Start Elasticsearch container
        container = docker_client.containers.run(
            "docker.elastic.co/elasticsearch/elasticsearch:8.11.0",
            name=container_name,
            environment={
                "discovery.type": "single-node",
                "xpack.security.enabled": "false",
                "ES_JAVA_OPTS": "-Xms512m -Xmx512m"
            },
            ports={"9200/tcp": 9200},
            detach=True,
            remove=True
        )
        
        # Wait for Elasticsearch to be ready
        max_retries = 30
        for i in range(max_retries):
            try:
                response = httpx.get("http://localhost:9200/_cluster/health", timeout=5.0)
                if response.status_code == 200:
                    break
            except:
                pass
            time.sleep(2)
        else:
            container.remove(force=True)
            pytest.skip("Elasticsearch failed to start")
        
        yield container
        
    finally:
        # Cleanup
        try:
            container.remove(force=True)
        except:
            pass


@pytest.fixture
async def elasticsearch_client(elasticsearch_container):
    """Elasticsearch client for tests."""
    async with httpx.AsyncClient(
        base_url="http://localhost:9200",
        timeout=30.0
    ) as client:
        yield client


@pytest.fixture
async def test_indices(elasticsearch_client):
    """Create test indices with sample data."""
    # Component template for analyzers
    component_template = {
        "template": {
            "settings": {
                "analysis": {
                    "normalizer": {
                        "custom_normalized_name_normalizer": {
                            "type": "custom",
                            "filter": ["lowercase", "asciifolding", "icu_folding"]
                        }
                    },
                    "analyzer": {
                        "icu_shingle_analyzer": {
                            "type": "custom",
                            "tokenizer": "icu_tokenizer",
                            "filter": ["icu_folding", "shingle"]
                        },
                        "char_ngram_analyzer": {
                            "type": "custom",
                            "tokenizer": "keyword",
                            "filter": ["lowercase", "char_ngram"]
                        }
                    },
                    "filter": {
                        "char_ngram": {
                            "type": "ngram",
                            "min_gram": 3,
                            "max_gram": 5
                        }
                    }
                }
            }
        }
    }
    
    # Create component template
    await elasticsearch_client.put(
        "/_component_template/test_analyzers",
        json=component_template
    )
    
    # Index templates
    persons_template = {
        "index_patterns": ["test_persons_*"],
        "template": {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "knn": True,
                "knn.algo_param.ef_search": 100
            },
            "mappings": {
                "properties": {
                    "entity_id": {"type": "keyword"},
                    "entity_type": {"type": "keyword"},
                    "normalized_name": {
                        "type": "keyword",
                        "normalizer": "custom_normalized_name_normalizer"
                    },
                    "aliases": {"type": "keyword"},
                    "country": {"type": "keyword"},
                    "dob": {"type": "date"},
                    "name_text": {
                        "type": "text",
                        "analyzer": "icu_shingle_analyzer"
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
        "composed_of": ["test_analyzers"]
    }
    
    orgs_template = {
        "index_patterns": ["test_orgs_*"],
        "template": {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "knn": True,
                "knn.algo_param.ef_search": 100
            },
            "mappings": {
                "properties": {
                    "entity_id": {"type": "keyword"},
                    "entity_type": {"type": "keyword"},
                    "normalized_name": {
                        "type": "keyword",
                        "normalizer": "custom_normalized_name_normalizer"
                    },
                    "aliases": {"type": "keyword"},
                    "country": {"type": "keyword"},
                    "name_text": {
                        "type": "text",
                        "analyzer": "icu_shingle_analyzer"
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
        "composed_of": ["test_analyzers"]
    }
    
    # Create index templates
    await elasticsearch_client.put(
        "/_index_template/test_persons_template",
        json=persons_template
    )
    
    await elasticsearch_client.put(
        "/_index_template/test_orgs_template",
        json=orgs_template
    )
    
    # Create test indices
    persons_index = "test_persons_001"
    orgs_index = "test_orgs_001"
    
    await elasticsearch_client.put(f"/{persons_index}")
    await elasticsearch_client.put(f"/{orgs_index}")
    
    # Sample test data
    test_persons = [
        {
            "entity_id": "person_001",
            "entity_type": "person",
            "normalized_name": "иван петров",
            "aliases": ["и. петров", "ivan petrov"],
            "country": "RU",
            "dob": "1980-05-15",
            "name_text": "иван петров",
            "name_ngrams": "иван петров",
            "name_vector": [0.1] * 384,
            "meta": {"source": "test", "list": "test_persons"}
        },
        {
            "entity_id": "person_002",
            "entity_type": "person",
            "normalized_name": "мария сидорова",
            "aliases": ["м. сидорова"],
            "country": "UA",
            "dob": "1975-12-03",
            "name_text": "мария сидорова",
            "name_ngrams": "мария сидорова",
            "name_vector": [0.2] * 384,
            "meta": {"source": "test", "list": "test_persons"}
        },
        {
            "entity_id": "person_003",
            "entity_type": "person",
            "normalized_name": "john smith",
            "aliases": ["j. smith"],
            "country": "US",
            "dob": "1985-03-20",
            "name_text": "john smith",
            "name_ngrams": "john smith",
            "name_vector": [0.3] * 384,
            "meta": {"source": "test", "list": "test_persons"}
        }
    ]
    
    test_orgs = [
        {
            "entity_id": "org_001",
            "entity_type": "org",
            "normalized_name": "ооо приватбанк",
            "aliases": ["приватбанк", "privatbank"],
            "country": "UA",
            "name_text": "ооо приватбанк",
            "name_ngrams": "ооо приватбанк",
            "name_vector": [0.4] * 384,
            "meta": {"source": "test", "list": "test_orgs"}
        },
        {
            "entity_id": "org_002",
            "entity_type": "org",
            "normalized_name": "apple inc",
            "aliases": ["apple", "apple computer"],
            "country": "US",
            "name_text": "apple inc",
            "name_ngrams": "apple inc",
            "name_vector": [0.5] * 384,
            "meta": {"source": "test", "list": "test_orgs"}
        }
    ]
    
    # Index test data
    for person in test_persons:
        await elasticsearch_client.post(
            f"/{persons_index}/_doc/{person['entity_id']}",
            json=person
        )
    
    for org in test_orgs:
        await elasticsearch_client.post(
            f"/{orgs_index}/_doc/{org['entity_id']}",
            json=org
        )
    
    # Refresh indices
    await elasticsearch_client.post(f"/{persons_index}/_refresh")
    await elasticsearch_client.post(f"/{orgs_index}/_refresh")
    
    yield {
        "persons_index": persons_index,
        "orgs_index": orgs_index,
        "test_persons": test_persons,
        "test_orgs": test_orgs
    }
    
    # Cleanup
    try:
        await elasticsearch_client.delete(f"/{persons_index}")
        await elasticsearch_client.delete(f"/{orgs_index}")
        await elasticsearch_client.delete("/_index_template/test_persons_template")
        await elasticsearch_client.delete("/_index_template/test_orgs_template")
        await elasticsearch_client.delete("/_component_template/test_analyzers")
    except:
        pass


@pytest.fixture
def mock_hybrid_search_service():
    """Mock HybridSearchService for unit tests."""
    from src.ai_service.layers.search import HybridSearchService
    from src.ai_service.contracts.search_contracts import Candidate, SearchType
    
    service = MagicMock(spec=HybridSearchService)
    
    # Mock find_candidates method
    async def mock_find_candidates(normalized, text, opts):
        return [
            Candidate(
                entity_id="test_001",
                entity_type="person",
                normalized_name="test name",
                aliases=[],
                country="RU",
                dob=None,
                meta={},
                final_score=0.9,
                ac_score=0.8,
                vector_score=0.7,
                features={"DOB_match": False, "need_context": False},
                search_type=SearchType.FUSION
            )
        ]
    
    service.find_candidates = AsyncMock(side_effect=mock_find_candidates)
    service.get_metrics = MagicMock(return_value=MagicMock(
        ac_attempts=1,
        vector_attempts=1,
        ac_success=1,
        vector_success=1,
        ac_latency_p95=50.0,
        vector_latency_p95=100.0,
        hit_rate=0.8,
        escalation_rate=0.2
    ))
    
    return service


@pytest.fixture
def mock_signals_result():
    """Mock SignalsResult for tests."""
    return {
        "persons": [
            {
                "normalized_name": "иван петров",
                "aliases": ["и. петров"],
                "confidence": 0.9,
                "date_match": True,
                "id_match": False
            }
        ],
        "organizations": [
            {
                "normalized_name": "ооо приватбанк",
                "aliases": ["приватбанк"],
                "confidence": 0.8,
                "date_match": False,
                "id_match": False
            }
        ],
        "processing_time": 0.1
    }


@pytest.fixture
def mock_normalization_result():
    """Mock NormalizationResult for tests."""
    from src.ai_service.contracts.base_contracts import NormalizationResult
    
    return NormalizationResult(
        normalized="иван петров",
        tokens=["иван", "петров"],
        trace=[],
        errors=[],
        language="ru",
        confidence=0.9,
        original_length=12,
        normalized_length=12,
        token_count=2,
        processing_time=0.05,
        success=True
    )


@pytest.fixture
def sample_query_vector():
    """Sample 384-dimensional query vector for tests."""
    return [0.1 + (i * 0.001) for i in range(384)]


# Pytest markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests requiring Elasticsearch")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "docker: Tests requiring Docker")

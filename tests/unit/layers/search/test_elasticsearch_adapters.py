import httpx
import pytest

from src.ai_service.layers.search.config import HybridSearchConfig
from src.ai_service.layers.search.contracts import SearchMode, SearchOpts
from src.ai_service.layers.search.elasticsearch_adapters import (
    ElasticsearchACAdapter,
    ElasticsearchVectorAdapter,
)
from src.ai_service.layers.search.elasticsearch_client import ElasticsearchClientFactory


def _mock_factory(config: HybridSearchConfig, handler) -> ElasticsearchClientFactory:
    transport = httpx.MockTransport(handler)
    return ElasticsearchClientFactory(config, transport=transport)


@pytest.mark.asyncio
async def test_ac_adapter_builds_query_and_parses_results():
    config = HybridSearchConfig.from_env(env={})

    response_payload = {
        "hits": {
            "max_score": 1.2,
            "hits": [
                {
                    "_id": "doc-1",
                    "_score": 1.2,
                    "_source": {
                        "normalized_text": "Иван Петров",
                        "entity_type": "person",
                        "metadata": {"country": "RU"},
                    },
                    "matched_queries": ["normalized_text"],
                }
            ],
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/watchlist_ac/_search"
        body = request.json()
        should = body["query"]["bool"]["should"]
        assert any("multi_match" in clause for clause in should)
        assert any(
            clause.get("term", {}).get("ac_patterns.keyword")
            for clause in should
        )
        assert body["min_score"] == config.ac_search.min_score
        return httpx.Response(200, json=response_payload)

    factory = _mock_factory(config, handler)
    adapter = ElasticsearchACAdapter(config, client_factory=factory)

    opts = SearchOpts(top_k=5, metadata_filters={"country": "RU"})
    results = await adapter.search("Иван Петров", opts)

    assert len(results) == 1
    result = results[0]
    assert result.doc_id == "doc-1"
    assert result.search_mode == SearchMode.AC
    assert result.metadata["country"] == "RU"

    await factory.close()


@pytest.mark.asyncio
async def test_vector_adapter_search():
    config = HybridSearchConfig.from_env(env={})
    config.vector_search.vector_dimension = 3

    response_payload = {
        "hits": {
            "max_score": 0.9,
            "hits": [
                {
                    "_id": "vec-1",
                    "_score": 0.9,
                    "_source": {
                        "normalized_text": "Ivan Petrov",
                        "entity_type": "person",
                        "metadata": {"country": "US"},
                    },
                }
            ],
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/watchlist_vector/_search"
        body = request.json()
        assert "knn" in body
        assert body["knn"]["field"] == config.vector_search.vector_field
        assert len(body["knn"]["query_vector"]) == 3
        assert body["knn"]["k"] == 3
        assert body["knn"]["ef_search"] == 64
        assert any(filter_clause.get("ids") for filter_clause in body.get("filter", []))
        return httpx.Response(200, json=response_payload)

    factory = _mock_factory(config, handler)
    adapter = ElasticsearchVectorAdapter(config, client_factory=factory)

    opts = SearchOpts(
        top_k=3,
        metadata_filters={"country": "US", "id": "vec-1"},
        vector_ef_search=64,
    )
    vector = [0.1, 0.2, 0.3]
    results = await adapter.search(vector, opts)

    assert len(results) == 1
    result = results[0]
    assert result.doc_id == "vec-1"
    assert result.search_mode == SearchMode.VECTOR
    assert result.match_fields == [config.vector_search.vector_field]

    await factory.close()


@pytest.mark.asyncio
async def test_vector_adapter_validates_dimension():
    config = HybridSearchConfig.from_env(env={})
    config.vector_search.vector_dimension = 4

    factory = _mock_factory(config, lambda request: httpx.Response(200, json={"hits": {"hits": []}}))
    adapter = ElasticsearchVectorAdapter(config, client_factory=factory)
    opts = SearchOpts(top_k=2)

    with pytest.raises(ValueError):
        await adapter.search([0.1, 0.2], opts)

    await factory.close()

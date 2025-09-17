import json
from pathlib import Path

import httpx
import pytest

from src.ai_service.layers.search.config import HybridSearchConfig
from src.ai_service.layers.search.elasticsearch_client import ElasticsearchClientFactory


def _write_settings(path: Path) -> None:
    data = {
        "search": {
            "elasticsearch": {
                "hosts": ["http://example.com:9200"],
                "verify_certs": False,
                "timeout": 3,
                "smoke_test_timeout": 1,
            }
        }
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def _mock_transport(status_code: int, payload: dict) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/_cluster/health"
        return httpx.Response(status_code, json=payload)

    return httpx.MockTransport(handler)


def test_hybrid_config_from_env(tmp_path, monkeypatch):
    settings_path = tmp_path / "settings.json"
    _write_settings(settings_path)
    monkeypatch.setenv("AI_SEARCH_SETTINGS_PATH", str(settings_path))
    monkeypatch.setenv("ES_HOSTS", "https://override:443")
    monkeypatch.setenv("ES_TIMEOUT", "15")

    cfg = HybridSearchConfig.from_env()

    assert cfg.elasticsearch.timeout == 15
    assert cfg.elasticsearch.normalized_hosts() == ["https://override:443"]


@pytest.mark.asyncio
async def test_elasticsearch_factory_health_check_success(tmp_path, monkeypatch):
    settings_path = tmp_path / "settings.json"
    _write_settings(settings_path)
    monkeypatch.setenv("AI_SEARCH_SETTINGS_PATH", str(settings_path))

    cfg = HybridSearchConfig.from_env()
    factory = ElasticsearchClientFactory(cfg, transport=_mock_transport(200, {"status": "green"}))

    health = await factory.health_check()

    assert health["status"] == "healthy"
    assert health["hosts"][0]["status"] == "healthy"

    await factory.close()


@pytest.mark.asyncio
async def test_elasticsearch_factory_health_check_failure(tmp_path, monkeypatch):
    settings_path = tmp_path / "settings.json"
    _write_settings(settings_path)
    monkeypatch.setenv("AI_SEARCH_SETTINGS_PATH", str(settings_path))

    cfg = HybridSearchConfig.from_env()
    factory = ElasticsearchClientFactory(cfg, transport=_mock_transport(503, {"status": "red"}))

    health = await factory.health_check()

    assert health["status"] == "unhealthy"
    assert health["hosts"][0]["status_code"] == 503
    assert health["hosts"][0]["status"] == "unhealthy"

    await factory.close()

"""
Integration tests for configuration validation endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.ai_service.main import app
from src.ai_service.config.settings import SearchConfig


class TestConfigValidationEndpoints:
    """Test configuration validation endpoints"""
    
    def test_validate_config_endpoint_requires_auth(self):
        """Test validate-config endpoint requires authentication"""
        client = TestClient(app)
        
        response = client.post("/validate-config")
        
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]
    
    def test_validate_config_endpoint_with_invalid_token(self):
        """Test validate-config endpoint with invalid token"""
        client = TestClient(app)
        
        response = client.post(
            "/validate-config",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
    
    @patch('src.ai_service.main.orchestrator')
    def test_validate_config_endpoint_no_orchestrator(self, mock_orchestrator):
        """Test validate-config endpoint when orchestrator not initialized"""
        mock_orchestrator = None
        
        client = TestClient(app)
        
        response = client.post(
            "/validate-config",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 503
        assert "Orchestrator not initialized" in response.json()["detail"]
    
    @patch('src.ai_service.main.orchestrator')
    def test_validate_config_endpoint_success(self, mock_orchestrator):
        """Test validate-config endpoint success"""
        # Mock orchestrator with search service
        mock_search_service = MagicMock()
        mock_search_service.config = SearchConfig()
        mock_search_service._client_factory = MagicMock()
        mock_search_service._client_factory.health_check.return_value = {"status": "green"}
        mock_search_service._fallback_watchlist_service = MagicMock()
        
        mock_orchestrator.search_service = mock_search_service
        
        client = TestClient(app)
        
        response = client.post(
            "/validate-config",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "search_service" in data
        assert data["search_service"]["enabled"] is True
        assert data["search_service"]["validation_passed"] is True
        assert data["search_service"]["errors"] == []
        assert data["search_service"]["warnings"] == []
    
    @patch('src.ai_service.main.orchestrator')
    def test_validate_config_endpoint_with_errors(self, mock_orchestrator):
        """Test validate-config endpoint with validation errors"""
        # Mock orchestrator with search service that has invalid config
        mock_search_service = MagicMock()
        mock_search_service.config = SearchConfig()
        mock_search_service.config.validate.side_effect = Exception("Invalid configuration")
        
        mock_orchestrator.search_service = mock_search_service
        
        client = TestClient(app)
        
        response = client.post(
            "/validate-config",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "search_service" in data
        assert data["search_service"]["enabled"] is True
        assert data["search_service"]["validation_passed"] is False
        assert len(data["search_service"]["errors"]) > 0
        assert "Invalid configuration" in data["search_service"]["errors"][0]
    
    @patch('src.ai_service.main.orchestrator')
    def test_validate_config_endpoint_with_warnings(self, mock_orchestrator):
        """Test validate-config endpoint with warnings"""
        # Mock orchestrator with search service that has warnings
        mock_search_service = MagicMock()
        mock_search_service.config = SearchConfig()
        mock_search_service._client_factory = MagicMock()
        mock_search_service._client_factory.health_check.return_value = {"status": "yellow"}
        mock_search_service._fallback_watchlist_service = None  # Missing fallback service
        
        mock_orchestrator.search_service = mock_search_service
        
        client = TestClient(app)
        
        response = client.post(
            "/validate-config",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "search_service" in data
        assert data["search_service"]["enabled"] is True
        assert data["search_service"]["validation_passed"] is True
        assert len(data["search_service"]["warnings"]) > 0
        
        # Check for specific warnings
        warnings = data["search_service"]["warnings"]
        assert any("Elasticsearch cluster status" in warning for warning in warnings)
        assert any("Fallback enabled but watchlist service not available" in warning for warning in warnings)
    
    def test_config_status_endpoint_requires_auth(self):
        """Test config-status endpoint requires authentication"""
        client = TestClient(app)
        
        response = client.get("/config-status")
        
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]
    
    def test_config_status_endpoint_with_invalid_token(self):
        """Test config-status endpoint with invalid token"""
        client = TestClient(app)
        
        response = client.get(
            "/config-status",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
    
    @patch('src.ai_service.main.orchestrator')
    def test_config_status_endpoint_no_orchestrator(self, mock_orchestrator):
        """Test config-status endpoint when orchestrator not initialized"""
        mock_orchestrator = None
        
        client = TestClient(app)
        
        response = client.get(
            "/config-status",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 503
        assert "Orchestrator not initialized" in response.json()["detail"]
    
    @patch('src.ai_service.main.orchestrator')
    def test_config_status_endpoint_success(self, mock_orchestrator):
        """Test config-status endpoint success"""
        # Mock orchestrator with search service
        mock_search_service = MagicMock()
        mock_search_service.config = SearchConfig()
        mock_search_service.config.get_reload_stats.return_value = {
            "last_reload": "2023-01-01T00:00:00",
            "reload_count": 5,
            "watcher_running": True
        }
        
        mock_orchestrator.search_service = mock_search_service
        
        client = TestClient(app)
        
        response = client.get(
            "/config-status",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "search_service" in data
        assert data["search_service"]["enabled"] is True
        assert data["search_service"]["hot_reload"] is True
        assert "reload_stats" in data["search_service"]
        assert data["search_service"]["reload_stats"]["reload_count"] == 5
    
    def test_reload_config_endpoint_requires_auth(self):
        """Test reload-config endpoint requires authentication"""
        client = TestClient(app)
        
        response = client.post("/reload-config")
        
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]
    
    def test_reload_config_endpoint_with_invalid_token(self):
        """Test reload-config endpoint with invalid token"""
        client = TestClient(app)
        
        response = client.post(
            "/reload-config",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
    
    @patch('src.ai_service.main.orchestrator')
    def test_reload_config_endpoint_no_orchestrator(self, mock_orchestrator):
        """Test reload-config endpoint when orchestrator not initialized"""
        mock_orchestrator = None
        
        client = TestClient(app)
        
        response = client.post(
            "/reload-config",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 503
        assert "Orchestrator not initialized" in response.json()["detail"]
    
    @patch('src.ai_service.main.orchestrator')
    def test_reload_config_endpoint_success(self, mock_orchestrator):
        """Test reload-config endpoint success"""
        # Mock orchestrator with search service
        mock_search_service = MagicMock()
        mock_search_service.config = SearchConfig()
        mock_search_service.config._reload_configuration = MagicMock()
        
        mock_orchestrator.search_service = mock_search_service
        
        client = TestClient(app)
        
        response = client.post(
            "/reload-config",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "Configuration reloaded successfully" in data["message"]
        
        # Verify reload method was called
        mock_search_service.config._reload_configuration.assert_called_once()
    
    @patch('src.ai_service.main.orchestrator')
    def test_reload_config_endpoint_error(self, mock_orchestrator):
        """Test reload-config endpoint with error"""
        # Mock orchestrator with search service that throws error
        mock_search_service = MagicMock()
        mock_search_service.config = SearchConfig()
        mock_search_service.config._reload_configuration.side_effect = Exception("Reload failed")
        
        mock_orchestrator.search_service = mock_search_service
        
        client = TestClient(app)
        
        response = client.post(
            "/reload-config",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 500
        data = response.json()
        
        assert "detail" in data
        assert "Internal Server Error" in data["detail"]

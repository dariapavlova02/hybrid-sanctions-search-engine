"""
Test suite for main API endpoints.

Tests the FastAPI application endpoints including process, normalize,
health checks, and admin functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from ai_service.main import app
from ai_service.contracts.base_contracts import (
    UnifiedProcessingResult, TokenTrace, SignalsResult, SignalsPerson, SignalsOrganization, SignalsExtras
)
from ai_service.exceptions import ServiceUnavailableError, InternalServerError


class TestMainEndpoints:
    """Test main API endpoints functionality"""

    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)

    def test_health_check_no_orchestrator(self):
        """Test health check when orchestrator not initialized"""
        with patch('ai_service.main.orchestrator', None):
            response = self.client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "initializing"
            assert data["orchestrator"]["initialized"] is False

    def test_health_check_with_orchestrator(self):
        """Test health check when orchestrator is initialized"""
        mock_stats = {
            "total_processed": 100,
            "successful": 95,
            "cache": {"hit_rate": 0.85},
            "services": {"normalization": "ready", "embeddings": "ready"}
        }

        mock_orchestrator = Mock()
        mock_orchestrator.get_processing_stats.return_value = mock_stats

        with patch('ai_service.main.orchestrator', mock_orchestrator):
            response = self.client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["orchestrator"]["initialized"] is True
            assert data["orchestrator"]["processed_total"] == 100
            assert data["orchestrator"]["success_rate"] == 0.95
            assert data["orchestrator"]["cache_hit_rate"] == 0.85

    def test_process_text_endpoint_success(self):
        """Test successful text processing endpoint"""
        # Create mock processing result
        mock_trace = TokenTrace(
            token="Иван",
            role="given",
            rule="name_pattern",
            morph_lang="ru",
            normal_form="Иван",
            output="Иван",
            fallback=False
        )

        mock_signals = SignalsResult(
            persons=[SignalsPerson(
                core=["Иван", "Иванов"],
                full_name="Иван Иванов",
                confidence=0.9,
                evidence=["name_pattern"]
            )],
            organizations=[SignalsOrganization(
                core="РОМАШКА",
                legal_form="ООО",
                full_name="ООО РОМАШКА",
                confidence=0.85,
                evidence=["legal_form_hit"]
            )],
            extras=SignalsExtras(),
            confidence=0.87
        )

        mock_result = UnifiedProcessingResult(
            original_text="ООО Ромашка, Иван Иванов",
            language="ru",
            language_confidence=0.95,
            normalized_text="ромашка иван иванов",
            tokens=["ромашка", "иван", "иванов"],
            trace=[mock_trace],
            signals=mock_signals,
            variants=["Ivan Ivanov", "Иван Иванов"],
            processing_time=0.05,
            success=True,
            errors=[]
        )

        mock_orchestrator = AsyncMock()
        mock_orchestrator.process.return_value = mock_result

        request_data = {
            "text": "ООО Ромашка, Иван Иванов",
            "generate_variants": True,
            "generate_embeddings": False
        }

        with patch('ai_service.main.orchestrator', mock_orchestrator):
            response = self.client.post("/process", json=request_data)

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert data["original_text"] == "ООО Ромашка, Иван Иванов"
            assert data["normalized_text"] == "ромашка иван иванов"
            assert data["language"] == "ru"
            assert data["language_confidence"] == 0.95
            assert data["tokens"] == ["ромашка", "иван", "иванов"]
            assert len(data["signals"]["persons"]) == 1
            assert len(data["signals"]["organizations"]) == 1
            assert data["signals"]["confidence"] == 0.87

            # Verify orchestrator was called correctly
            mock_orchestrator.process.assert_called_once_with(
                text="ООО Ромашка, Иван Иванов",
                generate_variants=True,
                generate_embeddings=False,
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True
            )

    def test_process_text_no_orchestrator(self):
        """Test process endpoint when orchestrator not initialized"""
        request_data = {
            "text": "test text",
            "generate_variants": False,
            "generate_embeddings": False
        }

        with patch('ai_service.main.orchestrator', None):
            response = self.client.post("/process", json=request_data)

            assert response.status_code == 503
            assert "Orchestrator not initialized" in response.json()["detail"]

    def test_process_text_internal_error(self):
        """Test process endpoint with internal processing error"""
        mock_orchestrator = AsyncMock()
        mock_orchestrator.process.side_effect = Exception("Processing failed")

        request_data = {
            "text": "test text",
            "generate_variants": False,
            "generate_embeddings": False
        }

        with patch('ai_service.main.orchestrator', mock_orchestrator):
            response = self.client.post("/process", json=request_data)

            assert response.status_code == 500
            assert "Processing failed" in response.json()["detail"]

    def test_process_text_validation_error(self):
        """Test process endpoint with request validation error"""
        # Missing required field
        invalid_request = {
            "generate_variants": True
            # text field is missing
        }

        response = self.client.post("/process", json=invalid_request)
        assert response.status_code == 422

        # Text too long
        long_text = "a" * 5001  # Exceeds max_length
        invalid_request = {
            "text": long_text,
            "generate_variants": False,
            "generate_embeddings": False
        }

        response = self.client.post("/process", json=invalid_request)
        assert response.status_code == 422

    def test_normalize_text_endpoint_success(self):
        """Test successful text normalization endpoint"""
        mock_trace = TokenTrace(
            token="Иван",
            role="given",
            rule="name_pattern",
            output="Иван"
        )

        mock_result = UnifiedProcessingResult(
            original_text="Иван Иванов",
            language="ru",
            language_confidence=0.95,
            normalized_text="иван иванов",
            tokens=["иван", "иванов"],
            trace=[mock_trace],
            signals=SignalsResult(
                persons=[],
                organizations=[],
                extras=SignalsExtras(),
                confidence=0.0
            ),
            processing_time=0.02,
            success=True
        )

        mock_orchestrator = AsyncMock()
        mock_orchestrator.process.return_value = mock_result

        request_data = {"text": "Иван Иванов"}

        with patch('ai_service.main.orchestrator', mock_orchestrator):
            response = self.client.post("/normalize", json=request_data)

            assert response.status_code == 200
            data = response.json()

            assert data["normalized_text"] == "иван иванов"
            assert data["tokens"] == ["иван", "иванов"]
            assert data["language"] == "ru"
            assert data["processing_time"] == 0.02

            # Should call process with variants/embeddings disabled
            mock_orchestrator.process.assert_called_once_with(
                text="Иван Иванов",
                generate_variants=False,
                generate_embeddings=False,
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True
            )

    def test_process_batch_endpoint_success(self):
        """Test successful batch processing endpoint"""
        mock_result = UnifiedProcessingResult(
            original_text="test",
            language="en",
            language_confidence=0.9,
            normalized_text="test",
            tokens=["test"],
            trace=[],
            signals=SignalsResult(
                persons=[], organizations=[], extras=SignalsExtras(), confidence=0.0
            ),
            success=True
        )

        mock_orchestrator = AsyncMock()
        mock_orchestrator.process_batch.return_value = [mock_result, mock_result]

        request_data = {
            "texts": ["text one", "text two"],
            "generate_variants": False,
            "generate_embeddings": False
        }

        with patch('ai_service.main.orchestrator', mock_orchestrator):
            response = self.client.post("/process-batch", json=request_data)

            assert response.status_code == 200
            data = response.json()

            assert len(data["results"]) == 2
            assert all(result["success"] for result in data["results"])

            mock_orchestrator.process_batch.assert_called_once()

    def test_search_similar_endpoint_success(self):
        """Test successful similarity search endpoint"""
        mock_results = [
            {
                "text": "John Smith",
                "similarity": 0.95,
                "metadata": {"source": "sanctions_list"}
            },
            {
                "text": "Jon Smith",
                "similarity": 0.87,
                "metadata": {"source": "pep_list"}
            }
        ]

        mock_orchestrator = AsyncMock()
        mock_orchestrator.search_similar.return_value = mock_results

        request_data = {
            "query": "John Smith",
            "candidates": ["John Smith", "Jon Smith", "Jane Doe"],
            "threshold": 0.8,
            "top_k": 5
        }

        with patch('ai_service.main.orchestrator', mock_orchestrator):
            response = self.client.post("/search-similar", json=request_data)

            assert response.status_code == 200
            data = response.json()

            assert len(data["results"]) == 2
            assert data["results"][0]["similarity"] == 0.95
            assert data["results"][1]["similarity"] == 0.87

    @pytest.mark.asyncio
    async def test_startup_event_success(self):
        """Test successful startup event"""
        mock_orchestrator = AsyncMock()

        with patch('ai_service.main.OrchestratorFactory') as mock_factory:
            with patch('ai_service.main.check_spacy_models', return_value=True):
                mock_factory.create_production_orchestrator.return_value = mock_orchestrator

                from ai_service.main import startup_event
                await startup_event()

                mock_factory.create_production_orchestrator.assert_called_once()

    @pytest.mark.asyncio
    async def test_startup_event_failure(self):
        """Test startup event with initialization failure"""
        with patch('ai_service.main.OrchestratorFactory') as mock_factory:
            with patch('ai_service.main.check_spacy_models', return_value=True):
                mock_factory.create_production_orchestrator.side_effect = Exception("Init failed")

                from ai_service.main import startup_event

                with pytest.raises(Exception) as exc_info:
                    await startup_event()

                assert "Init failed" in str(exc_info.value)

    def test_admin_status_endpoint_unauthorized(self):
        """Test admin status without proper authentication"""
        response = self.client.get("/admin/status")
        assert response.status_code == 403

    def test_admin_status_endpoint_invalid_token(self):
        """Test admin status with invalid token"""
        headers = {"Authorization": "Bearer invalid-token"}

        with patch('ai_service.main.SECURITY_CONFIG') as mock_config:
            mock_config.admin_api_key = "valid-token"

            response = self.client.get("/admin/status", headers=headers)
            assert response.status_code == 401

    def test_admin_status_endpoint_success(self):
        """Test admin status with valid token"""
        headers = {"Authorization": "Bearer valid-admin-token"}

        mock_orchestrator = Mock()
        mock_stats = {
            "total_processed": 1000,
            "successful": 950,
            "failed": 50,
            "cache": {"hits": 800, "misses": 200}
        }
        mock_orchestrator.get_detailed_stats.return_value = mock_stats

        with patch('ai_service.main.SECURITY_CONFIG') as mock_config:
            with patch('ai_service.main.orchestrator', mock_orchestrator):
                mock_config.admin_api_key = "valid-admin-token"

                response = self.client.get("/admin/status", headers=headers)

                assert response.status_code == 200
                data = response.json()
                assert "detailed_stats" in data
                assert data["detailed_stats"]["total_processed"] == 1000

    def test_cors_configuration(self):
        """Test CORS middleware configuration"""
        # This is more of an integration test
        # CORS headers should be present in responses
        response = self.client.options("/health")
        # Note: TestClient doesn't fully simulate CORS, but we can test the setup
        assert response.status_code in [200, 405]  # OPTIONS might not be implemented

    def test_request_validation_models(self):
        """Test Pydantic request model validation"""
        from ai_service.main import TextNormalizationRequest, ProcessTextRequest

        # Valid request
        valid_data = {"text": "test text"}
        request = TextNormalizationRequest(**valid_data)
        assert request.text == "test text"

        # Invalid request - text too long
        invalid_data = {"text": "a" * 10000}
        with pytest.raises(ValueError):
            TextNormalizationRequest(**invalid_data)

        # ProcessTextRequest with defaults
        process_request = ProcessTextRequest(text="test")
        assert process_request.generate_variants is True
        assert process_request.generate_embeddings is False

    def test_error_handler_responses(self):
        """Test custom error handler responses"""
        mock_orchestrator = AsyncMock()

        # Test ServiceUnavailableError handling
        mock_orchestrator.process.side_effect = ServiceUnavailableError("Service down")

        with patch('ai_service.main.orchestrator', mock_orchestrator):
            response = self.client.post("/process", json={
                "text": "test",
                "generate_variants": False,
                "generate_embeddings": False
            })

            assert response.status_code == 503

        # Test InternalServerError handling
        mock_orchestrator.process.side_effect = InternalServerError("Internal error")

        with patch('ai_service.main.orchestrator', mock_orchestrator):
            response = self.client.post("/process", json={
                "text": "test",
                "generate_variants": False,
                "generate_embeddings": False
            })

            assert response.status_code == 500
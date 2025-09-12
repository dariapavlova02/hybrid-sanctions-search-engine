#!/usr/bin/env python3
"""
Test pipeline without mocks to verify real functionality.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

import pytest
from ai_service.orchestration.clean_orchestrator import CleanOrchestratorService
from ai_service.config.settings import ServiceConfig


class TestPipelineWithoutMocks:
    """Test pipeline functionality without mocks."""

    @pytest.fixture(scope="function")
    def orchestrator_service(self):
        """Provides a clean orchestrator service instance without mocks."""
        # Create service configuration
        config = ServiceConfig(
            enable_advanced_features=True,
            enable_morphology=True,
            preserve_names=True,
            clean_unicode=True,
            enable_transliterations=True,
        )

        # Initialize orchestrator service
        service = CleanOrchestratorService(config=config)
        
        yield service

    def test_simple_name_extraction_no_mocks(self, orchestrator_service):
        """Test simple name extraction without mocks."""
        input_text = "Оплата от Петра Порошенка по Договору 123"
        
        result = orchestrator_service.process_text(input_text)
        
        print(f"\n=== NO MOCKS DEBUG ===")
        print(f"Input text: '{input_text}'")
        print(f"Result success: {result.success}")
        print(f"Result context: {result.context}")
        if result.context:
            print(f"Original text: '{result.context.original_text}'")
            print(f"Current text: '{result.context.current_text}'")
            print(f"Language: {result.context.language}")
            print(f"Metadata: {result.context.metadata}")
        print(f"Errors: {result.errors}")
        print(f"=====================\n")
        
        assert result is not None
        assert result.success is True
        
        assert result.context is not None
        normalized_text = result.context.current_text
        assert normalized_text is not None
        assert len(normalized_text) > 0
        
        # Check that the name is present in normalized text (case-insensitive)
        normalized_lower = normalized_text.lower()
        name_found = (("петро" in normalized_lower or "петра" in normalized_lower) and 
                     ("порошенко" in normalized_lower or "порошенка" in normalized_lower))
        assert name_found, f"Expected to find 'петро/петра' and 'порошенко/порошенка' in normalized text: '{normalized_text}'"
        
        detected_language = result.context.language
        assert detected_language in ["uk", "ru"], f"Expected Ukrainian or Russian language, got: {detected_language}"


if __name__ == "__main__":
    # Run the test directly
    import subprocess
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        __file__ + "::TestPipelineWithoutMocks::test_simple_name_extraction_no_mocks",
        "-v", "-s"
    ])
    sys.exit(result.returncode)

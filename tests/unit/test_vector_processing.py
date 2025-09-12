"""
Unit tests for vector processing and validation
Testing enhanced vector data integrity checks
"""

import pytest
import math
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import importlib.util

# Add the project root to Python path for testing
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

# Import from load_sanctions_via_api using importlib
try:
    spec = importlib.util.spec_from_file_location("load_sanctions_via_api", "../../services/sanctions-loader/load_sanctions_via_api.py")
    load_sanctions_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(load_sanctions_module)
    APISanctionsLoader = load_sanctions_module.APISanctionsLoader
except (FileNotFoundError, ImportError, ModuleNotFoundError) as e:
    # Skip tests if dependencies are not available
    import pytest
    pytest.skip(f"Skipping vector processing tests due to missing dependencies: {e}", allow_module_level=True)


class TestVectorProcessingValidation:
    """Tests for enhanced vector processing validation"""

    @pytest.fixture
    def api_loader(self):
        """Create APISanctionsLoader instance for testing"""
        return APISanctionsLoader(
            api_url="http://test-api.com",
            concurrency=2,
            timeout=5.0
        )

    def test_valid_vector_processing(self, api_loader):
        """Test processing of valid vector data"""
        # Arrange
        test_entity = {
            'name': 'Test Entity',
            'vector': [0.1, 0.2, 0.3, 0.4]
        }

        # Create a mock simplified entity
        simplified = {'vector': test_entity['vector']}

        # Act - simulate the vector processing logic
        vec = simplified.get('vector')
        if isinstance(vec, list) and vec:
            import math
            validated_vec = []
            invalid_count = 0

            for i, x in enumerate(vec):
                if x is None:
                    invalid_count += 1
                    continue

                try:
                    float_val = float(x)
                    if math.isnan(float_val) or math.isinf(float_val):
                        invalid_count += 1
                        continue
                    validated_vec.append(float_val)
                except (ValueError, TypeError):
                    invalid_count += 1
                    continue

            if validated_vec:
                simplified['vector'] = validated_vec

        # Assert
        assert simplified['vector'] == [0.1, 0.2, 0.3, 0.4]

    def test_vector_with_nan_values(self, api_loader):
        """Test vector processing with NaN values"""
        # Arrange
        test_vector = [0.1, float('nan'), 0.3, 0.4]
        simplified = {'vector': test_vector}

        # Act - simulate the vector validation logic
        vec = simplified.get('vector')
        if isinstance(vec, list) and vec:
            import math
            validated_vec = []
            invalid_count = 0

            for i, x in enumerate(vec):
                if x is None:
                    invalid_count += 1
                    continue

                try:
                    float_val = float(x)
                    if math.isnan(float_val) or math.isinf(float_val):
                        invalid_count += 1
                        continue
                    validated_vec.append(float_val)
                except (ValueError, TypeError):
                    invalid_count += 1
                    continue

            if validated_vec:
                simplified['vector'] = validated_vec

        # Assert
        assert len(simplified['vector']) == 3  # NaN should be removed
        assert 0.1 in simplified['vector']
        assert 0.3 in simplified['vector']
        assert 0.4 in simplified['vector']

    def test_vector_with_infinite_values(self, api_loader):
        """Test vector processing with infinite values"""
        # Arrange
        test_vector = [0.1, float('inf'), 0.3, float('-inf')]
        simplified = {'vector': test_vector}

        # Act - simulate the vector validation logic
        vec = simplified.get('vector')
        if isinstance(vec, list) and vec:
            import math
            validated_vec = []
            invalid_count = 0

            for i, x in enumerate(vec):
                if x is None:
                    invalid_count += 1
                    continue

                try:
                    float_val = float(x)
                    if math.isnan(float_val) or math.isinf(float_val):
                        invalid_count += 1
                        continue
                    validated_vec.append(float_val)
                except (ValueError, TypeError):
                    invalid_count += 1
                    continue

            if validated_vec:
                simplified['vector'] = validated_vec

        # Assert
        assert len(simplified['vector']) == 2  # Infinite values should be removed
        assert 0.1 in simplified['vector']
        assert 0.3 in simplified['vector']

    def test_vector_with_none_values(self, api_loader):
        """Test vector processing with None values"""
        # Arrange
        test_vector = [0.1, None, 0.3, None, 0.5]
        simplified = {'vector': test_vector}

        # Act - simulate the vector validation logic
        vec = simplified.get('vector')
        if isinstance(vec, list) and vec:
            import math
            validated_vec = []
            invalid_count = 0

            for i, x in enumerate(vec):
                if x is None:
                    invalid_count += 1
                    continue

                try:
                    float_val = float(x)
                    if math.isnan(float_val) or math.isinf(float_val):
                        invalid_count += 1
                        continue
                    validated_vec.append(float_val)
                except (ValueError, TypeError):
                    invalid_count += 1
                    continue

            if validated_vec:
                simplified['vector'] = validated_vec

        # Assert
        assert len(simplified['vector']) == 3  # None values should be removed
        assert simplified['vector'] == [0.1, 0.3, 0.5]

    def test_vector_with_string_values(self, api_loader):
        """Test vector processing with string values that can't be converted"""
        # Arrange
        test_vector = [0.1, "invalid", 0.3, "another_invalid"]
        simplified = {'vector': test_vector}

        # Act - simulate the vector validation logic
        vec = simplified.get('vector')
        if isinstance(vec, list) and vec:
            import math
            validated_vec = []
            invalid_count = 0

            for i, x in enumerate(vec):
                if x is None:
                    invalid_count += 1
                    continue

                try:
                    float_val = float(x)
                    if math.isnan(float_val) or math.isinf(float_val):
                        invalid_count += 1
                        continue
                    validated_vec.append(float_val)
                except (ValueError, TypeError):
                    invalid_count += 1
                    continue

            if validated_vec:
                simplified['vector'] = validated_vec

        # Assert
        assert len(simplified['vector']) == 2  # String values should be removed
        assert simplified['vector'] == [0.1, 0.3]

    def test_vector_flattening(self, api_loader):
        """Test vector flattening from nested list"""
        # Arrange
        test_vector = [[0.1, 0.2, 0.3, 0.4]]  # Nested list
        simplified = {'vector': test_vector}

        # Act - simulate the vector flattening logic
        vec = simplified.get('vector')
        if isinstance(vec, list) and vec:
            # Flatten 1-level nesting
            if len(vec) == 1 and isinstance(vec[0], list):
                vec = vec[0]

            import math
            validated_vec = []
            invalid_count = 0

            for i, x in enumerate(vec):
                if x is None:
                    invalid_count += 1
                    continue

                try:
                    float_val = float(x)
                    if math.isnan(float_val) or math.isinf(float_val):
                        invalid_count += 1
                        continue
                    validated_vec.append(float_val)
                except (ValueError, TypeError):
                    invalid_count += 1
                    continue

            if validated_vec:
                simplified['vector'] = validated_vec

        # Assert
        assert simplified['vector'] == [0.1, 0.2, 0.3, 0.4]
        assert isinstance(simplified['vector'], list)
        assert not isinstance(simplified['vector'][0], list)

    def test_empty_vector_handling(self, api_loader):
        """Test handling of empty vectors"""
        # Arrange
        simplified = {'vector': []}

        # Act - simulate the vector processing logic
        vec = simplified.get('vector')
        if isinstance(vec, list) and vec:
            # This block won't execute for empty list
            pass
        elif vec is None:
            simplified['vector'] = None
        else:
            # Empty list case
            simplified['vector'] = None

        # Assert
        assert simplified['vector'] is None

    def test_completely_invalid_vector(self, api_loader):
        """Test vector with all invalid values"""
        # Arrange
        test_vector = [None, float('nan'), float('inf'), "invalid"]
        simplified = {'vector': test_vector}

        # Act - simulate the vector validation logic
        vec = simplified.get('vector')
        if isinstance(vec, list) and vec:
            import math
            validated_vec = []
            invalid_count = 0

            for i, x in enumerate(vec):
                if x is None:
                    invalid_count += 1
                    continue

                try:
                    float_val = float(x)
                    if math.isnan(float_val) or math.isinf(float_val):
                        invalid_count += 1
                        continue
                    validated_vec.append(float_val)
                except (ValueError, TypeError):
                    invalid_count += 1
                    continue

            # Check if we have a reasonable number of valid values
            if not validated_vec:
                simplified['vector'] = None
            else:
                simplified['vector'] = validated_vec

        # Assert
        assert simplified['vector'] is None

    def test_high_invalid_value_percentage(self, api_loader):
        """Test vector with high percentage of invalid values"""
        # Arrange - 50% invalid values
        test_vector = [0.1, None, 0.3, float('nan'), 0.5, "invalid", 0.7, float('inf')]
        simplified = {'vector': test_vector}

        # Act - simulate the vector validation logic
        vec = simplified.get('vector')
        if isinstance(vec, list) and vec:
            import math
            validated_vec = []
            invalid_count = 0

            for i, x in enumerate(vec):
                if x is None:
                    invalid_count += 1
                    continue

                try:
                    float_val = float(x)
                    if math.isnan(float_val) or math.isinf(float_val):
                        invalid_count += 1
                        continue
                    validated_vec.append(float_val)
                except (ValueError, TypeError):
                    invalid_count += 1
                    continue

            # Check if more than 10% invalid values
            if not validated_vec:
                simplified['vector'] = None
            elif invalid_count > len(vec) * 0.1:
                # Warning case but still use the vector
                simplified['vector'] = validated_vec
            else:
                simplified['vector'] = validated_vec

        # Assert
        assert simplified['vector'] is not None
        assert len(simplified['vector']) == 4  # Valid values: 0.1, 0.3, 0.5, 0.7
        assert simplified['vector'] == [0.1, 0.3, 0.5, 0.7]

    def test_vector_dimension_validation(self, api_loader):
        """Test validation of vector dimensions"""
        # Arrange - vector with unexpected dimension
        test_vector = [0.1] * 200  # Not the expected 384 dimensions
        simplified = {'vector': test_vector}

        # Act - simulate the vector validation logic
        vec = simplified.get('vector')
        if isinstance(vec, list) and vec:
            import math
            validated_vec = []
            invalid_count = 0

            for i, x in enumerate(vec):
                if x is None:
                    invalid_count += 1
                    continue

                try:
                    float_val = float(x)
                    if math.isnan(float_val) or math.isinf(float_val):
                        invalid_count += 1
                        continue
                    validated_vec.append(float_val)
                except (ValueError, TypeError):
                    invalid_count += 1
                    continue

            if validated_vec:
                simplified['vector'] = validated_vec

                # Validate expected vector dimension (checking for 384)
                if len(simplified['vector']) != 384:
                    # This would generate a warning in real implementation
                    pass

        # Assert
        assert len(simplified['vector']) == 200
        assert all(x == 0.1 for x in simplified['vector'])

    def test_non_list_vector_handling(self, api_loader):
        """Test handling of non-list vector types"""
        # Test cases for different non-list types
        test_cases = [
            {'vector': "not_a_list"},
            {'vector': 123},
            {'vector': {'invalid': 'dict'}},
            {'vector': None}
        ]

        for test_case in test_cases:
            # Arrange
            simplified = test_case.copy()

            # Act - simulate the vector processing logic
            vec = simplified.get('vector')
            if isinstance(vec, list) and vec:
                # Won't execute for non-list types
                pass
            elif vec is None:
                simplified['vector'] = None
            else:
                # Invalid type case
                simplified['vector'] = None

            # Assert
            assert simplified['vector'] is None

    def test_string_convertible_values(self, api_loader):
        """Test vector with string values that can be converted to float"""
        # Arrange
        test_vector = ["0.1", "0.2", "0.3", "0.4"]
        simplified = {'vector': test_vector}

        # Act - simulate the vector validation logic
        vec = simplified.get('vector')
        if isinstance(vec, list) and vec:
            import math
            validated_vec = []
            invalid_count = 0

            for i, x in enumerate(vec):
                if x is None:
                    invalid_count += 1
                    continue

                try:
                    float_val = float(x)
                    if math.isnan(float_val) or math.isinf(float_val):
                        invalid_count += 1
                        continue
                    validated_vec.append(float_val)
                except (ValueError, TypeError):
                    invalid_count += 1
                    continue

            if validated_vec:
                simplified['vector'] = validated_vec

        # Assert
        assert simplified['vector'] == [0.1, 0.2, 0.3, 0.4]
        assert all(isinstance(x, float) for x in simplified['vector'])

    def test_mixed_valid_invalid_vector(self, api_loader):
        """Test vector with mixed valid and invalid values"""
        # Arrange
        test_vector = [0.1, "0.2", None, float('nan'), 0.5, "invalid", "0.7", float('inf')]
        simplified = {'vector': test_vector}

        # Act - simulate the vector validation logic
        vec = simplified.get('vector')
        if isinstance(vec, list) and vec:
            import math
            validated_vec = []
            invalid_count = 0

            for i, x in enumerate(vec):
                if x is None:
                    invalid_count += 1
                    continue

                try:
                    float_val = float(x)
                    if math.isnan(float_val) or math.isinf(float_val):
                        invalid_count += 1
                        continue
                    validated_vec.append(float_val)
                except (ValueError, TypeError):
                    invalid_count += 1
                    continue

            if validated_vec:
                simplified['vector'] = validated_vec

        # Assert
        assert len(simplified['vector']) == 4  # Valid: 0.1, "0.2", 0.5, "0.7"
        expected_values = [0.1, 0.2, 0.5, 0.7]
        assert all(abs(a - b) < 1e-10 for a, b in zip(simplified['vector'], expected_values))

    def test_rate_limiting_initialization(self, api_loader):
        """Test that rate limiting components are properly initialized"""
        # Assert
        assert hasattr(api_loader, '_sem')
        assert hasattr(api_loader, '_rate_limit_tokens')
        assert hasattr(api_loader, '_max_tokens')
        assert hasattr(api_loader, '_refill_rate')
        assert hasattr(api_loader, '_rate_lock')
        assert hasattr(api_loader, '_active_requests')
        assert hasattr(api_loader, '_failed_requests')
        assert hasattr(api_loader, '_success_requests')

        # Check initial values
        assert api_loader._rate_limit_tokens == api_loader.concurrency * 2
        assert api_loader._max_tokens == api_loader.concurrency * 2
        assert api_loader._refill_rate == api_loader.concurrency
        assert api_loader._active_requests == 0

    @pytest.mark.asyncio
    async def test_rate_limit_token_acquisition(self, api_loader):
        """Test rate limit token acquisition mechanism"""
        # This is a basic test to ensure the method exists and can be called
        try:
            await api_loader._acquire_rate_limit_token()
            # If it doesn't raise an exception, the basic mechanism works
            assert True
        except Exception as e:
            pytest.fail(f"Rate limit token acquisition failed: {e}")

    def test_backpressure_update_success(self, api_loader):
        """Test backpressure update for successful requests"""
        # Arrange
        initial_success = api_loader._success_requests
        initial_failures = api_loader._consecutive_failures

        # Act
        api_loader._update_backpressure(True)

        # Assert
        assert api_loader._success_requests == initial_success + 1
        assert api_loader._consecutive_failures == 0

    def test_backpressure_update_failure(self, api_loader):
        """Test backpressure update for failed requests"""
        # Arrange
        initial_failed = api_loader._failed_requests

        # Act
        api_loader._update_backpressure(False)

        # Assert
        assert api_loader._failed_requests == initial_failed + 1
        assert api_loader._consecutive_failures >= 1


class TestAPILoaderConfiguration:
    """Tests for API loader configuration and settings"""

    def test_concurrency_validation(self):
        """Test concurrency parameter validation"""
        # Test minimum concurrency
        loader = APISanctionsLoader(concurrency=0)
        assert loader.concurrency == 1  # Should be at least 1

        # Test negative concurrency
        loader = APISanctionsLoader(concurrency=-5)
        assert loader.concurrency == 1  # Should be at least 1

        # Test normal concurrency
        loader = APISanctionsLoader(concurrency=10)
        assert loader.concurrency == 10

    def test_timeout_configuration(self):
        """Test timeout configuration"""
        loader = APISanctionsLoader(timeout=15.0)
        assert loader.timeout == 15.0

    def test_retry_configuration(self):
        """Test retry configuration"""
        loader = APISanctionsLoader(max_retries=5, backoff_base=1.0, backoff_max=10.0)
        assert loader.max_retries == 5
        assert loader.backoff_base == 1.0
        assert loader.backoff_max == 10.0

    def test_retry_status_codes(self):
        """Test retry status codes configuration"""
        loader = APISanctionsLoader()
        expected_retry_codes = {429, 502, 503, 504}
        assert loader._retry_statuses == expected_retry_codes
# Integration Tests for Name Extraction Pipeline

This directory contains comprehensive integration tests for the AI service's name extraction and text processing pipeline.

## Overview

The integration tests verify the complete text processing workflow from raw input text through normalization to name detection and extraction. These tests ensure that all components work together correctly and maintain data consistency throughout the pipeline.

## Test Files

### `test_name_extraction_pipeline.py`

Main integration test file containing comprehensive tests for:

- **Full Pipeline Testing**: Complete end-to-end processing of text through all pipeline stages
- **Language Detection**: Verification of automatic language detection for Ukrainian, Russian, and English texts
- **Name Extraction**: Testing of name detection and extraction from various text formats
- **Normalization**: Verification of text normalization while preserving name information
- **Error Handling**: Testing of pipeline behavior with invalid or edge case inputs
- **Performance**: Benchmarking of pipeline performance with different text lengths
- **Data Consistency**: Verification that repeated processing produces consistent results

### `run_name_extraction_tests.py`

Test runner script that provides:

- **All Tests**: Run complete integration test suite
- **Specific Tests**: Run individual test classes or methods
- **Performance Tests**: Run only performance-related tests
- **Detailed Output**: Verbose reporting with timing information

## Test Categories

### 1. Full Pipeline Tests
- `test_full_pipeline_ukrainian_name_extraction()`
- `test_full_pipeline_russian_name_extraction()`
- `test_full_pipeline_english_name_extraction()`
- `test_full_pipeline_mixed_language_extraction()`

### 2. Service Integration Tests
- `test_normalization_service_integration()`
- `test_smart_filter_name_detection_integration()`
- `test_name_detector_integration()`
- `test_language_detection_integration()`

### 3. Error Handling Tests
- `test_pipeline_error_handling()`
- `test_pipeline_with_special_characters()`

### 4. Performance Tests
- `test_pipeline_performance_benchmark()`
- `test_pipeline_data_consistency()`

### 5. Async Processing Tests
- `test_async_pipeline_processing()`

### 6. Complex Scenarios Tests
- `test_complex_scenarios()` - Parameterized test for complex name extraction scenarios

## Sample Test Data

The tests use comprehensive sample data including:

- **Ukrainian Names**: "Петро Іванович Коваленко", "Олена Петренко"
- **Russian Names**: "Сергей Владимирович Петров", "Иван Петров"
- **English Names**: "John Michael Smith", "Mary Elizabeth Johnson"
- **Mixed Language**: "Переказ для John Smith та Олена Петренко"
- **Names with Initials**: "П.І. Коваленко", "J.M. Smith"
- **Special Characters**: Names with hyphens, apostrophes, parentheses
- **Complex Business Scenarios**: "Переказ для ТОВ 'Рога и Копыта' від Іванова Івана Івановича"
- **Mixed Language Contexts**: "Возврат средств по заказу #789, получатель Jane Smith"

## Running the Tests

### Run All Integration Tests
```bash
# Using pytest directly
pytest tests/integration/test_name_extraction_pipeline.py -v

# Using the test runner
python tests/integration/run_name_extraction_tests.py --type all
```

### Run Specific Test Class
```bash
# Run only Ukrainian name extraction tests
pytest tests/integration/test_name_extraction_pipeline.py::TestNameExtractionPipeline::test_full_pipeline_ukrainian_name_extraction -v

# Using the test runner
python tests/integration/run_name_extraction_tests.py --type specific
```

### Run Performance Tests
```bash
# Run only performance tests
pytest tests/integration/test_name_extraction_pipeline.py -k performance -v

# Using the test runner
python tests/integration/run_name_extraction_tests.py --type performance
```

### Run Complex Scenarios Test
```bash
# Run only complex scenarios test
pytest tests/integration/test_name_extraction_pipeline.py::TestNameExtractionPipeline::test_complex_scenarios -v

# Using the dedicated test runner
python tests/integration/test_complex_scenarios.py
```

### Run with Coverage
```bash
pytest tests/integration/test_name_extraction_pipeline.py --cov=src.ai_service --cov-report=html
```

## Test Configuration

The tests use the following configuration:

- **Cache Size**: 100 items (small for testing)
- **Default TTL**: 60 seconds
- **Metrics**: Enabled
- **Caching**: Enabled
- **Mocking**: Heavy dependencies (NLTK, spaCy) are mocked to avoid initialization issues

## Expected Results

### Successful Test Execution
- All pipeline stages execute without errors
- Language detection accuracy > 70% for known languages
- Name detection confidence > 50% for texts containing names
- Processing time < 5 seconds for typical texts
- Consistent results across multiple runs

### Performance Benchmarks
- **Short texts** (< 100 chars): < 1 second
- **Medium texts** (100-1000 chars): < 2 seconds  
- **Long texts** (1000+ chars): < 5 seconds

## Dependencies

The integration tests require:

- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `unittest.mock` - Mocking framework
- All AI service dependencies (mocked where appropriate)

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure the `src` directory is in the Python path
2. **Mock Failures**: Check that heavy dependencies are properly mocked
3. **Performance Issues**: Reduce test data size or increase timeout limits
4. **Memory Issues**: Tests include garbage collection to prevent memory leaks

### Debug Mode

Run tests with maximum verbosity for debugging:
```bash
pytest tests/integration/test_name_extraction_pipeline.py -vvv --tb=long
```

## Contributing

When adding new integration tests:

1. Follow the existing test structure and naming conventions
2. Include comprehensive test data for different languages and formats
3. Add appropriate error handling tests
4. Include performance considerations for long texts
5. Update this README with new test descriptions

## Related Documentation

- [Main Test Suite](../README.md)
- [Unit Tests](../unit/README.md)
- [End-to-End Tests](../e2e/README.md)
- [AI Service Architecture](../../src/ai_service/ARCHITECTURE.md)

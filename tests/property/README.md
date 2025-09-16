# Property-Based Tests for Hybrid Search System

This directory contains property-based tests using Hypothesis to prevent test overfitting and ensure system invariants are maintained across all possible inputs.

## Overview

Property-based testing generates random inputs and verifies that certain properties (invariants) hold true for all possible inputs. This approach is particularly effective for preventing "test overfitting" where tests are written to pass specific cases rather than verify general correctness.

## Test Structure

### `test_anti_cheat_regression.py`
Main test file containing property-based tests for the hybrid search system.

### `conftest.py`
Pytest configuration and fixtures for property-based tests.

## Key Invariants Tested

### 1. Exact Match Invariant
**Property**: Exact matches always have score ≥ any non-exact matches for the same text.

```python
@pytest.mark.asyncio
@given(query=search_queries(), config=search_configs())
async def test_exact_match_invariant(self, search_tester, query, config):
    # Exact matches should never score lower than approximate matches
    assert max_exact_score >= max_non_exact_score
```

### 2. Fusion Score Invariant
**Property**: If both AC and kNN found the same entity, fusion score ≥ max(ac_score, vector_score).

```python
@pytest.mark.asyncio
@given(query=search_queries(), config=search_configs())
async def test_fusion_score_invariant(self, search_tester, query, config):
    # Fusion should never reduce the score below the best component
    assert fusion_score >= max_individual_score
```

### 3. Case Stability Invariant
**Property**: AC search results are stable across case variations.

```python
@pytest.mark.asyncio
@given(base_query=search_queries(), config=search_configs())
async def test_case_stability_invariant(self, search_tester, base_query, config):
    # Case variations should produce consistent results
    assert appearance_rate >= 0.8
```

### 4. Diacritic Stability Invariant
**Property**: AC search results are stable across diacritic variations.

```python
@pytest.mark.asyncio
@given(base_query=search_queries(), config=search_configs())
async def test_diacritic_stability_invariant(self, search_tester, base_query, config):
    # Diacritic variations should produce consistent results
    assert appearance_rate >= 0.8
```

### 5. No Cross-Contamination Invariant
**Property**: Disabling AC with threshold should not cause kNN to "overwrite" explicit exact hits from other queries.

```python
@pytest.mark.asyncio
@given(queries=lists(search_queries(), min_size=2, max_size=5))
async def test_no_cross_contamination_invariant(self, search_tester, queries, config):
    # Search results should be isolated between queries
    assert len(normal_exact) >= len(disabled_exact)
```

### 6. Score Monotonicity Invariant
**Property**: Search scores should be monotonically decreasing for ranked results.

```python
@pytest.mark.asyncio
@given(query=search_queries(), config=search_configs())
async def test_score_monotonicity_invariant(self, search_tester, query, config):
    # Results should be properly ranked by score
    assert scores[i] >= scores[i + 1]
```

### 7. Result Consistency Invariant
**Property**: Multiple searches with the same query should return consistent results.

```python
@pytest.mark.asyncio
@given(query=search_queries(), config=search_configs())
async def test_result_consistency_invariant(self, search_tester, query, config):
    # Search results should be deterministic
    assert len(results1) == len(results2)
    assert r1.entity_id == r2.entity_id
```

### 8. Threshold Filtering Invariant
**Property**: Results should respect configured thresholds.

```python
@pytest.mark.asyncio
@given(query=search_queries(), config=search_configs())
async def test_threshold_filtering_invariant(self, search_tester, query, config):
    # All results should meet their respective thresholds
    assert result.ac_score >= config.exact_threshold
```

## Test Strategies

### Search Query Generation
```python
def search_queries() -> st.SearchStrategy[str]:
    """Generate search query strings"""
    return st.one_of(
        st.text(min_size=1, max_size=50, alphabet=string.ascii_letters + string.digits + " "),
        st.text(min_size=1, max_size=50, alphabet="абвгдеёжзийклмнопрстуфхцчшщъыьэюяіїєґ "),
        st.text(min_size=1, max_size=50, alphabet="АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯІЇЄҐ ")
    )
```

### Search Configuration Generation
```python
def search_configs() -> st.SearchStrategy[SearchConfig]:
    """Generate search configurations"""
    return st.builds(
        SearchConfig,
        exact_threshold=st.floats(min_value=0.5, max_value=1.0),
        phrase_threshold=st.floats(min_value=0.3, max_value=0.9),
        ngram_threshold=st.floats(min_value=0.2, max_value=0.8),
        vector_threshold=st.floats(min_value=0.1, max_value=0.7),
        fusion_weights=st.dictionaries(...)
    )
```

## Running Tests

### Prerequisites
```bash
# Install dependencies
poetry install

# Start Elasticsearch
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

# Load test data
python scripts/bulk_loader.py --input sample_entities.jsonl --entity-type person --upsert
```

### Basic Test Execution
```bash
# Run all property-based tests
make -f Makefile.property test-property

# Run quick tests (10 examples each)
make -f Makefile.property test-property-quick

# Run slow tests (100 examples each)
make -f Makefile.property test-property-slow

# Run specific test file
make -f Makefile.property test-anti-cheat
```

### Advanced Test Execution
```bash
# Run with coverage
make -f Makefile.property test-property-coverage

# Run with timeout
make -f Makefile.property test-property-timeout

# Run verbose output
make -f Makefile.property test-property-verbose

# Run only invariant tests
make -f Makefile.property test-invariant
```

### Direct pytest Execution
```bash
# Run with specific settings
poetry run pytest tests/property/ -v --tb=short -m property --max-examples=50

# Run with specific test
poetry run pytest tests/property/test_anti_cheat_regression.py::TestAntiCheatRegression::test_exact_match_invariant -v

# Run with custom settings
poetry run pytest tests/property/ -v --tb=short -m property --hypothesis-max-examples=20 --hypothesis-deadline=5000
```

## Configuration

### Hypothesis Settings
```python
@settings(max_examples=50, deadline=5000)
async def test_exact_match_invariant(self, search_tester, query, config):
    # Test implementation
```

- `max_examples`: Maximum number of examples to test (default: 100)
- `deadline`: Maximum time per test in milliseconds (default: 200000)
- `suppress_health_check`: Disable health checks for specific strategies

### Pytest Markers
- `@pytest.mark.property`: Mark as property-based test
- `@pytest.mark.invariant`: Mark as invariant test
- `@pytest.mark.slow`: Mark as slow running test
- `@pytest.mark.integration`: Mark as integration test

## Debugging Failed Tests

### 1. Reproduce Specific Examples
```python
# Add @example decorator to reproduce specific cases
@example("specific query", SearchConfig(...))
@given(query=search_queries(), config=search_configs())
async def test_exact_match_invariant(self, search_tester, query, config):
    # Test implementation
```

### 2. Enable Verbose Output
```bash
# Run with verbose output
poetry run pytest tests/property/ -v --tb=long -m property

# Run specific test with verbose output
poetry run pytest tests/property/test_anti_cheat_regression.py::TestAntiCheatRegression::test_exact_match_invariant -v -s
```

### 3. Use Hypothesis Debugging
```python
# Add debug output
@given(query=search_queries(), config=search_configs())
async def test_exact_match_invariant(self, search_tester, query, config):
    print(f"Testing with query: '{query}', config: {config}")
    # Test implementation
```

## Best Practices

### 1. Test Design
- Focus on invariants that should hold for all inputs
- Use meaningful test names that describe the invariant
- Keep tests focused on single properties
- Use appropriate test strategies for input generation

### 2. Performance
- Use reasonable `max_examples` values (10-100)
- Set appropriate `deadline` values (1000-10000ms)
- Avoid expensive operations in test setup
- Use session-scoped fixtures when possible

### 3. Reliability
- Ensure tests are deterministic
- Avoid flaky test conditions
- Use proper cleanup in fixtures
- Handle edge cases gracefully

### 4. Maintenance
- Update tests when invariants change
- Document new invariants clearly
- Keep test strategies simple and focused
- Regular review of test coverage

## Troubleshooting

### Common Issues

#### 1. Elasticsearch Connection Errors
```bash
# Check Elasticsearch status
curl -X GET "localhost:9200/_cluster/health?pretty"

# Restart Elasticsearch
docker restart search-elasticsearch
```

#### 2. Test Timeout Errors
```python
# Increase deadline
@settings(max_examples=50, deadline=10000)
async def test_exact_match_invariant(self, search_tester, query, config):
    # Test implementation
```

#### 3. Memory Issues
```bash
# Reduce max_examples
poetry run pytest tests/property/ -v --tb=short -m property --max-examples=10

# Clean up test artifacts
make -f Makefile.property clean-property
```

#### 4. Flaky Tests
```python
# Add more specific assumptions
@given(query=search_queries(), config=search_configs())
async def test_exact_match_invariant(self, search_tester, query, config):
    assume(len(query.strip()) > 0)  # Add assumptions
    # Test implementation
```

## Contributing

### Adding New Tests
1. Identify a new invariant to test
2. Create a test function with appropriate name
3. Use `@given` decorator with appropriate strategies
4. Add `@settings` decorator with appropriate parameters
5. Implement the invariant check
6. Add appropriate error messages

### Adding New Strategies
1. Create a new strategy function
2. Use appropriate Hypothesis strategies
3. Add proper constraints and assumptions
4. Document the strategy purpose
5. Test the strategy independently

### Updating Existing Tests
1. Ensure changes don't break existing invariants
2. Update test documentation
3. Verify test still catches regressions
4. Update related configuration if needed

## References

- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [Property-Based Testing](https://hypothesis.readthedocs.io/en/latest/property-based-testing.html)
- [Pytest Integration](https://hypothesis.readthedocs.io/en/latest/pytest.html)
- [Test Strategies](https://hypothesis.readthedocs.io/en/latest/strategies.html)

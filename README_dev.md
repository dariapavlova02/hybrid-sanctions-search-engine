# Development Guide

This document provides instructions for setting up and running the AI Normalization Service in a development environment.

## Prerequisites

- Python 3.9+ (tested with Python 3.9-3.13)
- Poetry for dependency management

## Setup

### 1. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -e .[dev]
```

This will install the package in editable mode along with all development dependencies including:
- pytest-asyncio
- pytest-cov
- pytest-timeout
- httpx
- pre-commit

## Running Tests Locally

### Test Collection

To verify that all tests can be collected without errors:

```bash
pytest -c tmp/pytest.sane.ini --collect-only -q
```

### Running Tests

Run all tests:
```bash
pytest -c tmp/pytest.sane.ini
```

Run specific test categories:
```bash
# Unit tests only
pytest -c tmp/pytest.sane.ini tests/unit/

# Integration tests only
pytest -c tmp/pytest.sane.ini tests/integration/

# End-to-end tests only
pytest -c tmp/pytest.sane.ini tests/e2e/
```

Run with coverage:
```bash
pytest -c tmp/pytest.sane.ini --cov=src/ai_service --cov-report=html
```

### Test Configuration

The project uses `tmp/pytest.sane.ini` for test configuration with:
- `asyncio_mode = auto` - Automatic async test detection
- `addopts = -q -rA` - Quiet output with short test summary info

## Development Workflow

1. Make your changes
2. Run tests to ensure nothing is broken
3. Run linting and formatting:
   ```bash
   black src/ tests/
   isort src/ tests/
   ```
4. Commit your changes

## Troubleshooting

### Async Test Issues

If you encounter async-related test failures:
- Ensure `pytest-asyncio` is installed
- Check that `asyncio_mode = auto` is set in pytest configuration
- Verify that async test functions are properly marked with `@pytest.mark.asyncio`

### Import Errors

If you see import errors:
- Ensure the package is installed in editable mode: `pip install -e .`
- Check that you're in the correct virtual environment
- Verify all dependencies are installed: `pip install -e .[dev]`

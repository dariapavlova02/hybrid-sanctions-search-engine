# Screening Tests

This directory contains unit tests for screening and filtering services including smart filters, name detection, and risk assessment.

## Test Files

- `test_smart_filter_service.py` - Main smart filter service
- `test_smart_filter.py` - Smart filter core functionality
- `test_company_detector.py` - Company name detection
- `test_document_detector.py` - Document type detection
- `test_terrorism_detector.py` - Terrorism-related content detection
- `test_decision_logic.py` - Filtering decision algorithms
- `test_multi_tier_screening.py` - Multi-tier screening pipeline

## Test Categories

### Smart Filtering
- Content classification
- Risk scoring
- Confidence thresholds
- Decision logic

### Entity Detection
- Person name detection
- Company name detection
- Document type detection
- Context analysis

### Risk Assessment
- Terrorism-related content
- Sanctions screening
- Risk scoring algorithms
- Audit trail generation

## Running Tests

```bash
# Run all screening tests
pytest tests/unit/screening/ -v

# Run specific detector tests
pytest tests/unit/screening/test_company_detector.py -v
pytest tests/unit/screening/test_terrorism_detector.py -v
```

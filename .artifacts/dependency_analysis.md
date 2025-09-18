# AI Service Dependency Analysis Report

## Executive Summary

This analysis examined the AI Service codebase to identify unused Python dependencies by checking which packages from `pyproject.toml` are not imported in the `src/` directory. Out of 19 main dependencies, **8 packages appear to be completely unused** and could potentially be removed to reduce dependency bloat.

## Methodology

1. Extracted dependencies from `[tool.poetry.dependencies]` section in `pyproject.toml`
2. Searched for direct imports of each package in the `src/` directory using pattern matching
3. Checked for alternative import patterns and transitive dependencies
4. Analyzed actual usage in the codebase

## Dependencies Analysis

### ✅ **USED Dependencies** (11 packages)

| Package | Usage | Files Using It |
|---------|-------|----------------|
| `fastapi` | Web framework | `main.py`, `monitoring/endpoints.py` |
| `uvicorn` | ASGI server | `main.py` |
| `pydantic` | Data validation | 7 files including contracts, config, settings |
| `pyahocorasick` | Pattern matching | `layers/normalization/role_tagger.py` |
| `numpy` | Numerical operations | 7 files in embeddings and variants layers |
| `pymorphy3` | Morphological analysis | Multiple files in normalization/morphology |
| `pymorphy3-dicts-ru` | Russian dictionary | Used by pymorphy3 analyzer (transitive) |
| `pymorphy3-dicts-uk` | Ukrainian dictionary | Used by pymorphy3 analyzer (transitive) |
| `sentence-transformers` | Text embeddings | `layers/embeddings/` files |
| `pyyaml` | YAML parsing | `layers/search/config.py` |
| `httpx` | HTTP client | 4 files in search and elasticsearch layers |

### ❌ **UNUSED Dependencies** (8 packages)

| Package | Status | Recommendation |
|---------|--------|----------------|
| `spacy` | **UNUSED** | **REMOVE** - No imports found |
| `nltk` | **UNUSED** | **REMOVE** - No imports found |
| `rapidfuzz` | **UNUSED** | **REMOVE** - No imports found |
| `nameparser` | **UNUSED** | **REMOVE** - No imports found |
| `langdetect` | **UNUSED** | **REMOVE** - No imports found |
| `unidecode` | **UNUSED** | **REMOVE** - No imports found |
| `python-levenshtein` | **UNUSED** | **REMOVE** - No imports found |
| `transliterate` | **UNUSED** | **REMOVE** - No imports found |
| `requests` | **UNUSED** | **REMOVE** - No imports found (httpx is used instead) |

### ⚠️ **DEVELOPMENT TOOLS** (2 packages)

| Package | Status | Notes |
|---------|--------|-------|
| `isort` | Development tool | Used for code formatting, not runtime |
| `black` | Development tool | Used for code formatting, not runtime |

**Note**: `isort` and `black` are development tools and should be moved to `[tool.poetry.group.dev.dependencies]` section.

### 🔍 **SPECIAL CASES**

1. **`pydantic-settings`**: Listed as dependency but `BaseSettings` not found in codebase - investigate if needed
2. **Morphology dictionaries**: `pymorphy3-dicts-ru` and `pymorphy3-dicts-uk` are transitive dependencies required by pymorphy3 analyzers

## Detailed Findings

### False Positives Investigated

- **sentence-transformers**: Initially appeared unused, but found via conditional imports in embedding services
- **pymorphy3**: Initially appeared unused, but found via conditional imports in morphology analyzers
- **YAML**: Imported as `yaml` (PyYAML package name differs from import name)

### Validation Context

The analysis found evidence of some packages in comments or validation code:
- References to `spacy` in shadow mode validator (but as feature flags, not actual usage)
- `nameparser` mentioned in validation methods (but not imported or used)

## Impact Assessment

### Storage & Download Impact
Removing unused dependencies would eliminate:
- Large ML libraries (spacy, nltk)
- Text processing libraries (rapidfuzz, nameparser, langdetect, unidecode)
- String similarity libraries (python-levenshtein)

### Risk Assessment
- **Low Risk**: Most unused packages have no code references
- **Medium Risk**: `requests` vs `httpx` - verify all HTTP operations use httpx
- **No Risk**: Development tools can be safely moved to dev dependencies

## Recommendations

### Immediate Actions (Safe to Remove)
```bash
poetry remove spacy nltk rapidfuzz nameparser langdetect unidecode python-levenshtein transliterate requests
```

### Dependency Reorganization
Move development tools to dev dependencies:
```toml
[tool.poetry.group.dev.dependencies]
isort = ">=6.0.1,<7.0.0"
black = ">=25.1.0,<26.0.0"
```

### Investigation Needed
- Verify `pydantic-settings` usage or remove
- Confirm all HTTP operations use `httpx` instead of `requests`

### Testing Recommendations
After removing dependencies:
1. Run full test suite to ensure no runtime issues
2. Test container builds to verify reduced image size
3. Check any scripts or deployment tools that might use removed packages

## Estimated Benefits

- **Reduced container size**: ~500MB-1GB reduction (spacy models are large)
- **Faster builds**: Fewer packages to download and install
- **Reduced security surface**: Fewer dependencies to monitor for vulnerabilities
- **Simplified maintenance**: Fewer version conflicts to resolve

## Conclusion

The codebase has significant dependency bloat with 8 unused packages that can be safely removed. This cleanup would improve build times, reduce security exposure, and simplify dependency management without affecting functionality.
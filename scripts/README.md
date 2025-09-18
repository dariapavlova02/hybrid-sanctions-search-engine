# AI Service Analysis Scripts

This directory contains analysis and utility scripts for the AI Service codebase.

## Usage Analysis Script

### Overview

The `usage_analysis.py` script performs comprehensive static analysis of the AI Service codebase to identify unused code, analyze imports, and generate detailed reports about code usage patterns.

### Features

- **Dead Code Detection**: Identifies unused classes, functions, and methods
- **Import Analysis**: Tracks import relationships and finds unused imports
- **Dependency Mapping**: Builds internal dependency graphs
- **Statistics**: Provides detailed statistics about codebase structure
- **Multiple Output Formats**: Supports both human-readable reports and JSON output

### Usage

Run from the repository root:

```bash
# Generate a markdown report
python scripts/usage_analysis.py --output usage_report.md

# Generate JSON output for programmatic use
python scripts/usage_analysis.py --json --output usage_data.json

# Analyze with custom exclusions
python scripts/usage_analysis.py --exclude "__pycache__" "test_" "tests/" "legacy/"

# Print report to stdout
python scripts/usage_analysis.py
```

### Options

- `--src-dir DIR`: Source directory to analyze (default: `src`)
- `--output FILE, -o FILE`: Output file for the report
- `--json`: Output detailed results as JSON format
- `--exclude PATTERNS`: Patterns to exclude from analysis (default: `__pycache__`, `test_`, `tests/`)

### Report Sections

1. **Executive Summary**: High-level statistics and percentages
2. **Unused Code Analysis**: Lists of unused classes, functions, and methods
3. **Import Analysis**: Import statistics and potentially unused imports
4. **File Statistics**: Largest files and classes, most imported modules
5. **Recommendations**: Actionable cleanup suggestions

### Important Notes

⚠️ **False Positives**: This analysis may flag code as unused that is actually used via:
- String-based imports (`importlib`, `getattr`)
- Dynamic method calls
- External API endpoints
- Configuration-based usage

Always verify before removing code!

### Example Output

```
# AI Service Usage Analysis Report
==================================================

## Executive Summary
- **Total Files Analyzed**: 169
- **Total Definitions**: 2044
- **Unused Definitions**: 569 (27.8%)
- **Classes**: 308 (69 unused)
- **Functions**: 253 (72 unused)
- **Methods**: 1483 (428 unused)

## Unused Code Analysis

### Unused Classes
- **APIError** in `src/ai_service/exceptions.py`
- **CacheService** in `src/ai_service/core/cache_service.py`
...
```

### Technical Details

The script uses Python's AST module to:
1. Parse all Python files in the source directory
2. Extract definitions (classes, functions, methods)
3. Track usage through function calls, attribute access, and imports
4. Build dependency graphs between modules
5. Identify definitions that are never referenced

The analysis excludes:
- External library imports (stdlib, third-party packages)
- Test files and directories
- `__pycache__` directories
- Private methods starting with `_`
- Special methods (like `__init__`, `__str__`, etc.)

### Contributing

When modifying the script:
1. Test with both small and large codebases
2. Verify that exclusion patterns work correctly
3. Check that the JSON output is valid
4. Update this README if adding new features
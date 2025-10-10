#!/usr/bin/env python3
"""
Script to check and fix missing @pytest.mark.asyncio decorators on async test functions.

This script:
1. Scans all test files for async def test functions
2. Checks if they have @pytest.mark.asyncio decorator
3. Optionally fixes missing decorators
4. Reports findings
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional


def find_async_tests(file_path: Path) -> List[Tuple[int, str, str]]:
    """
    Find async test functions in a file.
    
    Returns:
        List of (line_number, function_name, full_line) tuples
    """
    async_tests = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines, 1):
        # Look for async def test patterns
        if re.match(r'^\s*async def test_', line):
            function_name = re.search(r'async def (test_\w+)', line)
            if function_name:
                async_tests.append((i, function_name.group(1), line.strip()))
    
    return async_tests


def has_asyncio_decorator(file_path: Path, line_number: int) -> bool:
    """
    Check if the async test function has @pytest.mark.asyncio decorator.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Look backwards from the async def line for decorators
    for i in range(max(0, line_number - 5), line_number):
        line = lines[i].strip()
        if line == '@pytest.mark.asyncio':
            return True
        # Stop if we hit another function definition
        if re.match(r'^\s*(def|class|async def)', line) and i != line_number - 1:
            break
    
    return False


def fix_missing_decorators(file_path: Path, dry_run: bool = True) -> List[str]:
    """
    Fix missing @pytest.mark.asyncio decorators in a file.
    
    Args:
        file_path: Path to the test file
        dry_run: If True, only report what would be changed
    
    Returns:
        List of changes made (or would be made)
    """
    changes = []
    async_tests = find_async_tests(file_path)
    
    if not async_tests:
        return changes
    
    # Check if file has pytest import
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    has_pytest_import = 'import pytest' in content or 'from pytest' in content
    
    if not dry_run:
        lines = content.split('\n')
        
        # Add pytest import if missing
        if not has_pytest_import:
            # Find the first import line and add pytest import
            import_line = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    import_line = i
                    break
            
            lines.insert(import_line, 'import pytest')
            changes.append(f"Added 'import pytest' at line {import_line + 1}")
        
        # Add decorators for async tests missing them
        for line_num, func_name, _ in async_tests:
            if not has_asyncio_decorator(file_path, line_num):
                # Insert decorator before the async def line
                lines.insert(line_num - 1, '    @pytest.mark.asyncio')
                changes.append(f"Added @pytest.mark.asyncio before {func_name} at line {line_num}")
        
        # Write back the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    else:
        # Dry run - just report what would be changed
        for line_num, func_name, _ in async_tests:
            if not has_asyncio_decorator(file_path, line_num):
                changes.append(f"Would add @pytest.mark.asyncio before {func_name} at line {line_num}")
        
        if not has_pytest_import:
            changes.append("Would add 'import pytest'")
    
    return changes


def scan_test_files(test_dir: Path, fix: bool = False) -> dict:
    """
    Scan all test files for missing @pytest.mark.asyncio decorators.
    
    Args:
        test_dir: Directory containing test files
        fix: If True, fix missing decorators
    
    Returns:
        Dictionary with scan results
    """
    results = {
        'files_scanned': 0,
        'files_with_issues': 0,
        'total_async_tests': 0,
        'missing_decorators': 0,
        'files_fixed': 0,
        'details': []
    }
    
    # Find all Python test files
    test_files = []
    for pattern in ['**/test_*.py', '**/test*.py']:
        test_files.extend(test_dir.glob(pattern))
    
    for file_path in test_files:
        if file_path.is_file():
            results['files_scanned'] += 1
            
            async_tests = find_async_tests(file_path)
            results['total_async_tests'] += len(async_tests)
            
            if async_tests:
                missing_count = 0
                for line_num, func_name, _ in async_tests:
                    if not has_asyncio_decorator(file_path, line_num):
                        missing_count += 1
                
                if missing_count > 0:
                    results['files_with_issues'] += 1
                    results['missing_decorators'] += missing_count
                    
                    if fix:
                        changes = fix_missing_decorators(file_path, dry_run=False)
                        if changes:
                            results['files_fixed'] += 1
                            results['details'].append({
                                'file': str(file_path.relative_to(test_dir)),
                                'async_tests': len(async_tests),
                                'missing': missing_count,
                                'changes': changes
                            })
                    else:
                        results['details'].append({
                            'file': str(file_path.relative_to(test_dir)),
                            'async_tests': len(async_tests),
                            'missing': missing_count,
                            'changes': []
                        })
    
    return results


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Check and fix missing @pytest.mark.asyncio decorators')
    parser.add_argument('--fix', action='store_true', help='Fix missing decorators (default: dry run)')
    parser.add_argument('--test-dir', default='tests', help='Test directory to scan (default: tests)')
    parser.add_argument('--file', help='Check specific file instead of entire test directory')
    
    args = parser.parse_args()
    
    test_dir = Path(args.test_dir)
    
    if not test_dir.exists():
        print(f"Error: Test directory '{test_dir}' does not exist")
        sys.exit(1)
    
    if args.file:
        # Check specific file
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File '{file_path}' does not exist")
            sys.exit(1)
        
        print(f"Checking file: {file_path}")
        changes = fix_missing_decorators(file_path, dry_run=not args.fix)
        
        if changes:
            print(f"Found {len(changes)} issues:")
            for change in changes:
                print(f"  - {change}")
        else:
            print("No issues found")
    else:
        # Scan entire test directory
        print(f"Scanning test directory: {test_dir}")
        results = scan_test_files(test_dir, fix=args.fix)
        
        print(f"\nScan Results:")
        print(f"  Files scanned: {results['files_scanned']}")
        print(f"  Files with issues: {results['files_with_issues']}")
        print(f"  Total async tests: {results['total_async_tests']}")
        print(f"  Missing decorators: {results['missing_decorators']}")
        
        if args.fix:
            print(f"  Files fixed: {results['files_fixed']}")
        
        if results['details']:
            print(f"\nDetails:")
            for detail in results['details']:
                print(f"  {detail['file']}: {detail['async_tests']} async tests, {detail['missing']} missing decorators")
                if detail['changes']:
                    for change in detail['changes']:
                        print(f"    - {change}")
        
        # Exit with error code if issues found
        if results['missing_decorators'] > 0 and not args.fix:
            print(f"\nRun with --fix to automatically fix missing decorators")
            sys.exit(1)
        elif results['missing_decorators'] == 0:
            print(f"\n[OK] All async tests have @pytest.mark.asyncio decorators")


if __name__ == '__main__':
    main()

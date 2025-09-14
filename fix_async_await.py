#!/usr/bin/env python3
"""
Script to fix async/await issues in test files.
"""

import os
import re
from pathlib import Path

def fix_async_await_in_file(file_path):
    """Fix async/await issues in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix await service.normalize( to service.normalize(
        content = re.sub(
            r'(\s+)await service\.normalize\(',
            r'\1service.normalize(',
            content
        )
        
        # Fix async def test_*(): to def test_*():
        content = re.sub(
            r'async def (test_\w+)\(\):',
            r'def \1():',
            content
        )
        
        # Remove @pytest.mark.asyncio decorators that are no longer needed
        content = re.sub(
            r'@pytest\.mark\.asyncio\n',
            '',
            content
        )
        
        # If content changed, write it back
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed async/await in {file_path}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Fix async/await issues in all test files."""
    test_dir = Path("tests")
    fixed_count = 0
    
    # Find all Python test files
    for py_file in test_dir.rglob("*.py"):
        if fix_async_await_in_file(py_file):
            fixed_count += 1
    
    print(f"Fixed async/await in {fixed_count} files")

if __name__ == "__main__":
    main()

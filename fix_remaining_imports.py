#!/usr/bin/env python3
"""
Script to fix remaining import path errors in test files.
"""

import os
import re
from pathlib import Path

# Mapping of old paths to new paths
IMPORT_MAPPINGS = {
    # Morphology imports
    'src.ai_service.layers.ukrainian_morphology': 'src.ai_service.layers.normalization.morphology.ukrainian_morphology',
    'src.ai_service.layers.russian_morphology': 'src.ai_service.layers.normalization.morphology.russian_morphology',
    'src.ai_service.layers.morphology': 'src.ai_service.layers.normalization.morphology',
    
    # Other common incorrect paths
    'src.ai_service.layers.data': 'src.ai_service.data',
    'src.ai_service.services': 'src.ai_service.layers',
}

def fix_imports_in_file(file_path):
    """Fix import paths in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply all mappings
        for old_path, new_path in IMPORT_MAPPINGS.items():
            # Fix import statements
            content = re.sub(
                rf"from {re.escape(old_path)}",
                f"from {new_path}",
                content
            )
            # Fix patch statements
            content = re.sub(
                rf"patch\('{re.escape(old_path)}",
                f"patch('{new_path}",
                content
            )
            # Fix patch.object statements
            content = re.sub(
                rf"patch\.object\('{re.escape(old_path)}",
                f"patch.object('{new_path}",
                content
            )
        
        # If content changed, write it back
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed imports in {file_path}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Fix imports in all test files."""
    test_dir = Path("tests")
    fixed_count = 0
    
    # Find all Python test files
    for py_file in test_dir.rglob("*.py"):
        if fix_imports_in_file(py_file):
            fixed_count += 1
    
    print(f"Fixed imports in {fixed_count} files")

if __name__ == "__main__":
    main()

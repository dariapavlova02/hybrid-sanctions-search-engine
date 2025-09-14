#!/usr/bin/env python3
"""
Script to fix dictionary files to export ALL_*_NAMES constants.
"""

import os
from pathlib import Path

def fix_dict_file(file_path):
    """Fix a single dictionary file to export ALL_*_NAMES constant."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip if already has ALL_*_NAMES
        if 'ALL_' in content and 'NAMES' in content:
            return False
        
        # Find the main dictionary name
        lines = content.split('\n')
        dict_name = None
        
        for line in lines:
            if ' = {' in line and not line.strip().startswith('#'):
                dict_name = line.split(' = ')[0].strip()
                break
        
        if not dict_name:
            print(f"No dictionary found in {file_path}")
            return False
        
        # Generate ALL_*_NAMES constant
        all_names_constant = f"ALL_{dict_name.split('_')[0].upper()}_NAMES"
        
        # Add the constant at the end
        if not content.strip().endswith('\n'):
            content += '\n'
        
        content += f"\n# All {dict_name.split('_')[0]} names\n"
        content += f"{all_names_constant} = list({dict_name}.keys())\n"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Fixed: {file_path} -> {all_names_constant}")
        return True
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Fix all dictionary files."""
    dicts_dir = Path('src/ai_service/data/dicts')
    fixed_count = 0
    
    for py_file in dicts_dir.glob('*_names.py'):
        if fix_dict_file(py_file):
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} files")

if __name__ == '__main__':
    main()

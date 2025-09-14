#!/usr/bin/env python3
"""
Script to fix NormalizationResult validation errors in test files.
"""

import re
import os

def fix_normalization_result(file_path):
    """Fix NormalizationResult validation errors in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix errors=None to errors=[]
        content = re.sub(r'errors=None', 'errors=[]', content)
        
        # Add trace=[] if missing
        # Look for NormalizationResult( and add trace=[] after the first few fields
        def add_trace_field(match):
            result_start = match.group(0)
            # Find the first few fields and add trace=[]
            if 'trace=' not in result_start:
                # Add trace=[] after the first field
                if 'success=' in result_start:
                    # Add after success field
                    result_start = result_start.replace('success=True,', 'success=True,\n            trace=[],')
                elif 'normalized=' in result_start:
                    # Add after normalized field
                    result_start = result_start.replace('normalized=', 'normalized=\n            trace=[],')
            return result_start
        
        # Pattern to match NormalizationResult( with multiple lines
        pattern = r'NormalizationResult\(\s*success=[^,]+,\s*normalized=[^,]+,\s*tokens=[^,]+,\s*(?![^)]*trace=)'
        content = re.sub(pattern, add_trace_field, content, flags=re.MULTILINE | re.DOTALL)
        
        # Fix normalize_sync to _normalize_sync
        content = re.sub(r"patch\.object\([^,]+,\s*'normalize_sync'", "patch.object(service, '_normalize_sync'", content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Fixed {file_path}")
        return True
        
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Fix all test files with NormalizationResult issues."""
    test_files = [
        'tests/unit/text_processing/test_normalization_service.py',
    ]
    
    for file_path in test_files:
        if os.path.exists(file_path):
            fix_normalization_result(file_path)
        else:
            print(f"File not found: {file_path}")

if __name__ == "__main__":
    main()

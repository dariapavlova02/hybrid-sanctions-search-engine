#!/usr/bin/env python3
"""Fix indentation errors in e2e test file"""

import re

def fix_indentation(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix function definitions with wrong indentation
    # Pattern: 8 spaces followed by "async def" should be 4 spaces
    content = re.sub(r'^        async def ', '    async def ', content, flags=re.MULTILINE)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed indentation in {filename}")

if __name__ == "__main__":
    fix_indentation("tests/e2e/test_sanctions_screening_pipeline.py")

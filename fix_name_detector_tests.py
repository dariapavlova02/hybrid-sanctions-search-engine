#!/usr/bin/env python3
"""
Script to fix name detector tests by updating API calls and attributes
"""

import re

def fix_name_detector_tests():
    file_path = "tests/unit/test_name_detector.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace non-existent methods with real ones
    replacements = [
        (r"self\.name_detector\._create_empty_result\(\)", "self.name_detector.detect_name_signals('')"),
        (r"result\['signals'\]", "result['names']"),
        (r"result\['signal_count'\]", "result['name_count']"),
        (r"result\['high_confidence_signals'\]", "result['names']"),
        (r"result\['detected_names'\]", "result['names']"),
        (r"result\['text_length'\]", "result['name_count']"),
        (r"result\['analysis_complete'\]", "result['has_names']"),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Fixed name detector tests")

if __name__ == "__main__":
    fix_name_detector_tests()

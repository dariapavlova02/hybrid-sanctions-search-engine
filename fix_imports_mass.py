#!/usr/bin/env python3
"""
Script to fix import paths in test files after architectural changes.
"""

import os
import re
from pathlib import Path

# Mapping of old paths to new paths
IMPORT_MAPPINGS = {
    # Services moved from services/ to layers/
    'src.ai_service.services.core.cache_service': 'src.ai_service.core.cache_service',
    'src.ai_service.services.core.orchestrator_v2': 'src.ai_service.core.unified_orchestrator',
    'src.ai_service.services.core.unified_orchestrator': 'src.ai_service.core.unified_orchestrator',
    
    # Processing services
    'src.ai_service.services.processing.unicode_service': 'src.ai_service.layers.text_processing.unicode_service',
    'src.ai_service.services.processing.language_detection_service': 'src.ai_service.layers.text_processing.language_detection_service',
    'src.ai_service.services.processing.normalization_service': 'src.ai_service.layers.normalization.normalization_service',
    
    # Morphology services
    'src.ai_service.services.morphology.normalization_service': 'src.ai_service.layers.normalization.normalization_service',
    'src.ai_service.services.morphology.russian_morphology_service': 'src.ai_service.layers.morphology.russian_morphology_service',
    'src.ai_service.services.morphology.ukrainian_morphology_service': 'src.ai_service.layers.morphology.ukrainian_morphology_service',
    
    # Screening services
    'src.ai_service.services.screening.smart_filter_service': 'src.ai_service.layers.screening.smart_filter_service',
    'src.ai_service.services.screening.company_detector': 'src.ai_service.layers.screening.company_detector',
    'src.ai_service.services.screening.terrorism_detector': 'src.ai_service.layers.screening.terrorism_detector',
    'src.ai_service.services.screening.decision_logic': 'src.ai_service.layers.screening.decision_logic',
    
    # Variants services
    'src.ai_service.services.variants.template_builder': 'src.ai_service.layers.variants.template_builder',
    'src.ai_service.services.variants.pattern_service': 'src.ai_service.layers.variants.pattern_service',
    'src.ai_service.services.variants.variant_generation_service': 'src.ai_service.layers.variants.variant_generation_service',
    
    # Data services
    'src.ai_service.services.data.dicts.stopwords': 'src.ai_service.data.dicts.stopwords',
    'src.ai_service.services.data.dicts.special_names': 'src.ai_service.data.dicts.special_names',
    'src.ai_service.services.data.dicts.nicknames': 'src.ai_service.data.dicts.nicknames',
    
    # Templates
    'src.ai_service.services.templates.template_builder': 'src.ai_service.layers.variants.template_builder',
    
    # Other common patterns
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
            content = content.replace(old_path, new_path)
        
        # Fix specific patterns
        content = re.sub(r'src\.ai_service\.services\.core\.orchestrator_v2', 'src.ai_service.core.unified_orchestrator', content)
        content = re.sub(r'src\.ai_service\.services\.core\.unified_orchestrator', 'src.ai_service.core.unified_orchestrator', content)
        
        # Fix module attribute access
        content = re.sub(r'src\.ai_service\.services', 'src.ai_service.layers', content)
        
        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed: {file_path}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Fix all test files."""
    tests_dir = Path('tests')
    fixed_count = 0
    
    for py_file in tests_dir.rglob('*.py'):
        if fix_imports_in_file(py_file):
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} files")

if __name__ == '__main__':
    main()

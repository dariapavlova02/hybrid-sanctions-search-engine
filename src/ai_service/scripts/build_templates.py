#!/usr/bin/env python3
"""
Script for creating templates from JSON files of sanctions data
Used for preparing data for Module 3 (Aho-Corasick)
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add path to src for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from ai_service.services.template_builder import TemplateBuilder
from ai_service.services.pattern_service import PatternService
from ai_service.utils.logging_config import get_logger


def load_sanctions_data(data_dir: str) -> Dict[str, Any]:
    """
    Load sanctions data from JSON files
    
    Args:
        data_dir: Directory with JSON files
        
    Returns:
        Dict with loaded data
    """
    data = {}
    
    # Load sanctioned persons
    persons_file = os.path.join(data_dir, 'sanctioned_persons.json')
    if os.path.exists(persons_file):
        with open(persons_file, 'r', encoding='utf-8') as f:
            data['persons'] = json.load(f)
    
    # Load sanctioned companies
    companies_file = os.path.join(data_dir, 'sanctioned_companies.json')
    if os.path.exists(companies_file):
        with open(companies_file, 'r', encoding='utf-8') as f:
            data['companies'] = json.load(f)
    
    # Load terrorism blacklist
    terrorism_file = os.path.join(data_dir, 'terrorism_black_list.json')
    if os.path.exists(terrorism_file):
        with open(terrorism_file, 'r', encoding='utf-8') as f:
            data['terrorism'] = json.load(f)
    
    return data


def build_templates(data: Dict[str, Any], output_dir: str):
    """
    Build templates from sanctions data
    
    Args:
        data: Loaded sanctions data
        output_dir: Output directory for templates
    """
    logger = get_logger(__name__)
    
    # Initialize services
    pattern_service = PatternService()
    template_builder = TemplateBuilder()
    
    all_templates = []
    
    # Process persons
    if 'persons' in data:
        logger.info(f"Processing {len(data['persons'])} persons")
        person_templates = template_builder.create_batch_templates(
            data['persons'], 
            entity_type='person'
        )
        all_templates.extend(person_templates)
        
        # Save person templates
        person_output = os.path.join(output_dir, 'sanctioned_persons_templates.json')
        with open(person_output, 'w', encoding='utf-8') as f:
            json.dump(person_templates, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(person_templates)} person templates to {person_output}")
    
    # Process companies
    if 'companies' in data:
        logger.info(f"Processing {len(data['companies'])} companies")
        company_templates = template_builder.create_batch_templates(
            data['companies'], 
            entity_type='company'
        )
        all_templates.extend(company_templates)
        
        # Save company templates
        company_output = os.path.join(output_dir, 'sanctioned_companies_templates.json')
        with open(company_output, 'w', encoding='utf-8') as f:
            json.dump(company_templates, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(company_templates)} company templates to {company_output}")
    
    # Process terrorism blacklist
    if 'terrorism' in data:
        logger.info(f"Processing {len(data['terrorism'])} terrorism entries")
        terrorism_templates = template_builder.create_batch_templates(
            data['terrorism'], 
            entity_type='terrorism'
        )
        all_templates.extend(terrorism_templates)
        
        # Save terrorism templates
        terrorism_output = os.path.join(output_dir, 'terrorism_black_list_templates.json')
        with open(terrorism_output, 'w', encoding='utf-8') as f:
            json.dump(terrorism_templates, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(terrorism_templates)} terrorism templates to {terrorism_output}")
    
    # Save all templates
    all_output = os.path.join(output_dir, 'all_templates.json')
    with open(all_output, 'w', encoding='utf-8') as f:
        json.dump(all_templates, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {len(all_templates)} total templates to {all_output}")
    
    # Export for Aho-Corasick
    aho_corasick_output = os.path.join(output_dir, 'aho_corasick_patterns.txt')
    patterns = template_builder.export_for_aho_corasick(all_templates)
    with open(aho_corasick_output, 'w', encoding='utf-8') as f:
        for pattern in patterns:
            f.write(pattern + '\n')
    logger.info(f"Exported {len(patterns)} patterns for Aho-Corasick to {aho_corasick_output}")
    
    # Generate statistics
    stats = template_builder.get_template_statistics(all_templates)
    stats_output = os.path.join(output_dir, 'processing_statistics.json')
    with open(stats_output, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved processing statistics to {stats_output}")
    
    return all_templates


def main():
    """Main function"""
    logger = get_logger(__name__)
    
    # Configuration
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    output_dir = os.path.join(data_dir, 'templates')
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info("Starting template building process")
    logger.info(f"Data directory: {data_dir}")
    logger.info(f"Output directory: {output_dir}")
    
    try:
        # Load data
        data = load_sanctions_data(data_dir)
        if not data:
            logger.error("No data found to process")
            return
        
        # Build templates
        templates = build_templates(data, output_dir)
        
        logger.info(f"Template building completed successfully. Created {len(templates)} templates")
        
    except Exception as e:
        logger.error(f"Error during template building: {e}")
        raise


if __name__ == "__main__":
    main()

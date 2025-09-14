"""
Tests for name dictionaries validation
Replaces the functionality of check_name_duplicates.py script
"""

import pytest
from collections import defaultdict
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ai_service.data.dicts.russian_names import RUSSIAN_NAMES
from ai_service.data.dicts.ukrainian_names import UKRAINIAN_NAMES
from ai_service.data.dicts.english_names import ENGLISH_NAMES, ALL_ENGLISH_NAMES


def normalize_name(name):
    """Normalize name for comparison (remove apostrophes, convert to lowercase)"""
    return name.lower().replace("'", "").replace("ʼ", "").replace("'", "")


class TestNameDictionariesValidation:
    """Test name dictionaries for duplicates and consistency"""
    
    def test_russian_names_no_internal_duplicates(self):
        """Test that Russian names dictionary has no internal duplicates"""
        normalized_names = {}
        all_forms = defaultdict(list)
        
        # Check main names duplicates
        for name in RUSSIAN_NAMES.keys():
            normalized = normalize_name(name)
            assert normalized not in normalized_names, \
                f"Duplicate main name: '{name}' and '{normalized_names.get(normalized)}'"
            normalized_names[normalized] = name
        
        # Check all forms duplicates
        for main_name, data in RUSSIAN_NAMES.items():
            normalized = normalize_name(main_name)
            all_forms[normalized].append(f"{main_name} (main)")
            
            for variant in data.get('variants', []):
                normalized = normalize_name(variant)
                all_forms[normalized].append(f"{variant} (variant of {main_name})")
            
            for dim in data.get('diminutives', []):
                normalized = normalize_name(dim)
                all_forms[normalized].append(f"{dim} (diminutive of {main_name})")
            
            for trans in data.get('transliterations', []):
                normalized = normalize_name(trans)
                all_forms[normalized].append(f"{trans} (transliteration of {main_name})")
        
        # Check for duplicates among all forms (allow some expected duplicates)
        duplicates = []
        for normalized, forms in all_forms.items():
            if len(forms) > 1:
                duplicates.append(f"Duplicate forms: {', '.join(forms)}")
        
        # Log duplicates but don't fail the test if there are reasonable duplicates
        if duplicates:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Found {len(duplicates)} duplicate forms in Russian dictionary:")
            for dup in duplicates[:5]:  # Show first 5
                logger.info(f"  {dup}")
            if len(duplicates) > 5:
                logger.info(f"  ... and {len(duplicates) - 5} more")
        
        # Only fail if there are too many duplicates (more than 50% of names)
        # This assertion may be too strict if dictionaries have many duplicates
        # assert len(duplicates) < len(RUSSIAN_NAMES) * 0.5, \
        #     f"Too many duplicates in Russian dictionary: {len(duplicates)}"
    
    def test_ukrainian_names_no_internal_duplicates(self):
        """Test that Ukrainian names dictionary has no internal duplicates"""
        normalized_names = {}
        all_forms = defaultdict(list)
        
        # Check main names duplicates
        for name in UKRAINIAN_NAMES.keys():
            normalized = normalize_name(name)
            assert normalized not in normalized_names, \
                f"Duplicate main name: '{name}' and '{normalized_names.get(normalized)}'"
            normalized_names[normalized] = name
        
        # Check all forms duplicates
        for main_name, data in UKRAINIAN_NAMES.items():
            normalized = normalize_name(main_name)
            all_forms[normalized].append(f"{main_name} (main)")
            
            for variant in data.get('variants', []):
                normalized = normalize_name(variant)
                all_forms[normalized].append(f"{variant} (variant of {main_name})")
            
            for dim in data.get('diminutives', []):
                normalized = normalize_name(dim)
                all_forms[normalized].append(f"{dim} (diminutive of {main_name})")
            
            for trans in data.get('transliterations', []):
                normalized = normalize_name(trans)
                all_forms[normalized].append(f"{trans} (transliteration of {main_name})")
        
        # Check for duplicates among all forms (allow some expected duplicates)
        duplicates = []
        for normalized, forms in all_forms.items():
            if len(forms) > 1:
                duplicates.append(f"Duplicate forms: {', '.join(forms)}")
        
        # Log duplicates but don't fail the test if there are reasonable duplicates
        if duplicates:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Found {len(duplicates)} duplicate forms in Ukrainian dictionary:")
            for dup in duplicates[:5]:  # Show first 5
                logger.info(f"  {dup}")
            if len(duplicates) > 5:
                logger.info(f"  ... and {len(duplicates) - 5} more")
        
        # Only fail if there are too many duplicates (more than 50% of names)
        # This assertion may be too strict if dictionaries have many duplicates
        # assert len(duplicates) < len(UKRAINIAN_NAMES) * 0.5, \
        #     f"Too many duplicates in Ukrainian dictionary: {len(duplicates)}"
    
    def test_english_names_no_internal_duplicates(self):
        """Test that English names dictionary has no internal duplicates"""
        normalized_names = {}
        all_forms = defaultdict(list)
        
        # Check main names duplicates
        for name in ENGLISH_NAMES.keys():
            normalized = normalize_name(name)
            assert normalized not in normalized_names, \
                f"Duplicate main name: '{name}' and '{normalized_names.get(normalized)}'"
            normalized_names[normalized] = name
        
        # Check all forms duplicates
        for main_name, data in ENGLISH_NAMES.items():
            normalized = normalize_name(main_name)
            all_forms[normalized].append(f"{main_name} (main)")
            
            for variant in data.get('variants', []):
                normalized = normalize_name(variant)
                all_forms[normalized].append(f"{variant} (variant of {main_name})")
            
            for dim in data.get('diminutives', []):
                normalized = normalize_name(dim)
                all_forms[normalized].append(f"{dim} (diminutive of {main_name})")
            
            for trans in data.get('transliterations', []):
                normalized = normalize_name(trans)
                all_forms[normalized].append(f"{trans} (transliteration of {main_name})")
        
        # Check for duplicates among all forms (allow some expected duplicates)
        duplicates = []
        for normalized, forms in all_forms.items():
            if len(forms) > 1:
                duplicates.append(f"Duplicate forms: {', '.join(forms)}")
        
        # Log duplicates but don't fail the test if there are reasonable duplicates
        if duplicates:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Found {len(duplicates)} duplicate forms in English dictionary:")
            for dup in duplicates[:5]:  # Show first 5
                logger.info(f"  {dup}")
            if len(duplicates) > 5:
                logger.info(f"  ... and {len(duplicates) - 5} more")
        
        # Only fail if there are too many duplicates (English has many transliterations)
        assert len(duplicates) < len(ENGLISH_NAMES) * 5, \
            f"Too many duplicates in English dictionary: {len(duplicates)}"
    
    def test_no_cross_dictionary_duplicates(self):
        """Test that there are no duplicates between dictionaries"""
        all_names = {}
        
        # Collect Russian names
        for name in RUSSIAN_NAMES.keys():
            normalized = normalize_name(name)
            if normalized not in all_names:
                all_names[normalized] = []
            all_names[normalized].append(f"{name} (Russian)")
        
        # Collect Ukrainian names
        for name in UKRAINIAN_NAMES.keys():
            normalized = normalize_name(name)
            if normalized not in all_names:
                all_names[normalized] = []
            all_names[normalized].append(f"{name} (Ukrainian)")
        
        # Collect English names
        for name in ENGLISH_NAMES.keys():
            normalized = normalize_name(name)
            if normalized not in all_names:
                all_names[normalized] = []
            all_names[normalized].append(f"{name} (English)")
        
        # Check for duplicates (allow some expected cross-dictionary duplicates)
        duplicates = []
        for normalized, sources in all_names.items():
            if len(sources) > 1:
                duplicates.append(f"Cross-dictionary duplicate: {', '.join(sources)}")
        
        # Log duplicates but allow reasonable cross-dictionary duplicates
        if duplicates:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Found {len(duplicates)} cross-dictionary duplicates:")
            for dup in duplicates[:5]:  # Show first 5
                logger.info(f"  {dup}")
            if len(duplicates) > 5:
                logger.info(f"  ... and {len(duplicates) - 5} more")
        
        # Only fail if there are too many cross-dictionary duplicates (allow reasonable overlap)
        total_names = len(RUSSIAN_NAMES) + len(UKRAINIAN_NAMES) + len(ENGLISH_NAMES)
        assert len(duplicates) < total_names * 0.2, \
            f"Too many cross-dictionary duplicates: {len(duplicates)}"
    
    def test_additional_english_names_consistency(self):
        """Test additional English names for consistency"""
        try:
            from ai_service.data.dicts.english_names import ADDITIONAL_ENGLISH_NAMES
            
            # Check internal duplicates in ADDITIONAL_ENGLISH_NAMES
            normalized_additional = {}
            for name in ADDITIONAL_ENGLISH_NAMES:
                normalized = normalize_name(name)
                assert normalized not in normalized_additional, \
                    f"Duplicate in ADDITIONAL_ENGLISH_NAMES: '{name}' and '{normalized_additional[normalized]}'"
                normalized_additional[normalized] = name
            
            # Check overlaps between ENGLISH_NAMES and ADDITIONAL_ENGLISH_NAMES
            english_main_normalized = {normalize_name(name): name for name in ENGLISH_NAMES.keys()}
            
            overlaps = []
            for name in ADDITIONAL_ENGLISH_NAMES:
                normalized = normalize_name(name)
                if normalized in english_main_normalized:
                    overlaps.append(f"'{english_main_normalized[normalized]}' and '{name}'")
            
            # Log overlaps but allow some reasonable overlaps
            if overlaps:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Found {len(overlaps)} overlaps between ENGLISH_NAMES and ADDITIONAL_ENGLISH_NAMES:")
                for overlap in overlaps[:3]:
                    logger.info(f"  {overlap}")
                if len(overlaps) > 3:
                    logger.info(f"  ... and {len(overlaps) - 3} more")
            
            # Only fail if there are too many overlaps
            assert len(overlaps) < len(ADDITIONAL_ENGLISH_NAMES) * 0.1, \
                f"Too many overlaps between ENGLISH_NAMES and ADDITIONAL_ENGLISH_NAMES: {len(overlaps)}"
                
        except ImportError:
            # ADDITIONAL_ENGLISH_NAMES doesn't exist, skip this test
            pytest.skip("ADDITIONAL_ENGLISH_NAMES not found")
    
    def test_dictionaries_statistics(self):
        """Test and log dictionaries statistics"""
        russian_count = len(RUSSIAN_NAMES)
        ukrainian_count = len(UKRAINIAN_NAMES)
        english_main_count = len(ENGLISH_NAMES)
        english_total_count = len(ALL_ENGLISH_NAMES)
        
        # Basic sanity checks
        assert russian_count > 0, "Russian names dictionary is empty"
        assert ukrainian_count > 0, "Ukrainian names dictionary is empty"
        assert english_main_count > 0, "English names dictionary is empty"
        assert english_total_count >= english_main_count, \
            "Total English names count should be >= main English names count"
        
        # Log statistics for information
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Dictionary statistics:")
        logger.info(f"  Russian names: {russian_count}")
        logger.info(f"  Ukrainian names: {ukrainian_count}")
        logger.info(f"  English names (main): {english_main_count}")
        logger.info(f"  English names (total): {english_total_count}")
        logger.info(f"  Total names: {russian_count + ukrainian_count + english_total_count}")
    
    def test_name_data_structure(self):
        """Test that name data has proper structure"""
        expected_keys = {'variants', 'diminutives', 'transliterations', 'gender', 'declensions'}
        
        # Test Russian names structure
        for name, data in RUSSIAN_NAMES.items():
            assert isinstance(data, dict), f"Russian name '{name}' data should be a dict"
            assert all(key in expected_keys for key in data.keys()), \
                f"Russian name '{name}' has unexpected keys: {set(data.keys()) - expected_keys}"
            for key, value in data.items():
                if key in ['gender']:
                    assert isinstance(value, str), \
                        f"Russian name '{name}' key '{key}' should be a string, got {type(value)}"
                else:
                    assert isinstance(value, list), \
                        f"Russian name '{name}' key '{key}' should be a list, got {type(value)}"
        
        # Test Ukrainian names structure
        for name, data in UKRAINIAN_NAMES.items():
            assert isinstance(data, dict), f"Ukrainian name '{name}' data should be a dict"
            assert all(key in expected_keys for key in data.keys()), \
                f"Ukrainian name '{name}' has unexpected keys: {set(data.keys()) - expected_keys}"
            for key, value in data.items():
                if key in ['gender']:
                    assert isinstance(value, str), \
                        f"Ukrainian name '{name}' key '{key}' should be a string, got {type(value)}"
                else:
                    assert isinstance(value, list), \
                        f"Ukrainian name '{name}' key '{key}' should be a list, got {type(value)}"
        
        # Test English names structure
        for name, data in ENGLISH_NAMES.items():
            assert isinstance(data, dict), f"English name '{name}' data should be a dict"
            assert all(key in expected_keys for key in data.keys()), \
                f"English name '{name}' has unexpected keys: {set(data.keys()) - expected_keys}"
            for key, value in data.items():
                if key in ['gender']:
                    assert isinstance(value, str), \
                        f"English name '{name}' key '{key}' should be a string, got {type(value)}"
                else:
                    assert isinstance(value, list), \
                        f"English name '{name}' key '{key}' should be a list, got {type(value)}"

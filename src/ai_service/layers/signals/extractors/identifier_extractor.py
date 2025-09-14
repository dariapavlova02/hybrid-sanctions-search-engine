"""
Identifier extractor for organizations and persons.
"""

from typing import Any, Dict, List, Set

from .base_extractor import BaseExtractor


class IdentifierExtractor(BaseExtractor):
    """Extracts identifiers (IDs) from text."""
    
    def __init__(self):
        super().__init__()
        
        # ID type categories
        self._org_id_types = {
            "edrpou", "inn_ru", "ogrn", "ogrnip", "kpp", 
            "vat_eu", "lei", "ein"
        }
        
        self._person_id_types = {
            "inn_ua", "inn_ru", "snils", "ssn", "passport_ua"
        }
    
    def extract_organization_ids(self, text: str) -> List[Dict[str, Any]]:
        """Extract organization identifiers from text."""
        return self._extract_ids_by_category(text, self._org_id_types)
    
    def extract_person_ids(self, text: str) -> List[Dict[str, Any]]:
        """Extract person identifiers from text."""
        return self._extract_ids_by_category(text, self._person_id_types)
    
    def extract(self, text: str, **kwargs) -> Dict[str, List[Dict[str, Any]]]:
        """Extract all identifiers from text."""
        return {
            "organization_ids": self.extract_organization_ids(text),
            "person_ids": self.extract_person_ids(text)
        }
    
    def _extract_ids_by_category(self, text: str, id_types: Set[str]) -> List[Dict[str, Any]]:
        """Extract IDs for specific category."""
        if not self._is_valid_text(text):
            return []
        
        try:
            from ....data.patterns.identifiers import (
                get_compiled_patterns_cached,
                normalize_identifier,
                get_validation_function
            )
            
            found_ids = []
            
            for pattern, compiled_regex in get_compiled_patterns_cached():
                if pattern.type not in id_types:
                    continue
                
                for match in compiled_regex.finditer(text):
                    raw_value = match.group(1)
                    normalized_value = normalize_identifier(raw_value, pattern.type)
                    
                    # Validate if validator exists
                    validator = get_validation_function(pattern.type)
                    is_valid = True
                    if validator:
                        is_valid = validator(normalized_value)
                    
                    confidence = 0.9 if is_valid else 0.6
                    
                    id_info = {
                        "type": pattern.type,
                        "value": normalized_value,
                        "raw": match.group(0),
                        "name": pattern.name,
                        "confidence": confidence,
                        "position": match.span(),
                        "valid": is_valid
                    }
                    found_ids.append(id_info)
            
            # Remove duplicates by value
            unique_ids = []
            seen_values = set()
            for id_info in found_ids:
                if id_info["value"] not in seen_values:
                    seen_values.add(id_info["value"])
                    unique_ids.append(id_info)
            
            entity_type = "organization" if id_types == self._org_id_types else "person"
            self._log_extraction_result(text, len(unique_ids), f"{entity_type}_id")
            return unique_ids
            
        except ImportError:
            self.logger.warning("Identifier patterns not available, falling back to empty result")
            return []
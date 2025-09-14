"""
Person entity extractor.
"""

import re
from typing import Any, Dict, List

from .base_extractor import BaseExtractor


class PersonExtractor(BaseExtractor):
    """Extracts person names from text using pattern matching."""
    
    def __init__(self):
        super().__init__()
        
        # Patterns for different languages
        self._cyrillic_pattern = r'\b[А-ЯЁЇІЄҐ][а-яёїієґ]+(?:\s+[А-ЯЁЇІЄҐ][а-яёїієґ]+){1,2}\b'
        self._latin_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b'
    
    def extract(self, text: str, language: str = "uk", **kwargs) -> List[List[str]]:
        """
        Extract person name tokens from text.
        
        Args:
            text: Input text
            language: Text language 
            
        Returns:
            List of person name token lists
        """
        if not self._is_valid_text(text):
            return []
        
        found_names = []
        
        # Extract Cyrillic names (Ukrainian/Russian)  
        for match in re.finditer(self._cyrillic_pattern, text):
            name_tokens = match.group(0).split()
            if not self._contains_legal_form(name_tokens):
                found_names.append(name_tokens)
        
        # Extract Latin names
        for match in re.finditer(self._latin_pattern, text):
            name_tokens = match.group(0).split()
            if not self._contains_legal_form(name_tokens):
                found_names.append(name_tokens)
        
        self._log_extraction_result(text, len(found_names), "person")
        return found_names
    
    def _contains_legal_form(self, tokens: List[str]) -> bool:
        """Check if tokens contain legal form words."""
        from ....data.patterns.legal_forms import get_legal_forms_set
        
        try:
            legal_forms = get_legal_forms_set()
            return any(token.upper() in legal_forms for token in tokens)
        except ImportError:
            # Fallback if legal forms module not available
            common_legal_forms = {"ТОВ", "ООО", "ЗАО", "ПАО", "LLC", "INC", "LTD", "CORP"}
            return any(token.upper() in common_legal_forms for token in tokens)
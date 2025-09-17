"""
Embedding Preprocessor - normalizes text for embedding generation

This module provides text preprocessing specifically designed for embedding generation.
It follows the architectural principle of separation of concerns:

- NAMES/ORGANIZATIONS → Embeddings for semantic similarity
- DATES/IDs → Separate processing in Signals/Decision layers

Key Design Decisions:
1. Remove dates/IDs by default to focus on semantic content
2. Keep only names, organizations, and titles for vector generation
3. include_attrs=True flag for attribute-aware embeddings (country, DOB, gender)

Usage:
    preprocessor = EmbeddingPreprocessor()
    clean_text = preprocessor.normalize_for_embedding("Ivan Petrov 1980-01-01 passport12345")
    # Result: "Ivan Petrov" (dates/IDs removed)
    
    # With attributes included
    clean_text = preprocessor.normalize_for_embedding("Ivan Petrov", include_attrs=True, 
                                                     attributes={"country": "UA", "dob": "1980-01-01", "gender": "M"})
    # Result: "Ivan Petrov country:UA dob:1980-01-01 gender:M"
"""

import json
import re
from pathlib import Path
from typing import Optional, Dict, Any

from ..utils.logging_config import get_logger


class EmbeddingPreprocessor:
    """Preprocessor for text normalization before embedding generation"""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the preprocessor"""
        self.logger = get_logger(__name__)
        
        # Load configuration
        self.config = self._load_config(config_path)

        # Patterns for dates and IDs that should be removed by default
        self.date_patterns = [
            r"\b\d{4}-\d{2}-\d{2}\b",  # YYYY-MM-DD
            r"\b\d{2}\.\d{2}\.\d{4}\b",  # DD.MM.YYYY
            r"\b\d{2}/\d{2}/\d{4}\b",  # DD/MM/YYYY
            r"\b\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4}\b",  # Russian dates
            r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",  # English dates
        ]

        self.id_patterns = [
            r"\bpassport\s*\d+\b",  # passport12345
            r"\bpassport\s*№\s*\d+\b",  # passport №12345
            r"\bID\s*\d+\b",  # ID12345
            r"\b№\s*\d+\b",  # №12345
            r"\bИНН\s*\d+\b",  # ИНН1234567890
            r"\bЄДРПОУ\s*\d+\b",  # ЄДРПОУ1234567890
            r"\bОГРН\s*\d+\b",  # ОГРН1234567890
            r"\bVAT\s*\d+\b",  # VAT1234567890
            r"\b\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\b",  # credit card numbers
            r"\b\d{3}-\d{3}-\d{3}\b",  # phone numbers
            r"№\s*\d+",  # №12345 (without word boundary for special character)
        ]
        
        # Attribute patterns for include_attrs mode
        self.attribute_patterns = {
            "country": [
                r"\b(?:country|страна|країна)\s*:?\s*([A-Z]{2,3})\b",  # country:UA, страна:RU
                r"\b(?:UA|RU|US|GB|DE|FR|IT|ES|PL|RO|MD|BY|KZ|UZ|AZ|AM|GE|KG|TJ|TM)\b",  # Country codes
            ],
            "dob": [
                r"\b(?:dob|дата рождения|дата народження|birth)\s*:?\s*(\d{4}-\d{2}-\d{2})\b",  # dob:1980-01-01
                r"\b(?:dob|дата рождения|дата народження|birth)\s*:?\s*(\d{2}\.\d{2}\.\d{4})\b",  # dob:01.01.1980
                r"\b(?:dob|дата рождения|дата народження|birth)\s*:?\s*(\d{2}/\d{2}/\d{4})\b",  # dob:01/01/1980
            ],
            "gender": [
                r"\b(?:gender|пол|стать)\s*:?\s*([MFmf])\b",  # gender:M, пол:М
                r"\b(?:male|female|мужской|женский|чоловічий|жіночий)\b",  # Full words
            ]
        }
        
        # Compile patterns for efficiency
        self.compiled_date_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.date_patterns]
        self.compiled_id_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.id_patterns]
        self.compiled_attribute_patterns = {
            attr: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for attr, patterns in self.attribute_patterns.items()
        }

    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        default_config = {
            "include_attrs": {
                "enabled": True,
                "attributes": ["country", "dob", "gender"],
                "format": "key:value",
                "separator": " "
            },
            "attribute_mapping": {
                "country": {
                    "aliases": ["country", "страна", "країна"],
                    "format": "country:{value}"
                },
                "dob": {
                    "aliases": ["dob", "дата рождения", "дата народження", "birth"],
                    "format": "dob:{value}"
                },
                "gender": {
                    "aliases": ["gender", "пол", "стать"],
                    "format": "gender:{value}"
                }
            }
        }
        
        if config_path is None:
            config_path = "config/embedding_preprocessor_config.json"
        
        config_file = Path(config_path)
        if config_file.exists():
            try:
                with config_file.open("r", encoding="utf-8") as f:
                    user_config = json.load(f)
                # Merge with defaults
                default_config.update(user_config)
                self.logger.info(f"Loaded embedding preprocessor config from {config_path}")
            except Exception as e:
                self.logger.warning(f"Failed to load config from {config_path}: {e}, using defaults")
        else:
            self.logger.info(f"Config file {config_path} not found, using defaults")
        
        return default_config

    def normalize_for_embedding(
        self, text: str, *, fold_spaces: bool = True, include_attrs: bool = False, 
        attributes: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Normalize text for embedding generation

        Args:
            text: Input text to normalize
            fold_spaces: Whether to collapse multiple spaces into single space
            include_attrs: Whether to include attributes (country, DOB, gender)
            attributes: Dictionary of attributes to include (country, dob, gender)

        Returns:
            Normalized text with dates/IDs removed by default, or with attributes included
        """
        if not text or not text.strip():
            return ""

        # Start with the input text
        normalized = text.strip()

        if include_attrs:
            # Extract attributes from text and provided attributes
            extracted_attrs = self._extract_attributes_from_text(normalized)
            if attributes:
                # Provided attributes take precedence over extracted ones
                for key, value in attributes.items():
                    extracted_attrs[key] = value
            
            # Remove dates and IDs from the main text
            for pattern in self.compiled_date_patterns:
                normalized = pattern.sub("", normalized)
            
            for pattern in self.compiled_id_patterns:
                normalized = pattern.sub("", normalized)
            
            # Add attributes to the text
            if extracted_attrs:
                attr_text = self._format_attributes(extracted_attrs)
                if attr_text:
                    normalized = f"{normalized} {attr_text}".strip()
        else:
            # Remove dates
            for pattern in self.compiled_date_patterns:
                normalized = pattern.sub("", normalized)

            # Remove IDs
            for pattern in self.compiled_id_patterns:
                normalized = pattern.sub("", normalized)

        # Clean up the text
        if fold_spaces:
            # Collapse multiple whitespace into single space
            normalized = re.sub(r"\s+", " ", normalized)

        # Remove leading/trailing whitespace
        normalized = normalized.strip()

        self.logger.debug(
            f"Normalized '{text}' -> '{normalized}' (include_attrs={include_attrs})"
        )

        return normalized

    def _extract_attributes_from_text(self, text: str) -> Dict[str, str]:
        """Extract attributes from text using patterns"""
        attributes = {}
        
        for attr_name, patterns in self.compiled_attribute_patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    if pattern.groups:
                        # Pattern has capture groups
                        value = match.group(1)
                    else:
                        # Pattern matches the whole value
                        value = match.group(0)
                    
                    # Normalize the value
                    normalized_value = self._normalize_attribute_value(attr_name, value)
                    if normalized_value:
                        attributes[attr_name] = normalized_value
                        break  # Use first match for each attribute
        
        return attributes

    def _normalize_attribute_value(self, attr_name: str, value: str) -> str:
        """Normalize attribute values to standard format"""
        if not value:
            return ""
        
        value = value.strip()
        
        if attr_name == "country":
            # Normalize country codes to uppercase
            return value.upper()
        
        elif attr_name == "dob":
            # Normalize date formats to YYYY-MM-DD
            return self._normalize_date(value)
        
        elif attr_name == "gender":
            # Normalize gender to M/F
            value_lower = value.lower()
            if value_lower in ["m", "male", "мужской", "чоловічий"]:
                return "M"
            elif value_lower in ["f", "female", "женский", "жіночий"]:
                return "F"
            else:
                return value.upper()
        
        return value

    def _normalize_date(self, date_str: str) -> str:
        """Normalize date string to YYYY-MM-DD format"""
        # Try different date formats
        date_patterns = [
            (r"(\d{4})-(\d{1,2})-(\d{1,2})", r"\1-\2-\3"),  # YYYY-MM-DD
            (r"(\d{1,2})\.(\d{1,2})\.(\d{4})", r"\3-\1-\2"),  # DD.MM.YYYY
            (r"(\d{1,2})/(\d{1,2})/(\d{4})", r"\3-\1-\2"),  # DD/MM/YYYY
        ]
        
        for pattern, replacement in date_patterns:
            match = re.match(pattern, date_str)
            if match:
                year, month, day = match.groups()
                # Pad with zeros
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        return date_str  # Return as-is if no pattern matches

    def _format_attributes(self, attributes: Dict[str, str]) -> str:
        """Format attributes according to configuration"""
        if not attributes:
            return ""
        
        config = self.config.get("include_attrs", {})
        enabled_attrs = config.get("attributes", ["country", "dob", "gender"])
        separator = config.get("separator", " ")
        
        formatted_parts = []
        
        for attr_name in enabled_attrs:
            if attr_name in attributes:
                value = attributes[attr_name]
                attr_config = self.config.get("attribute_mapping", {}).get(attr_name, {})
                format_template = attr_config.get("format", f"{attr_name}:{{value}}")
                
                formatted_attr = format_template.format(value=value)
                formatted_parts.append(formatted_attr)
        
        return separator.join(formatted_parts)

    def extract_name_only(self, text: str) -> str:
        """
        Extract only the name/title part, removing all dates and IDs

        Args:
            text: Input text

        Returns:
            Text with only name/title content
        """
        return self.normalize_for_embedding(text, fold_spaces=True, include_attrs=False)

    def should_include_attrs(self) -> bool:
        """
        Check if attributes should be included based on configuration

        Returns:
            True if include_attrs is enabled in config, False otherwise
        """
        return self.config.get("include_attrs", {}).get("enabled", True)

    def normalize_with_attributes(
        self, text: str, attributes: Optional[Dict[str, Any]] = None, 
        fold_spaces: bool = True
    ) -> str:
        """
        Convenience method for normalizing text with attributes included

        Args:
            text: Input text to normalize
            attributes: Dictionary of attributes to include
            fold_spaces: Whether to collapse multiple spaces into single space

        Returns:
            Normalized text with attributes included
        """
        return self.normalize_for_embedding(
            text, fold_spaces=fold_spaces, include_attrs=True, attributes=attributes
        )

"""
Embedding preprocessor for cleaning and preparing text for embedding generation
"""

import re
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class EmbeddingPreprocessor:
    """
    Preprocessor for cleaning text before embedding generation
    """
    
    def __init__(self):
        """Initialize the embedding preprocessor"""
        self.logger = logging.getLogger(__name__)
        
        # Patterns to remove (dates, IDs, etc.)
        self.date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # MM/DD/YYYY or DD/MM/YYYY
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',    # YYYY/MM/DD
            r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}\b',  # DD Mon YYYY
        ]
        
        self.id_patterns = [
            r'\b[A-Z]{2,}\d{4,}\b',  # ID patterns like ABC1234
            r'\b\d{6,}\b',           # Long number sequences
        ]
        
        # Compile patterns for efficiency
        self.compiled_date_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.date_patterns]
        self.compiled_id_patterns = [re.compile(pattern) for pattern in self.id_patterns]
    
    def preprocess(self, text: str) -> str:
        """
        Preprocess text for embedding generation
        
        Args:
            text: Input text to preprocess
            
        Returns:
            Preprocessed text
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Convert to string and strip whitespace
        processed = str(text).strip()
        
        # Remove dates
        for pattern in self.compiled_date_patterns:
            processed = pattern.sub('', processed)
        
        # Remove ID patterns
        for pattern in self.compiled_id_patterns:
            processed = pattern.sub('', processed)
        
        # Clean up extra whitespace
        processed = re.sub(r'\s+', ' ', processed).strip()
        
        return processed
    
    def preprocess_batch(self, texts: List[str]) -> List[str]:
        """
        Preprocess a batch of texts
        
        Args:
            texts: List of input texts
            
        Returns:
            List of preprocessed texts
        """
        return [self.preprocess(text) for text in texts]
    
    def is_valid_for_embedding(self, text: str) -> bool:
        """
        Check if text is valid for embedding generation
        
        Args:
            text: Text to check
            
        Returns:
            True if valid, False otherwise
        """
        if not text or not isinstance(text, str):
            return False
        
        # Check minimum length
        if len(text.strip()) < 2:
            return False
        
        # Check if it contains meaningful content (not just numbers or special chars)
        if re.match(r'^[\d\s\-_.,!?]+$', text.strip()):
            return False
        
        return True

"""
Name parsing and processing utilities with graceful degradation.
"""

from typing import Optional, Dict, Any, List, Tuple
import re
import logging

from .lazy_imports import NAMEPARSER, RAPIDFUZZ, NLP_EN, NLP_UK, NLP_RU

logger = logging.getLogger(__name__)

class NameParser:
    """Name parser with graceful degradation."""
    
    def __init__(self):
        self.nameparser = NAMEPARSER
        self.rapidfuzz = RAPIDFUZZ
        self.nlp_en = NLP_EN
        self.nlp_uk = NLP_UK
        self.nlp_ru = NLP_RU
        
        if self.nameparser is None:
            logger.warning("nameparser not available, using fallback parsing")
        if self.rapidfuzz is None:
            logger.warning("rapidfuzz not available, using fallback similarity")
        if self.nlp_en is None:
            logger.warning("spacy English model not available")
        if self.nlp_uk is None:
            logger.warning("spacy Ukrainian model not available")
        if self.nlp_ru is None:
            logger.warning("spacy Russian model not available")
    
    def parse_name(self, full_name: str) -> Dict[str, Any]:
        """
        Parse full name into components.
        
        Args:
            full_name: Full name to parse
            
        Returns:
            Dictionary with parsed components
        """
        if not full_name or not full_name.strip():
            return {
                "first": "",
                "last": "",
                "middle": "",
                "suffix": "",
                "title": "",
                "raw": full_name
            }
        
        # Clean the input
        cleaned_name = full_name.strip()
        
        if self.nameparser:
            try:
                parsed = self.nameparser.HumanName(cleaned_name)
                return {
                    "first": parsed.first or "",
                    "last": parsed.last or "",
                    "middle": parsed.middle or "",
                    "suffix": parsed.suffix or "",
                    "title": parsed.title or "",
                    "raw": cleaned_name
                }
            except Exception as e:
                logger.warning(f"nameparser failed for '{cleaned_name}': {e}")
        
        # Fallback parsing
        return self._fallback_parse_name(cleaned_name)
    
    def _fallback_parse_name(self, full_name: str) -> Dict[str, Any]:
        """Fallback name parsing when nameparser is not available."""
        parts = full_name.split()
        
        if len(parts) == 0:
            return {
                "first": "",
                "last": "",
                "middle": "",
                "suffix": "",
                "title": "",
                "raw": full_name
            }
        elif len(parts) == 1:
            return {
                "first": parts[0],
                "last": "",
                "middle": "",
                "suffix": "",
                "title": "",
                "raw": full_name
            }
        elif len(parts) == 2:
            return {
                "first": parts[0],
                "last": parts[1],
                "middle": "",
                "suffix": "",
                "title": "",
                "raw": full_name
            }
        else:
            # Multiple parts - assume first, middle(s), last
            return {
                "first": parts[0],
                "last": parts[-1],
                "middle": " ".join(parts[1:-1]),
                "suffix": "",
                "title": "",
                "raw": full_name
            }
    
    def extract_entities(self, text: str, language: str = "en") -> List[Dict[str, Any]]:
        """
        Extract named entities from text using spacy.
        
        Args:
            text: Text to process
            language: Language code (en, uk, ru)
            
        Returns:
            List of entities with their labels and positions
        """
        if not text or not text.strip():
            return []
        
        # Select appropriate model
        nlp = None
        if language == "en" and self.nlp_en:
            nlp = self.nlp_en
        elif language == "uk" and self.nlp_uk:
            nlp = self.nlp_uk
        elif language == "ru" and self.nlp_ru:
            nlp = self.nlp_ru
        
        if nlp is None:
            logger.warning(f"No spacy model available for language '{language}'")
            return []
        
        try:
            doc = nlp(text)
            entities = []
            
            for ent in doc.ents:
                entities.append({
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "confidence": 1.0  # spacy doesn't provide confidence scores
                })
            
            return entities
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []
    
    def calculate_similarity(self, text1: str, text2: str, method: str = "ratio") -> float:
        """
        Calculate similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            method: Similarity method (ratio, partial_ratio, token_sort_ratio, token_set_ratio)
            
        Returns:
            Similarity score between 0 and 100
        """
        if not text1 or not text2:
            return 0.0
        
        if self.rapidfuzz:
            try:
                if method == "ratio":
                    return self.rapidfuzz.fuzz.ratio(text1, text2)
                elif method == "partial_ratio":
                    return self.rapidfuzz.fuzz.partial_ratio(text1, text2)
                elif method == "token_sort_ratio":
                    return self.rapidfuzz.fuzz.token_sort_ratio(text1, text2)
                elif method == "token_set_ratio":
                    return self.rapidfuzz.fuzz.token_set_ratio(text1, text2)
                else:
                    logger.warning(f"Unknown similarity method: {method}")
                    return self.rapidfuzz.fuzz.ratio(text1, text2)
            except Exception as e:
                logger.error(f"Error calculating similarity: {e}")
        
        # Fallback similarity calculation
        return self._fallback_similarity(text1, text2)
    
    def _fallback_similarity(self, text1: str, text2: str) -> float:
        """Fallback similarity calculation when rapidfuzz is not available."""
        if text1 == text2:
            return 100.0
        
        # Simple character-based similarity
        if not text1 or not text2:
            return 0.0
        
        # Convert to lowercase for comparison
        t1 = text1.lower().strip()
        t2 = text2.lower().strip()
        
        if t1 == t2:
            return 100.0
        
        # Simple Jaccard similarity on character n-grams
        def get_ngrams(text: str, n: int = 2) -> set:
            return set(text[i:i+n] for i in range(len(text) - n + 1))
        
        ngrams1 = get_ngrams(t1, 2)
        ngrams2 = get_ngrams(t2, 2)
        
        if not ngrams1 and not ngrams2:
            return 100.0
        if not ngrams1 or not ngrams2:
            return 0.0
        
        intersection = len(ngrams1.intersection(ngrams2))
        union = len(ngrams1.union(ngrams2))
        
        return (intersection / union) * 100 if union > 0 else 0.0
    
    def find_best_match(self, query: str, candidates: List[str], threshold: float = 80.0) -> Optional[Tuple[str, float]]:
        """
        Find the best matching candidate for a query.
        
        Args:
            query: Query string
            candidates: List of candidate strings
            threshold: Minimum similarity threshold
            
        Returns:
            Tuple of (best_match, score) or None if no match above threshold
        """
        if not query or not candidates:
            return None
        
        best_match = None
        best_score = 0.0
        
        for candidate in candidates:
            score = self.calculate_similarity(query, candidate)
            if score > best_score and score >= threshold:
                best_score = score
                best_match = candidate
        
        return (best_match, best_score) if best_match else None

# Global instance
name_parser = NameParser()

def get_name_parser() -> NameParser:
    """Get the global name parser instance."""
    return name_parser

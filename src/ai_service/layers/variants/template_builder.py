"""
Service for creating ready-made templates for Module 3
Collects all data from different services into a unified structure
"""

import json
import logging
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np

# Add path for imports
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# If running file directly
if __name__ == "__main__":
    from config import TEMPLATE_CONFIG


@dataclass
class EntityTemplate:
    """Ready-made entity template for Module 3"""
    # Original data
    original_text: str
    entity_type: str
    source: str
    
    # Normalized data
    normalized_text: str
    language: str
    language_confidence: float
    
    # Templates for Aho-Corasick
    search_patterns: List[str]
    
    # Writing variants
    variants: List[str]
    
    # New structure: variants for each token (ELIMINATING COMBINATORIAL EXPLOSION)
    token_variants: Dict[str, List[str]]
    
    # Embeddings for fuzzy search
    embeddings: Optional[List[float]] = None
    
    # Metadata
    creation_date: str = None
    complexity_score: float = 0.0
    processing_time: float = 0.0
    template_confidence: float = 0.0
    
    def __post_init__(self):
        """Post-initialization processing"""
        if self.creation_date is None:
            self.creation_date = datetime.now().isoformat()
        
        # Calculate total number of variants from token_variants
        if self.token_variants:
            total_token_variants = sum(len(variants) for variants in self.token_variants.values())
            self.total_variants = len(self.variants) + total_token_variants
        else:
            self.total_variants = len(self.variants)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for saving"""
        result = asdict(self)
        
        # Convert numpy arrays to lists
        if self.embeddings is not None:
            if isinstance(self.embeddings, np.ndarray):
                result['embeddings'] = self.embeddings.tolist()
            elif isinstance(self.embeddings, list):
                # If it's a list of numpy arrays
                result['embeddings'] = [emb.tolist() if isinstance(emb, np.ndarray) else emb for emb in self.embeddings]
        
        return result
    
    def get_search_keywords(self) -> List[str]:
        """Get search keywords"""
        keywords = []
        
        # Add all patterns
        keywords.extend(self.search_patterns)
        
        # Add writing variants (maintain backward compatibility)
        keywords.extend(self.variants)
        
        # Add variants from new token_variants structure
        if self.token_variants:
            for token, variants in self.token_variants.items():
                keywords.append(token)
                keywords.extend(variants)
        
        return list(set(keywords))  # Unique keys
    
    def get_high_confidence_patterns(self, threshold: float = 0.7) -> List[str]:
        """Get patterns with high confidence"""
        if self.template_confidence >= threshold:
            return self.search_patterns
        return []


class TemplateBuilder:
    """Service for creating ready-made templates"""
    
    def __init__(self):
        """Initialize template builder"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("TemplateBuilder initialized")
    
    def create_entity_template(
        self,
        entity: Dict,
        normalized_text: str,
        language: str,
        language_confidence: float,
        variants: List[str],
        token_variants: Dict[str, List[str]] = None,
        embeddings: Optional[List[float]] = None
    ) -> EntityTemplate:
        """
        Create ready-made template for one entity
        
        Args:
            entity: Original entity
            normalized_text: Normalized text
            language: Language
            language_confidence: Language confidence
            variants: Writing variants
            token_variants: Variants for each token
            embeddings: Text embeddings
            
        Returns:
            Ready-made EntityTemplate
        """
        try:
            # Generate search patterns
            search_patterns = self._generate_search_patterns(normalized_text, variants)
            
            # Calculate complexity score
            complexity_score = self._calculate_complexity_score(
                language_confidence=language_confidence,
                pattern_count=len(search_patterns),
                variant_count=len(variants),
                normalized_text=normalized_text
            )
            
            # Create template
            template = EntityTemplate(
                original_text=entity.get('text', ''),
                entity_type=entity.get('type', 'unknown'),
                source=entity.get('source', 'unknown'),
                normalized_text=normalized_text,
                language=language,
                language_confidence=language_confidence,
                search_patterns=search_patterns,
                variants=variants,
                token_variants=token_variants or {},
                embeddings=embeddings,
                complexity_score=complexity_score,
                template_confidence=language_confidence
            )
            
            self.logger.info(f"Created template for entity: {entity.get('text', '')[:50]}...")
            return template
            
        except Exception as e:
            self.logger.error(f"Failed to create template for entity {entity.get('text', '')}: {e}")
            # Return minimal template
            return EntityTemplate(
                original_text=entity.get('text', ''),
                entity_type=entity.get('type', 'unknown'),
                source=entity.get('source', 'unknown'),
                normalized_text=normalized_text,
                language=language,
                language_confidence=language_confidence,
                search_patterns=[normalized_text],
                variants=[normalized_text],
                token_variants={},
                complexity_score=1.0,
                template_confidence=0.0
            )
    
    def create_batch_templates(
        self,
        entities: List[Dict],
        normalized_texts: List[str],
        languages: List[str],
        language_confidences: List[float],
        variants_list: List[List[str]],
        embeddings_list: List[Optional[List[float]]] = None,
        token_variants_list: List[Dict[str, List[str]]] = None
    ) -> List[EntityTemplate]:
        """
        Create templates for a batch of entities
        
        Args:
            entities: List of original entities
            normalized_texts: List of normalized texts
            languages: List of languages
            language_confidences: List of language confidences
            variants_list: List of variant lists
            embeddings_list: List of embedding lists
            token_variants_list: List of token variants dictionaries
            
        Returns:
            List of ready-made templates
        """
        if embeddings_list is None:
            embeddings_list = [None] * len(entities)
        
        if token_variants_list is None:
            token_variants_list = [{}] * len(entities)
        
        templates = []
        
        for i, entity in enumerate(entities):
            try:
                template = self.create_entity_template(
                    entity=entity,
                    normalized_text=normalized_texts[i],
                    language=languages[i],
                    language_confidence=language_confidences[i],
                    variants=variants_list[i],
                    token_variants=token_variants_list[i],
                    embeddings=embeddings_list[i]
                )
                templates.append(template)
            except Exception as e:
                self.logger.error(f"Failed to create template for entity {i}: {e}")
                continue
        
        self.logger.info(f"Created {len(templates)} templates from {len(entities)} entities")
        return templates
    
    def _generate_search_patterns(self, normalized_text: str, variants: List[str]) -> List[str]:
        """Generate search patterns"""
        patterns = [normalized_text]
        
        # Add high-quality variants
        for variant in variants:
            if len(variant) >= 3 and variant != normalized_text:
                patterns.append(variant)
        
        # Limit patterns to avoid explosion
        return patterns[:20]
    
    def _calculate_complexity_score(
        self,
        language_confidence: float,
        pattern_count: int,
        variant_count: int,
        normalized_text: str
    ) -> float:
        """
        Calculate processing complexity score
        
        Args:
            language_confidence: Language confidence
            pattern_count: Number of found patterns
            variant_count: Number of writing variants
            normalized_text: Normalized text
            
        Returns:
            Complexity score (0.0 - 1.0)
        """
        score = 0.0
        
        # Language complexity (0-0.3)
        language_score = 1.0 - language_confidence
        score += language_score * 0.3
        
        # Pattern complexity (0-0.3)
        if pattern_count > 10:
            pattern_score = min((pattern_count - 10) / 20.0, 1.0)  # Normalize to 1.0
            score += pattern_score * 0.3
        
        # Variant complexity (0-0.2)
        if variant_count > 20:
            variant_score = min((variant_count - 20) / 50.0, 1.0)
            score += variant_score * 0.2
        
        # Text complexity (0-0.2)
        text_length = len(normalized_text)
        if text_length > 100:
            text_score = min((text_length - 100) / 200.0, 1.0)
            score += text_score * 0.2
        
        return min(score, 1.0)
    
    def get_template_statistics(self, templates: List[EntityTemplate]) -> Dict[str, Any]:
        """
        Get statistics on templates
        
        Args:
            templates: List of templates
            
        Returns:
            Dictionary with statistics
        """
        if not templates:
            return {}
        
        stats = {
            'total_templates': len(templates),
            'total_patterns': sum(len(t.search_patterns) for t in templates),
            'total_variants': sum(len(t.variants) for t in templates),
            'average_complexity': sum(t.complexity_score for t in templates) / len(templates),
            'language_distribution': {},
            'type_distribution': {},
            'confidence_distribution': {
                'high': len([t for t in templates if t.template_confidence >= 0.8]),
                'medium': len([t for t in templates if 0.5 <= t.template_confidence < 0.8]),
                'low': len([t for t in templates if t.template_confidence < 0.5])
            }
        }
        
        # Language distribution
        for template in templates:
            lang = template.language
            stats['language_distribution'][lang] = stats['language_distribution'].get(lang, 0) + 1
        
        # Type distribution
        for template in templates:
            entity_type = template.entity_type
            stats['type_distribution'][entity_type] = stats['type_distribution'].get(entity_type, 0) + 1
        
        return stats
    
    def export_for_aho_corasick(self, templates: List[EntityTemplate]) -> List[str]:
        """
        Export templates for Aho-Corasick algorithm
        
        Args:
            templates: List of templates
            
        Returns:
            List of strings for search
        """
        patterns = []
        
        for template in templates:
            # Add all patterns with high confidence
            if template.template_confidence >= 0.7:
                patterns.extend(template.search_patterns)
            
            # Add writing variants
            patterns.extend(template.variants)
            
            # Add variants from new token_variants structure
            if template.token_variants:
                for token, variants in template.token_variants.items():
                    # Add the token itself
                    patterns.append(token)
                    # Add all its variants
                    patterns.extend(variants)
        
        # Unique patterns
        return list(set(patterns))

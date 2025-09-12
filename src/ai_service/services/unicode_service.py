"""
Unicode normalization service for preventing False Negatives
"""

import re
import logging
import unicodedata
from typing import Dict, List, Optional, Union, Any
from datetime import datetime

from ..utils import get_logger


class UnicodeService:
    """Service for Unicode normalization with focus on preventing FN"""
    
    def __init__(self):
        """Initialize Unicode service"""
        self.logger = get_logger(__name__)
        
        # Mapping for complex characters
        self.character_mapping = {
            # Cyrillic characters that may have different Unicode representations
            'ё': 'е', 'Ё': 'Е',
            'й': 'и', 'Й': 'И',
            'і': 'и', 'І': 'И',  # Ukrainian i -> Russian и
            'ї': 'и', 'Ї': 'И',  # Ukrainian ї -> Russian и
            'є': 'е', 'Є': 'Е',  # Ukrainian є -> Russian е
            'ґ': 'г', 'Ґ': 'Г',  # Ukrainian ґ -> Russian г
            
            # Latin characters with diacritics
            'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
            'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
            'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
            'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
            'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
            'ý': 'y', 'ÿ': 'y',
            
            # German umlauts
            'ä': 'a', 'ö': 'o', 'ü': 'u', 'ß': 'ss',
            'Ä': 'A', 'Ö': 'O', 'Ü': 'U',
            
            # French characters
            'à': 'a', 'â': 'a', 'ç': 'c', 'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
            'î': 'i', 'ï': 'i', 'ô': 'o', 'ù': 'u', 'û': 'u', 'ü': 'u', 'ÿ': 'y'
        }
        
        # Characters that we always preserve
        self.preserved_chars = set('а-яёіїєґА-ЯЁІЇЄҐ')
        
        self.logger.info("UnicodeService initialized")
    
    def _attempt_encoding_recovery(self, text: str) -> str:
        """Attempt to recover corrupted encoding"""
        if not text:
            return text
        
        # List of common encoding problems
        encoding_fixes = [
            # Windows-1252 -> UTF-8 (most common problem)
            ('\x80', '€'), ('\x81', ''), ('\x82', '‚'), ('\x83', 'ƒ'),
            ('\x84', '„'), ('\x85', '…'), ('\x86', '†'), ('\x87', '‡'),
            ('\x88', 'ˆ'), ('\x89', '‰'), ('\x8A', 'Š'), ('\x8B', '‹'),
            ('\x8C', 'Œ'), ('\x8D', ''), ('\x8E', 'Ž'), ('\x8F', ''),
            ('\x90', ''), ('\x91', ''), ('\x92', ''), ('\x93', '"'),
            ('\x94', '"'), ('\x95', '•'), ('\x96', '–'), ('\x97', '—'),
            ('\x98', '˜'), ('\x99', '™'), ('\x9A', 'š'), ('\x9B', '›'),
            ('\x9C', 'œ'), ('\x9D', ''), ('\x9E', 'ž'), ('\x9F', 'Ÿ'),
            
            # CP1251 -> UTF-8 (Cyrillic)
            ('\x80', 'Ђ'), ('\x81', 'Ѓ'), ('\x82', '‚'), ('\x83', 'ѓ'),
            ('\x84', '„'), ('\x85', '…'), ('\x86', '†'), ('\x87', '‡'),
            ('\x88', '€'), ('\x89', '‰'), ('\x8A', 'Љ'), ('\x8B', '‹'),
            ('\x8C', 'Њ'), ('\x8D', 'Ќ'), ('\x8E', 'Ћ'), ('\x8F', 'Џ'),
            ('\x90', 'ђ'), ('\x91', 'ѓ'), ('\x92', '‚'), ('\x93', 'ѓ'),
            ('\x94', '„'), ('\x95', '…'), ('\x96', '†'), ('\x97', '‡'),
            ('\x98', '€'), ('\x99', '‰'), ('\x9A', 'љ'), ('\x9B', '‹'),
            ('\x9C', 'њ'), ('\x9D', 'ќ'), ('\x9E', 'ћ'), ('\x9F', 'џ')
        ]
        
        # Apply fixes
        recovered_text = text
        for old_char, new_char in encoding_fixes:
            recovered_text = recovered_text.replace(old_char, new_char)
        
        # Assess recovery quality
        if recovered_text != text:
            # Cyrillic letters
            cyrillic_count = len(re.findall(r'[а-яёіїєґ]', recovered_text, re.IGNORECASE))
            # Latin letters
            latin_count = len(re.findall(r'[a-z]', recovered_text, re.IGNORECASE))
            # Total score (Cyrillic is more important for our texts)
            total_score = cyrillic_count * 2 + latin_count
            
            # Check if text became more meaningful
            if total_score > 0:
                self.logger.info(f"Encoding recovery successful: {cyrillic_count} Cyrillic, {latin_count} Latin characters")
                return recovered_text
        
        # Try partial recovery for mixed encodings
        if 'Ð' in text or 'Ñ' in text:
            # Look for patterns of corrupted encoding and try to fix them partially
            # Pattern for corrupted characters like Ð¸, Ð¹, etc.
            partial_fixes = {
                # Replace common corrupted sequences
                'Ð¡': 'С', 'Ðµ': 'е', 'Ñ€': 'р', 'Ð³': 'г', 'Ð¸': 'и', 'Ð¹': 'й',
                'Ð˜': 'И', 'Ð²': 'в', 'Ð°': 'а', 'Ð½': 'н', 'Ð¾': 'о', 'Ð²': 'в',
                'Ñ': 'с', 'Ñ‚': 'т', 'Ñƒ': 'у', 'Ñ„': 'ф', 'Ñ…': 'х', 'Ñ†': 'ц',
                'Ñ‡': 'ч', 'Ñˆ': 'ш', 'Ñ‰': 'щ', 'ÑŠ': 'ъ', 'Ñ‹': 'ы', 'ÑŒ': 'ь',
                'Ñ': 'э', 'ÑŽ': 'ю', 'Ñ': 'я'
            }
            
            partially_recovered = text
            for corrupted, fixed in partial_fixes.items():
                partially_recovered = partially_recovered.replace(corrupted, fixed)
            
            # Assess partial recovery quality
            if partially_recovered != text:
                cyrillic_count = len(re.findall(r'[а-яёіїєґ]', partially_recovered, re.IGNORECASE))
                if cyrillic_count > 0:
                    self.logger.info(f"Partial encoding recovery successful: {cyrillic_count} Cyrillic characters")
                    return partially_recovered
        
        return text
    
    def normalize_text(
        self,
        text: str,
        aggressive: bool = False
    ) -> Dict[str, Any]:
        """
        Unicode normalization of text with focus on preventing FN
        
        Args:
            text: Input text
            aggressive: Aggressive normalization (may change meaning)
            
        Returns:
            Dict with normalized text and metadata
        """
        if not text:
            result = self._create_normalization_result('', 1.0, 0, 0, 0)
            result['original'] = text  # Preserve None or empty string
            return result
        
        # Preserve original text before any changes
        original_text = text
        changes_count = 0
        char_replacements = 0
        
        # 0. Attempt to recover corrupted encoding
        recovered_text = self._attempt_encoding_recovery(text)
        if recovered_text != text:
            text = recovered_text
            changes_count += 1
        
        # 1. Basic Unicode normalization (NFD -> NFKC)
        normalized_text = self._apply_unicode_normalization(text)
        
        # 2. Case normalization
        normalized_text = self._normalize_case(normalized_text)
        
        # 3. Replace complex characters
        normalized_text, replacements = self._replace_complex_characters(normalized_text)
        char_replacements += replacements
        
        # 4. ASCII folding (always in aggressive mode, or only if not aggressive)
        if aggressive:
            normalized_text, ascii_changes = self._apply_ascii_folding(normalized_text)
            char_replacements += ascii_changes
        
        # 5. Final cleanup
        normalized_text = self._final_cleanup(normalized_text)
        
        # Calculate confidence
        confidence = self._calculate_normalization_confidence(
            original_text, normalized_text, char_replacements
        )
        
        result = self._create_normalization_result(
            normalized_text, confidence, changes_count, char_replacements, len(original_text)
        )
        # Add original text to result
        result['original'] = original_text
        
        self.logger.info(f"Text normalized: {len(original_text)} -> {len(normalized_text)} chars, confidence: {confidence:.2f}")
        return result
    
    def normalize_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Normalize multiple texts in batch"""
        results = []
        for text in texts:
            results.append(self.normalize_text(text))
        return results
    
    def _apply_unicode_normalization(self, text: str) -> str:
        """Apply Unicode normalization"""
        try:
            # NFD -> NFKC for better handling of complex characters
            normalized = unicodedata.normalize('NFKC', text)
            return normalized
        except Exception as e:
            self.logger.warning(f"Unicode normalization failed: {e}")
            return text
    
    def _normalize_case(self, text: str) -> str:
        """Case normalization"""
        return text.lower()
    
    def _replace_complex_characters(self, text: str) -> tuple[str, int]:
        """Replace complex characters"""
        replacements = 0
        result = ""
        
        for char in text:
            if char in self.character_mapping:
                result += self.character_mapping[char]
                replacements += 1
            else:
                result += char
        
        return result, replacements
    
    def _apply_ascii_folding(self, text: str) -> tuple[str, int]:
        """ASCII folding for Latin characters (preserve Cyrillic)"""
        try:
            from unidecode import unidecode
            changes = 0
            result = ""
            
            # Apply unidecode only to Latin characters with diacritics
            # Preserve Cyrillic characters
            for char in text:
                # Check if it's a Cyrillic character
                if '\u0400' <= char <= '\u04FF':  # Cyrillic Unicode block
                    result += char  # Preserve Cyrillic unchanged
                elif char.isascii():
                    result += char  # ASCII characters remain unchanged
                else:
                    # For other characters (Latin with diacritics) use unidecode
                    folded = unidecode(char)
                    if folded != char:
                        changes += 1
                    result += folded
            
            # Count changes
            if changes > 0:
                self.logger.debug(f"ASCII folding applied: {changes} characters changed")
                # Additional logging of changes for debug
                for i, (orig, folded) in enumerate(zip(text, result)):
                    if orig != folded:
                        self.logger.debug(f"Character {i}: '{orig}' -> '{folded}'")
            
            return result, changes
            
        except ImportError:
            self.logger.warning("unidecode not available, skipping ASCII folding")
            return text, 0
    
    def _final_cleanup(self, text: str) -> str:
        """Final text cleanup"""
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove null characters
        text = text.replace('\x00', '')
        
        # Remove other control characters
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        return text
    
    def _calculate_normalization_confidence(
        self,
        original: str,
        normalized: str,
        char_replacements: int
    ) -> float:
        """Calculate normalization confidence"""
        # Base confidence
        confidence = 1.0
        
        # Lower confidence for each change
        if char_replacements > 0:
            # Character replacement - small reduction
            confidence -= min(0.2, char_replacements * 0.01)
        
        if len(normalized) != len(original):
            # ASCII folding - more reduction
            confidence -= min(0.3, abs(len(normalized) - len(original)) * 0.05)
        
        # Confidence cannot be less than 0.1
        return max(0.1, confidence)
    

    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between texts after normalization"""
        try:
            # Simple similarity algorithm
            norm1 = self.normalize_text(text1)['normalized']
            norm2 = self.normalize_text(text2)['normalized']
            
            # Levenshtein distance
            distance = self._levenshtein_distance(norm1, norm2)
            max_len = max(len(norm1), len(norm2))
            
            if max_len == 0:
                return 1.0
            
            similarity = 1.0 - (distance / max_len)
            return max(0.0, similarity)
            
        except Exception as e:
            self.logger.error(f"Similarity calculation failed: {e}")
            return 0.0
    
    def get_similarity_score(self, text1: str, text2: str) -> float:
        """Get similarity score between texts (alias for calculate_similarity)"""
        return self.calculate_similarity(text1, text2)
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Levenshtein distance calculation"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def detect_encoding_issues(self, text: str) -> List[Dict[str, Any]]:
        """Detect encoding issues"""
        issues = []
        
        # Check for character replacement
        for char in text:
            if char in self.character_mapping:
                # Check if it's not a replacement
                if char not in self.preserved_chars:
                    issues.append({
                        'type': 'replacement_char',
                        'character': char,
                        'suggested': self.character_mapping[char],
                        'position': text.index(char)
                    })
        
        # Check for null characters
        if '\x00' in text:
            issues.append({
                'type': 'null_char',
                'count': text.count('\x00'),
                'positions': [i for i, char in enumerate(text) if char == '\x00']
            })
        
        # Check for other control characters
        control_chars = re.findall(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', text)
        if control_chars:
            issues.append({
                'type': 'control_character',
                'characters': list(set(control_chars)),
                'count': len(control_chars)
            })
        
        return issues
    
    def _create_normalization_result(
        self,
        normalized_text: str,
        confidence: float,
        changes_count: int,
        char_replacements: int,
        original_length: int
    ) -> Dict[str, Any]:
        """Create normalization result"""
        # Create changes list for tracking what was changed
        changes = []
        if char_replacements > 0:
            changes.append({
                'type': 'char_replacement',
                'count': char_replacements
            })
        
        return {
            'normalized': normalized_text,
            'original': normalized_text,  # For backward compatibility
            'confidence': confidence,
            'changes_count': changes_count,
            'char_replacements': char_replacements,
            'original_length': original_length,
            'length_original': original_length,  # For backward compatibility
            'normalized_length': len(normalized_text),
            'length_normalized': len(normalized_text),  # For backward compatibility
            'changes': changes,
            'timestamp': datetime.now().isoformat()
        }

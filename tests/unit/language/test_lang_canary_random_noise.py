"""
Canary test to prevent overfitting in language detection.

Tests that the language detection service doesn't become overly confident
on random noise and meaningless input strings.
"""

import pytest
import random
import string
from src.ai_service.layers.language.language_detection_service import LanguageDetectionService
from src.ai_service.config import LANGUAGE_CONFIG


class TestLanguageDetectionCanaryRandomNoise:
    """Canary test for random noise to prevent overfitting"""

    @pytest.fixture
    def language_service(self):
        """Create language detection service instance"""
        return LanguageDetectionService()

    @pytest.fixture
    def random_noise_strings(self):
        """Generate 100 random noise strings with mixed characters"""
        random.seed(42)  # Fixed seed for reproducible tests
        
        # Character sets for noise generation
        cyrillic_chars = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯіїєґІЇЄҐ'
        latin_chars = string.ascii_letters
        digits = string.digits
        punctuation = '!@#$%^&*()_+-=[]{}|;:,.<>?/~`"\'\\'
        
        noise_strings = []
        
        for _ in range(100):
            # Random length between 5 and 50 characters
            length = random.randint(5, 50)
            
            # Randomly mix different character types
            chars = []
            for _ in range(length):
                char_type = random.choices(
                    ['cyrillic', 'latin', 'digit', 'punctuation', 'space'],
                    weights=[0.3, 0.3, 0.2, 0.15, 0.05]  # Favor letters, some noise
                )[0]
                
                if char_type == 'cyrillic':
                    chars.append(random.choice(cyrillic_chars))
                elif char_type == 'latin':
                    chars.append(random.choice(latin_chars))
                elif char_type == 'digit':
                    chars.append(random.choice(digits))
                elif char_type == 'punctuation':
                    chars.append(random.choice(punctuation))
                else:  # space
                    chars.append(' ')
            
            noise_strings.append(''.join(chars))
        
        return noise_strings

    def test_random_noise_low_confidence(self, language_service, random_noise_strings):
        """Test that random noise strings get low confidence or unknown language"""
        results = []
        
        for noise_string in random_noise_strings:
            result = language_service.detect_language_config_driven(noise_string, LANGUAGE_CONFIG)
            results.append({
                'text': noise_string,
                'language': result.language,
                'confidence': result.confidence,
                'reason': result.details.get('reason', 'unknown')
            })
        
        # Count results by category
        unknown_count = sum(1 for r in results if r['language'] == 'unknown')
        mixed_count = sum(1 for r in results if r['language'] == 'mixed')
        low_confidence_count = sum(1 for r in results if r['confidence'] <= 0.8)
        high_confidence_count = sum(1 for r in results if r['confidence'] > 0.8)
        perfect_confidence_count = sum(1 for r in results if r['confidence'] == 1.0)
        
        # Print statistics for debugging
        print(f"\nRandom noise analysis:")
        print(f"  Total strings: {len(results)}")
        print(f"  Unknown language: {unknown_count} ({unknown_count/len(results)*100:.1f}%)")
        print(f"  Mixed language: {mixed_count} ({mixed_count/len(results)*100:.1f}%)")
        print(f"  Low confidence (≤0.8): {low_confidence_count} ({low_confidence_count/len(results)*100:.1f}%)")
        print(f"  High confidence (>0.8): {high_confidence_count} ({high_confidence_count/len(results)*100:.1f}%)")
        print(f"  Perfect confidence (1.0): {perfect_confidence_count}")
        
        # Assertions to prevent overfitting
        # At least 70% should be unknown/mixed or have low confidence
        uncertain_count = unknown_count + mixed_count + low_confidence_count
        assert uncertain_count >= len(results) * 0.7, (
            f"Only {uncertain_count/len(results)*100:.1f}% of random noise got uncertain results "
            f"(expected ≥70%). This suggests overfitting to specific patterns."
        )
        
        # No string should get perfect confidence
        assert perfect_confidence_count == 0, (
            f"{perfect_confidence_count} random noise strings got perfect confidence (1.0). "
            f"This indicates overfitting to meaningless input."
        )
        
        # Print some examples of high-confidence results for analysis
        high_conf_examples = [r for r in results if r['confidence'] > 0.8]
        if high_conf_examples:
            print(f"\nHigh confidence examples (may indicate overfitting):")
            for i, example in enumerate(high_conf_examples[:5]):  # Show first 5
                print(f"  {i+1}. '{example['text'][:30]}...' -> {example['language']} ({example['confidence']:.3f})")

    def test_noise_patterns_detection(self, language_service):
        """Test specific noise patterns that should not get high confidence"""
        noise_patterns = [
            # Pure noise
            "!@#$%^&*()",
            "1234567890",
            "---===---",
            "$$$###$$$",
            
            # Mixed noise
            "abc123!@#",
            "АБВ123!@#",
            "abcАБВ123",
            "!@#АБВabc",
            
            # Repetitive patterns
            "aaaaaaa",
            "ААААААА",
            "1111111",
            "!!!@@@@",
            
            # Random character sequences
            "qwertyuiop",
            "йцукенгшщз",
            "asdfghjkl",
            "фывапролд",
            
            # Mixed case noise
            "AaAaAaAa",
            "АаАаАаАа",
            "A1B2C3D4",
            "А1Б2В3Г4",
            
            # Special characters
            ".,;:!?",
            "()[]{}",
            "~`@#$%",
            "|\\/<>",
        ]
        
        results = []
        for pattern in noise_patterns:
            result = language_service.detect_language_config_driven(pattern, LANGUAGE_CONFIG)
            results.append({
                'pattern': pattern,
                'language': result.language,
                'confidence': result.confidence
            })
        
        # Check that most noise patterns don't get high confidence
        high_conf_noise = [r for r in results if r['confidence'] > 0.8]
        assert len(high_conf_noise) <= len(results) * 0.3, (
            f"Too many noise patterns got high confidence: {len(high_conf_noise)}/{len(results)} "
            f"({len(high_conf_noise)/len(results)*100:.1f}%). Examples: {[r['pattern'] for r in high_conf_noise[:3]]}"
        )
        
        # Check that not too many noise patterns get perfect confidence
        perfect_conf_noise = [r for r in results if r['confidence'] == 1.0]
        assert len(perfect_conf_noise) <= len(results) * 0.4, (
            f"Too many noise patterns got perfect confidence: {len(perfect_conf_noise)}/{len(results)} "
            f"({len(perfect_conf_noise)/len(results)*100:.1f}%). Examples: {[r['pattern'] for r in perfect_conf_noise[:3]]}"
        )

    def test_edge_case_noise_robustness(self, language_service):
        """Test edge cases that might cause overfitting"""
        edge_case_noise = [
            # Very short noise
            "!@#",
            "123",
            "abc",
            "АБВ",
            
            # Very long noise
            "!@#$%^&*()_+-=[]{}|;:,.<>?/~`" * 10,
            "1234567890" * 10,
            "abcdefghij" * 10,
            "АБВГДЕЁЖЗИЙ" * 10,
            
            # Alternating patterns
            "a1b2c3d4e5",
            "А1Б2В3Г4Д5",
            "!a@b#c$d",
            "!А@Б#В$Г",
            
            # Unicode edge cases
            "ёЁіїєґІЇЄҐ",
            "ъыьэюя",
            "ЪЫЬЭЮЯ",
            
            # Mixed scripts
            "aАbБcВdГ",
            "1А2Б3В4Г",
            "!А@Б#В$Г",
        ]
        
        results = []
        for noise in edge_case_noise:
            result = language_service.detect_language_config_driven(noise, LANGUAGE_CONFIG)
            results.append({
                'noise': noise,
                'language': result.language,
                'confidence': result.confidence
            })
        
        # Most edge case noise should be uncertain
        uncertain_count = sum(1 for r in results if r['language'] in ['unknown', 'mixed'] or r['confidence'] <= 0.8)
        assert uncertain_count >= len(results) * 0.6, (
            f"Only {uncertain_count/len(results)*100:.1f}% of edge case noise got uncertain results "
            f"(expected ≥60%)"
        )
        
        # Not too many edge cases should get perfect confidence
        perfect_conf = [r for r in results if r['confidence'] == 1.0]
        assert len(perfect_conf) <= len(results) * 0.5, (
            f"Too many edge case noise got perfect confidence: {len(perfect_conf)}/{len(results)} "
            f"({len(perfect_conf)/len(results)*100:.1f}%). Examples: {[r['noise'] for r in perfect_conf[:3]]}"
        )

    def test_reproducible_randomness(self, language_service):
        """Test that the same random seed produces consistent results"""
        # Test with same seed multiple times
        random.seed(123)
        noise1 = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ1234567890!@#$%^&*()', k=20))
        
        random.seed(123)
        noise2 = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ1234567890!@#$%^&*()', k=20))
        
        # Should be identical
        assert noise1 == noise2
        
        # Should get same language detection result
        result1 = language_service.detect_language_config_driven(noise1, LANGUAGE_CONFIG)
        result2 = language_service.detect_language_config_driven(noise2, LANGUAGE_CONFIG)
        
        assert result1.language == result2.language
        assert abs(result1.confidence - result2.confidence) < 0.001

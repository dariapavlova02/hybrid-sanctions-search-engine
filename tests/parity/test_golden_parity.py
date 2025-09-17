"""
Golden parity tests for legacy vs factory normalization.

This module tests that the factory normalization produces equivalent results
to the legacy normalization for golden test cases.
"""

import pytest
import json
from typing import Dict, Any, List, Tuple
from pathlib import Path

from src.ai_service.layers.normalization.normalization_service import NormalizationService
from src.ai_service.layers.normalization.processors.normalization_factory import (
    NormalizationFactory, 
    NormalizationConfig
)
from src.ai_service.config.feature_flags import FeatureFlags


class TestGoldenParity:
    """Test golden parity between legacy and factory normalization."""
    
    @pytest.fixture(scope="class")
    def legacy_service(self):
        """Create legacy normalization service."""
        return NormalizationService()
    
    @pytest.fixture(scope="class")
    def factory_service(self):
        """Create factory normalization service."""
        return NormalizationFactory()
    
    @pytest.fixture(scope="class")
    def golden_cases(self):
        """Load golden test cases."""
        return self._load_golden_cases()
    
    def _load_golden_cases(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load golden test cases from file."""
        golden_file = Path(__file__).parent / "golden_cases.json"
        
        if not golden_file.exists():
            # Create default golden cases if file doesn't exist
            return self._create_default_golden_cases()
        
        try:
            with open(golden_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            pytest.skip(f"Could not load golden cases: {e}")
    
    def _create_default_golden_cases(self) -> Dict[str, List[Dict[str, Any]]]:
        """Create default golden test cases."""
        return {
            "ru": [
                {"input": "Иван Петров", "expected": "Иван Петров"},
                {"input": "Анна Сидорова", "expected": "Анна Сидорова"},
                {"input": "Владимир Иванович", "expected": "Владимир Иванович"},
                {"input": "Екатерина Петровна", "expected": "Екатерина Петровна"},
                {"input": "А. Б. Сидоров", "expected": "А. Б. Сидоров"},
                {"input": "И. П. Козлов", "expected": "И. П. Козлов"},
                {"input": "Мария-Анна Петрова", "expected": "Мария-Анна Петрова"},
                {"input": "О'Коннор", "expected": "О'Коннор"},
            ],
            "uk": [
                {"input": "Олександр Коваленко", "expected": "Олександр Коваленко"},
                {"input": "Наталія Шевченко", "expected": "Наталія Шевченко"},
                {"input": "Михайло Іванович", "expected": "Михайло Іванович"},
                {"input": "Оксана Петрівна", "expected": "Оксана Петрівна"},
                {"input": "А. Б. Коваленко", "expected": "А. Б. Коваленко"},
                {"input": "І. П. Шевченко", "expected": "І. П. Шевченко"},
                {"input": "Марія-Оксана Коваленко", "expected": "Марія-Оксана Коваленко"},
                {"input": "О'Коннор", "expected": "О'Коннор"},
            ],
            "en": [
                {"input": "John Smith", "expected": "John Smith"},
                {"input": "Jane Doe", "expected": "Jane Doe"},
                {"input": "Dr. Robert Johnson", "expected": "Dr. Robert Johnson"},
                {"input": "Mary O'Connor", "expected": "Mary O'Connor"},
                {"input": "A. B. Smith", "expected": "A. B. Smith"},
                {"input": "J. P. Doe", "expected": "J. P. Doe"},
                {"input": "Mary-Jane Smith", "expected": "Mary-Jane Smith"},
                {"input": "Jean-Pierre Dubois", "expected": "Jean-Pierre Dubois"},
            ]
        }
    
    @pytest.mark.asyncio
    async def test_ru_parity(self, legacy_service, factory_service, golden_cases):
        """Test Russian parity between legacy and factory."""
        ru_cases = golden_cases.get("ru", [])
        
        if not ru_cases:
            pytest.skip("No Russian golden cases available")
        
        results = []
        
        for case in ru_cases:
            input_text = case["input"]
            expected = case["expected"]
            
            # Test legacy normalization
            legacy_result = await legacy_service.normalize_async(
                input_text,
                language="ru",
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True
            )
            
            # Test factory normalization with all flags enabled
            factory_config = NormalizationConfig(
                language="ru",
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True,
                enable_spacy_ner=True,
                enable_nameparser_en=True,
                strict_stopwords=True,
                fsm_tuned_roles=True,
                enhanced_diminutives=True,
                enhanced_gender_rules=True,
                enable_ac_tier0=True,
                enable_vector_fallback=True,
                ascii_fastpath=True
            )
            
            factory_flags = FeatureFlags(
                enable_spacy_ner=True,
                enable_nameparser_en=True,
                strict_stopwords=True,
                fsm_tuned_roles=True,
                enhanced_diminutives=True,
                enhanced_gender_rules=True,
                enable_ac_tier0=True,
                enable_vector_fallback=True,
                ascii_fastpath=True
            )
            
            factory_result = await factory_service.normalize_text(
                input_text, factory_config, factory_flags
            )
            
            # Compare results
            legacy_normalized = legacy_result.normalized if hasattr(legacy_result, 'normalized') else str(legacy_result)
            factory_normalized = factory_result.normalized
            
            results.append({
                "input": input_text,
                "expected": expected,
                "legacy": legacy_normalized,
                "factory": factory_normalized,
                "match": legacy_normalized == factory_normalized
            })
        
        # Calculate success rate
        total = len(results)
        passed = sum(1 for r in results if r["match"])
        success_rate = passed / total if total > 0 else 0.0
        
        # Store results for reporting
        self._store_parity_results("ru", total, passed, success_rate, results)
        
        # Assert minimum success rate
        assert success_rate >= 0.9, f"Russian parity failed: {passed}/{total} ({success_rate:.1%}) < 90%"
    
    @pytest.mark.asyncio
    async def test_uk_parity(self, legacy_service, factory_service, golden_cases):
        """Test Ukrainian parity between legacy and factory."""
        uk_cases = golden_cases.get("uk", [])
        
        if not uk_cases:
            pytest.skip("No Ukrainian golden cases available")
        
        results = []
        
        for case in uk_cases:
            input_text = case["input"]
            expected = case["expected"]
            
            # Test legacy normalization
            legacy_result = await legacy_service.normalize_async(
                input_text,
                language="uk",
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True
            )
            
            # Test factory normalization with all flags enabled
            factory_config = NormalizationConfig(
                language="uk",
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True,
                enable_spacy_ner=True,
                enable_nameparser_en=True,
                strict_stopwords=True,
                fsm_tuned_roles=True,
                enhanced_diminutives=True,
                enhanced_gender_rules=True,
                enable_ac_tier0=True,
                enable_vector_fallback=True,
                ascii_fastpath=True
            )
            
            factory_flags = FeatureFlags(
                enable_spacy_ner=True,
                enable_nameparser_en=True,
                strict_stopwords=True,
                fsm_tuned_roles=True,
                enhanced_diminutives=True,
                enhanced_gender_rules=True,
                enable_ac_tier0=True,
                enable_vector_fallback=True,
                ascii_fastpath=True
            )
            
            factory_result = await factory_service.normalize_text(
                input_text, factory_config, factory_flags
            )
            
            # Compare results
            legacy_normalized = legacy_result.normalized if hasattr(legacy_result, 'normalized') else str(legacy_result)
            factory_normalized = factory_result.normalized
            
            results.append({
                "input": input_text,
                "expected": expected,
                "legacy": legacy_normalized,
                "factory": factory_normalized,
                "match": legacy_normalized == factory_normalized
            })
        
        # Calculate success rate
        total = len(results)
        passed = sum(1 for r in results if r["match"])
        success_rate = passed / total if total > 0 else 0.0
        
        # Store results for reporting
        self._store_parity_results("uk", total, passed, success_rate, results)
        
        # Assert minimum success rate
        assert success_rate >= 0.9, f"Ukrainian parity failed: {passed}/{total} ({success_rate:.1%}) < 90%"
    
    @pytest.mark.asyncio
    async def test_en_parity(self, legacy_service, factory_service, golden_cases):
        """Test English parity between legacy and factory."""
        en_cases = golden_cases.get("en", [])
        
        if not en_cases:
            pytest.skip("No English golden cases available")
        
        results = []
        
        for case in en_cases:
            input_text = case["input"]
            expected = case["expected"]
            
            # Test legacy normalization
            legacy_result = await legacy_service.normalize_async(
                input_text,
                language="en",
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True
            )
            
            # Test factory normalization with all flags enabled
            factory_config = NormalizationConfig(
                language="en",
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True,
                enable_spacy_ner=True,
                enable_nameparser_en=True,
                strict_stopwords=True,
                fsm_tuned_roles=True,
                enhanced_diminutives=True,
                enhanced_gender_rules=True,
                enable_ac_tier0=True,
                enable_vector_fallback=True,
                ascii_fastpath=True
            )
            
            factory_flags = FeatureFlags(
                enable_spacy_ner=True,
                enable_nameparser_en=True,
                strict_stopwords=True,
                fsm_tuned_roles=True,
                enhanced_diminutives=True,
                enhanced_gender_rules=True,
                enable_ac_tier0=True,
                enable_vector_fallback=True,
                ascii_fastpath=True
            )
            
            factory_result = await factory_service.normalize_text(
                input_text, factory_config, factory_flags
            )
            
            # Compare results
            legacy_normalized = legacy_result.normalized if hasattr(legacy_result, 'normalized') else str(legacy_result)
            factory_normalized = factory_result.normalized
            
            results.append({
                "input": input_text,
                "expected": expected,
                "legacy": legacy_normalized,
                "factory": factory_normalized,
                "match": legacy_normalized == factory_normalized
            })
        
        # Calculate success rate
        total = len(results)
        passed = sum(1 for r in results if r["match"])
        success_rate = passed / total if total > 0 else 0.0
        
        # Store results for reporting
        self._store_parity_results("en", total, passed, success_rate, results)
        
        # Assert minimum success rate
        assert success_rate >= 0.9, f"English parity failed: {passed}/{total} ({success_rate:.1%}) < 90%"
    
    def _store_parity_results(self, language: str, total: int, passed: int, success_rate: float, results: List[Dict[str, Any]]):
        """Store parity results for reporting."""
        # This would typically store results in a global variable or file
        # For now, we'll just print them
        print(f"\n{language.upper()} Parity Results:")
        print(f"  Total: {total}")
        print(f"  Passed: {passed}")
        print(f"  Failed: {total - passed}")
        print(f"  Success Rate: {success_rate:.1%}")
        
        # Print failed cases
        failed_cases = [r for r in results if not r["match"]]
        if failed_cases:
            print(f"  Failed Cases:")
            for case in failed_cases:
                print(f"    Input: '{case['input']}'")
                print(f"    Legacy: '{case['legacy']}'")
                print(f"    Factory: '{case['factory']}'")
                print(f"    Expected: '{case['expected']}'")
                print()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

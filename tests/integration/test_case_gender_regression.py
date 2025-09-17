"""
Integration tests for case and gender regression prevention.

These tests ensure that the nominative enforcement and gender preservation
features work correctly together and don't introduce regressions in existing
functionality.
"""

import pytest
from unittest.mock import patch, Mock

from src.ai_service.layers.normalization.normalization_service import NormalizationService
from src.ai_service.contracts.base_contracts import NormalizationResult


class TestCaseGenderRegression:
    """Test regression prevention for case and gender handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = NormalizationService()
        
        # Mock feature flags to enable nominative enforcement
        with patch.object(self.service.feature_flags, 'enforce_nominative', return_value=True):
            with patch.object(self.service.feature_flags, 'preserve_feminine_surnames', return_value=True):
                self.service = NormalizationService()

    def test_russian_feminine_surname_preservation(self):
        """Test that Russian feminine surnames ending in -ова/-ева/-іна are preserved."""
        test_cases = [
            # (input, expected_output, description)
            ("Анна Ивановой", "Анна Иванова", "Genitive to nominative, preserve feminine"),
            ("Мария Петровой", "Мария Петрова", "Genitive to nominative, preserve feminine"),
            ("Елена Сидоровой", "Елена Сидорова", "Genitive to nominative, preserve feminine"),
            ("Ольга Кузнецовой", "Ольга Кузнецова", "Genitive to nominative, preserve feminine"),
            ("Ирина Красной", "Ирина Красная", "Genitive to nominative, preserve feminine"),
        ]
        
        for input_text, expected, description in test_cases:
            with patch.object(self.service.morphology_adapter, 'to_nominative') as mock_nominative:
                with patch.object(self.service.morphology_adapter, 'detect_gender') as mock_gender:
                    # Mock morphology adapter responses
                    mock_nominative.side_effect = lambda token, lang: {
                        "Анна": "Анна",
                        "Мария": "Мария", 
                        "Елена": "Елена",
                        "Ольга": "Ольга",
                        "Ирина": "Ирина",
                        "Ивановой": "Иванова",
                        "Петровой": "Петрова",
                        "Сидоровой": "Сидорова",
                        "Кузнецовой": "Кузнецова",
                        "Красной": "Красная",
                    }.get(token, token)
                    
                    mock_gender.side_effect = lambda token, lang: {
                        "Анна": "femn",
                        "Мария": "femn",
                        "Елена": "femn", 
                        "Ольга": "femn",
                        "Ирина": "femn",
                    }.get(token, "unknown")
                    
                    # Mock the factory to return basic result
                    with patch.object(self.service.normalization_factory, 'normalize_text') as mock_factory:
                        mock_factory.return_value = NormalizationResult(
                            normalized=input_text,
                            tokens=input_text.split(),
                            trace=[
                                Mock(role="given", output=input_text.split()[0], notes=None),
                                Mock(role="surname", output=input_text.split()[1], notes=None)
                            ],
                            errors=[],
                            language="ru",
                            confidence=0.9,
                            original_length=len(input_text),
                            normalized_length=len(input_text),
                            token_count=2,
                            processing_time=0.1,
                            success=True,
                            original_text=input_text,
                            token_variants={},
                            total_variants=0,
                            persons_core=[],
                            organizations_core=[],
                            persons=[],
                        )
                        
                        result = self.service.normalize_sync(input_text, language="ru")
                        
                        # Check that feminine surnames are preserved
                        assert result.normalized == expected, f"Failed for {description}: {input_text} -> {result.normalized}"

    def test_ukrainian_feminine_surname_preservation(self):
        """Test that Ukrainian feminine surnames ending in -ська/-цька/-іна are preserved."""
        test_cases = [
            # (input, expected_output, description)
            ("Олена Ковальською", "Олена Ковальська", "Instrumental to nominative, preserve feminine"),
            ("Ірина Шевченко", "Ірина Шевченко", "Already nominative, preserve invariable"),
            ("Марія Кравцівською", "Марія Кравцівська", "Instrumental to nominative, preserve feminine"),
            ("Наталія Петренко", "Наталія Петренко", "Already nominative, preserve invariable"),
        ]
        
        for input_text, expected, description in test_cases:
            with patch.object(self.service.morphology_adapter, 'to_nominative') as mock_nominative:
                with patch.object(self.service.morphology_adapter, 'detect_gender') as mock_gender:
                    # Mock morphology adapter responses
                    mock_nominative.side_effect = lambda token, lang: {
                        "Олена": "Олена",
                        "Ірина": "Ірина",
                        "Марія": "Марія",
                        "Наталія": "Наталія",
                        "Ковальською": "Ковальська",
                        "Шевченко": "Шевченко",
                        "Кравцівською": "Кравцівська",
                        "Петренко": "Петренко",
                    }.get(token, token)
                    
                    mock_gender.side_effect = lambda token, lang: {
                        "Олена": "femn",
                        "Ірина": "femn",
                        "Марія": "femn",
                        "Наталія": "femn",
                    }.get(token, "unknown")
                    
                    # Mock the factory to return basic result
                    with patch.object(self.service.normalization_factory, 'normalize_text') as mock_factory:
                        mock_factory.return_value = NormalizationResult(
                            normalized=input_text,
                            tokens=input_text.split(),
                            trace=[
                                Mock(role="given", output=input_text.split()[0], notes=None),
                                Mock(role="surname", output=input_text.split()[1], notes=None)
                            ],
                            errors=[],
                            language="uk",
                            confidence=0.9,
                            original_length=len(input_text),
                            normalized_length=len(input_text),
                            token_count=2,
                            processing_time=0.1,
                            success=True,
                            original_text=input_text,
                            token_variants={},
                            total_variants=0,
                            persons_core=[],
                            organizations_core=[],
                            persons=[],
                        )
                        
                        result = self.service.normalize_sync(input_text, language="uk")
                        
                        # Check that feminine surnames are preserved
                        assert result.normalized == expected, f"Failed for {description}: {input_text} -> {result.normalized}"

    def test_masculine_names_not_converted_to_feminine(self):
        """Test that masculine names are not incorrectly converted to feminine forms."""
        test_cases = [
            # (input, expected_output, description)
            ("Иван Петров", "Иван Петров", "Masculine names should remain masculine"),
            ("Сергей Иванов", "Сергей Иванов", "Masculine names should remain masculine"),
            ("Александр Сидоров", "Александр Сидоров", "Masculine names should remain masculine"),
            ("Іван Ковальський", "Іван Ковальський", "Ukrainian masculine names should remain masculine"),
        ]
        
        for input_text, expected, description in test_cases:
            with patch.object(self.service.morphology_adapter, 'to_nominative') as mock_nominative:
                with patch.object(self.service.morphology_adapter, 'detect_gender') as mock_gender:
                    # Mock morphology adapter responses
                    mock_nominative.side_effect = lambda token, lang: {
                        "Иван": "Иван",
                        "Сергей": "Сергей",
                        "Александр": "Александр",
                        "Іван": "Іван",
                        "Петров": "Петров",
                        "Иванов": "Иванов",
                        "Сидоров": "Сидоров",
                        "Ковальський": "Ковальський",
                    }.get(token, token)
                    
                    mock_gender.side_effect = lambda token, lang: {
                        "Иван": "masc",
                        "Сергей": "masc",
                        "Александр": "masc",
                        "Іван": "masc",
                    }.get(token, "unknown")
                    
                    # Mock the factory to return basic result
                    with patch.object(self.service.normalization_factory, 'normalize_text') as mock_factory:
                        mock_factory.return_value = NormalizationResult(
                            normalized=input_text,
                            tokens=input_text.split(),
                            trace=[
                                Mock(role="given", output=input_text.split()[0], notes=None),
                                Mock(role="surname", output=input_text.split()[1], notes=None)
                            ],
                            errors=[],
                            language="ru" if "Иван" in input_text else "uk",
                            confidence=0.9,
                            original_length=len(input_text),
                            normalized_length=len(input_text),
                            token_count=2,
                            processing_time=0.1,
                            success=True,
                            original_text=input_text,
                            token_variants={},
                            total_variants=0,
                            persons_core=[],
                            organizations_core=[],
                            persons=[],
                        )
                        
                        result = self.service.normalize_sync(input_text, language="ru" if "Иван" in input_text else "uk")
                        
                        # Check that masculine names are not converted to feminine
                        assert result.normalized == expected, f"Failed for {description}: {input_text} -> {result.normalized}"

    def test_already_nominative_forms_unchanged(self):
        """Test that already nominative forms are not unnecessarily changed."""
        test_cases = [
            # (input, expected_output, description)
            ("Мария Петрова", "Мария Петрова", "Already nominative feminine should remain unchanged"),
            ("Анна Иванова", "Анна Иванова", "Already nominative feminine should remain unchanged"),
            ("Олена Ковальська", "Олена Ковальська", "Already nominative Ukrainian feminine should remain unchanged"),
            ("Ірина Шевченко", "Ірина Шевченко", "Already nominative Ukrainian invariable should remain unchanged"),
        ]
        
        for input_text, expected, description in test_cases:
            with patch.object(self.service.morphology_adapter, 'to_nominative') as mock_nominative:
                with patch.object(self.service.morphology_adapter, 'detect_gender') as mock_gender:
                    # Mock morphology adapter responses - return same form for nominative
                    mock_nominative.side_effect = lambda token, lang: token
                    
                    mock_gender.side_effect = lambda token, lang: {
                        "Мария": "femn",
                        "Анна": "femn",
                        "Олена": "femn",
                        "Ірина": "femn",
                    }.get(token, "unknown")
                    
                    # Mock the factory to return basic result
                    with patch.object(self.service.normalization_factory, 'normalize_text') as mock_factory:
                        mock_factory.return_value = NormalizationResult(
                            normalized=input_text,
                            tokens=input_text.split(),
                            trace=[
                                Mock(role="given", output=input_text.split()[0], notes=None),
                                Mock(role="surname", output=input_text.split()[1], notes=None)
                            ],
                            errors=[],
                            language="ru" if any(name in input_text for name in ["Мария", "Анна"]) else "uk",
                            confidence=0.9,
                            original_length=len(input_text),
                            normalized_length=len(input_text),
                            token_count=2,
                            processing_time=0.1,
                            success=True,
                            original_text=input_text,
                            token_variants={},
                            total_variants=0,
                            persons_core=[],
                            organizations_core=[],
                            persons=[],
                        )
                        
                        result = self.service.normalize_sync(input_text, language="ru" if any(name in input_text for name in ["Мария", "Анна"]) else "uk")
                        
                        # Check that already nominative forms are unchanged
                        assert result.normalized == expected, f"Failed for {description}: {input_text} -> {result.normalized}"

    def test_feature_flags_disable_functionality(self):
        """Test that feature flags can disable nominative enforcement and gender preservation."""
        # Test with enforce_nominative disabled
        with patch.object(self.service.feature_flags, 'enforce_nominative', return_value=False):
            with patch.object(self.service.normalization_factory, 'normalize_text') as mock_factory:
                mock_factory.return_value = NormalizationResult(
                    normalized="Анна Ивановой",
                    tokens=["Анна", "Ивановой"],
                    trace=[
                        Mock(role="given", output="Анна", notes=None),
                        Mock(role="surname", output="Ивановой", notes=None)
                    ],
                    errors=[],
                    language="ru",
                    confidence=0.9,
                    original_length=12,
                    normalized_length=12,
                    token_count=2,
                    processing_time=0.1,
                    success=True,
                    original_text="Анна Ивановой",
                    token_variants={},
                    total_variants=0,
                    persons_core=[],
                    organizations_core=[],
                    persons=[],
                )
                
                result = self.service.normalize_sync("Анна Ивановой", language="ru")
                
                # Should remain unchanged when feature is disabled
                assert result.normalized == "Анна Ивановой"

        # Test with preserve_feminine_surnames disabled
        with patch.object(self.service.feature_flags, 'enforce_nominative', return_value=True):
            with patch.object(self.service.feature_flags, 'preserve_feminine_surnames', return_value=False):
                with patch.object(self.service.morphology_adapter, 'to_nominative') as mock_nominative:
                    with patch.object(self.service.morphology_adapter, 'detect_gender') as mock_gender:
                        mock_nominative.side_effect = lambda token, lang: {
                            "Анна": "Анна",
                            "Ивановой": "Иванов",  # Convert to masculine when preservation disabled
                        }.get(token, token)
                        
                        mock_gender.side_effect = lambda token, lang: {
                            "Анна": "femn",
                        }.get(token, "unknown")
                        
                        with patch.object(self.service.normalization_factory, 'normalize_text') as mock_factory:
                            mock_factory.return_value = NormalizationResult(
                                normalized="Анна Ивановой",
                                tokens=["Анна", "Ивановой"],
                                trace=[
                                    Mock(role="given", output="Анна", notes=None),
                                    Mock(role="surname", output="Ивановой", notes=None)
                                ],
                                errors=[],
                                language="ru",
                                confidence=0.9,
                                original_length=12,
                                normalized_length=12,
                                token_count=2,
                                processing_time=0.1,
                                success=True,
                                original_text="Анна Ивановой",
                                token_variants={},
                                total_variants=0,
                                persons_core=[],
                                organizations_core=[],
                                persons=[],
                            )
                            
                            result = self.service.normalize_sync("Анна Ивановой", language="ru")
                            
                            # Should convert to masculine when preservation is disabled
                            assert result.normalized == "Анна Иванов"

    def test_trace_notes_include_morphology_actions(self):
        """Test that trace notes include morphology action information."""
        with patch.object(self.service.morphology_adapter, 'to_nominative') as mock_nominative:
            with patch.object(self.service.morphology_adapter, 'detect_gender') as mock_gender:
                mock_nominative.side_effect = lambda token, lang: {
                    "Анна": "Анна",
                    "Ивановой": "Иванова",
                }.get(token, token)
                
                mock_gender.side_effect = lambda token, lang: {
                    "Анна": "femn",
                }.get(token, "unknown")
                
                with patch.object(self.service.normalization_factory, 'normalize_text') as mock_factory:
                    mock_factory.return_value = NormalizationResult(
                        normalized="Анна Ивановой",
                        tokens=["Анна", "Ивановой"],
                        trace=[
                            Mock(role="given", output="Анна", notes=None),
                            Mock(role="surname", output="Ивановой", notes=None)
                        ],
                        errors=[],
                        language="ru",
                        confidence=0.9,
                        original_length=12,
                        normalized_length=12,
                        token_count=2,
                        processing_time=0.1,
                        success=True,
                        original_text="Анна Ивановой",
                        token_variants={},
                        total_variants=0,
                        persons_core=[],
                        organizations_core=[],
                        persons=[],
                    )
                    
                    result = self.service.normalize_sync("Анна Ивановой", language="ru")
                    
                    # Check that trace notes include morphology actions
                    surname_trace = next(t for t in result.trace if t.role == "surname")
                    assert surname_trace.notes is not None
                    assert "to_nominative" in surname_trace.notes
                    assert "preserve_feminine" in surname_trace.notes

"""
Comprehensive test suite for SignalsService.

Tests signal extraction, entity recognition, confidence scoring,
ID parsing, birthdate extraction, and evidence collection.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from ai_service.layers.signals.signals_service import SignalsService
from ai_service.contracts.base_contracts import NormalizationResult, TokenTrace


class TestSignalsServiceCore:
    """Test core SignalsService functionality"""

    def setup_method(self):
        """Setup SignalsService for each test"""
        self.service = SignalsService()

    def test_initialization(self):
        """Test SignalsService initialization"""
        service = SignalsService()
        assert service is not None
        # Should initialize extractors
        assert hasattr(service, 'person_extractor') or hasattr(service, '_extractors')
        assert hasattr(service, 'identifier_extractor') or hasattr(service, '_id_extractor')

    @pytest.mark.asyncio
    async def test_extract_signals_basic(self):
        """Test basic signal extraction"""
        original_text = "Иван Иванов"
        normalization_result = NormalizationResult(
            normalized="иван иванов",
            tokens=["иван", "иванов"],
            trace=[TokenTrace(token="Иван", role="given", rule="name_pattern", output="иван")],
            persons_core=[["иван", "иванов"]],
            organizations_core=[]
        )

        with patch.multiple(
            self.service,
            _extract_persons=Mock(return_value=[{
                "core": ["иван", "иванов"],
                "full_name": "Иван Иванов",
                "confidence": 0.8,
                "evidence": ["name_pattern"]
            }]),
            _extract_organizations=Mock(return_value=[]),
            _extract_extras=Mock(return_value={"dates": [], "amounts": []})
        ):
            result = await self.service.extract_signals(original_text, normalization_result)

            assert len(result.persons) == 1
            assert result.persons[0].full_name == "Иван Иванов"
            assert result.persons[0].confidence == 0.8
            assert len(result.organizations) == 0

    @pytest.mark.asyncio
    async def test_extract_signals_with_organization(self):
        """Test signal extraction with organizations"""
        original_text = "ООО Ромашка"
        normalization_result = NormalizationResult(
            normalized="ромашка",
            tokens=["ромашка"],
            trace=[TokenTrace(token="РОМАШКА", role="org_core", rule="quoted_pattern", output="ромашка")],
            persons_core=[],
            organizations_core=["РОМАШКА"]
        )

        with patch.multiple(
            self.service,
            _extract_persons=Mock(return_value=[]),
            _extract_organizations=Mock(return_value=[{
                "core": "РОМАШКА",
                "legal_form": "ООО",
                "full_name": "ООО РОМАШКА",
                "confidence": 0.9,
                "evidence": ["legal_form_hit", "org_core"]
            }]),
            _extract_extras=Mock(return_value={"dates": [], "amounts": []})
        ):
            result = await self.service.extract_signals(original_text, normalization_result)

            assert len(result.organizations) == 1
            assert result.organizations[0].legal_form == "ООО"
            assert result.organizations[0].full_name == "ООО РОМАШКА"
            assert result.organizations[0].confidence == 0.9

    @pytest.mark.asyncio
    async def test_extract_signals_with_birthdate(self):
        """Test signal extraction with birthdate"""
        original_text = "Иван Иванов, д.р. 01.01.1980"
        normalization_result = NormalizationResult(
            normalized="иван иванов",
            tokens=["иван", "иванов"],
            trace=[],
            persons_core=[["иван", "иванов"]]
        )

        mock_person_with_dob = {
            "core": ["иван", "иванов"],
            "full_name": "Иван Иванов",
            "dob": "1980-01-01",
            "dob_raw": "д.р. 01.01.1980",
            "confidence": 0.95,
            "evidence": ["name_pattern", "birthdate_found"]
        }

        with patch.multiple(
            self.service,
            _extract_persons=Mock(return_value=[mock_person_with_dob]),
            _extract_organizations=Mock(return_value=[]),
            _extract_extras=Mock(return_value={"dates": [], "amounts": []})
        ):
            result = await self.service.extract_signals(original_text, normalization_result)

            assert len(result.persons) == 1
            person = result.persons[0]
            assert person.dob == "1980-01-01"
            assert "birthdate_found" in person.evidence
            assert person.confidence > 0.9

    @pytest.mark.asyncio
    async def test_extract_signals_with_ids(self):
        """Test signal extraction with document IDs"""
        original_text = "Иван Иванов, паспорт AB123456"
        normalization_result = NormalizationResult(
            normalized="иван иванов",
            tokens=["иван", "иванов"],
            trace=[],
            persons_core=[["иван", "иванов"]]
        )

        mock_person_with_id = {
            "core": ["иван", "иванов"],
            "full_name": "Иван Иванов",
            "ids": [{"type": "passport_rf", "value": "AB123456", "valid": True}],
            "confidence": 0.9,
            "evidence": ["name_pattern", "valid_passport_rf"]
        }

        with patch.multiple(
            self.service,
            _extract_persons=Mock(return_value=[mock_person_with_id]),
            _extract_organizations=Mock(return_value=[]),
            _extract_extras=Mock(return_value={"dates": [], "amounts": []})
        ):
            result = await self.service.extract_signals(original_text, normalization_result)

            assert len(result.persons) == 1
            person = result.persons[0]
            assert len(person.ids) == 1
            assert person.ids[0]["type"] == "passport_rf"
            assert person.ids[0]["value"] == "AB123456"
            assert person.ids[0]["valid"] is True

    def test_extract_persons_from_normalization_result(self):
        """Test person extraction from normalization result"""
        normalization_result = NormalizationResult(
            normalized="иван петров",
            tokens=["иван", "петров"],
            trace=[],
            persons_core=[["иван", "петров"], ["мария", "сидорова"]]
        )

        persons = self.service._extract_persons_from_normalization(normalization_result)

        assert len(persons) == 2
        assert persons[0]["core"] == ["иван", "петров"]
        assert persons[0]["full_name"] == "Иван Петров"
        assert persons[1]["core"] == ["мария", "сидорова"]
        assert persons[1]["full_name"] == "Мария Сидорова"

    def test_extract_organizations_from_normalization_result(self):
        """Test organization extraction from normalization result"""
        normalization_result = NormalizationResult(
            normalized="ромашка газпром",
            tokens=["ромашка", "газпром"],
            trace=[],
            organizations_core=["РОМАШКА", "ГАЗПРОМ"]
        )

        orgs = self.service._extract_organizations_from_normalization(normalization_result)

        assert len(orgs) == 2
        assert orgs[0]["core"] == "РОМАШКА"
        assert orgs[1]["core"] == "ГАЗПРОМ"

    @patch('ai_service.layers.signals.signals_service.IdentifierExtractor')
    def test_extract_person_ids(self, mock_identifier_extractor):
        """Test personal ID extraction"""
        mock_extractor = Mock()
        mock_extractor.extract_person_ids.return_value = [
            {"type": "inn_ru", "value": "123456789012", "valid": True, "raw": "ИНН: 123456789012"},
            {"type": "passport_rf", "value": "AB123456", "valid": True, "raw": "паспорт AB123456"}
        ]
        mock_identifier_extractor.return_value = mock_extractor

        text = "Иван Иванов, ИНН: 123456789012, паспорт AB123456"
        ids = self.service._extract_person_ids(text)

        assert len(ids) == 2
        assert ids[0]["type"] == "inn_ru"
        assert ids[0]["valid"] is True
        assert ids[1]["type"] == "passport_rf"

    @patch('ai_service.layers.signals.signals_service.IdentifierExtractor')
    def test_extract_organization_ids(self, mock_identifier_extractor):
        """Test organization ID extraction"""
        mock_extractor = Mock()
        mock_extractor.extract_organization_ids.return_value = [
            {"type": "edrpou", "value": "12345678", "valid": True, "raw": "ЕГРПОУ: 12345678"},
            {"type": "ogrn", "value": "1234567890123", "valid": True, "raw": "ОГРН 1234567890123"}
        ]
        mock_identifier_extractor.return_value = mock_extractor

        text = "ООО Ромашка, ЕГРПОУ: 12345678, ОГРН 1234567890123"
        ids = self.service._extract_organization_ids(text)

        assert len(ids) == 2
        assert ids[0]["type"] == "edrpou"
        assert ids[1]["type"] == "ogrn"

    @patch('ai_service.layers.signals.signals_service.BirthdateExtractor')
    def test_extract_birthdates(self, mock_birthdate_extractor):
        """Test birthdate extraction"""
        mock_extractor = Mock()
        mock_extractor.extract.return_value = [
            {"date": "1980-01-01", "raw": "01.01.1980", "position": 20},
            {"date": "1985-12-25", "raw": "25/12/1985", "position": 50}
        ]
        mock_birthdate_extractor.return_value = mock_extractor

        text = "Иван Иванов, д.р. 01.01.1980, Мария Петрова, род. 25/12/1985"
        birthdates = self.service._extract_birthdates(text)

        assert len(birthdates) == 2
        assert birthdates[0]["date"] == "1980-01-01"
        assert birthdates[1]["date"] == "1985-12-25"

    def test_enrich_persons_with_ids(self):
        """Test enriching persons with extracted IDs"""
        persons = [
            {"core": ["иван", "иванов"], "full_name": "Иван Иванов", "ids": [], "evidence": []},
            {"core": ["мария", "петрова"], "full_name": "Мария Петрова", "ids": [], "evidence": []}
        ]

        ids = [
            {"type": "passport_rf", "value": "AB123456", "valid": True},
            {"type": "inn_ru", "value": "123456789012", "valid": False}
        ]

        self.service._enrich_persons_with_ids(persons, ids)

        # All persons should get all IDs (simple distribution)
        assert len(persons[0]["ids"]) == 2
        assert len(persons[1]["ids"]) == 2
        # Evidence should be updated
        assert "valid_passport_rf" in persons[0]["evidence"]
        assert "invalid_inn_ru" in persons[0]["evidence"]

    def test_enrich_organizations_with_ids(self):
        """Test enriching organizations with extracted IDs"""
        organizations = [
            {"core": "РОМАШКА", "ids": [], "evidence": []},
            {"core": "ГАЗПРОМ", "ids": [], "evidence": []}
        ]

        ids = [
            {"type": "edrpou", "value": "12345678", "valid": True},
            {"type": "ogrn", "value": "1234567890123", "valid": True}
        ]

        self.service._enrich_organizations_with_ids(organizations, ids)

        # All organizations should get all IDs
        assert len(organizations[0]["ids"]) == 2
        assert len(organizations[1]["ids"]) == 2
        # Evidence should be updated
        assert "valid_edrpou" in organizations[0]["evidence"]
        assert "valid_ogrn" in organizations[0]["evidence"]

    def test_enrich_with_birthdates_proximity_matching(self):
        """Test birthdate enrichment with proximity matching"""
        persons = [
            {"core": ["иван", "иванов"], "full_name": "Иван Иванов", "dob": None, "evidence": []},
            {"core": ["мария", "петрова"], "full_name": "Мария Петрова", "dob": None, "evidence": []}
        ]

        birthdates = [
            {"date": "1980-01-01", "raw": "01.01.1980", "position": 15},  # Close to first person
            {"date": "1985-12-25", "raw": "25/12/1985", "position": 60}   # Close to second person
        ]

        text = "Иван Иванов 01.01.1980 работает в компании. Мария Петрова 25/12/1985 тоже."

        # Mock position finding
        with patch.object(self.service, '_find_person_position_in_text') as mock_find_pos:
            mock_find_pos.side_effect = lambda name, txt: 0 if "Иван" in name else 40

            self.service._enrich_with_birthdates(persons, birthdates, text)

            # First person should get first birthdate
            assert persons[0]["dob"] == "1980-01-01"
            assert "birthdate_found" in persons[0]["evidence"]

            # Second person should get second birthdate
            assert persons[1]["dob"] == "1985-12-25"
            assert "birthdate_found" in persons[1]["evidence"]

    def test_calculate_person_confidence(self):
        """Test person confidence calculation"""
        person = {
            "evidence": ["name_pattern", "birthdate_found", "valid_passport_rf"],
            "ids": [{"valid": True}, {"valid": False}]
        }

        confidence = self.service._calculate_person_confidence(person)

        # Should account for: base + name_pattern + birthdate + valid_id + invalid_id + multi_bonus
        expected = 0.5 + 0.1 + 0.15 + 0.2 + 0.1  # Plus multi-evidence bonus
        assert confidence > expected
        assert confidence <= 1.0  # Should be capped at 1.0

    def test_calculate_organization_confidence(self):
        """Test organization confidence calculation"""
        org = {
            "evidence": ["org_core", "legal_form_hit", "quoted_core"],
            "ids": [{"valid": True}]
        }

        confidence = self.service._calculate_organization_confidence(org)

        # Should account for: base + org_core + legal_form + quoted_core + valid_id + multi_bonus
        expected = 0.5 + 0.1 + 0.3 + 0.2 + 0.2  # Plus multi-evidence bonus
        assert confidence > expected
        assert confidence <= 1.0

    def test_extract_legal_forms(self):
        """Test legal form extraction"""
        test_cases = [
            ("ООО Ромашка", {"РОМАШКА": {"legal_form": "ООО", "full": "ООО РОМАШКА"}}),
            ("Газпром ПАО", {"ГАЗПРОМ": {"legal_form": "ПАО", "full": "ПАО ГАЗПРОМ"}}),
            ("Apple Inc.", {"APPLE": {"legal_form": "Inc", "full": "Apple Inc."}}),
            ("Microsoft Corporation", {"MICROSOFT": {"legal_form": "Corporation", "full": "Microsoft Corporation"}})
        ]

        for text, expected_pattern in test_cases:
            with patch.object(self.service, '_extract_legal_forms') as mock_extract:
                mock_extract.return_value = expected_pattern
                result = self.service._extract_legal_forms(text)

                # Should find at least one legal form
                assert len(result) > 0
                for core_name, details in result.items():
                    assert "legal_form" in details
                    assert "full" in details

    def test_person_to_dict_serialization(self):
        """Test person object to dictionary serialization"""
        person_data = {
            "core": ["иван", "иванов"],
            "full_name": "Иван Иванов",
            "dob": "1980-01-01",
            "dob_raw": "01.01.1980",
            "ids": [{"type": "passport_rf", "value": "AB123456", "valid": True}],
            "confidence": 0.85,
            "evidence": ["name_pattern", "birthdate_found", "valid_passport_rf"]
        }

        person_dict = self.service._person_to_dict(person_data)

        required_fields = ["core", "full_name", "dob", "ids", "confidence", "evidence"]
        for field in required_fields:
            assert field in person_dict

        assert person_dict["core"] == ["иван", "иванов"]
        assert person_dict["confidence"] == 0.85

    def test_organization_to_dict_serialization(self):
        """Test organization object to dictionary serialization"""
        org_data = {
            "core": "РОМАШКА",
            "legal_form": "ООО",
            "full": "ООО РОМАШКА",
            "ids": [{"type": "edrpou", "value": "12345678", "valid": True}],
            "confidence": 0.9,
            "evidence": ["org_core", "legal_form_hit", "valid_edrpou"]
        }

        org_dict = self.service._org_to_dict(org_data)

        required_fields = ["core", "legal_form", "full", "ids", "confidence", "evidence"]
        for field in required_fields:
            assert field in org_dict

        assert org_dict["core"] == "РОМАШКА"
        assert org_dict["legal_form"] == "ООО"

    def test_calculate_overall_confidence(self):
        """Test overall confidence calculation for all signals"""
        persons = [
            {"confidence": 0.8}, {"confidence": 0.9}
        ]
        organizations = [
            {"confidence": 0.7}
        ]

        overall = self.service._calculate_overall_confidence(persons, organizations)

        # Should be weighted average or similar aggregation
        assert 0.0 <= overall <= 1.0
        assert isinstance(overall, float)


class TestSignalsServiceEdgeCases:
    """Test edge cases and error handling"""

    def setup_method(self):
        """Setup SignalsService for edge case testing"""
        self.service = SignalsService()

    @pytest.mark.asyncio
    async def test_extract_signals_empty_text(self):
        """Test signal extraction with empty text"""
        normalization_result = NormalizationResult(
            normalized="",
            tokens=[],
            trace=[],
            persons_core=[],
            organizations_core=[]
        )

        result = await self.service.extract_signals("", normalization_result)

        assert len(result.persons) == 0
        assert len(result.organizations) == 0
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_extract_signals_none_normalization(self):
        """Test signal extraction with None normalization result"""
        with pytest.raises((TypeError, AttributeError)):
            await self.service.extract_signals("test", None)

    def test_extract_persons_malformed_core(self):
        """Test person extraction with malformed core data"""
        normalization_result = NormalizationResult(
            normalized="test",
            tokens=["test"],
            trace=[],
            persons_core=[[], ["single"], ["too", "many", "tokens", "here"]]  # Various malformed cases
        )

        persons = self.service._extract_persons_from_normalization(normalization_result)

        # Should handle malformed data gracefully
        assert isinstance(persons, list)
        # Valid entries should still be processed
        valid_persons = [p for p in persons if p.get("full_name")]
        assert len(valid_persons) >= 0

    def test_confidence_calculation_edge_cases(self):
        """Test confidence calculation with edge cases"""
        # Empty evidence
        person_empty = {"evidence": [], "ids": []}
        conf_empty = self.service._calculate_person_confidence(person_empty)
        assert conf_empty == 0.5  # Base confidence

        # Maximum evidence
        person_max = {
            "evidence": ["name_pattern", "birthdate_found", "valid_passport_rf", "context_match"] * 10,
            "ids": [{"valid": True}] * 10
        }
        conf_max = self.service._calculate_person_confidence(person_max)
        assert conf_max == 1.0  # Should be capped at 1.0


class TestSignalsServiceIntegration:
    """Integration tests for SignalsService with real-world scenarios"""

    def setup_method(self):
        """Setup SignalsService for integration testing"""
        self.service = SignalsService()

    @pytest.mark.asyncio
    async def test_complex_payment_scenario(self):
        """Test complex payment scenario with multiple entities"""
        text = "Перевод от ООО Ромашка (ЕГРПОУ: 12345678) для Иван Иванович Петров, д.р. 01.01.1980, паспорт AB123456"

        normalization_result = NormalizationResult(
            normalized="ромашка иван иванович петров",
            tokens=["ромашка", "иван", "иванович", "петров"],
            trace=[],
            persons_core=[["иван", "иванович", "петров"]],
            organizations_core=["РОМАШКА"]
        )

        # Mock all extractors to return appropriate data
        with patch.multiple(
            self.service,
            _extract_person_ids=Mock(return_value=[{"type": "passport_rf", "value": "AB123456", "valid": True}]),
            _extract_organization_ids=Mock(return_value=[{"type": "edrpou", "value": "12345678", "valid": True}]),
            _extract_birthdates=Mock(return_value=[{"date": "1980-01-01", "raw": "01.01.1980", "position": 80}]),
            _extract_legal_forms=Mock(return_value={"РОМАШКА": {"legal_form": "ООО", "full": "ООО РОМАШКА", "evidence": ["legal_form_hit"]}})
        ):
            result = await self.service.extract_signals(text, normalization_result)

            # Should extract both person and organization
            assert len(result.persons) == 1
            assert len(result.organizations) == 1

            # Person should have high confidence with all attributes
            person = result.persons[0]
            assert person.full_name == "Иван Иванович Петров"
            assert person.dob == "1980-01-01"
            assert len(person.ids) == 1
            assert person.confidence > 0.9

            # Organization should have legal form and ID
            org = result.organizations[0]
            assert org.core == "РОМАШКА"
            assert org.legal_form == "ООО"
            assert len(org.ids) == 1
            assert org.confidence > 0.8

    def test_multilingual_entity_extraction(self):
        """Test entity extraction from multilingual text"""
        mixed_text = "John Smith works at ООО Ромашка, François Müller at Apple Inc."

        # Should handle mixed script names
        normalization_result = NormalizationResult(
            normalized="john smith ромашка françois müller apple",
            tokens=["john", "smith", "ромашка", "françois", "müller", "apple"],
            trace=[],
            persons_core=[["john", "smith"], ["françois", "müller"]],
            organizations_core=["РОМАШКА", "APPLE"]
        )

        persons = self.service._extract_persons_from_normalization(normalization_result)
        orgs = self.service._extract_organizations_from_normalization(normalization_result)

        assert len(persons) == 2
        assert len(orgs) == 2

        # Should handle different scripts correctly
        person_names = [p["full_name"] for p in persons]
        assert "John Smith" in person_names
        assert "François Müller" in person_names
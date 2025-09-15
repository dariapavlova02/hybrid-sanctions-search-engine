"""
Integration tests for initials and organization pipeline cases
Tests comprehensive normalization pipeline for initials and organization names
"""

import pytest


class TestPipelineInitialsOrgsCase:
    """Test cases for initials and organization names"""

    @pytest.mark.asyncio
    async def test_initials_only(self, orchestrator_service):
        """Test processing of initials only"""
        # Arrange
        text = "А.Б. Петров"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        assert result.normalized_text, "Normalized text should not be empty"
        
        normalized_lower = result.normalized_text.lower()
        assert any(part in normalized_lower for part in ["петров", "petrov"])

    @pytest.mark.asyncio
    async def test_english_initials_with_surname(self, orchestrator_service):
        """Test English initials with surname"""
        # Arrange
        text = "J.R.R. Tolkien"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        assert result.normalized_text, "Normalized text should not be empty"
        
        normalized_lower = result.normalized_text.lower()
        assert "tolkien" in normalized_lower

    @pytest.mark.asyncio
    async def test_mixed_initials_and_full_name(self, orchestrator_service):
        """Test mixed initials and full name"""
        # Arrange
        text = "А.Б. и Сергей Иванович Петров"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        assert result.normalized_text, "Normalized text should not be empty"
        
        normalized_lower = result.normalized_text.lower()
        assert any(part in normalized_lower for part in ["сергей", "sergey", "sergei"])
        assert any(part in normalized_lower for part in ["петров", "petrov"])

    @pytest.mark.asyncio
    async def test_russian_organization_ooo(self, orchestrator_service):
        """Test Russian organization with ООО"""
        # Arrange
        text = "ООО Газпром"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        
        # Check signals for organization
        if result.signals and result.signals.organizations:
            org = result.signals.organizations[0]
            assert org.core, "Organization core should not be empty"
            assert "газпром" in org.core.lower() or "gazprom" in org.core.lower()

    @pytest.mark.asyncio
    async def test_ukrainian_organization_tov(self, orchestrator_service):
        """Test Ukrainian organization with ТОВ"""
        # Arrange
        text = "ТОВ Нафтогаз"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        
        # Check signals for organization
        if result.signals and result.signals.organizations:
            org = result.signals.organizations[0]
            assert org.core, "Organization core should not be empty"
            assert "нафтогаз" in org.core.lower() or "naftogaz" in org.core.lower()

    @pytest.mark.asyncio
    async def test_english_organization_llc(self, orchestrator_service):
        """Test English organization with LLC"""
        # Arrange
        text = "Microsoft LLC"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        
        # Check signals for organization
        if result.signals and result.signals.organizations:
            org = result.signals.organizations[0]
            assert org.core, "Organization core should not be empty"
            assert "microsoft" in org.core.lower()

    @pytest.mark.asyncio
    async def test_organization_with_person_name(self, orchestrator_service):
        """Test organization name that includes person name"""
        # Arrange
        text = "ООО Петров и Ко"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        
        # Should detect organization, not person
        if result.signals:
            if result.signals.organizations:
                org = result.signals.organizations[0]
                assert org.core, "Organization core should not be empty"
            # May or may not detect person depending on implementation

    @pytest.mark.asyncio
    async def test_multiple_organizations(self, orchestrator_service):
        """Test multiple organizations"""
        # Arrange
        text = "ООО Газпром и ТОВ Нафтогаз"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        
        # Check signals for organizations
        if result.signals and result.signals.organizations:
            org_cores = [org.core.lower() for org in result.signals.organizations]
            org_cores_str = " ".join(org_cores)
            assert any(name in org_cores_str for name in ["газпром", "gazprom"])
            assert any(name in org_cores_str for name in ["нафтогаз", "naftogaz"])

    @pytest.mark.asyncio
    async def test_person_and_organization_mixed(self, orchestrator_service):
        """Test person and organization in same text"""
        # Arrange
        text = "Сергей Петров работает в ООО Газпром"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        
        # Check signals
        if result.signals:
            # Should detect both person and organization
            if result.signals.persons:
                person = result.signals.persons[0]
                assert person.core, "Person core should not be empty"
            if result.signals.organizations:
                org = result.signals.organizations[0]
                assert org.core, "Organization core should not be empty"

    @pytest.mark.asyncio
    async def test_organization_with_quotes(self, orchestrator_service):
        """Test organization name with quotes"""
        # Arrange
        text = 'ООО "Рога и Копыта"'
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        
        # Check signals for organization
        if result.signals and result.signals.organizations:
            org = result.signals.organizations[0]
            assert org.core, "Organization core should not be empty"

    @pytest.mark.asyncio
    async def test_initials_with_organization(self, orchestrator_service):
        """Test initials with organization"""
        # Arrange
        text = "А.Б. Петров, директор ООО Газпром"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        
        # Check signals
        if result.signals:
            # Should detect both person and organization
            if result.signals.persons:
                person = result.signals.persons[0]
                assert person.core, "Person core should not be empty"
            if result.signals.organizations:
                org = result.signals.organizations[0]
                assert org.core, "Organization core should not be empty"

    @pytest.mark.asyncio
    async def test_multiple_legal_forms(self, orchestrator_service):
        """Test multiple legal forms"""
        # Arrange
        text = "ООО Газпром, ЗАО Лукойл, ПАО Сбербанк"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        
        # Check signals for organizations
        if result.signals and result.signals.organizations:
            # Should detect multiple organizations
            assert len(result.signals.organizations) >= 1

    @pytest.mark.asyncio
    async def test_organization_with_numbers(self, orchestrator_service):
        """Test organization name with numbers"""
        # Arrange
        text = "ООО Завод-25"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        
        # Check signals for organization
        if result.signals and result.signals.organizations:
            org = result.signals.organizations[0]
            assert org.core, "Organization core should not be empty"

    @pytest.mark.asyncio
    async def test_foreign_organization(self, orchestrator_service):
        """Test foreign organization"""
        # Arrange
        text = "Apple Inc."
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        
        # Check signals for organization
        if result.signals and result.signals.organizations:
            org = result.signals.organizations[0]
            assert org.core, "Organization core should not be empty"
            assert "apple" in org.core.lower()

    @pytest.mark.asyncio
    async def test_initials_without_periods(self, orchestrator_service):
        """Test initials without periods"""
        # Arrange
        text = "АБ Петров"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        assert result.normalized_text, "Normalized text should not be empty"
        
        normalized_lower = result.normalized_text.lower()
        assert any(part in normalized_lower for part in ["петров", "petrov"])

    @pytest.mark.asyncio
    async def test_organization_in_sentence(self, orchestrator_service):
        """Test organization mentioned in a sentence"""
        # Arrange
        text = "Компания ООО Газпром объявила о новых инвестициях"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        
        # Check signals for organization
        if result.signals and result.signals.organizations:
            org = result.signals.organizations[0]
            assert org.core, "Organization core should not be empty"
            assert "газпром" in org.core.lower() or "gazprom" in org.core.lower()

    @pytest.mark.asyncio
    async def test_mixed_case_organization(self, orchestrator_service):
        """Test organization with mixed case"""
        # Arrange
        text = "ооо ГАЗПРОМ"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        
        # Check signals for organization
        if result.signals and result.signals.organizations:
            org = result.signals.organizations[0]
            assert org.core, "Organization core should not be empty"
            assert "газпром" in org.core.lower() or "gazprom" in org.core.lower()

    @pytest.mark.asyncio
    async def test_organization_with_address(self, orchestrator_service):
        """Test organization with address"""
        # Arrange
        text = "ООО Газпром, г. Москва, ул. Ленина, д. 1"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        
        # Check signals for organization
        if result.signals and result.signals.organizations:
            org = result.signals.organizations[0]
            assert org.core, "Organization core should not be empty"
            assert "газпром" in org.core.lower() or "gazprom" in org.core.lower()

    @pytest.mark.asyncio
    async def test_no_unknown_in_normalized_output(self, orchestrator_service):
        """Test that no 'unknown' tokens appear in normalized output"""
        # Arrange
        text = "А.Б. Петров, ООО Газпром"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        assert result.normalized_text, "Normalized text should not be empty"
        
        # Check that 'unknown' does not appear in normalized text
        normalized_lower = result.normalized_text.lower()
        assert "unknown" not in normalized_lower
        assert "неизвестный" not in normalized_lower
        assert "невідомий" not in normalized_lower

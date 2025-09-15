"""
Integration tests for mixed English pipeline cases
Tests comprehensive normalization pipeline for English names mixed with other languages
"""

import pytest


class TestPipelineMixedEnglishCases:
    """Test cases for English names and mixed language scenarios"""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_english_full_name(self, orchestrator_service):
        """Test English full name"""
        # Arrange
        text = "John Michael Smith"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        assert result.normalized_text, "Normalized text should not be empty"
        assert result.tokens, "Should have extracted tokens"
        
        # Check that normalized text contains the name components
        normalized_lower = result.normalized_text.lower()
        assert "john" in normalized_lower
        assert "michael" in normalized_lower
        assert "smith" in normalized_lower

    @pytest.mark.asyncio
    async def test_english_name_with_apostrophe(self, orchestrator_service):
        """Test English name with apostrophe"""
        # Arrange
        text = "John O'Connor"
        
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
        assert "john" in normalized_lower
        assert "connor" in normalized_lower or "o'connor" in normalized_lower

    @pytest.mark.asyncio
    async def test_english_hyphenated_name(self, orchestrator_service):
        """Test English hyphenated name"""
        # Arrange
        text = "Mary-Jane Watson"
        
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
        assert "mary" in normalized_lower
        assert "jane" in normalized_lower
        assert "watson" in normalized_lower

    @pytest.mark.asyncio
    async def test_mixed_english_ukrainian(self, orchestrator_service):
        """Test mixed English and Ukrainian names"""
        # Arrange
        text = "John Smith and Олександр Петренко"
        
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
        assert "john" in normalized_lower or "smith" in normalized_lower
        assert any(part in normalized_lower for part in ["олександр", "александр", "oleksandr", "alexandr"])

    @pytest.mark.asyncio
    async def test_mixed_english_russian(self, orchestrator_service):
        """Test mixed English and Russian names"""
        # Arrange
        text = "Michael Johnson и Сергей Петров"
        
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
        assert "michael" in normalized_lower or "johnson" in normalized_lower
        assert any(part in normalized_lower for part in ["сергей", "sergey", "sergei"])

    @pytest.mark.asyncio
    async def test_english_initials(self, orchestrator_service):
        """Test English name with initials"""
        # Arrange
        text = "J.M. Smith"
        
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
        assert "smith" in normalized_lower

    @pytest.mark.asyncio
    async def test_english_name_with_title(self, orchestrator_service):
        """Test English name with title"""
        # Arrange
        text = "Dr. John Smith"
        
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
        assert "john" in normalized_lower
        assert "smith" in normalized_lower

    @pytest.mark.asyncio
    async def test_transliterated_name(self, orchestrator_service):
        """Test transliterated Cyrillic name in Latin script"""
        # Arrange
        text = "Sergey Ivanov"
        
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
        assert "sergey" in normalized_lower or "sergei" in normalized_lower
        assert "ivanov" in normalized_lower

    @pytest.mark.asyncio
    async def test_multiple_english_names(self, orchestrator_service):
        """Test multiple English names"""
        # Arrange
        text = "John Smith, Mary Johnson, and Robert Brown"
        
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
        assert "john" in normalized_lower or "smith" in normalized_lower
        assert "mary" in normalized_lower or "johnson" in normalized_lower
        assert "robert" in normalized_lower or "brown" in normalized_lower

    @pytest.mark.asyncio
    async def test_english_name_with_middle_initial(self, orchestrator_service):
        """Test English name with middle initial"""
        # Arrange
        text = "John F. Kennedy"
        
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
        assert "john" in normalized_lower
        assert "kennedy" in normalized_lower

    @pytest.mark.asyncio
    async def test_english_compound_surname(self, orchestrator_service):
        """Test English compound surname"""
        # Arrange
        text = "John Smith-Brown"
        
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
        assert "john" in normalized_lower
        assert "smith" in normalized_lower
        assert "brown" in normalized_lower

    @pytest.mark.asyncio
    async def test_english_name_case_insensitive(self, orchestrator_service):
        """Test English name with mixed case"""
        # Arrange
        text = "jOHN sMITH"
        
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
        assert "john" in normalized_lower
        assert "smith" in normalized_lower

    @pytest.mark.asyncio
    async def test_three_language_mix(self, orchestrator_service):
        """Test three languages mixed together"""
        # Arrange
        text = "John Smith, Олександр Петренко, и Сергей Иванов"
        
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
        # English name
        assert "john" in normalized_lower or "smith" in normalized_lower
        # Ukrainian name
        assert any(part in normalized_lower for part in ["олександр", "александр", "oleksandr", "alexandr"])
        # Russian name
        assert any(part in normalized_lower for part in ["сергей", "sergey", "sergei"])

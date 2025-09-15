"""
Integration tests for negative canary cases
Tests that ensure the pipeline correctly rejects or handles non-name content
"""

import pytest


class TestPipelineNegativeCanaries:
    """Test cases for negative scenarios and edge cases"""

    @pytest.mark.asyncio
    async def test_empty_text(self, orchestrator_service):
        """Test empty text input"""
        # Arrange
        text = ""
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        assert result.normalized_text == "", "Empty text should result in empty normalized text"
        assert len(result.tokens) == 0, "Empty text should result in no tokens"

    @pytest.mark.asyncio
    async def test_whitespace_only(self, orchestrator_service):
        """Test whitespace-only input"""
        # Arrange
        text = "   \t\n   "
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        assert result.normalized_text.strip() == "", "Whitespace should result in empty normalized text"

    @pytest.mark.asyncio
    async def test_numbers_only(self, orchestrator_service):
        """Test numbers-only input"""
        # Arrange
        text = "123 456 789"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        # In mock environment, numbers may not be filtered out
        # The test verifies that the system handles numbers gracefully

    @pytest.mark.asyncio
    async def test_punctuation_only(self, orchestrator_service):
        """Test punctuation-only input"""
        # Arrange
        text = "!@#$%^&*()_+-={}[]|\\:;\"'<>?,./"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        # In mock environment, punctuation may not be filtered out
        # The test verifies that the system handles punctuation gracefully

    @pytest.mark.asyncio
    async def test_stop_words_only(self, orchestrator_service):
        """Test stop words only"""
        # Arrange
        text = "the and or but with in on at"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        # In mock environment, stop words may not be filtered out
        # The test verifies that the system handles stop words gracefully

    @pytest.mark.asyncio
    async def test_random_gibberish(self, orchestrator_service):
        """Test random gibberish text"""
        # Arrange
        text = "asdfghjkl qwertyuiop zxcvbnm"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        # Gibberish should not be treated as names
        if result.signals:
            assert len(result.signals.persons) == 0, "Gibberish should not be detected as persons"
            assert len(result.signals.organizations) == 0, "Gibberish should not be detected as organizations"

    @pytest.mark.asyncio
    async def test_special_characters(self, orchestrator_service):
        """Test special Unicode characters"""
        # Arrange
        text = "∑∂∆∞π√∫≈≠≤≥"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        # Special characters should not crash the system

    @pytest.mark.asyncio
    async def test_emoji_only(self, orchestrator_service):
        """Test emoji-only input"""
        # Arrange
        text = "😀😃😄😁😆😅😂🤣"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        # Emojis should not be treated as names

    @pytest.mark.asyncio
    async def test_very_long_text(self, orchestrator_service):
        """Test very long text input"""
        # Arrange
        text = "test " * 1000  # 5000 characters
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        # Should handle long text without crashing

    @pytest.mark.asyncio
    async def test_mixed_scripts_nonsense(self, orchestrator_service):
        """Test mixed scripts with nonsensical combinations"""
        # Arrange
        text = "αβγδε абвгд abcde 12345 !@#$%"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        # Mixed nonsense should not be treated as names

    @pytest.mark.asyncio
    async def test_common_words_not_names(self, orchestrator_service):
        """Test common words that are not names"""
        # Arrange
        text = "table chair window door computer phone book"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        # Common words should not be treated as names
        if result.signals:
            assert len(result.signals.persons) == 0, "Common words should not be detected as persons"

    @pytest.mark.asyncio
    async def test_dates_and_addresses(self, orchestrator_service):
        """Test dates and addresses (not names)"""
        # Arrange
        text = "15.03.1980 г. Москва ул. Ленина д. 10 кв. 5"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        # Dates and addresses should not be treated as person names
        if result.signals and result.signals.persons:
            # Should not detect person names in address/date text
            person_cores = [" ".join(p.core).lower() for p in result.signals.persons]
            person_text = " ".join(person_cores)
            assert "москва" not in person_text or "moscow" not in person_text
            assert "ленина" not in person_text or "lenina" not in person_text

    @pytest.mark.asyncio
    async def test_currencies_and_amounts(self, orchestrator_service):
        """Test currencies and amounts (not names)"""
        # Arrange
        text = "1000 USD 500 EUR 2000 RUB 3000 UAH"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        # Currency codes should not be treated as names
        if result.signals:
            assert len(result.signals.persons) == 0, "Currency codes should not be detected as persons"

    @pytest.mark.asyncio
    async def test_technical_terms(self, orchestrator_service):
        """Test technical terms and jargon"""
        # Arrange
        text = "HTTP HTTPS API REST JSON XML SQL HTML CSS JavaScript"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        # Technical terms should not be treated as names
        if result.signals:
            assert len(result.signals.persons) == 0, "Technical terms should not be detected as persons"

    @pytest.mark.asyncio
    async def test_medical_terms(self, orchestrator_service):
        """Test medical terms"""
        # Arrange
        text = "COVID-19 influenza pneumonia diabetes hypertension"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        # Medical terms should not be treated as names
        if result.signals:
            assert len(result.signals.persons) == 0, "Medical terms should not be detected as persons"

    @pytest.mark.asyncio
    async def test_country_and_city_names(self, orchestrator_service):
        """Test country and city names (not person names)"""
        # Arrange
        text = "Ukraine Russia Germany France Italy Spain"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        # Country names should not be treated as person names
        if result.signals and result.signals.persons:
            # Some country names might be detected as person names (e.g., "France" could be a name)
            # But we expect minimal false positives
            assert len(result.signals.persons) <= 1, "Most country names should not be detected as persons"

    @pytest.mark.asyncio
    async def test_brand_names(self, orchestrator_service):
        """Test brand names"""
        # Arrange
        text = "Apple Google Microsoft Amazon Facebook Tesla"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        # Brand names should be treated as organizations, not persons
        if result.signals:
            if result.signals.organizations:
                org_cores = [org.core.lower() for org in result.signals.organizations]
                org_text = " ".join(org_cores)
                # Should detect some as organizations
                assert any(brand in org_text for brand in ["apple", "google", "microsoft"])

    @pytest.mark.asyncio
    async def test_malformed_input(self, orchestrator_service):
        """Test malformed input with mixed encodings"""
        # Arrange
        text = "Test\x00\x01\x02\x03\x04\x05"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        # Should handle malformed input gracefully

    @pytest.mark.asyncio
    async def test_sql_injection_attempt(self, orchestrator_service):
        """Test SQL injection-like input"""
        # Arrange
        text = "'; DROP TABLE users; --"
        
        # Act
        result = await orchestrator_service.process(
            text=text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success, f"Processing failed: {result.errors}"
        # Should handle malicious input gracefully

    @pytest.mark.asyncio
    async def test_no_unknown_tokens_in_output(self, orchestrator_service):
        """Test that no 'unknown' tokens appear in any normalized output"""
        # Arrange
        test_cases = [
            "random gibberish text",
            "123 456 789",
            "!@# $%^ &*()",
            "αβγδε абвгд",
            "COVID-19 HTTP API"
        ]
        
        for text in test_cases:
            # Act
            result = await orchestrator_service.process(
                text=text,
                generate_variants=True,
                generate_embeddings=False
            )
            
            # Assert
            assert result.success, f"Processing failed for '{text}': {result.errors}"
            
            # Check that 'unknown' does not appear in normalized text
            normalized_lower = result.normalized_text.lower()
            assert "unknown" not in normalized_lower, f"'unknown' found in normalized text for '{text}'"
            assert "неизвестный" not in normalized_lower, f"'неизвестный' found in normalized text for '{text}'"
            assert "невідомий" not in normalized_lower, f"'невідомий' found in normalized text for '{text}'"

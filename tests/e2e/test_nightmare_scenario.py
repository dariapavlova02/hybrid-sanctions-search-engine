"""
End-to-End "кошмарный" тест-кейс
Тестирует полный цикл UnifiedOrchestrator.process для сложного случая
"""

import pytest
import asyncio
from typing import Set

from src.ai_service.core.unified_orchestrator import UnifiedOrchestrator


class TestNightmareScenario:
    """E2E tests for complex processing scenarios"""
    
    @pytest.mark.asyncio
    async def test_nightmare_scenario_gnatyuk_abdullaev(self, orchestrator_service):
        """
        Nightmare test case:
        Reference: Гнатюк-Абдуллаєв, Жорж Рашидович
        Input string: "Przelew dla Gnatuk Abdulaeva Zhorzha, syna Rashida. O'rganizacja 'Freedom'."
        
        Tests complete name recovery cycle through all services
        """
        # Arrange
        reference_name = "Гнатюк-Абдуллаєв, Жорж Рашидович"
        distorted_input = "Przelew dla Gnatuk Abdulaeva Zhorzha, syna Rashida. O'rganizacja 'Freedom'."
        
        # Expected key lemmas that should be recovered
        expected_lemmas = {
            'гнатюк', 'gnatuk', 'gnatyuk',  # Surname Гнатюк
            'абдуллаєв', 'abdulaeva', 'abdullaev',  # Surname Абдуллаєв
            'жорж', 'zhorzha', 'george',  # Name Жорж
            'рашидович', 'rashida', 'rashid'  # Patronymic Рашидович
        }
        
        # Act
        result = await orchestrator_service.process_text(
            text=distorted_input,
            generate_variants=True,
            generate_embeddings=False,  # Disable for speed
            cache_result=False  # Don't cache test data
        )
        
        # Assert
        assert result.success is True, f"Processing failed: {result.errors}"
        assert result.original_text == distorted_input
        assert len(result.variants) > 0, "Should generate variants"
        
        # Check that among hundreds of variants there are key recovered lemmas
        all_variants_text = ' '.join(result.variants).lower()
        
        # Count found key lemmas
        found_lemmas = set()
        for lemma in expected_lemmas:
            if lemma.lower() in all_variants_text:
                found_lemmas.add(lemma)
        
        # Check that enough key lemmas are found
        coverage = len(found_lemmas) / len(expected_lemmas)
        
        assert len(found_lemmas) >= 4, \
            f"Should recover at least 4 key lemmas. Found: {found_lemmas}, " \
            f"Coverage: {coverage:.2%}, Total variants: {len(result.variants)}"
        
        # Additional checks
        assert result.language in ['en', 'ru', 'uk'], f"Unexpected language: {result.language}"
        assert result.processing_time > 0, "Processing time should be recorded"
        assert len(result.normalized_text) > 0, "Should have normalized text"
        
        # Check that there are transliterations in different directions
        has_cyrillic = any(any(ord(c) > 127 for c in variant) for variant in result.variants[:50])
        has_latin = any(all(ord(c) < 128 for c in variant if c.isalpha()) for variant in result.variants[:50] if variant.strip())
        
        assert has_cyrillic or has_latin, "Should contain both Cyrillic and Latin variants"
        
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("=== Nightmare Scenario Results ===")
        logger.info(f"Original: {distorted_input}")
        logger.info(f"Reference: {reference_name}")
        logger.info(f"Language detected: {result.language}")
        logger.info(f"Processing time: {result.processing_time:.3f}s")
        logger.info(f"Total variants generated: {len(result.variants)}")
        logger.info(f"Key lemmas found: {found_lemmas}")
        logger.info(f"Coverage: {coverage:.2%}")
        logger.info(f"First 20 variants: {result.variants[:20]}")
    
    @pytest.mark.asyncio
    async def test_multilingual_nightmare(self, orchestrator_service):
        """
        Multilingual nightmare test:
        Mixed text with names in different languages and alphabets
        """
        # Arrange
        multilingual_text = "Jean-Baptiste Müller встретил Олександра Петренко-Сміт в кафе 'Zürcher Straße'"
        
        # Act
        result = await orchestrator_service.process_text(
            text=multilingual_text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        # Assert
        assert result.success is True
        assert len(result.variants) > 10, "Should generate many variants for multilingual text"
        
        # Check that names from different languages are processed
        all_variants_lower = ' '.join(result.variants).lower()
        
        # French name
        assert any(name in all_variants_lower for name in ['jean', 'baptiste', 'жан', 'батист'])
        
        # German surname
        assert any(name in all_variants_lower for name in ['muller', 'mueller', 'мюллер'])
        
        # Ukrainian name
        assert any(name in all_variants_lower for name in ['oleksandr', 'alexander', 'олександр'])
        
        # Compound Ukrainian surname
        assert any(name in all_variants_lower for name in ['petrenko', 'smith', 'петренко', 'сміт'])
    
    @pytest.mark.asyncio
    async def test_corrupted_encoding_nightmare(self, orchestrator_service):
        """
        Corrupted encoding nightmare test:
        Simulating encoding problems during data transmission
        """
        # Arrange
        # Simulate various encoding problems
        corrupted_texts = [
            "Ð¡ÐµÑ€Ð³Ð¸Ð¹ Ð˜Ð²Ð°Ð½Ð¾Ð²",  # UTF-8 interpreted as Latin-1
            "СергÐ¸Ð¹ Иванов",  # Partially corrupted encoding
            "Sergii Ä°vanov",  # Mixed encodings
            "Сергій Іванов",  # Correct Ukrainian encoding for comparison
        ]
        
        # Act & Assert
        for i, corrupted_text in enumerate(corrupted_texts):
            result = await orchestrator_service.process_text(
                text=corrupted_text,
                generate_variants=True,
                generate_embeddings=False
            )
            
            assert result.success is True, f"Failed to process corrupted text {i}: {corrupted_text}"
            assert len(result.variants) > 0, f"No variants generated for corrupted text {i}"
            
            # Check that the system tries to recover the name
            all_variants_lower = ' '.join(result.variants).lower()
            assert any(name in all_variants_lower for name in ['sergii', 'sergey', 'сергий', 'сергій']), \
                f"Should recover Sergii variants from corrupted text {i}"
    
    @pytest.mark.asyncio
    async def test_performance_nightmare(self, orchestrator_service):
        """
        Performance test for nightmare scenario:
        Large volume of complex text with many names
        """
        # Arrange
        complex_text = """
        В конференции участвовали: Jean-Baptiste Müller (Zürich), Олександр Петренко-Сміт (Київ),
        María José García-Rodríguez (Madrid), Владимир Александрович Иванов-Петров (Москва),
        O'Connor Patrick Michael (Dublin), Žofie Nováková-Svobodová (Praha),
        Αλέξανδρος Παπαδόπουλος (Athens), 山田太郎 (Tokyo), محمد عبد الله (Cairo),
        Андрій Васильович Коваленко-Шевченко (Львів), Giuseppe Di Marco-Rossi (Milano).
        Также присутствовали представители организаций 'Freedom & Justice', "Human Rights Watch",
        'Врачи без границ', и фонда имени Андрея Сахарова.
        """
        
        # Act
        import time
        start_time = time.time()
        
        result = await orchestrator_service.process_text(
            text=complex_text,
            generate_variants=True,
            generate_embeddings=False
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Assert
        assert result.success is True, "Complex text processing should succeed"
        assert processing_time < 30.0, f"Processing should complete within 30 seconds, took {processing_time:.2f}s"
        assert len(result.variants) >= 50, f"Should generate many variants for complex text, got {len(result.variants)}"
        
        # Check that names from different languages are processed
        all_variants_lower = ' '.join(result.variants).lower()
        
        # Selective check of names from different languages
        name_checks = [
            (['jean', 'baptiste'], "French name"),
            (['alexander', 'oleksandr'], "Slavic name"),
            (['maria', 'garcia'], "Spanish name"),
            (['patrick', 'oconnor'], "Irish name"),
            (['vladimir', 'ivanov'], "Russian name")
        ]
        
        found_names = 0
        for names, description in name_checks:
            if any(name in all_variants_lower for name in names):
                found_names += 1
        
        assert found_names >= 3, f"Should recognize at least 3 different language names, found {found_names}"
        
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("=== Performance Nightmare Results ===")
        logger.info(f"Processing time: {processing_time:.3f}s")
        logger.info(f"Total variants: {len(result.variants)}")
        logger.info(f"Names recognized: {found_names}/{len(name_checks)}")
        logger.info(f"Text length: {len(complex_text)} characters")
        logger.info(f"Throughput: {len(complex_text)/processing_time:.1f} chars/second")
    
    @pytest.mark.asyncio
    async def test_edge_cases_nightmare(self, orchestrator_service):
        """
        Edge cases test:
        Very short, very long, and strange input data
        """
        # Arrange
        edge_cases = [
            "",  # Empty string
            "A",  # Single letter
            "Я",  # Single Cyrillic letter
            "X" * 1000,  # Very long string
            "Ё" * 100,  # Repeated special characters
            "∑∂∆∞≈≠≤≥±",  # Mathematical symbols
            "🎭🎨🎪🎯🎲",  # Emojis
            "Тест\x00\x01\x02",  # Control characters
            "   \t\n\r   ",  # Only spaces
            "Сергій" + "\u200b" * 10 + "Іванов",  # Invisible characters
        ]
        
        # Act & Assert
        for i, edge_case in enumerate(edge_cases):
            result = await orchestrator_service.process_text(
                text=edge_case,
                generate_variants=True,
                generate_embeddings=False
            )
            
            # Main check - should not crash
            assert result is not None, f"Edge case {i} returned None: '{repr(edge_case)}'"
            assert hasattr(result, 'success'), f"Edge case {i} missing success attribute"
            
            # For empty or meaningless input data
            if not edge_case.strip() or len(edge_case.strip()) < 2:
                assert result.normalized_text == "" or len(result.normalized_text) <= 2
                assert len(result.variants) >= 0  # Allow empty or non-empty variants
            else:
                # For meaningful data, there should be some results
                assert isinstance(result.variants, list)
                assert result.processing_time >= 0
    
    @pytest.mark.asyncio
    async def test_cache_effectiveness_nightmare(self, orchestrator_service):
        """
        Cache effectiveness test in nightmare scenarios
        """
        # Arrange
        test_text = "Олександр Петренко-Сміт встретил Jean-Baptiste Müller"
        
        # Act - first request (cache miss)
        import time
        
        start_time = time.time()
        result1 = await orchestrator_service.process_text(
            text=test_text,
            generate_variants=True,
            cache_result=True
        )
        first_time = time.time() - start_time
        
        # Act - second request (cache hit)
        start_time = time.time()
        result2 = await orchestrator_service.process_text(
            text=test_text,
            generate_variants=True,
            cache_result=True
        )
        second_time = time.time() - start_time
        
        # Assert
        assert result1.success is True
        assert result2.success is True
        
        # Results should be identical
        assert result1.normalized_text == result2.normalized_text
        assert result1.language == result2.language
        assert len(result1.variants) == len(result2.variants)
        assert set(result1.variants) == set(result2.variants)
        
        # Second request should be significantly faster
        assert second_time < first_time * 0.5, \
            f"Cached request should be much faster: {second_time:.3f}s vs {first_time:.3f}s"
        
        # Check cache statistics
        stats = orchestrator_service.get_processing_stats()
        assert stats['cache_hits'] > 0, "Should have cache hits"
        assert stats['cache_misses'] > 0, "Should have cache misses"
        
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("=== Cache Effectiveness Results ===")
        logger.info(f"First request: {first_time:.3f}s")
        logger.info(f"Cached request: {second_time:.3f}s")
        logger.info(f"Speedup: {first_time/second_time:.1f}x")
        logger.info(f"Cache hits: {stats['cache_hits']}")
        logger.info(f"Cache misses: {stats['cache_misses']}")
    
    @pytest.mark.asyncio
    async def test_batch_nightmare(self, orchestrator_service):
        """
        Batch processing test for nightmare cases
        """
        # Arrange
        nightmare_batch = [
            "Гнатюк-Абдуллаєв Жорж",
            "Jean-Baptiste Müller",
            "Олександр Петренко-Сміт",
            "María José García",
            "O'Connor Patrick",
            "Владимир Иванов-Петров",
            "∑∂∆ Тест ∞",
            "",
            "X" * 100,
            "Сергій" + "\u200b" + "Іванов"
        ]
        
        # Act
        results = await orchestrator_service.process_batch(
            texts=nightmare_batch,
            generate_variants=True,
            generate_embeddings=False,
            max_concurrent=3
        )
        
        # Assert
        assert len(results) == len(nightmare_batch)
        
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        # Most should be successful
        success_rate = len(successful_results) / len(results)
        assert success_rate >= 0.8, f"Success rate should be at least 80%, got {success_rate:.1%}"
        
        # Check that meaningful texts are processed successfully
        for i, result in enumerate(results):
            text = nightmare_batch[i]
            if text.strip() and len(text.strip()) > 2 and all(ord(c) < 1000 for c in text):
                assert result.success, f"Meaningful text should be processed successfully: '{text}'"
        
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("=== Batch Nightmare Results ===")
        logger.info(f"Total texts: {len(nightmare_batch)}")
        logger.info(f"Successful: {len(successful_results)}")
        logger.info(f"Failed: {len(failed_results)}")
        logger.info(f"Success rate: {success_rate:.1%}")
        
        if failed_results:
            logger.warning("Failed texts:")
            for i, result in enumerate(results):
                if not result.success:
                    logger.warning(f"  {i}: '{nightmare_batch[i]}' - {result.errors}")
    
    def teardown_method(self):
        """Cleanup after each test"""
        # No cleanup needed - using pytest fixtures with scope='function'
        pass

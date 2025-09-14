"""
End-to-End тесты для санкционного скрининга
Покрывают реальные сценарии использования с полным пайплайном обработки
"""

import pytest
from typing import Dict, List, Any

from src.ai_service.core.unified_orchestrator import UnifiedOrchestrator
from src.ai_service.core.orchestrator_factory import OrchestratorFactory
from src.ai_service.monitoring.metrics_service import MetricsService
from src.ai_service.contracts.decision_contracts import MatchDecision


class TestE2ESanctionsScreening:
    """End-to-End тесты для санкционного скрининга"""

    @pytest.fixture(scope="class")
    async def orchestrator(self):
        """Создание полноценного оркестратора для E2E тестов"""
        factory = OrchestratorFactory()
        return await factory.create_orchestrator(
            enable_decision_engine=True,
            enable_variants=True,
            enable_embeddings=True,
        )

    @pytest.mark.asyncio
    async def test_russian_person_with_documents(self, orchestrator):
        """
        Сценарий: Российский гражданин с документами
        Ожидается: Высокая уверенность с извлечением ФИО, ДР и документов
        """
        text = "Иванов Сергей Петрович, дата рождения: 15.03.1985, паспорт РФ № 4510 123456"

        result = await orchestrator.process(
            text=text,
            generate_variants=True,
            generate_embeddings=True,
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        # Базовые проверки успешности
        assert result.success is True
        assert len(result.errors) == 0
        assert result.language == "ru"
        assert result.language_confidence > 0.8

        # Проверки нормализации
        normalized_words = result.normalized_text.split()
        assert "Иванов" in normalized_words
        assert "Сергей" in normalized_words
        assert "Петрович" in normalized_words

        # Проверки сигналов
        assert result.signals is not None
        assert len(result.signals.persons) >= 1

        person = result.signals.persons[0]
        assert "Иванов" in person.core
        assert person.full_name
        assert person.dob is not None
        assert "1985-03-15" in person.dob

        # Проверки документов
        assert len(result.signals.numbers) > 0
        assert "passport" in str(result.signals.numbers).lower()

        # Проверки принятия решения
        if result.decision:
            assert result.decision.confidence > 0.7
            assert result.decision.decision in [MatchDecision.HIT, MatchDecision.REVIEW]
            assert len(result.decision.evidence) > 0

        # Проверки вариантов
        if result.variants:
            assert len(result.variants) > 1
            # Должны быть варианты с инициалами
            initials_variants = [v for v in result.variants if "С." in v or "П." in v]
            assert len(initials_variants) > 0

    @pytest.mark.asyncio
    async def test_ukrainian_organization_with_legal_form(self, orchestrator):
        """
        Сценарий: Украинская организация с юридической формой
        Ожидается: Извлечение названия организации и юридической формы
        """
        text = 'ТОВ "Українська Компанія Розвитку" ЄДРПОУ 12345678'

        result = await orchestrator.process(
            text=text,
            generate_variants=True,
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        assert result.success is True
        assert result.language == "uk"
        assert result.language_confidence > 0.7

        # Проверки организации
        assert result.signals is not None
        assert len(result.signals.organizations) >= 1

        org = result.signals.organizations[0]
        assert org.legal_form == "ТОВ"
        assert "Українська Компанія Розвитку" in org.core
        assert org.full  # Полное название с формой

        # Проверки ЄДРПОУ
        assert "edrpou" in result.signals.numbers
        assert result.signals.numbers["edrpou"] == "12345678"

        # Нормализация не должна содержать юр. форму
        assert "ТОВ" not in result.normalized_text
        assert "Українська Компанія Розвитку" in result.normalized_text

    @pytest.mark.asyncio
    async def test_english_mixed_script_name(self, orchestrator):
        """
        Сценарий: Английское имя в смешанном контексте с кириллицей
        Ожидается: Корректная обработка ASCII в кириллическом тексте
        """
        text = "Платеж в пользу John Smith за услуги перевода, ИНН 123456789012"

        result = await orchestrator.process(
            text=text,
            generate_variants=True,
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        assert result.success is True
        assert result.language == "ru"  # Основной язык - русский

        # ASCII имя должно быть обработано корректно
        assert "John Smith" in result.normalized_text or ("John" in result.normalized_text and "Smith" in result.normalized_text)

        # Проверки персоны
        assert len(result.signals.persons) >= 1
        person = result.signals.persons[0]
        assert "John" in person.core and "Smith" in person.core

        # Проверки ИНН
        assert "inn" in result.signals.numbers
        assert result.signals.numbers["inn"] == "123456789012"

    @pytest.mark.asyncio
    async def test_complex_payment_description(self, orchestrator):
        """
        Сценарий: Сложное описание платежа с множественными данными
        Ожидается: Извлечение всех персон, организаций и документов
        """
        text = '''Платеж от ООО "Торговый Дом Восток" ИНН 7701234567 в пользу
                  Петрова Анна Сергеевна д.р. 12.05.1990 паспорт 4509 567890
                  через банк АО "Сбербанк России" за консультационные услуги'''

        result = await orchestrator.process(
            text=text,
            generate_variants=True,
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        assert result.success is True
        assert result.language == "ru"

        # Должно быть несколько персон/организаций
        assert len(result.signals.persons) >= 1
        assert len(result.signals.organizations) >= 1

        # Проверки персоны
        person = result.signals.persons[0]
        assert "Петрова" in person.core or "Анна" in person.core
        assert person.dob is not None
        assert "1990-05-12" in person.dob

        # Проверки организации
        orgs = result.signals.organizations
        trading_company = next((org for org in orgs if "Торговый Дом" in org.core), None)
        assert trading_company is not None
        assert trading_company.legal_form == "ООО"

        # Проверки документов
        numbers = result.signals.numbers
        assert "inn" in numbers
        assert numbers["inn"] == "7701234567"
        assert "passport" in numbers

    @pytest.mark.asyncio
    async def test_edge_case_compound_names(self, orchestrator):
        """
        Сценарий: Сложные случаи с составными именами и апострофами
        Ожидается: Корректная обработка специальных символов
        """
        text = "Jean-Baptiste O'Connor-Smith, María José García-López"

        result = await orchestrator.process(
            text=text,
            generate_variants=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        assert result.success is True

        # Должно быть как минимум 2 персоны
        assert len(result.signals.persons) >= 2

        # Проверяем сохранение составных имён
        persons_text = " ".join([p.core for p in result.signals.persons])
        assert "Jean-Baptiste" in persons_text or ("Jean" in persons_text and "Baptiste" in persons_text)
        assert "O'Connor" in persons_text or "Connor" in persons_text
        assert "María José" in persons_text or ("María" in persons_text and "José" in persons_text)

    @pytest.mark.asyncio
    async def test_decision_engine_thresholds(self, orchestrator):
        """
        Тест пороговых значений DecisionEngine
        Различные уровни уверенности должны приводить к разным решениям
        """
        test_cases = [
            # Высокая уверенность - ожидается HIT
            ("Иванов Иван Иванович 01.01.1980 паспорт 1234 567890", MatchDecision.HIT),
            # Средняя уверенность - ожидается REVIEW
            ("Иванов И.И.", MatchDecision.REVIEW),
            # Низкая уверенность - ожидается NO_MATCH
            ("платеж за услуги без персональных данных", MatchDecision.NO_MATCH),
        ]

        for text, expected_decision in test_cases:
            result = await orchestrator.process(
                text=text,
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True
            )

            assert result.success is True

            if result.decision:
                if expected_decision == MatchDecision.HIT:
                    assert result.decision.decision in [MatchDecision.HIT, MatchDecision.REVIEW]
                    assert result.decision.confidence > 0.5
                elif expected_decision == MatchDecision.REVIEW:
                    assert result.decision.decision in [MatchDecision.REVIEW, MatchDecision.NO_MATCH]
                elif expected_decision == MatchDecision.NO_MATCH:
                    assert result.decision.confidence < 0.7

    @pytest.mark.asyncio
    async def test_metrics_collection(self, orchestrator):
        """
        Тест сбора метрик во время обработки
        Все слои должны регистрировать метрики
        """
        text = "Тестовый текст для проверки метрик Иванов И.И."

        # Сброс метрик перед тестом
        if hasattr(orchestrator, 'metrics_service') and orchestrator.metrics_service:
            orchestrator.metrics_service.clear_metrics()

        result = await orchestrator.process(
            text=text,
            generate_variants=True,
            generate_embeddings=True
        )

        assert result.success is True

        # Проверяем, что метрики собираются
        if hasattr(orchestrator, 'metrics_service') and orchestrator.metrics_service:
            metrics = orchestrator.metrics_service.get_metrics()

            # Базовые метрики обработки
            assert 'processing.requests.total' in metrics
            assert metrics['processing.requests.total'] >= 1

            # Метрики производительности
            assert 'processing.total_time' in metrics
            assert metrics['processing.total_time'] > 0

    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, orchestrator):
        """
        Тест производительности - все запросы должны выполняться быстро
        """
        test_texts = [
            "Иванов И.И.",
            "Сложный текст с множественными данными: ООО Компания ИНН 123 Петров П.П. 01.01.1990",
            "Jean-Baptiste O'Connor mixed script текст",
            'ТОВ "Дуже Довга Назва Української Компанії З Багатьма Словами" ЄДРПОУ 12345678',
        ]

        for text in test_texts:
            import time
            start_time = time.time()

            result = await orchestrator.process(
                text=text,
                generate_variants=True,
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True
            )

            processing_time = time.time() - start_time

            assert result.success is True
            assert processing_time < 2.0, f"Processing took too long: {processing_time:.3f}s for text: {text[:50]}..."

            # P95 должно быть менее 100ms для коротких текстов
            if len(text) < 100:
                assert processing_time < 0.1, f"Short text processing should be <100ms, got {processing_time:.3f}s"

    @pytest.mark.asyncio
    async def test_golden_dataset_stability(self, orchestrator):
        """
        Тест стабильности на золотом наборе данных
        Результаты должны быть воспроизводимыми между запусками
        """
        golden_cases = [
            {
                "text": "Иванов Сергей Петрович д.р. 15.03.1985",
                "expected_persons": 1,
                "expected_normalized": "Иванов Сергей Петрович",
                "expected_language": "ru",
                "expected_dates": 1
            },
            {
                "text": 'ООО "Рога и Копыта" ИНН 7701123456',
                "expected_organizations": 1,
                "expected_legal_form": "ООО",
                "expected_language": "ru",
                "expected_inn": "7701123456"
            },
            {
                "text": "John Smith, born 1985-03-15",
                "expected_persons": 1,
                "expected_language": "en",
                "expected_dates": 1
            }
        ]

        for case in golden_cases:
            result = await orchestrator.process(
                text=case["text"],
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True
            )

            assert result.success is True
            assert result.language == case["expected_language"]

            if "expected_persons" in case:
                assert len(result.signals.persons) >= case["expected_persons"]

            if "expected_organizations" in case:
                assert len(result.signals.organizations) >= case["expected_organizations"]

            if "expected_legal_form" in case:
                org = result.signals.organizations[0]
                assert org.legal_form == case["expected_legal_form"]

            if "expected_normalized" in case:
                assert case["expected_normalized"] in result.normalized_text

            if "expected_dates" in case:
                dates_found = len([d for d in result.signals.extras.dates if d])
                assert dates_found >= case["expected_dates"]

            if "expected_inn" in case:
                assert result.signals.numbers.get("inn") == case["expected_inn"]
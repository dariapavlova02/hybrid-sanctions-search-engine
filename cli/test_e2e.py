#!/usr/bin/env python3
"""
CLI script для end-to-end тестирования AI сервиса
Позволяет быстро проверить работу всего пайплайна локально
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from ai_service.core.orchestrator_factory import OrchestratorFactory
from ai_service.utils.logging_config import get_logger

logger = get_logger(__name__)


class E2ETester:
    """E2E тестер для AI сервиса"""

    def __init__(self):
        """Инициализация тестера"""
        self.orchestrator = None
        self.factory = OrchestratorFactory()

    async def initialize(self):
        """Инициализация оркестратора"""
        logger.info("Initializing orchestrator...")
        self.orchestrator = await self.factory.create_unified_orchestrator(
            enable_decision_engine=True,
            enable_metrics=True,
            enable_variants=True,
            enable_embeddings=False,  # Disable for faster testing
        )
        logger.info("Orchestrator initialized successfully")

    async def test_single_text(self, text: str, show_details: bool = True) -> Dict[str, Any]:
        """Тест одного текста с подробным выводом"""
        if not self.orchestrator:
            await self.initialize()

        logger.info(f"Testing text: {text}")
        start_time = time.time()

        try:
            result = await self.orchestrator.process(
                text=text,
                generate_variants=True,
                generate_embeddings=False,
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True
            )

            processing_time = time.time() - start_time

            # Создаем результат для вывода
            output = {
                "input": text,
                "success": result.success,
                "processing_time_ms": round(processing_time * 1000, 2),
                "language": result.language,
                "language_confidence": round(result.language_confidence, 3),
                "normalized": result.normalized_text,
                "errors": result.errors,
                "signals": {
                    "persons": [],
                    "organizations": [],
                    "numbers": result.signals.numbers if result.signals else {},
                    "dates": result.signals.extras.dates if result.signals and result.signals.extras else []
                }
            }

            # Извлекаем сигналы
            if result.signals:
                for person in result.signals.persons:
                    output["signals"]["persons"].append({
                        "core": person.core,
                        "full_name": person.full_name,
                        "dob": person.dob,
                        "confidence": round(person.confidence, 3)
                    })

                for org in result.signals.organizations:
                    output["signals"]["organizations"].append({
                        "core": org.core,
                        "legal_form": org.legal_form,
                        "full": org.full,
                        "confidence": round(org.confidence, 3)
                    })

            # Добавляем решение
            if result.decision:
                output["decision"] = {
                    "decision": result.decision.decision.value,
                    "confidence": round(result.decision.confidence, 3),
                    "reasoning": result.decision.reasoning,
                    "evidence_count": len(result.decision.evidence)
                }

            # Добавляем варианты (первые 5)
            if result.variants:
                output["variants"] = result.variants[:5]

            # Подробный вывод
            if show_details:
                print("=" * 80)
                print(f"INPUT: {text}")
                print(f"LANGUAGE: {result.language} (confidence: {result.language_confidence:.3f})")
                print(f"NORMALIZED: {result.normalized_text}")
                print(f"PROCESSING TIME: {processing_time * 1000:.2f}ms")

                if result.signals and result.signals.persons:
                    print("\nPERSONS:")
                    for i, person in enumerate(result.signals.persons):
                        print(f"  {i+1}. {person.full_name} (confidence: {person.confidence:.3f})")
                        if person.dob:
                            print(f"      DOB: {person.dob}")

                if result.signals and result.signals.organizations:
                    print("\nORGANIZATIONS:")
                    for i, org in enumerate(result.signals.organizations):
                        print(f"  {i+1}. {org.full} (confidence: {org.confidence:.3f})")

                if result.signals and result.signals.numbers:
                    print("\nDOCUMENTS/NUMBERS:")
                    for doc_type, doc_value in result.signals.numbers.items():
                        print(f"  {doc_type.upper()}: {doc_value}")

                if result.decision:
                    print(f"\nDECISION: {result.decision.decision.value}")
                    print(f"CONFIDENCE: {result.decision.confidence:.3f}")
                    print(f"REASONING: {result.decision.reasoning}")

                if result.variants:
                    print(f"\nVARIANTS (first 5 of {len(result.variants)}):")
                    for i, variant in enumerate(result.variants[:5]):
                        print(f"  {i+1}. {variant}")

                print("=" * 80)

            return output

        except Exception as e:
            logger.error(f"Error processing text: {e}")
            return {
                "input": text,
                "success": False,
                "error": str(e),
                "processing_time_ms": round((time.time() - start_time) * 1000, 2)
            }

    async def run_test_suite(self):
        """Запуск набора тестовых случаев"""
        test_cases = [
            # Русские ФИО с документами
            "Иванов Сергей Петрович, дата рождения: 15.03.1985, паспорт РФ № 4510 123456",

            # Украинская организация
            'ТОВ "Українська Компанія Розвитку" ЄДРПОУ 12345678',

            # Английское имя в смешанном контексте
            "Платеж в пользу John Smith за услуги перевода, ИНН 123456789012",

            # Сложное описание платежа
            '''Платеж от ООО "Торговый Дом Восток" ИНН 7701234567 в пользу
               Петрова Анна Сергеевна д.р. 12.05.1990 паспорт 4509 567890''',

            # Составные имена
            "Jean-Baptiste O'Connor-Smith, María José García-López",

            # Короткие инициалы
            "Иванов И.И.",

            # Только организация без персон
            "ОАО Газпром ИНН 7736050003",

            # Платежное описание без персональных данных
            "Оплата за консультационные услуги согласно договору №123"
        ]

        print("Starting E2E test suite...")
        print(f"Running {len(test_cases)} test cases")
        print()

        results = []
        total_time = 0

        for i, test_case in enumerate(test_cases, 1):
            print(f"Test {i}/{len(test_cases)}")
            result = await self.test_single_text(test_case, show_details=True)
            results.append(result)
            total_time += result.get("processing_time_ms", 0)
            print()

        # Итоговая статистика
        successful = len([r for r in results if r.get("success", False)])
        print("=" * 80)
        print("TEST SUITE SUMMARY")
        print("=" * 80)
        print(f"Total tests: {len(test_cases)}")
        print(f"Successful: {successful}")
        print(f"Failed: {len(test_cases) - successful}")
        print(f"Total processing time: {total_time:.2f}ms")
        print(f"Average processing time: {total_time / len(test_cases):.2f}ms")
        print("=" * 80)

        return results

    async def run_performance_test(self, iterations: int = 10):
        """Тест производительности"""
        test_text = "Иванов Сергей Петрович, дата рождения: 15.03.1985, паспорт РФ № 4510 123456"

        print(f"Running performance test with {iterations} iterations...")

        times = []
        for i in range(iterations):
            start = time.time()
            result = await self.test_single_text(test_text, show_details=False)
            duration = time.time() - start
            times.append(duration * 1000)  # Convert to ms

            if i % (iterations // 10) == 0:
                print(f"Progress: {i}/{iterations}")

        # Статистика
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        p95_time = sorted(times)[int(len(times) * 0.95)]
        p99_time = sorted(times)[int(len(times) * 0.99)]

        print("\nPERFORMANCE RESULTS:")
        print(f"Average: {avg_time:.2f}ms")
        print(f"Min: {min_time:.2f}ms")
        print(f"Max: {max_time:.2f}ms")
        print(f"P95: {p95_time:.2f}ms")
        print(f"P99: {p99_time:.2f}ms")

        # Проверка соответствия целевым показателям
        if avg_time < 100:
            print("✅ Average time meets target (<100ms)")
        else:
            print("❌ Average time exceeds target (>100ms)")

        if p95_time < 200:
            print("✅ P95 time meets target (<200ms)")
        else:
            print("❌ P95 time exceeds target (>200ms)")


async def main():
    """Основная функция"""
    import argparse

    parser = argparse.ArgumentParser(description="E2E тестер AI сервиса")
    parser.add_argument("--text", "-t", type=str, help="Тест одного текста")
    parser.add_argument("--suite", "-s", action="store_true", help="Запуск набора тестов")
    parser.add_argument("--performance", "-p", type=int, help="Тест производительности (количество итераций)")
    parser.add_argument("--json", "-j", action="store_true", help="Вывод в JSON формате")

    args = parser.parse_args()

    tester = E2ETester()

    try:
        if args.text:
            result = await tester.test_single_text(args.text, show_details=not args.json)
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))

        elif args.performance:
            await tester.run_performance_test(args.performance)

        elif args.suite:
            results = await tester.run_test_suite()
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))

        else:
            print("Использование:")
            print("  python cli/test_e2e.py -t 'Иванов И.И.'  # Тест одного текста")
            print("  python cli/test_e2e.py -s                # Набор тестов")
            print("  python cli/test_e2e.py -p 50             # Тест производительности")
            print("  python cli/test_e2e.py -t 'текст' -j     # Вывод в JSON")

    except KeyboardInterrupt:
        print("\nТестирование прервано пользователем")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
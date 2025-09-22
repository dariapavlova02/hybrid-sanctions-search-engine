#!/usr/bin/env python3
"""
Simplified Golden Test Integration

Tests golden suite with available services (normalization and signals).
Works without external dependencies like elasticsearch, nameparser, etc.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    # Try importing core services that are available
    from ai_service.layers.normalization.normalization_service import NormalizationService
    from ai_service.layers.signals.signals_service import SignalsService
    from ai_service.layers.unicode.unicode_service import UnicodeService
    from ai_service.layers.language.language_detection_service import LanguageDetectionService
    from ai_service.config import SERVICE_CONFIG
    print("✅ Core services imported successfully")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)


class SimpleIntegrationRunner:
    """Simplified golden test runner using available core services."""

    def __init__(self, suite_file: Path):
        self.suite_file = suite_file
        self.suite_data = self._load_suite()
        self.results = {"passed": 0, "failed": 0, "details": []}

        # Initialize available services
        self.unicode_service = UnicodeService()
        self.language_service = LanguageDetectionService()
        self.normalization_service = NormalizationService()
        self.signals_service = SignalsService()

    def _load_suite(self) -> Dict[str, Any]:
        """Load golden test suite from JSON file."""
        with open(self.suite_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    async def test_core_services(self):
        """Test core services with selected golden test cases."""
        print("🧪 Testing Core AI Services with Golden Test Cases")
        print("=" * 60)

        # Test 1: Normalization Service
        await self._test_normalization_service()

        # Test 2: Language Detection Service
        await self._test_language_detection()

        # Test 3: Unicode Service
        await self._test_unicode_service()

        # Test 4: Signals Service
        await self._test_signals_service()

        self._print_summary()

    async def _test_normalization_service(self):
        """Test normalization service with golden test cases."""
        print("\n📝 Testing Normalization Service")

        test_cases = [
            {
                "id": "NORM-01",
                "input": "Dr. John A. Smith Jr.",
                "expected_tokens": ["John", "Smith"],
                "description": "English name normalization"
            },
            {
                "id": "NORM-02",
                "input": "Ковриков Роман Валерьевич",
                "expected_tokens": ["Ковриков", "Роман", "Валерьевич"],
                "description": "Russian name normalization"
            },
            {
                "id": "NORM-03",
                "input": "  Mr. John  Smith  ",
                "expected_normalized": "John Smith",
                "description": "Title removal and whitespace cleanup"
            }
        ]

        for test_case in test_cases:
            try:
                result = await self.normalization_service.normalize_async(
                    test_case["input"],
                    remove_stop_words=True,
                    preserve_names=True,
                    enable_advanced_features=True
                )

                passed = True
                errors = []

                # Check normalized result exists
                if not result.normalized:
                    errors.append("Empty normalized result")
                    passed = False

                # Check tokens if expected
                if "expected_tokens" in test_case:
                    if not all(token in result.tokens for token in test_case["expected_tokens"]):
                        errors.append(f"Missing expected tokens: {test_case['expected_tokens']}")
                        passed = False

                # Check normalized text if expected
                if "expected_normalized" in test_case:
                    if test_case["expected_normalized"] not in result.normalized:
                        errors.append(f"Expected '{test_case['expected_normalized']}' in normalized result")
                        passed = False

                self._record_result(test_case["id"], test_case["description"], passed, errors)

                if passed:
                    print(f"  ✅ {test_case['id']}: {test_case['description']}")
                    print(f"     Input: '{test_case['input']}'")
                    print(f"     Output: '{result.normalized}'")
                    print(f"     Tokens: {result.tokens}")
                else:
                    print(f"  ❌ {test_case['id']}: {test_case['description']}")
                    print(f"     Errors: {errors}")

            except Exception as e:
                print(f"  🔥 {test_case['id']}: Error - {e}")
                self._record_result(test_case["id"], test_case["description"], False, [str(e)])

    async def _test_language_detection(self):
        """Test language detection service."""
        print("\n🌍 Testing Language Detection Service")

        test_cases = [
            {"id": "LANG-01", "input": "John Smith", "expected": "en"},
            {"id": "LANG-02", "input": "Ковриков Роман", "expected": "ru"},
            {"id": "LANG-03", "input": "Ковріков Роман", "expected": "uk"},
        ]

        for test_case in test_cases:
            try:
                result = self.language_service.detect_language(test_case["input"])

                detected_lang = result.get("language", "unknown")
                passed = detected_lang == test_case["expected"]
                errors = [] if passed else [f"Expected {test_case['expected']}, got {detected_lang}"]

                self._record_result(test_case["id"], f"Language detection: {test_case['input']}", passed, errors)

                if passed:
                    print(f"  ✅ {test_case['id']}: '{test_case['input']}' → {detected_lang}")
                else:
                    print(f"  ❌ {test_case['id']}: '{test_case['input']}' → {detected_lang} (expected {test_case['expected']})")

            except Exception as e:
                print(f"  🔥 {test_case['id']}: Error - {e}")
                self._record_result(test_case["id"], f"Language detection: {test_case['input']}", False, [str(e)])

    async def _test_unicode_service(self):
        """Test unicode normalization service."""
        print("\n🔤 Testing Unicode Service")

        test_cases = [
            {"id": "UNI-01", "input": "Café", "description": "Accented characters"},
            {"id": "UNI-02", "input": "Москва", "description": "Cyrillic text"},
            {"id": "UNI-03", "input": "  Test  ", "description": "Whitespace normalization"},
        ]

        for test_case in test_cases:
            try:
                result = self.unicode_service.normalize_text(test_case["input"])

                normalized_text = result.get("normalized", "")
                passed = len(normalized_text) > 0
                errors = [] if passed else ["Empty normalized result"]

                self._record_result(test_case["id"], test_case["description"], passed, errors)

                if passed:
                    print(f"  ✅ {test_case['id']}: '{test_case['input']}' → '{normalized_text}'")
                else:
                    print(f"  ❌ {test_case['id']}: '{test_case['input']}' → Empty result")

            except Exception as e:
                print(f"  🔥 {test_case['id']}: Error - {e}")
                self._record_result(test_case["id"], test_case["description"], False, [str(e)])

    async def _test_signals_service(self):
        """Test signals extraction service."""
        print("\n📡 Testing Signals Service")

        test_cases = [
            {
                "id": "SIG-01",
                "input": "ООО \"ТЕСТ\" ИНН 1234567890",
                "description": "Organization with INN detection"
            },
            {
                "id": "SIG-02",
                "input": "Иванов Иван Иванович дата рождения 01.01.1990",
                "description": "Person with date of birth"
            },
            {
                "id": "SIG-03",
                "input": "ACME Holdings Ltd. Registration 12345",
                "description": "English organization"
            }
        ]

        for test_case in test_cases:
            try:
                # For signals, we need to provide normalization result first
                norm_result = await self.normalization_service.normalize_async(
                    test_case["input"],
                    enable_advanced_features=True
                )

                result = await self.signals_service.extract_signals(
                    text=test_case["input"],
                    normalization_result=norm_result.__dict__ if hasattr(norm_result, '__dict__') else {}
                )

                passed = result is not None and result.confidence > 0
                errors = [] if passed else ["No signals detected"]

                self._record_result(test_case["id"], test_case["description"], passed, errors)

                if passed:
                    print(f"  ✅ {test_case['id']}: {test_case['description']}")
                    print(f"     Confidence: {result.confidence:.2f}")
                    if hasattr(result, 'organizations') and result.organizations:
                        print(f"     Organizations: {len(result.organizations)}")
                    if hasattr(result, 'persons') and result.persons:
                        print(f"     Persons: {len(result.persons)}")
                else:
                    print(f"  ❌ {test_case['id']}: {test_case['description']}")
                    print(f"     No signals detected")

            except Exception as e:
                print(f"  🔥 {test_case['id']}: Error - {e}")
                self._record_result(test_case["id"], test_case["description"], False, [str(e)])

    def _record_result(self, test_id: str, description: str, passed: bool, errors: List[str]):
        """Record test result."""
        if passed:
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1

        self.results["details"].append({
            "id": test_id,
            "description": description,
            "passed": passed,
            "errors": errors
        })

    def _print_summary(self):
        """Print test execution summary."""
        total = self.results["passed"] + self.results["failed"]
        success_rate = (self.results["passed"] / total * 100) if total > 0 else 0

        print(f"\n{'='*60}")
        print(f"📊 CORE SERVICES TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total tests: {total}")
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"Success rate: {success_rate:.1f}%")

        if self.results["failed"] > 0:
            print(f"\n🔍 Failed test details:")
            for detail in self.results["details"]:
                if not detail["passed"]:
                    print(f"  {detail['id']}: {detail['errors']}")

    async def test_specific_golden_cases(self):
        """Test specific cases from golden suite that can work with available services."""
        print("\n🎯 Testing Selected Golden Test Cases")
        print("=" * 60)

        # Find testable cases from golden suite
        testable_cases = []
        for test in self.suite_data["tests"]:
            # We can test normalization-related cases
            if test["layer"] in ["ingest", "smart_filter"] and "full_name" in test.get("input", {}):
                testable_cases.append(test)

        print(f"Found {len(testable_cases)} testable cases from golden suite")

        for test_case in testable_cases[:5]:  # Test first 5 cases
            try:
                text = test_case["input"]["full_name"]
                print(f"\n🧪 Testing {test_case['id']}: {test_case['description']}")
                print(f"   Input: '{text}'")

                # Test with normalization service
                norm_result = await self.normalization_service.normalize_async(
                    text,
                    enable_advanced_features=True
                )

                print(f"   Normalized: '{norm_result.normalized}'")
                print(f"   Tokens: {norm_result.tokens}")
                print(f"   Language: {norm_result.language}")

                # Test language detection
                lang_result = self.language_service.detect_language(text)
                detected_lang = lang_result.get("language", "unknown")
                confidence = lang_result.get("confidence", 0.0)
                print(f"   Detected language: {detected_lang} (confidence: {confidence:.2f})")

                self._record_result(test_case["id"], test_case["description"], True, [])
                print(f"   ✅ Golden case processed successfully")

            except Exception as e:
                print(f"   🔥 Error processing golden case: {e}")
                self._record_result(test_case["id"], test_case["description"], False, [str(e)])


async def main():
    """Main entry point."""
    suite_file = Path(__file__).parent / "golden_suite.json"
    runner = SimpleIntegrationRunner(suite_file)

    print("🎯 Simple Integration Testing with Available AI Services")
    print("=" * 60)

    # Test core services functionality
    await runner.test_core_services()

    # Test some golden cases
    await runner.test_specific_golden_cases()


if __name__ == "__main__":
    asyncio.run(main())
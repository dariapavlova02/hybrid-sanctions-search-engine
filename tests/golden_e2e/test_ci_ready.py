#!/usr/bin/env python3
"""
CI-Ready Golden Test Suite

Production-ready pytest integration for golden e2e tests.
Designed to be integrated with existing test infrastructure.
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any, List


class TestGoldenE2ESuite:
    """CI-ready golden test suite for pytest integration."""

    @classmethod
    def setup_class(cls):
        """Setup test suite data."""
        suite_file = Path(__file__).parent / "golden_suite.json"
        with open(suite_file, 'r', encoding='utf-8') as f:
            cls.suite_data = json.load(f)

        # Group tests by layer
        cls.tests_by_layer = {}
        for test in cls.suite_data["tests"]:
            layer = test["layer"]
            if layer not in cls.tests_by_layer:
                cls.tests_by_layer[layer] = []
            cls.tests_by_layer[layer].append(test)

    def test_ingest_layer_coverage(self):
        """Test that ingest layer has required test coverage."""
        ingest_tests = self.tests_by_layer.get("ingest", [])
        assert len(ingest_tests) >= 3, "Ingest layer should have at least 3 test cases"

        # Check that we cover different input types
        test_types = set()
        for test in ingest_tests:
            if "person_id" in test["input"]:
                test_types.add("person")
            if "entity_id" in test["input"]:
                test_types.add("company")

        assert "person" in test_types, "Should test person input"
        assert "company" in test_types, "Should test company input"

    def test_smart_filter_layer_coverage(self):
        """Test that smart filter layer has required test coverage."""
        sf_tests = self.tests_by_layer.get("smart_filter", [])
        assert len(sf_tests) >= 5, "Smart filter layer should have at least 5 test cases"

        # Check language coverage
        languages = set()
        for test in sf_tests:
            lang = test["input"].get("lang", "unknown")
            languages.add(lang)

        assert "en" in languages, "Should test English language"
        assert "ru-ua" in languages or "ru" in languages, "Should test Russian/Ukrainian language"

    def test_pattern_builder_layer_coverage(self):
        """Test that pattern builder layer has required test coverage."""
        pb_tests = self.tests_by_layer.get("pattern_builder", [])
        assert len(pb_tests) >= 6, "Pattern builder layer should have at least 6 test cases"

        # Check tier coverage
        tier_patterns = set()
        for test in pb_tests:
            for assertion in test.get("assert", []):
                if "tier1" in assertion:
                    tier_patterns.add("tier1")
                if "tier2" in assertion:
                    tier_patterns.add("tier2")
                if "tier3" in assertion:
                    tier_patterns.add("tier3")

        assert "tier1" in tier_patterns, "Should test tier1 patterns"
        assert "tier2" in tier_patterns, "Should test tier2 patterns"

    def test_signals_layer_coverage(self):
        """Test that signals layer has required test coverage."""
        signals_tests = self.tests_by_layer.get("signals", [])
        assert len(signals_tests) >= 5, "Signals layer should have at least 5 test cases"

        # Check signal types coverage
        signal_types = set()
        for test in signals_tests:
            expected_signal = test.get("expect", {}).get("signal")
            if expected_signal:
                signal_types.add(expected_signal)

        assert "exact" in signal_types, "Should test exact matches"
        assert "strong" in signal_types, "Should test strong matches"
        assert "none" in signal_types, "Should test no matches"

    def test_decision_engine_layer_coverage(self):
        """Test that decision engine layer has required test coverage."""
        dec_tests = self.tests_by_layer.get("decision_engine", [])
        assert len(dec_tests) >= 5, "Decision engine layer should have at least 5 test cases"

        # Check decision types coverage
        decisions = set()
        for test in dec_tests:
            expected_decision = test.get("expect", {}).get("decision")
            if expected_decision:
                decisions.add(expected_decision)

        assert "REJECT" in decisions, "Should test rejection decisions"
        assert "REVIEW" in decisions, "Should test review decisions"
        assert "PASS" in decisions, "Should test pass decisions"

    def test_sanitizer_layer_coverage(self):
        """Test that post export sanitizer layer has required test coverage."""
        san_tests = self.tests_by_layer.get("post_export_sanitizer", [])
        assert len(san_tests) >= 5, "Sanitizer layer should have at least 5 test cases"

        # Check sanitization types
        sanitization_types = set()
        for test in san_tests:
            if "strings" in test["input"]:
                if any("  " in s for s in test["input"]["strings"]):
                    sanitization_types.add("whitespace")
                if any(s.lower() != s for s in test["input"]["strings"]):
                    sanitization_types.add("case")

        assert len(sanitization_types) > 0, "Should test various sanitization types"

    def test_report_assembler_layer_coverage(self):
        """Test that report assembler layer has required test coverage."""
        rep_tests = self.tests_by_layer.get("report_assembler", [])
        assert len(rep_tests) >= 3, "Report assembler layer should have at least 3 test cases"

        # Check report types
        entity_types = set()
        for test in rep_tests:
            if "person_id" in test["input"]:
                entity_types.add("person")
            if "entity_id" in test["input"]:
                entity_types.add("company")

        assert len(entity_types) > 0, "Should test different entity types"

    def test_all_tests_have_required_fields(self):
        """Test that all tests have required fields."""
        required_fields = ["id", "layer", "description", "input"]

        for test in self.suite_data["tests"]:
            for field in required_fields:
                assert field in test, f"Test {test.get('id', 'unknown')} missing required field: {field}"

            # Test ID format
            assert test["id"].startswith("G-"), f"Test ID {test['id']} should start with 'G-'"
            assert len(test["id"].split("-")) == 3, f"Test ID {test['id']} should have format G-XXX-##"

    def test_layer_names_are_valid(self):
        """Test that all layer names are from expected set."""
        expected_layers = {
            "ingest", "smart_filter", "pattern_builder", "signals",
            "decision_engine", "post_export_sanitizer", "report_assembler"
        }

        actual_layers = set(test["layer"] for test in self.suite_data["tests"])
        assert actual_layers <= expected_layers, f"Unexpected layers found: {actual_layers - expected_layers}"
        assert actual_layers == expected_layers, f"Missing layers: {expected_layers - actual_layers}"

    def test_assertions_are_valid_python(self):
        """Test that all assertion strings are valid Python expressions."""
        import ast

        for test in self.suite_data["tests"]:
            assertions = test.get("assert", [])
            for assertion in assertions:
                try:
                    # Try to parse as Python AST
                    ast.parse(assertion, mode='eval')
                except SyntaxError as e:
                    pytest.fail(f"Invalid assertion syntax in {test['id']}: '{assertion}' - {e}")

    def test_expected_values_are_reasonable(self):
        """Test that expected values are within reasonable bounds."""
        for test in self.suite_data["tests"]:
            expected = test.get("expect", {})

            # Check confidence values are in [0, 1]
            for key, value in expected.items():
                if "confidence" in key.lower() and isinstance(value, (int, float)):
                    assert 0 <= value <= 1, f"Confidence value {value} in {test['id']} should be in [0, 1]"

    def test_test_ids_are_unique(self):
        """Test that all test IDs are unique."""
        test_ids = [test["id"] for test in self.suite_data["tests"]]
        assert len(test_ids) == len(set(test_ids)), "Duplicate test IDs found"

    def test_input_output_consistency(self):
        """Test that inputs and expected outputs are consistent."""
        for test in self.suite_data["tests"]:
            layer = test["layer"]
            input_data = test["input"]
            expected = test.get("expect", {})

            # Layer-specific consistency checks
            if layer == "ingest":
                if "full_name" in input_data:
                    # If input has full_name, output should have full_name_raw
                    expected_keys = list(expected.keys())
                    assert any("full_name" in key for key in expected_keys), \
                        f"Ingest test {test['id']} with full_name input should expect full_name output"

            elif layer == "smart_filter":
                if "full_name_raw" in input_data:
                    expected_keys = list(expected.keys())
                    assert any("cleaned_name" in key for key in expected_keys), \
                        f"Smart filter test {test['id']} should expect cleaned_name output"

    @pytest.mark.parametrize("layer_name", [
        "ingest", "smart_filter", "pattern_builder", "signals",
        "decision_engine", "post_export_sanitizer", "report_assembler"
    ])
    def test_layer_has_tests(self, layer_name):
        """Test that each layer has at least one test."""
        layer_tests = self.tests_by_layer.get(layer_name, [])
        assert len(layer_tests) > 0, f"Layer '{layer_name}' should have at least one test"

    def test_suite_metadata_is_valid(self):
        """Test that suite metadata is valid and up-to-date."""
        metadata = self.suite_data.get("metadata", {})

        assert "version" in metadata, "Suite should have version"
        assert "description" in metadata, "Suite should have description"
        assert "test_count" in metadata, "Suite should have test_count"

        actual_test_count = len(self.suite_data["tests"])
        expected_test_count = metadata["test_count"]
        assert actual_test_count == expected_test_count, \
            f"Test count mismatch: metadata says {expected_test_count}, actual {actual_test_count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
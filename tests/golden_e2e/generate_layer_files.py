#!/usr/bin/env python3
"""
Generate individual layer test files from golden suite.
"""

import json
from pathlib import Path


def generate_layer_files():
    """Generate layer-specific test files from golden suite."""
    suite_file = Path(__file__).parent / "golden_suite.json"

    with open(suite_file, 'r', encoding='utf-8') as f:
        suite = json.load(f)

    # Group tests by layer
    layers = {}
    for test in suite["tests"]:
        layer = test["layer"]
        if layer not in layers:
            layers[layer] = []
        layers[layer].append(test)

    # Generate files for each layer
    for layer_name, tests in layers.items():
        layer_file = {
            "layer": layer_name,
            "description": f"{layer_name.replace('_', ' ').title()} layer tests",
            "tests": tests
        }

        output_file = Path(__file__).parent / f"layer_{layer_name}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(layer_file, f, indent=2, ensure_ascii=False)

        print(f"Generated {output_file} with {len(tests)} tests")

    print(f"\nGenerated {len(layers)} layer files from {len(suite['tests'])} total tests")


if __name__ == "__main__":
    generate_layer_files()
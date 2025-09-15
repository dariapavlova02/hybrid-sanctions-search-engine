#!/usr/bin/env python3
"""Debug initials formatting issue"""

import sys
import os
sys.path.insert(0, '/Users/dariapavlova/Desktop/ai-service/src')

from ai_service.layers.normalization.normalization_service import NormalizationService

def debug_initials_format():
    """Debug initials formatting"""
    print("=== Initials Formatting Debug ===")

    service = NormalizationService()

    test_text = 'П.І. Коваленко, ТОВ "ПРИВАТБАНК" та Петросян працюють разом'
    print(f"Testing: {test_text}")

    # Test full normalization
    result = service._normalize_sync(test_text, language="uk")
    print(f"Normalized: '{result.normalized}'")
    print(f"Tokens: {result.tokens}")

    print("\nTrace:")
    for trace in result.trace:
        print(f"  {trace.token} -> {trace.output} (role: {trace.role})")

    # Test step by step
    print(f"\n--- Step by step ---")

    # Step 1: Strip noise and tokenize
    tokens = service._strip_noise_and_tokenize(test_text, language="uk")
    print(f"1. Tokenized: {tokens}")

    # Step 2: Tag roles
    tagged = service._tag_roles(tokens, "uk")
    print(f"2. Tagged: {tagged}")

    # Step 3: Extract person tokens manually
    person_tokens = []
    person_traces = []
    for i, (token, role) in enumerate(tagged):
        if role in ["given", "surname", "patronymic", "initial"]:
            person_tokens.append(token)
            # Create mock trace for testing
            from ai_service.contracts.base_contracts import TokenTrace
            person_traces.append(TokenTrace(
                token=token, role=role, rule="test",
                morph_lang="uk", normal_form=None,
                output=token, fallback=False
            ))

    print(f"3. Person tokens: {person_tokens}")

    # Step 4: Test reconstruction
    reconstructed = service._reconstruct_text_with_multiple_persons(person_tokens, person_traces, "uk")
    print(f"4. Reconstructed: '{reconstructed}'")

if __name__ == "__main__":
    debug_initials_format()
#!/usr/bin/env python3
"""
Debug token duplication issue in normalization
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

async def debug_duplication():
    """Debug why tokens are duplicated in trace."""
    print("🔍 DEBUGGING TOKEN DUPLICATION")
    print("="*40)

    test_case = "ШЕВЧЕНКО АНДРІЙ АНАТОЛІЙОВИЧ"  # All caps input

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()

        result = await service.normalize_async(
            test_case,
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True,
            preserve_feminine_suffix_uk=True
        )

        print(f"Input: '{test_case}'")
        print(f"Normalized: '{result.normalized}'")
        print(f"Tokens: {result.tokens}")

        print(f"\n📝 TRACE ANALYSIS:")
        for i, trace_item in enumerate(result.trace):
            token = trace_item.token if hasattr(trace_item, 'token') else str(trace_item)[:50]
            role = trace_item.role if hasattr(trace_item, 'role') else 'N/A'
            output = trace_item.output if hasattr(trace_item, 'output') else 'N/A'

            print(f"  {i+1}. Token: '{token}' -> Role: '{role}' -> Output: '{output}'")

        print(f"\n🔍 ORIGINAL TOKENS ANALYSIS:")
        original_tokens = test_case.split()
        for i, token in enumerate(original_tokens):
            print(f"  {i+1}. Original: '{token}'")
            # Check how many times this token appears in trace
            appearances = 0
            for trace_item in result.trace:
                if hasattr(trace_item, 'token'):
                    trace_token = trace_item.token.lower()
                    if trace_token == token.lower():
                        appearances += 1
            print(f"     Appears in trace: {appearances} times")

        print(f"\n🎯 PROBLEMS IDENTIFIED:")
        problems = []

        # Check for duplicates
        seen_tokens = set()
        for trace_item in result.trace:
            if hasattr(trace_item, 'token'):
                token_lower = trace_item.token.lower()
                if token_lower in seen_tokens:
                    problems.append(f"Duplicate token: '{trace_item.token}'")
                seen_tokens.add(token_lower)

        # Check for unknown roles
        for trace_item in result.trace:
            if hasattr(trace_item, 'role') and trace_item.role == 'unknown':
                problems.append(f"Token '{trace_item.token}' marked as 'unknown' but should be 'given'")

        if problems:
            for problem in problems:
                print(f"  ❌ {problem}")
        else:
            print("  ✅ No obvious problems found")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(debug_duplication())
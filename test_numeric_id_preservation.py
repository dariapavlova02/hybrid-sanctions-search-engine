#!/usr/bin/env python3

"""
Test numeric ID preservation in normalization.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_numeric_id_preservation():
    """Test that numeric IDs are preserved during normalization."""
    print("🔍 TESTING NUMERIC ID PRESERVATION")
    print("=" * 60)

    try:
        from ai_service.layers.normalization.role_tagger_service import RoleTaggerService, TokenRole
        from ai_service.config.settings import SERVICE_CONFIG

        print("✅ Successfully imported RoleTaggerService and TokenRole")
        print(f"📊 TokenRole.ID available: {hasattr(TokenRole, 'ID')}")

        # Create role tagger service with minimal config
        try:
            # Try with minimal config
            from ai_service.config.normalization_config import NormalizationConfig
            from ai_service.layers.normalization.processors.data_config import DataConfig
            from ai_service.layers.normalization.processors.rules_config import RulesConfig

            # Create minimal configs
            data_config = DataConfig()
            rules_config = RulesConfig()
            norm_config = NormalizationConfig(data=data_config, rules=rules_config)

            role_tagger = RoleTaggerService(
                lang="ru",
                config=norm_config
            )
            print("✅ Successfully created RoleTaggerService")
        except Exception as service_e:
            print(f"❌ Failed to create RoleTaggerService: {service_e}")
            print("Trying with default parameters...")
            try:
                # Simplified initialization
                role_tagger = RoleTaggerService()
                print("✅ Successfully created RoleTaggerService with defaults")
            except Exception as simple_e:
                print(f"❌ Failed with defaults too: {simple_e}")
                return

        # Test cases with numeric IDs
        test_cases = [
            {
                "name": "Ukrainian INN with marker",
                "tokens": ["ІПН", "782611846337"],
                "expected_id_positions": [1]
            },
            {
                "name": "Russian INN with marker",
                "tokens": ["ИНН", "782611846337"],
                "expected_id_positions": [1]
            },
            {
                "name": "English INN with marker",
                "tokens": ["INN", "782611846337"],
                "expected_id_positions": [1]
            },
            {
                "name": "EDRPOU marker",
                "tokens": ["ЄДРПОУ", "12345678"],
                "expected_id_positions": [1]
            },
            {
                "name": "EDRPOU lowercase marker",
                "tokens": ["єдрпоу", "12345678"],
                "expected_id_positions": [1]
            },
            {
                "name": "Name with embedded INN",
                "tokens": ["Петров", "Иван", "ІПН", "782611846337"],
                "expected_id_positions": [3]
            },
            {
                "name": "ID without marker (should still be detected)",
                "tokens": ["Петров", "782611846337"],
                "expected_id_positions": [1]
            }
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}. TEST: {test_case['name']}")
            print(f"   Tokens: {test_case['tokens']}")
            print(f"   Expected ID positions: {test_case['expected_id_positions']}")

            try:
                # Tag tokens
                role_tags = role_tagger.tag(test_case['tokens'], "ru")

                # Check results
                id_positions = []
                for pos, role_tag in enumerate(role_tags):
                    if hasattr(role_tag, 'role') and hasattr(role_tag.role, 'value'):
                        role_value = role_tag.role.value
                    else:
                        role_value = str(role_tag.role)

                    print(f"     Token[{pos}]: '{test_case['tokens'][pos]}' -> {role_value} (conf: {role_tag.confidence:.2f})")

                    if role_value == 'id':
                        id_positions.append(pos)

                # Check if expected IDs were found
                if id_positions == test_case['expected_id_positions']:
                    print(f"   ✅ SUCCESS: Found ID tokens at positions {id_positions}")
                else:
                    print(f"   ❌ FAILED: Expected ID at {test_case['expected_id_positions']}, got {id_positions}")

            except Exception as test_e:
                print(f"   ❌ TEST ERROR: {test_e}")
                import traceback
                traceback.print_exc()

    except Exception as e:
        print(f"❌ Setup error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("NUMERIC ID PRESERVATION TEST COMPLETE")

if __name__ == "__main__":
    test_numeric_id_preservation()
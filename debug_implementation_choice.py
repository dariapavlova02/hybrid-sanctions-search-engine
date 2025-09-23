#!/usr/bin/env python3

import sys
sys.path.append("src")

from ai_service.utils.feature_flags import FeatureFlags, FeatureFlagManager, NormalizationImplementation

# Test the feature flags logic directly
def test_feature_flags():
    print("=== Testing Feature Flags Logic ===")

    # Create feature flag manager
    flag_manager = FeatureFlagManager()

    print(f"Flag manager created")

    # Test should_use_factory method
    should_use = flag_manager.should_use_factory(
        language="uk",
        user_id=None,
        request_context=None
    )
    print(f"should_use_factory() result: {should_use}")

    # Test monitoring config
    monitoring = flag_manager.get_monitoring_config()
    print(f"Monitoring config: {monitoring}")
    print(f"log_implementation_choice: {monitoring.get('log_implementation_choice')}")
    print(f"enable_dual_processing: {monitoring.get('enable_dual_processing')}")

if __name__ == "__main__":
    test_feature_flags()
#!/usr/bin/env python3
"""
Debug SmartFilter threshold issue
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ai_service.layers.smart_filter.smart_filter_service import SmartFilterService
from ai_service.data.dicts.smart_filter_patterns import CONFIDENCE_THRESHOLDS

def test_smartfilter_threshold():
    """Test SmartFilter threshold decision for simple names"""

    print("🔍 Testing SmartFilter threshold issue")
    print("="*60)

    # Initialize SmartFilter service
    smart_filter = SmartFilterService()

    print(f"📊 Current thresholds: {CONFIDENCE_THRESHOLDS}")
    print(f"🎯 Min processing threshold: {CONFIDENCE_THRESHOLDS['min_processing_threshold']}")

    test_names = [
        "Дарья Павлова",
        "John Smith",
        "Кухарук Вікторія",
        "Іван Петров"
    ]

    print(f"\n🧪 Testing simple names:")
    for name in test_names:
        try:
            result = smart_filter.should_process_text(name)

            print(f"\n📝 Input: '{name}'")
            print(f"  should_process: {result.should_process}")
            print(f"  confidence: {result.confidence:.4f}")
            print(f"  detected_signals: {result.detected_signals}")
            print(f"  recommendation: {result.processing_recommendation}")

            # Check if confidence meets threshold
            meets_threshold = result.confidence >= CONFIDENCE_THRESHOLDS['min_processing_threshold']
            print(f"  meets_min_threshold: {meets_threshold}")

            if not result.should_process and meets_threshold:
                print(f"  ⚠️  BUG: Confidence {result.confidence} >= {CONFIDENCE_THRESHOLDS['min_processing_threshold']} but should_process=False!")

            # Get detailed signal analysis
            signal_details = result.signal_details
            if 'names' in signal_details:
                name_confidence = signal_details['names'].get('confidence', 0)
                print(f"  name_detector_confidence: {name_confidence:.4f}")

            if 'companies' in signal_details:
                company_confidence = signal_details['companies'].get('confidence', 0)
                print(f"  company_detector_confidence: {company_confidence:.4f}")

        except Exception as e:
            print(f"  ❌ Error: {e}")

    print(f"\n🎯 Summary:")
    print(f"  Threshold configured: {CONFIDENCE_THRESHOLDS['min_processing_threshold']}")
    print(f"  Expected behavior: Any confidence >= 0.001 should process")
    print(f"  Actual behavior: Names with low confidence get skipped")

if __name__ == "__main__":
    test_smartfilter_threshold()
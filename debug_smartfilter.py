#!/usr/bin/env python3
"""
Debug SmartFilter to see why it blocks processing for "Ковриков Роман Валерійович"
"""
import sys
sys.path.insert(0, 'src')

from ai_service.layers.smart_filter.smart_filter_service import SmartFilterService

def debug_smartfilter():
    # Test text that's failing
    test_text = "Ковриков Роман Валерійович"

    print("=== Debugging SmartFilter ===")
    print(f"Test text: {test_text}")

    # Initialize SmartFilter
    smart_filter = SmartFilterService(
        language_service=None,
        signal_service=None,
        enable_terrorism_detection=True,
        enable_aho_corasick=True
    )

    # Get filter result
    result = smart_filter.should_process_text(test_text)

    print(f"\n=== Filter Result ===")
    print(f"should_process: {result.should_process}")
    print(f"confidence: {result.confidence}")
    print(f"detected_signals: {result.detected_signals}")
    print(f"processing_recommendation: {result.processing_recommendation}")
    print(f"estimated_complexity: {result.estimated_complexity}")

    # Check signal details
    print(f"\n=== Signal Details ===")
    signal_details = result.signal_details
    print(f"Companies confidence: {signal_details.get('companies', {}).get('confidence', 0)}")
    print(f"Names confidence: {signal_details.get('names', {}).get('confidence', 0)}")
    print(f"Context confidence: {signal_details.get('context', {}).get('confidence', 0)}")

    # Check AC matches
    ac_info = signal_details.get('aho_corasick_matches', {})
    print(f"AC matches: {ac_info.get('total_matches', 0)}")
    print(f"AC enabled: {ac_info.get('enabled', False)}")
    print(f"AC confidence bonus: {ac_info.get('confidence_bonus', 0)}")

    # Get comprehensive analysis
    comprehensive = smart_filter.get_comprehensive_analysis(test_text)

    print(f"\n=== Comprehensive Analysis ===")
    legacy = comprehensive['legacy_analysis']
    print(f"Legacy should_process: {legacy['should_process']}")
    print(f"Legacy confidence: {legacy['confidence']}")

    decision = comprehensive['decision_analysis']
    print(f"Decision result: {decision.get('decision_result', {})}")

if __name__ == "__main__":
    debug_smartfilter()
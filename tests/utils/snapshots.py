"""
Utilities for creating stable snapshots of SearchTrace data.

Normalizes dynamic fields and ensures deterministic ordering for snapshot testing.
"""

import json
from typing import Any, Dict, List, Optional, Union
from dataclasses import asdict

from src.ai_service.contracts.trace_models import SearchTrace, SearchTraceStep, SearchTraceHit


def normalize_trace_for_snapshot(trace: SearchTrace, max_hits: int = 3) -> Dict[str, Any]:
    """
    Normalize SearchTrace for stable snapshot comparison.
    
    Args:
        trace: SearchTrace object to normalize
        max_hits: Maximum number of hits to include per step (default: 3)
    
    Returns:
        Normalized dictionary suitable for snapshot testing
    """
    if not trace.enabled:
        return {"enabled": False, "steps": [], "notes": []}
    
    normalized_steps = []
    for step in trace.steps:
        normalized_step = _normalize_step_for_snapshot(step, max_hits)
        normalized_steps.append(normalized_step)
    
    return {
        "enabled": trace.enabled,
        "steps": normalized_steps,
        "notes": trace.notes
    }


def _normalize_step_for_snapshot(step: SearchTraceStep, max_hits: int) -> Dict[str, Any]:
    """Normalize SearchTraceStep for snapshot comparison."""
    # Round took_ms to 0.1ms precision
    rounded_took_ms = round(step.took_ms, 1)
    
    # Normalize hits (limit count, sort deterministically)
    normalized_hits = _normalize_hits_for_snapshot(step.hits, max_hits)
    
    # Clean meta data (remove volatile fields)
    cleaned_meta = _clean_meta_for_snapshot(step.meta)
    
    return {
        "stage": step.stage,
        "query": step.query,
        "topk": step.topk,
        "took_ms": rounded_took_ms,
        "hits": normalized_hits,
        "meta": cleaned_meta
    }


def _normalize_hits_for_snapshot(hits: List[SearchTraceHit], max_hits: int) -> List[Dict[str, Any]]:
    """Normalize SearchTraceHit list for snapshot comparison."""
    if not hits:
        return []
    
    # Sort deterministically: score desc, doc_id asc
    sorted_hits = sorted(hits, key=lambda h: (-h.score, h.doc_id))
    
    # Limit to max_hits
    limited_hits = sorted_hits[:max_hits]
    
    # Convert to normalized dict format
    normalized = []
    for hit in limited_hits:
        normalized_hit = {
            "doc_id": hit.doc_id,
            "score": round(hit.score, 3),  # Round to 3 decimal places
            "rank": hit.rank,
            "source": hit.source,
            "signals": _clean_signals_for_snapshot(hit.signals)
        }
        normalized.append(normalized_hit)
    
    return normalized


def _clean_meta_for_snapshot(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Remove volatile fields from meta data."""
    if not meta:
        return {}
    
    # Fields to exclude (volatile/timestamp data)
    volatile_fields = {
        'timestamp', 'created_at', 'updated_at', 'start_time', 'end_time',
        'random_seed', 'session_id', 'request_id', 'trace_id',
        'duration_ms', 'elapsed_time', 'processing_time'
    }
    
    cleaned = {}
    for key, value in meta.items():
        if key.lower() not in volatile_fields:
            if isinstance(value, dict):
                # Recursively clean nested dicts
                cleaned[key] = _clean_meta_for_snapshot(value)
            elif isinstance(value, list):
                # Clean list items if they're dicts
                cleaned[key] = [
                    _clean_meta_for_snapshot(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                cleaned[key] = value
    
    return cleaned


def _clean_signals_for_snapshot(signals: Dict[str, Any]) -> Dict[str, Any]:
    """Clean signals data for snapshot comparison."""
    if not signals:
        return {}
    
    # Round numeric values for stability
    cleaned = {}
    for key, value in signals.items():
        if isinstance(value, float):
            cleaned[key] = round(value, 3)
        elif isinstance(value, dict):
            cleaned[key] = _clean_signals_for_snapshot(value)
        elif isinstance(value, list):
            cleaned[key] = [
                round(item, 3) if isinstance(item, float) else item
                for item in value
            ]
        else:
            cleaned[key] = value
    
    return cleaned


def create_snapshot_file(trace: SearchTrace, filename: str, max_hits: int = 3) -> None:
    """
    Create a snapshot file from SearchTrace.
    
    Args:
        trace: SearchTrace object to snapshot
        filename: Output filename for snapshot
        max_hits: Maximum number of hits per step
    """
    normalized = normalize_trace_for_snapshot(trace, max_hits)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)


def compare_trace_snapshots(expected_file: str, actual_trace: SearchTrace, max_hits: int = 3) -> bool:
    """
    Compare actual SearchTrace with expected snapshot.
    
    Args:
        expected_file: Path to expected snapshot file
        actual_trace: Actual SearchTrace to compare
        max_hits: Maximum number of hits per step
    
    Returns:
        True if traces match, False otherwise
    """
    try:
        with open(expected_file, 'r', encoding='utf-8') as f:
            expected = json.load(f)
        
        actual = normalize_trace_for_snapshot(actual_trace, max_hits)
        
        return expected == actual
    except (FileNotFoundError, json.JSONDecodeError):
        return False


def assert_trace_snapshot_matches(actual_trace: SearchTrace, expected_file: str, max_hits: int = 3) -> None:
    """
    Assert that SearchTrace matches expected snapshot.
    
    Args:
        actual_trace: Actual SearchTrace to check
        expected_file: Path to expected snapshot file
        max_hits: Maximum number of hits per step
    
    Raises:
        AssertionError: If traces don't match
    """
    normalized = normalize_trace_for_snapshot(actual_trace, max_hits)
    
    try:
        with open(expected_file, 'r', encoding='utf-8') as f:
            expected = json.load(f)
    except FileNotFoundError:
        # Create expected file if it doesn't exist
        with open(expected_file, 'w', encoding='utf-8') as f:
            json.dump(normalized, f, indent=2, ensure_ascii=False)
        raise AssertionError(f"Created expected snapshot file: {expected_file}")
    
    if expected != normalized:
        # Create diff file for debugging
        diff_file = expected_file.replace('.json', '_diff.json')
        with open(diff_file, 'w', encoding='utf-8') as f:
            json.dump({
                "expected": expected,
                "actual": normalized,
                "differences": _find_differences(expected, normalized)
            }, f, indent=2, ensure_ascii=False)
        
        raise AssertionError(f"Trace snapshot mismatch. See diff file: {diff_file}")


def _find_differences(expected: Dict[str, Any], actual: Dict[str, Any], path: str = "") -> List[str]:
    """Find differences between expected and actual data structures."""
    differences = []
    
    if type(expected) != type(actual):
        differences.append(f"{path}: type mismatch - expected {type(expected)}, got {type(actual)}")
        return differences
    
    if isinstance(expected, dict):
        all_keys = set(expected.keys()) | set(actual.keys())
        for key in sorted(all_keys):
            new_path = f"{path}.{key}" if path else key
            if key not in expected:
                differences.append(f"{new_path}: missing in expected")
            elif key not in actual:
                differences.append(f"{new_path}: missing in actual")
            else:
                differences.extend(_find_differences(expected[key], actual[key], new_path))
    elif isinstance(expected, list):
        if len(expected) != len(actual):
            differences.append(f"{path}: length mismatch - expected {len(expected)}, got {len(actual)}")
        else:
            for i, (exp_item, act_item) in enumerate(zip(expected, actual)):
                differences.extend(_find_differences(exp_item, act_item, f"{path}[{i}]"))
    else:
        if expected != actual:
            differences.append(f"{path}: value mismatch - expected {expected}, got {actual}")
    
    return differences


# Convenience functions for common snapshot operations
def normalize_for_snapshot(data: Any, max_hits: int = 3) -> Any:
    """
    Normalize any SearchTrace-related data for snapshot comparison.
    
    Args:
        data: Data to normalize (SearchTrace, SearchTraceStep, or SearchTraceHit)
        max_hits: Maximum number of hits per step
    
    Returns:
        Normalized data structure
    """
    if isinstance(data, SearchTrace):
        return normalize_trace_for_snapshot(data, max_hits)
    elif isinstance(data, SearchTraceStep):
        return _normalize_step_for_snapshot(data, max_hits)
    elif isinstance(data, list) and data and isinstance(data[0], SearchTraceHit):
        return _normalize_hits_for_snapshot(data, max_hits)
    else:
        return data


def create_stable_snapshot(trace: SearchTrace, output_dir: str, test_name: str, max_hits: int = 3) -> str:
    """
    Create a stable snapshot file with standardized naming.
    
    Args:
        trace: SearchTrace to snapshot
        output_dir: Directory to save snapshot
        test_name: Name of the test (used in filename)
        max_hits: Maximum number of hits per step
    
    Returns:
        Path to created snapshot file
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    filename = os.path.join(output_dir, f"{test_name}_snapshot.json")
    create_snapshot_file(trace, filename, max_hits)
    
    return filename

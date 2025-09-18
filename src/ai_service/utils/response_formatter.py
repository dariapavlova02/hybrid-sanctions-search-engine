"""
Response formatter for API endpoints.

Provides standardized JSON response formatting with clear structure
and backward compatibility for processing results.
"""

from typing import Any, Dict, List, Optional

from ..contracts.base_contracts import UnifiedProcessingResult
from ..contracts.decision_contracts import DecisionOutput, RiskLevel


def format_processing_result(result: UnifiedProcessingResult) -> Dict[str, Any]:
    """
    Format processing result into standardized JSON response.
    
    Args:
        result: UnifiedProcessingResult from orchestrator
        
    Returns:
        Dictionary with standardized response structure including:
        - Basic processing fields (original_text, normalized_text, etc.)
        - Risk assessment fields (risk_level, risk_score, etc.)
        - Raw evidence fields (smart_filter, signals)
        - Metadata (processing_time, success, errors)
    """
    
    # Base response structure
    response = {
        # Core processing results
        "original_text": result.original_text,
        "normalized_text": result.normalized_text,
        "language": result.language,
        "language_confidence": result.language_confidence,
        
        # Variants and tokens
        "variants": result.variants or [],
        "tokens": result.tokens or [],
        "token_variants": _extract_token_variants(result),
        
        # Risk assessment (from decision engine)
        "risk_level": _get_risk_level(result.decision),
        "risk_score": _get_risk_score(result.decision),
        "decision_reasons": _get_decision_reasons(result.decision),
        "decision_details": _get_decision_details(result.decision),
        
        # Business gates
        "review_required": _get_review_required(result.decision),
        "required_additional_fields": _get_required_additional_fields(result.decision),
        
        # Raw evidence (for debugging and analysis)
        "smart_filter": _extract_smart_filter_info(result),
        "signals": _extract_signals_summary(result),
        
        # Processing metadata
        "processing_time": result.processing_time,
        "success": result.success,
        "errors": result.errors or [],
    }
    
    return response


def _extract_token_variants(result: UnifiedProcessingResult) -> List[Dict[str, Any]]:
    """Extract token variants from processing result."""
    if not result.trace:
        return []
    
    token_variants = []
    for trace_item in result.trace:
        if hasattr(trace_item, 'token') and hasattr(trace_item, 'role'):
            token_variants.append({
                "token": trace_item.token,
                "role": trace_item.role,
                "normal_form": getattr(trace_item, 'normal_form', None),
                "confidence": getattr(trace_item, 'confidence', None),
            })
    
    return token_variants


def _get_risk_level(decision: Optional[DecisionOutput]) -> str:
    """Get risk level from decision result."""
    if decision is None:
        return "unknown"
    return decision.risk.value


def _get_risk_score(decision: Optional[DecisionOutput]) -> Optional[float]:
    """Get risk score from decision result."""
    if decision is None:
        return None
    return decision.score


def _get_decision_reasons(decision: Optional[DecisionOutput]) -> List[str]:
    """Get decision reasons from decision result."""
    if decision is None:
        return ["decision_engine_not_enabled"]
    return decision.reasons


def _get_decision_details(decision: Optional[DecisionOutput]) -> Dict[str, Any]:
    """Get decision details from decision result."""
    if decision is None:
        return {}
    return decision.details


def _extract_smart_filter_info(result: UnifiedProcessingResult) -> Dict[str, Any]:
    """Extract smart filter information from processing result."""
    # Smart filter info is typically stored in context metadata
    # For now, we'll extract what we can from the result
    smart_filter_info = {
        "enabled": False,
        "should_process": True,
        "confidence": 1.0,
        "classification": None,
        "detected_signals": [],
        "details": {}
    }
    
    # If we have decision details, extract smart filter info from there
    if result.decision and "smartfilter" in result.decision.details:
        sf_details = result.decision.details["smartfilter"]
        smart_filter_info.update({
            "enabled": True,
            "should_process": sf_details.get("should_process", True),
            "confidence": sf_details.get("confidence", 1.0),
            "classification": sf_details.get("estimated_complexity"),
            "detected_signals": [],
            "details": sf_details
        })
    
    return smart_filter_info


def _extract_signals_summary(result: UnifiedProcessingResult) -> Dict[str, Any]:
    """Extract signals summary from processing result."""
    if not result.signals:
        return {
            "persons": [],
            "organizations": [],
            "confidence": 0.0,
            "summary": {
                "persons_count": 0,
                "organizations_count": 0,
                "total_confidence": 0.0
            }
        }
    
    # Extract person information
    persons = []
    if result.signals.persons:
        for person in result.signals.persons:
            person_info = {
                "name": getattr(person, 'name', ''),
                "confidence": getattr(person, 'confidence', 0.0),
                "role": getattr(person, 'role', 'unknown'),
            }
            # Add IDs if available
            if hasattr(person, 'ids') and person.ids:
                person_info["ids"] = person.ids
            persons.append(person_info)
    
    # Extract organization information
    organizations = []
    if result.signals.organizations:
        for org in result.signals.organizations:
            org_info = {
                "name": getattr(org, 'name', ''),
                "confidence": getattr(org, 'confidence', 0.0),
                "type": getattr(org, 'type', 'unknown'),
            }
            # Add IDs if available
            if hasattr(org, 'ids') and org.ids:
                org_info["ids"] = org.ids
            organizations.append(org_info)
    
    return {
        "persons": persons,
        "organizations": organizations,
        "confidence": result.signals.confidence,
        "summary": {
            "persons_count": len(persons),
            "organizations_count": len(organizations),
            "total_confidence": result.signals.confidence
        }
    }


def format_error_response(error_message: str, error_code: str = "processing_error") -> Dict[str, Any]:
    """
    Format error response for API endpoints.
    
    Args:
        error_message: Human-readable error message
        error_code: Machine-readable error code
        
    Returns:
        Dictionary with error response structure
    """
    return {
        "success": False,
        "error": {
            "code": error_code,
            "message": error_message
        },
        "original_text": "",
        "normalized_text": "",
        "language": "unknown",
        "language_confidence": 0.0,
        "variants": [],
        "token_variants": [],
        "risk_level": "unknown",
        "risk_score": None,
        "decision_reasons": ["processing_failed"],
        "decision_details": {},
        "smart_filter": {
            "enabled": False,
            "should_process": False,
            "confidence": 0.0,
            "classification": None,
            "detected_signals": [],
            "details": {}
        },
        "signals": {
            "persons": [],
            "organizations": [],
            "confidence": 0.0,
            "summary": {
                "persons_count": 0,
                "organizations_count": 0,
                "total_confidence": 0.0
            }
        },
        "processing_time": 0.0,
        "errors": [error_message],
        "review_required": False,
        "required_additional_fields": []
    }


def _get_review_required(decision: Optional[DecisionOutput]) -> bool:
    """Extract review_required from decision output."""
    if not decision:
        return False
    return getattr(decision, 'review_required', False)


def _get_required_additional_fields(decision: Optional[DecisionOutput]) -> List[str]:
    """Extract required_additional_fields from decision output."""
    if not decision:
        return []
    return getattr(decision, 'required_additional_fields', [])

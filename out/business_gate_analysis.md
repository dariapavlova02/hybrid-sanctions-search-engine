# Business Gate Analysis: TIN + DOB Requirements

## Current State

**Business Rule**: When a name match is found, always require TIN (Tax Identification Number) + DOB (Date of Birth) for verification.

**Exception**: If the sanctions card has neither TIN nor DOB, then reject based on PIB (Personal Information Block) is acceptable.

## Current Implementation Analysis

### Decision Engine Location
**File**: `src/ai_service/core/decision_engine.py`

**Current Logic**:
```python
def _calculate_weighted_score(self, inp: DecisionInput) -> float:
    # Current scoring includes:
    # - person_confidence (name match)
    # - org_confidence (organization match)  
    # - similarity_cos_top (cosine similarity)
    # - date_bonus (if inp.signals.date_match)
    # - id_bonus (if inp.signals.id_match)
```

**Missing**: Explicit TIN + DOB requirement logic for name matches.

### Signals Structure
**File**: `src/ai_service/contracts/decision_contracts.py`

**Current SignalsInfo**:
```python
@dataclass
class SignalsInfo:
    person_confidence: float
    org_confidence: float
    date_match: bool  # DOB match
    id_match: bool    # TIN match
    evidence: Dict[str, Any]
```

**Status**: ✅ TIN and DOB signals are already available in the decision engine.

## Required Implementation

### 1. Business Gate Logic

**Location**: `src/ai_service/core/decision_engine.py`

**New Method**:
```python
def _check_business_gate(self, inp: DecisionInput) -> Tuple[bool, List[str]]:
    """
    Check business gate requirements for name matches.
    
    Returns:
        Tuple of (gate_passed, reasons)
    """
    reasons = []
    
    # Check if we have a name match (person_confidence > threshold)
    name_match_threshold = 0.7
    has_name_match = inp.signals.person_confidence >= name_match_threshold
    
    if not has_name_match:
        return True, ["No name match - business gate not applicable"]
    
    # Name match found - check TIN + DOB requirements
    has_tin = inp.signals.id_match
    has_dob = inp.signals.date_match
    
    if has_tin and has_dob:
        return True, ["Name match with TIN + DOB - gate passed"]
    
    # Check if sanctions card has neither TIN nor DOB
    sanctions_has_tin = self._check_sanctions_has_tin(inp)
    sanctions_has_dob = self._check_sanctions_has_dob(inp)
    
    if not sanctions_has_tin and not sanctions_has_dob:
        return True, ["Name match but sanctions card has no TIN/DOB - PIB reject acceptable"]
    
    # Business gate failed
    missing = []
    if not has_tin:
        missing.append("TIN")
    if not has_dob:
        missing.append("DOB")
    
    return False, [f"Name match requires {', '.join(missing)} but not provided"]
```

### 2. Integration with Decision Flow

**Modify**: `decide()` method in `DecisionEngine`

```python
def decide(self, inp: DecisionInput, search_trace: Optional[SearchTrace] = None) -> DecisionOutput:
    # ... existing logic ...
    
    # NEW: Check business gate before calculating score
    gate_passed, gate_reasons = self._check_business_gate(safe_input)
    if not gate_passed:
        return DecisionOutput(
            risk=RiskLevel.HIGH,
            score=0.0,
            reasons=gate_reasons,
            details={"business_gate_failed": True, "gate_reasons": gate_reasons}
        )
    
    # ... continue with existing logic ...
```

### 3. Sanctions Card TIN/DOB Check

**New Method**:
```python
def _check_sanctions_has_tin(self, inp: DecisionInput) -> bool:
    """Check if sanctions card has TIN information."""
    # This would need to be implemented based on how sanctions data is structured
    # For now, assume we can check evidence or search results
    evidence = inp.signals.evidence
    return any("tin" in str(key).lower() or "tax_id" in str(key).lower() 
              for key in evidence.keys())

def _check_sanctions_has_dob(self, inp: DecisionInput) -> bool:
    """Check if sanctions card has DOB information."""
    evidence = inp.signals.evidence
    return any("dob" in str(key).lower() or "birth" in str(key).lower() 
              for key in evidence.keys())
```

## Test Cases

### 1. Name Match with TIN + DOB
**Input**: Name match (confidence > 0.7) + TIN match + DOB match
**Expected**: Gate passed, continue processing
**Test**:
```python
def test_business_gate_name_match_with_tin_dob():
    inp = DecisionInput(
        text="John Smith",
        language="en",
        smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
        signals=SignalsInfo(
            person_confidence=0.8,  # Name match
            org_confidence=0.0,
            date_match=True,        # DOB match
            id_match=True,          # TIN match
            evidence={}
        ),
        similarity=SimilarityInfo(cos_top=0.9, cos_p95=0.8)
    )
    
    engine = DecisionEngine()
    result = engine.decide(inp)
    
    assert result.risk != RiskLevel.HIGH
    assert "business_gate_failed" not in result.details
```

### 2. Name Match without TIN + DOB
**Input**: Name match (confidence > 0.7) + no TIN + no DOB
**Expected**: Gate failed, return HIGH risk
**Test**:
```python
def test_business_gate_name_match_without_tin_dob():
    inp = DecisionInput(
        text="John Smith",
        language="en",
        smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
        signals=SignalsInfo(
            person_confidence=0.8,  # Name match
            org_confidence=0.0,
            date_match=False,       # No DOB match
            id_match=False,         # No TIN match
            evidence={}
        ),
        similarity=SimilarityInfo(cos_top=0.9, cos_p95=0.8)
    )
    
    engine = DecisionEngine()
    result = engine.decide(inp)
    
    assert result.risk == RiskLevel.HIGH
    assert result.details["business_gate_failed"] == True
    assert "TIN" in str(result.reasons)
    assert "DOB" in str(result.reasons)
```

### 3. Name Match with Sanctions Card Missing TIN/DOB
**Input**: Name match + no TIN/DOB + sanctions card has no TIN/DOB
**Expected**: Gate passed (PIB reject acceptable)
**Test**:
```python
def test_business_gate_sanctions_no_tin_dob():
    inp = DecisionInput(
        text="John Smith",
        language="en",
        smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
        signals=SignalsInfo(
            person_confidence=0.8,  # Name match
            org_confidence=0.0,
            date_match=False,       # No DOB match
            id_match=False,         # No TIN match
            evidence={"name": "John Smith"}  # No TIN/DOB in evidence
        ),
        similarity=SimilarityInfo(cos_top=0.9, cos_p95=0.8)
    )
    
    engine = DecisionEngine()
    result = engine.decide(inp)
    
    assert result.risk != RiskLevel.HIGH
    assert "PIB reject acceptable" in str(result.reasons)
```

## Implementation Priority

### P0 (Critical)
1. Implement `_check_business_gate()` method
2. Integrate gate check into `decide()` method
3. Add unit tests for all scenarios

### P1 (High)
1. Implement sanctions card TIN/DOB checking
2. Add integration tests
3. Add monitoring/metrics for gate failures

### P2 (Medium)
1. Add configuration for gate thresholds
2. Add detailed logging for gate decisions
3. Add performance monitoring

## Risk Assessment

**Low Risk**: 
- Business gate logic is additive, doesn't change existing scoring
- Clear test cases for validation
- Graceful fallback if gate check fails

**Medium Risk**:
- Sanctions card TIN/DOB checking depends on data structure
- May need coordination with search/retrieval services

**Mitigation**:
- Implement with feature flag for easy rollback
- Add comprehensive logging for debugging
- Start with simple evidence checking, enhance later

## Monitoring

**Metrics to Track**:
- `business_gate_passed_total` - Count of gate passes
- `business_gate_failed_total` - Count of gate failures
- `business_gate_failed_reasons` - Breakdown of failure reasons
- `business_gate_sanctions_no_tin_dob` - Count of PIB reject acceptable cases

**Alerts**:
- High gate failure rate (>10%)
- Unexpected gate behavior patterns
- Performance impact of gate checking

## Next Steps

1. **Implement business gate logic** in `DecisionEngine`
2. **Add unit tests** for all scenarios
3. **Deploy with feature flag** for safe rollout
4. **Monitor metrics** for 24-48 hours
5. **Iterate based on real-world usage**

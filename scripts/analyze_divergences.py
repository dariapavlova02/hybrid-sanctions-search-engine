#!/usr/bin/env python3
"""
Analyze divergences between legacy and factory outputs.
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any

def analyze_divergence_patterns(results_file: str) -> Dict[str, Any]:
    """Analyze patterns in divergences."""
    # Find the most recent results file if not specified
    if not results_file:
        scripts_dir = Path(__file__).parent
        pattern = "comparison_results_*.json"
        files = list(scripts_dir.glob(pattern))
        if not files:
            raise FileNotFoundError("No comparison results found")
        results_file = str(max(files, key=lambda f: f.stat().st_mtime))

    with open(results_file) as f:
        data = json.load(f)

    results = data['results']

    # Categorize issues
    issues = {
        'morphology': [],
        'tokenization': [],
        'role_classification': [],
        'diminutives': [],
        'gender': [],
        'unicode': [],
        'context_filtering': [],
        'initials': [],
        'unknown': []
    }

    # Analyze each divergent case
    for result in results:
        if not result['match']:
            case_id = result['case_id']
            legacy = result['legacy_output']
            factory = result['factory_output']
            expected = result['expected']

            # Pattern analysis
            if 'diminutive' in case_id:
                issues['diminutives'].append({
                    'case_id': case_id,
                    'issue': f"Factory output '{factory}' vs legacy '{legacy}'",
                    'severity': 'high' if result['legacy_match'] and not result['factory_match'] else 'medium'
                })

            elif 'initials' in case_id or 'И..' in factory:
                issues['initials'].append({
                    'case_id': case_id,
                    'issue': f"Double dots in initials: '{factory}'",
                    'severity': 'high'
                })

            elif 'hyphenated' in case_id or '-' in legacy != '-' in factory:
                issues['tokenization'].append({
                    'case_id': case_id,
                    'issue': f"Hyphenated name handling: '{factory}' vs '{legacy}'",
                    'severity': 'medium'
                })

            elif 'apostrophe' in case_id:
                issues['unicode'].append({
                    'case_id': case_id,
                    'issue': f"Apostrophe handling: '{factory}' vs '{legacy}'",
                    'severity': 'medium'
                })

            elif 'context' in case_id or 'noise' in case_id:
                issues['context_filtering'].append({
                    'case_id': case_id,
                    'issue': f"Context filtering: '{factory}' vs '{legacy}'",
                    'severity': 'high'
                })

            elif 'feminine' in case_id or 'gender' in case_id:
                issues['gender'].append({
                    'case_id': case_id,
                    'issue': f"Gender handling: '{factory}' vs '{legacy}'",
                    'severity': 'high' if result['factory_match'] and not result['legacy_match'] else 'medium'
                })

            elif 'declension' in case_id or 'nominative' in case_id:
                issues['morphology'].append({
                    'case_id': case_id,
                    'issue': f"Morphology: '{factory}' vs '{legacy}'",
                    'severity': 'medium'
                })

            else:
                issues['unknown'].append({
                    'case_id': case_id,
                    'issue': f"Unknown pattern: '{factory}' vs '{legacy}'",
                    'severity': 'medium'
                })

    return issues

def create_improvement_plan(issues: Dict[str, List]) -> List[Dict[str, Any]]:
    """Create prioritized improvement plan."""
    plan = []

    # High priority fixes
    if issues['initials']:
        plan.append({
            'priority': 1,
            'category': 'tokenization',
            'title': 'Fix double dots in initials (И.. → И.)',
            'description': 'TokenProcessor is producing double dots for initials',
            'affected_cases': [item['case_id'] for item in issues['initials']],
            'estimated_effort': 'low',
            'impact': 'high'
        })

    if issues['diminutives']:
        plan.append({
            'priority': 2,
            'category': 'morphology',
            'title': 'Fix diminutive name expansion',
            'description': 'Diminutive to full name mapping not working correctly',
            'affected_cases': [item['case_id'] for item in issues['diminutives']],
            'estimated_effort': 'medium',
            'impact': 'high'
        })

    if issues['context_filtering']:
        plan.append({
            'priority': 3,
            'category': 'tokenization',
            'title': 'Improve context word filtering',
            'description': 'Stop words and context tokens leaking into normalized output',
            'affected_cases': [item['case_id'] for item in issues['context_filtering']],
            'estimated_effort': 'high',
            'impact': 'high'
        })

    # Medium priority fixes
    if issues['gender']:
        plan.append({
            'priority': 4,
            'category': 'morphology',
            'title': 'Fix gender-based morphology',
            'description': 'Gender inference and surname adjustment issues',
            'affected_cases': [item['case_id'] for item in issues['gender']],
            'estimated_effort': 'medium',
            'impact': 'medium'
        })

    if issues['tokenization']:
        plan.append({
            'priority': 5,
            'category': 'tokenization',
            'title': 'Fix hyphenated name tokenization',
            'description': 'Preserve hyphens in compound names',
            'affected_cases': [item['case_id'] for item in issues['tokenization']],
            'estimated_effort': 'low',
            'impact': 'medium'
        })

    if issues['unicode']:
        plan.append({
            'priority': 6,
            'category': 'unicode',
            'title': 'Fix apostrophe normalization',
            'description': 'Proper handling of apostrophes in names',
            'affected_cases': [item['case_id'] for item in issues['unicode']],
            'estimated_effort': 'low',
            'impact': 'low'
        })

    return plan

def print_analysis(issues: Dict[str, List], plan: List[Dict[str, Any]]):
    """Print detailed analysis."""
    print("="*80)
    print("DIVERGENCE PATTERN ANALYSIS")
    print("="*80)

    total_issues = sum(len(category_issues) for category_issues in issues.values())
    print(f"Total divergent cases analyzed: {total_issues}")

    print("\nIssue categories:")
    for category, category_issues in issues.items():
        if category_issues:
            print(f"  {category}: {len(category_issues)} cases")
            for issue in category_issues:
                print(f"    - {issue['case_id']}: {issue['issue']} [{issue['severity']}]")

    print("\n" + "="*80)
    print("IMPROVEMENT PLAN")
    print("="*80)

    for item in plan:
        print(f"\n{item['priority']}. [{item['category'].upper()}] {item['title']}")
        print(f"   Description: {item['description']}")
        print(f"   Affected cases: {', '.join(item['affected_cases'])}")
        print(f"   Effort: {item['estimated_effort']}, Impact: {item['impact']}")

    print("\n" + "="*80)
    print("SUMMARY & RECOMMENDATIONS")
    print("="*80)

    print("\n🔥 Critical Issues (Fix First):")
    critical_items = [item for item in plan if item['priority'] <= 3]
    for item in critical_items:
        print(f"  - {item['title']} ({len(item['affected_cases'])} cases)")

    print("\n📊 Key Metrics to Track:")
    print("  - Parity rate: Target 90%+ (currently 48.4%)")
    print("  - Factory accuracy: Target 80%+ (currently 29.0%)")
    print("  - Performance: Factory is ~80x slower (93ms vs 1.2ms)")

    print("\n💡 Strategic Recommendations:")
    print("  1. Focus on tokenization issues first (biggest impact)")
    print("  2. Improve diminutive handling (user-visible functionality)")
    print("  3. Address performance gap in parallel")
    print("  4. Consider incremental rollout with feature flags")

def main():
    """Main analysis function."""
    # Find the most recent results file
    scripts_dir = Path(__file__).parent
    pattern = "comparison_results_*.json"
    files = list(scripts_dir.glob(pattern))

    if not files:
        print("No comparison results found. Run compare_legacy_vs_factory.py first.")
        return

    results_file = str(max(files, key=lambda f: f.stat().st_mtime))
    print(f"Analyzing results from: {results_file}")

    issues = analyze_divergence_patterns(results_file)
    plan = create_improvement_plan(issues)
    print_analysis(issues, plan)

if __name__ == "__main__":
    main()
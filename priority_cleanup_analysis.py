#!/usr/bin/env python3
"""
Priority cleanup analysis for dead code removal.
Focus on files with the highest cleanup impact and safest removals.
"""

import ast
import os
import re
from pathlib import Path
from collections import defaultdict, namedtuple
from typing import Dict, List, Set, Tuple, Any

Definition = namedtuple('Definition', ['name', 'type', 'file_path', 'line_number', 'is_public', 'is_dunder'])
Usage = namedtuple('Usage', ['name', 'file_path', 'line_number', 'context'])

class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.definitions = []
        self.usages = []
        self.imports = []
        self.current_class = None

    def visit_FunctionDef(self, node):
        is_public = not node.name.startswith('_')
        is_dunder = node.name.startswith('__') and node.name.endswith('__')

        self.definitions.append(Definition(
            name=node.name,
            type='function',
            file_path=self.file_path,
            line_number=node.lineno,
            is_public=is_public,
            is_dunder=is_dunder
        ))

        # If inside a class, also record as method
        if self.current_class:
            method_name = f"{self.current_class}.{node.name}"
            self.definitions.append(Definition(
                name=method_name,
                type='method',
                file_path=self.file_path,
                line_number=node.lineno,
                is_public=is_public,
                is_dunder=is_dunder
            ))

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)  # Treat async functions same as regular functions

    def visit_ClassDef(self, node):
        is_public = not node.name.startswith('_')
        is_dunder = node.name.startswith('__') and node.name.endswith('__')

        self.definitions.append(Definition(
            name=node.name,
            type='class',
            file_path=self.file_path,
            line_number=node.lineno,
            is_public=is_public,
            is_dunder=is_dunder
        ))

        # Visit class body with current class context
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports.append((name, alias.name, self.file_path, node.lineno))

    def visit_ImportFrom(self, node):
        if node.module:
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                full_name = f"{node.module}.{alias.name}"
                self.imports.append((name, full_name, self.file_path, node.lineno))

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.usages.append(Usage(
                name=node.id,
                file_path=self.file_path,
                line_number=node.lineno,
                context='name_reference'
            ))
        self.generic_visit(node)

    def visit_Attribute(self, node):
        # Handle method calls like obj.method()
        if isinstance(node.ctx, ast.Load):
            self.usages.append(Usage(
                name=node.attr,
                file_path=self.file_path,
                line_number=node.lineno,
                context='attribute_access'
            ))
        self.generic_visit(node)

def find_all_python_files(root_dir: str) -> List[str]:
    """Find all Python files in the given directory."""
    python_files = []
    for root, dirs, files in os.walk(root_dir):
        # Skip certain directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__']]

        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def analyze_file(file_path: str) -> Tuple[List[Definition], List[Usage], List[Tuple]]:
    """Analyze a single Python file for definitions and usages."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content, filename=file_path)
        analyzer = CodeAnalyzer(file_path)
        analyzer.visit(tree)

        return analyzer.definitions, analyzer.usages, analyzer.imports
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return [], [], []

def find_string_usages(file_path: str, definitions: List[Definition]) -> List[Usage]:
    """Find string-based usages that AST might miss."""
    string_usages = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Look for string references to function/class names
        for line_num, line in enumerate(lines, 1):
            for definition in definitions:
                # Skip if it's in the same file as definition
                if definition.file_path == file_path:
                    continue

                # Look for string references
                if definition.name in line:
                    # Check if it's in a string, comment, or decorator
                    if ('"' + definition.name + '"' in line or
                        "'" + definition.name + "'" in line or
                        f"@{definition.name}" in line or
                        f"# {definition.name}" in line):
                        string_usages.append(Usage(
                            name=definition.name,
                            file_path=file_path,
                            line_number=line_num,
                            context='string_reference'
                        ))
    except Exception as e:
        print(f"Error finding string usages in {file_path}: {e}")

    return string_usages

def analyze_codebase(root_dir: str):
    """Perform comprehensive analysis of the codebase."""
    print(f"Analyzing codebase in: {root_dir}")

    # Find all Python files
    python_files = find_all_python_files(root_dir)
    print(f"Found {len(python_files)} Python files")

    all_definitions = []
    all_usages = []
    all_imports = []

    # Analyze each file
    for file_path in python_files:
        definitions, usages, imports = analyze_file(file_path)
        all_definitions.extend(definitions)
        all_usages.extend(usages)
        all_imports.extend(imports)

        # Also find string-based usages
        string_usages = find_string_usages(file_path, all_definitions)
        all_usages.extend(string_usages)

    print(f"Found {len(all_definitions)} definitions")
    print(f"Found {len(all_usages)} usages")
    print(f"Found {len(all_imports)} imports")

    # Group usages by name
    usage_map = defaultdict(list)
    for usage in all_usages:
        usage_map[usage.name].append(usage)

    # Find unused definitions
    unused_definitions = []
    used_definitions = []

    for definition in all_definitions:
        # Skip dunder methods and certain special cases
        if definition.is_dunder:
            continue

        # Check if the definition is used
        is_used = False
        usages_found = []

        # Direct name match
        if definition.name in usage_map:
            for usage in usage_map[definition.name]:
                # Don't count usage in the same line as definition
                if usage.file_path != definition.file_path or usage.line_number != definition.line_number:
                    is_used = True
                    usages_found.append(usage)

        # For methods, also check class.method pattern
        if definition.type == 'method' and '.' in definition.name:
            class_name, method_name = definition.name.split('.', 1)
            if method_name in usage_map:
                for usage in usage_map[method_name]:
                    if usage.file_path != definition.file_path or usage.line_number != definition.line_number:
                        is_used = True
                        usages_found.append(usage)

        if is_used:
            used_definitions.append((definition, usages_found))
        else:
            unused_definitions.append(definition)

    return unused_definitions, used_definitions, all_definitions

def get_file_size_estimate(file_path: str) -> int:
    """Get line count of a file as size estimate."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except:
        return 0

def calculate_cleanup_impact(unused_definitions: List[Definition]) -> Dict[str, Dict]:
    """Calculate cleanup impact by file and priority."""
    by_file = defaultdict(list)
    for definition in unused_definitions:
        relative_path = definition.file_path.replace('/Users/dariapavlova/Desktop/ai-service/', '')
        by_file[relative_path].append(definition)

    file_impact = {}
    for file_path, definitions in by_file.items():
        abs_path = f"/Users/dariapavlova/Desktop/ai-service/{file_path}"
        file_size = get_file_size_estimate(abs_path)

        # Calculate different metrics
        total_unused = len(definitions)
        private_unused = len([d for d in definitions if not d.is_public])
        public_unused = len([d for d in definitions if d.is_public])

        # Assign priority scores
        priority_score = 0

        # High priority files
        if ('exception' in file_path.lower() or
            'main.py' in file_path or
            'monitoring/' in file_path):
            priority_score += 10

        # Size impact (more unused = higher priority)
        if total_unused >= 15:
            priority_score += 8
        elif total_unused >= 10:
            priority_score += 5
        elif total_unused >= 5:
            priority_score += 3

        # Safety (more private = safer = higher priority)
        safety_ratio = private_unused / total_unused if total_unused > 0 else 0
        if safety_ratio >= 0.8:
            priority_score += 5
        elif safety_ratio >= 0.6:
            priority_score += 3

        # File size impact
        if file_size > 0:
            unused_percentage = total_unused / file_size * 100
            if unused_percentage >= 20:
                priority_score += 7
            elif unused_percentage >= 10:
                priority_score += 4

        file_impact[file_path] = {
            'total_unused': total_unused,
            'private_unused': private_unused,
            'public_unused': public_unused,
            'file_size': file_size,
            'unused_percentage': unused_percentage if file_size > 0 else 0,
            'priority_score': priority_score,
            'definitions': definitions
        }

    return file_impact

def generate_priority_report(unused_definitions: List[Definition], all_definitions: List[Definition]):
    """Generate priority-based cleanup report."""

    print("\n" + "="*80)
    print("PRIORITY CLEANUP ANALYSIS")
    print("="*80)

    # Calculate impact
    file_impact = calculate_cleanup_impact(unused_definitions)

    # Sort by priority score
    sorted_files = sorted(file_impact.items(), key=lambda x: x[1]['priority_score'], reverse=True)

    total_definitions = len(all_definitions)
    unused_count = len(unused_definitions)
    unused_percentage = (unused_count / total_definitions * 100) if total_definitions > 0 else 0

    print(f"\nEXECUTIVE SUMMARY:")
    print(f"  Total definitions: {total_definitions}")
    print(f"  Unused definitions: {unused_count} ({unused_percentage:.1f}%)")
    print(f"  Files with unused code: {len(file_impact)}")

    # Estimate cleanup impact
    high_priority_files = [f for f, data in sorted_files if data['priority_score'] >= 8]
    medium_priority_files = [f for f, data in sorted_files if 4 <= data['priority_score'] < 8]
    low_priority_files = [f for f, data in sorted_files if data['priority_score'] < 4]

    print(f"\nCLEANUP OPPORTUNITY:")
    print(f"  High priority files: {len(high_priority_files)}")
    print(f"  Medium priority files: {len(medium_priority_files)}")
    print(f"  Low priority files: {len(low_priority_files)}")

    # Top 10 highest impact files
    print(f"\nTOP 10 HIGHEST IMPACT FILES FOR CLEANUP:")
    print(f"{'File':<60} {'Score':<6} {'Unused':<7} {'%':<6} {'Private':<8}")
    print("-" * 90)

    for i, (file_path, data) in enumerate(sorted_files[:10]):
        print(f"{file_path:<60} {data['priority_score']:<6} {data['total_unused']:<7} {data['unused_percentage']:<6.1f} {data['private_unused']:<8}")

    # Detailed breakdown for highest priority files
    print(f"\n" + "="*80)
    print("DETAILED BREAKDOWN - TOP PRIORITY FILES")
    print("="*80)

    for i, (file_path, data) in enumerate(sorted_files[:5]):
        print(f"\n{i+1}. {file_path}")
        print(f"   Priority Score: {data['priority_score']}")
        print(f"   Total unused: {data['total_unused']} ({data['unused_percentage']:.1f}% of file)")
        print(f"   Private/Safe: {data['private_unused']}, Public/Review: {data['public_unused']}")
        print(f"   Definitions to remove:")

        # Group by type and visibility
        by_type = defaultdict(list)
        for definition in data['definitions']:
            visibility = "private" if not definition.is_public else "public"
            key = f"{definition.type}_{visibility}"
            by_type[key].append(definition)

        for type_vis, defs in sorted(by_type.items()):
            print(f"     {type_vis}: {len(defs)} items")
            # Show first few examples
            for def_item in sorted(defs, key=lambda x: x.line_number)[:3]:
                print(f"       Line {def_item.line_number}: {def_item.name}")
            if len(defs) > 3:
                print(f"       ... and {len(defs) - 3} more")

    # Special focus sections
    print(f"\n" + "="*80)
    print("SPECIAL FOCUS AREAS")
    print("="*80)

    # Exceptions.py analysis
    exceptions_files = [f for f in file_impact.keys() if f.endswith('exceptions.py')]
    if exceptions_files:
        print(f"\nEXCEPTIONS.PY ANALYSIS:")
        for file_path in exceptions_files:
            data = file_impact[file_path]
            print(f"  {file_path}:")
            print(f"    {data['total_unused']} unused exception classes/functions")
            print(f"    Recommendation: Review carefully - some may be needed for future API compatibility")

    # Main.py analysis
    main_files = [f for f in file_impact.keys() if f.endswith('main.py')]
    if main_files:
        print(f"\nMAIN.PY ANALYSIS:")
        for file_path in main_files:
            data = file_impact[file_path]
            print(f"  {file_path}:")
            print(f"    {data['total_unused']} unused definitions")
            print(f"    Recommendation: High impact - clean up unused API models and utilities")

    # Monitoring directory
    monitoring_files = [f for f in file_impact.keys() if 'monitoring/' in f]
    if monitoring_files:
        print(f"\nMONITORING DIRECTORY ANALYSIS:")
        total_monitoring_unused = sum(file_impact[f]['total_unused'] for f in monitoring_files)
        print(f"    {len(monitoring_files)} files with {total_monitoring_unused} total unused definitions")
        print(f"    Recommendation: Medium priority - monitoring code is often added for future use")

    # Generate removal commands
    print(f"\n" + "="*80)
    print("RECOMMENDED CLEANUP SEQUENCE")
    print("="*80)

    print(f"\nPHASE 1 - SAFE REMOVALS (High Priority, Low Risk):")
    phase1_files = [f for f, data in sorted_files if data['priority_score'] >= 8 and data['private_unused'] >= data['total_unused'] * 0.7]
    for file_path in phase1_files[:5]:
        data = file_impact[file_path]
        print(f"  {file_path} - Remove {data['private_unused']} private definitions")

    print(f"\nPHASE 2 - MODERATE REMOVALS (Medium Priority):")
    phase2_files = [f for f, data in sorted_files if 5 <= data['priority_score'] < 8]
    for file_path in phase2_files[:5]:
        data = file_impact[file_path]
        print(f"  {file_path} - Review and remove {data['total_unused']} definitions")

    print(f"\nPHASE 3 - CAREFUL REVIEW (Lower Priority):")
    phase3_files = [f for f, data in sorted_files if data['priority_score'] < 5 and data['total_unused'] >= 3]
    for file_path in phase3_files[:5]:
        data = file_impact[file_path]
        print(f"  {file_path} - Manual review needed for {data['total_unused']} definitions")

    print(f"\nESTIMATED CLEANUP IMPACT:")
    phase1_removals = sum(file_impact[f]['private_unused'] for f in phase1_files)
    phase2_removals = sum(file_impact[f]['total_unused'] for f in phase2_files)
    total_safe_removals = phase1_removals + phase2_removals * 0.7  # Assume 70% of phase 2 is safe

    print(f"  Phase 1 (safe): ~{phase1_removals} definitions")
    print(f"  Phase 2 (review): ~{len(phase2_files) * 5} definitions (estimated)")
    print(f"  Total potential: ~{int(total_safe_removals)} definitions ({total_safe_removals/unused_count*100:.1f}% of unused)")

if __name__ == "__main__":
    # Analyze the src/ai_service directory
    root_directory = "/Users/dariapavlova/Desktop/ai-service/src/ai_service"
    unused_definitions, used_definitions, all_definitions = analyze_codebase(root_directory)
    generate_priority_report(unused_definitions, all_definitions)
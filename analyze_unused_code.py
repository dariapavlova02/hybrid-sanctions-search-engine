#!/usr/bin/env python3
"""
Comprehensive dead code analysis for AI service codebase.
Identifies unused function definitions, class definitions, and imports.
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

def categorize_unused_by_safety(unused_definitions: List[Definition]) -> Dict[str, List[Definition]]:
    """Categorize unused definitions by removal safety."""
    categories = {
        'safe_to_remove': [],           # Private functions/classes with no external dependencies
        'probably_safe': [],            # Public but clearly unused
        'review_required': [],          # Could be used via reflection or external tools
        'keep_for_api': []             # Public API methods that should be kept
    }

    for definition in unused_definitions:
        file_path = definition.file_path

        # Determine safety based on various factors
        if definition.type == 'function':
            if not definition.is_public:  # Private function
                if ('test' in file_path.lower() or
                    'example' in file_path.lower() or
                    'script' in file_path.lower()):
                    categories['safe_to_remove'].append(definition)
                else:
                    categories['probably_safe'].append(definition)
            else:  # Public function
                if ('main.py' in file_path or
                    'cli' in file_path.lower() or
                    '__init__.py' in file_path):
                    categories['keep_for_api'].append(definition)
                elif ('util' in file_path.lower() or
                      'helper' in file_path.lower()):
                    categories['review_required'].append(definition)
                else:
                    categories['probably_safe'].append(definition)

        elif definition.type == 'class':
            if not definition.is_public:  # Private class
                categories['probably_safe'].append(definition)
            else:  # Public class
                if ('exception' in file_path.lower() or
                    'error' in file_path.lower() or
                    'contract' in file_path.lower()):
                    categories['review_required'].append(definition)
                elif '__init__.py' in file_path:
                    categories['keep_for_api'].append(definition)
                else:
                    categories['probably_safe'].append(definition)

        elif definition.type == 'method':
            if definition.name.endswith('.__init__'):
                categories['keep_for_api'].append(definition)
            elif not definition.is_public:
                categories['probably_safe'].append(definition)
            else:
                categories['review_required'].append(definition)

    return categories

def generate_report(unused_definitions: List[Definition], all_definitions: List[Definition]):
    """Generate comprehensive analysis report."""

    print("\n" + "="*80)
    print("DEAD CODE ANALYSIS REPORT")
    print("="*80)

    # Summary statistics
    total_definitions = len(all_definitions)
    unused_count = len(unused_definitions)
    unused_percentage = (unused_count / total_definitions * 100) if total_definitions > 0 else 0

    print(f"\nSUMMARY:")
    print(f"  Total definitions found: {total_definitions}")
    print(f"  Unused definitions: {unused_count}")
    print(f"  Percentage unused: {unused_percentage:.1f}%")

    # Group by file
    by_file = defaultdict(list)
    for definition in unused_definitions:
        relative_path = definition.file_path.replace('/Users/dariapavlova/Desktop/ai-service/', '')
        by_file[relative_path].append(definition)

    # Categorize by safety
    categories = categorize_unused_by_safety(unused_definitions)

    print(f"\nUNUSED DEFINITIONS BY SAFETY CATEGORY:")
    for category, defs in categories.items():
        print(f"  {category}: {len(defs)} definitions")

    print(f"\nUNUSED DEFINITIONS BY FILE:")
    print(f"{'File':<60} {'Count':<8} {'Types'}")
    print("-" * 80)

    for file_path in sorted(by_file.keys()):
        definitions = by_file[file_path]
        count = len(definitions)
        types = set(d.type for d in definitions)
        types_str = ', '.join(sorted(types))
        print(f"{file_path:<60} {count:<8} {types_str}")

    # Detailed breakdown by category
    print(f"\n" + "="*80)
    print("DETAILED BREAKDOWN BY SAFETY CATEGORY")
    print("="*80)

    for category_name, definitions in categories.items():
        if not definitions:
            continue

        print(f"\n{category_name.upper().replace('_', ' ')} ({len(definitions)} items):")
        print("-" * 60)

        by_file_cat = defaultdict(list)
        for definition in definitions:
            relative_path = definition.file_path.replace('/Users/dariapavlova/Desktop/ai-service/', '')
            by_file_cat[relative_path].append(definition)

        for file_path in sorted(by_file_cat.keys()):
            file_definitions = by_file_cat[file_path]
            print(f"\n  {file_path}:")
            for definition in sorted(file_definitions, key=lambda x: x.line_number):
                visibility = "public" if definition.is_public else "private"
                print(f"    Line {definition.line_number:4d}: {definition.type:<8} {definition.name} ({visibility})")

    # Special focus on high-priority files
    print(f"\n" + "="*80)
    print("HIGH-PRIORITY FILES ANALYSIS")
    print("="*80)

    priority_files = ['exceptions.py', 'main.py']
    monitoring_files = [f for f in by_file.keys() if 'monitoring/' in f]

    for priority_file in priority_files:
        matching_files = [f for f in by_file.keys() if f.endswith(priority_file)]
        for file_path in matching_files:
            if file_path in by_file:
                print(f"\n{file_path}:")
                for definition in sorted(by_file[file_path], key=lambda x: x.line_number):
                    print(f"  Line {definition.line_number:4d}: {definition.type} {definition.name}")

    if monitoring_files:
        print(f"\nMONITORING DIRECTORY:")
        for file_path in sorted(monitoring_files):
            if file_path in by_file:
                print(f"\n  {file_path}:")
                for definition in sorted(by_file[file_path], key=lambda x: x.line_number):
                    print(f"    Line {definition.line_number:4d}: {definition.type} {definition.name}")

if __name__ == "__main__":
    # Analyze the src/ai_service directory
    root_directory = "/Users/dariapavlova/Desktop/ai-service/src/ai_service"
    unused_definitions, used_definitions, all_definitions = analyze_codebase(root_directory)
    generate_report(unused_definitions, all_definitions)
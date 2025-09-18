#!/usr/bin/env python3
"""
AI Service Usage Analysis Script

This script analyzes the AI Service codebase to identify unused services, classes,
and functions. It builds a dependency graph and generates a comprehensive report
of potentially dead code.

Usage:
    python scripts/usage_analysis.py

Features:
- Parses all Python files in src/
- Identifies imports and function/class calls
- Builds a dependency graph
- Finds unused services, classes, and functions
- Generates detailed reports with statistics
"""

import ast
import os
import sys
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
import json
import argparse


class CodeAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze Python code for definitions and usage."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.module_name = self._get_module_name(filepath)

        # Definitions in this file
        self.classes: Set[str] = set()
        self.functions: Set[str] = set()
        self.methods: Dict[str, Set[str]] = defaultdict(set)

        # Usage in this file
        self.imports: Dict[str, Set[str]] = defaultdict(set)  # module -> {imported_names}
        self.function_calls: Set[str] = set()
        self.attribute_access: Set[str] = set()
        self.class_instantiations: Set[str] = set()

        # Context tracking
        self.current_class: Optional[str] = None
        self.import_aliases: Dict[str, str] = {}  # alias -> real_name

    def _get_module_name(self, filepath: str) -> str:
        """Convert file path to module name."""
        # Convert to relative path from src/
        rel_path = Path(filepath).relative_to(Path(filepath).parts[0])
        parts = rel_path.parts

        # Find src/ in the path
        try:
            src_idx = parts.index('src')
            module_parts = parts[src_idx + 1:]
        except ValueError:
            module_parts = parts

        # Remove .py extension and convert to module name
        if module_parts[-1].endswith('.py'):
            module_parts = module_parts[:-1] + (module_parts[-1][:-3],)

        # Remove __init__ if present
        if module_parts[-1] == '__init__':
            module_parts = module_parts[:-1]

        return '.'.join(module_parts) if module_parts else ''

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions."""
        self.classes.add(node.name)
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions."""
        if self.current_class:
            self.methods[self.current_class].add(node.name)
        else:
            self.functions.add(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions."""
        if self.current_class:
            self.methods[self.current_class].add(node.name)
        else:
            self.functions.add(node.name)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statements."""
        for alias in node.names:
            module = alias.name
            name = alias.asname if alias.asname else alias.name
            if alias.asname:
                self.import_aliases[alias.asname] = alias.name
            self.imports[module].add(name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from ... import statements."""
        if node.module:
            for alias in node.names:
                name = alias.name
                asname = alias.asname if alias.asname else name
                if alias.asname:
                    self.import_aliases[asname] = f"{node.module}.{name}"
                self.imports[node.module].add(name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function calls."""
        func_name = self._get_call_name(node.func)
        if func_name:
            self.function_calls.add(func_name)
            # Also consider it a class instantiation
            self.class_instantiations.add(func_name)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Visit attribute access."""
        attr_name = self._get_attribute_name(node)
        if attr_name:
            self.attribute_access.add(attr_name)
        self.generic_visit(node)

    def _get_call_name(self, node: ast.AST) -> Optional[str]:
        """Extract function name from call node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_attribute_name(node)
        return None

    def _get_attribute_name(self, node: ast.Attribute) -> Optional[str]:
        """Extract attribute name from attribute node."""
        if isinstance(node.value, ast.Name):
            base = node.value.id
            # Resolve aliases
            if base in self.import_aliases:
                base = self.import_aliases[base]
            return f"{base}.{node.attr}"
        elif isinstance(node.value, ast.Attribute):
            base = self._get_attribute_name(node.value)
            if base:
                return f"{base}.{node.attr}"
        return None


class UsageAnalyzer:
    """Main analyzer for finding unused code."""

    def __init__(self, src_dir: str, exclude_patterns: List[str] = None):
        self.src_dir = Path(src_dir)
        self.exclude_patterns = exclude_patterns or ['__pycache__', 'test_', 'tests/']

        # Analysis results
        self.files: Dict[str, CodeAnalyzer] = {}
        self.all_definitions: Dict[str, Dict[str, str]] = {
            'classes': {},      # name -> file
            'functions': {},    # name -> file
            'methods': {}       # class.method -> file
        }
        self.usage_graph: Dict[str, Set[str]] = defaultdict(set)
        self.import_graph: Dict[str, Set[str]] = defaultdict(set)

    def should_exclude_file(self, filepath: str) -> bool:
        """Check if file should be excluded from analysis."""
        path_str = str(filepath)
        return any(pattern in path_str for pattern in self.exclude_patterns)

    def analyze_codebase(self) -> None:
        """Analyze all Python files in the codebase."""
        print("🔍 Analyzing codebase...")

        # Find all Python files
        python_files = list(self.src_dir.rglob("*.py"))
        python_files = [f for f in python_files if not self.should_exclude_file(f)]

        print(f"📁 Found {len(python_files)} Python files to analyze")

        # Analyze each file
        for filepath in python_files:
            try:
                self._analyze_file(filepath)
            except Exception as e:
                print(f"⚠️  Error analyzing {filepath}: {e}")

        # Build usage and import graphs
        self._build_graphs()

    def _analyze_file(self, filepath: Path) -> None:
        """Analyze a single Python file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            analyzer = CodeAnalyzer(str(filepath))
            analyzer.visit(tree)

            self.files[str(filepath)] = analyzer

            # Register definitions
            for class_name in analyzer.classes:
                self.all_definitions['classes'][class_name] = str(filepath)

            for func_name in analyzer.functions:
                self.all_definitions['functions'][func_name] = str(filepath)

            for class_name, methods in analyzer.methods.items():
                for method_name in methods:
                    full_name = f"{class_name}.{method_name}"
                    self.all_definitions['methods'][full_name] = str(filepath)

        except Exception as e:
            print(f"⚠️  Could not parse {filepath}: {e}")

    def _build_graphs(self) -> None:
        """Build usage and import dependency graphs."""
        print("🔗 Building dependency graphs...")

        for filepath, analyzer in self.files.items():
            # Import graph
            for module, names in analyzer.imports.items():
                if not self._is_external_import(module):
                    self.import_graph[analyzer.module_name].add(module)

            # Usage graph - track what this file uses
            all_used = (analyzer.function_calls |
                       analyzer.class_instantiations |
                       analyzer.attribute_access)

            for used_name in all_used:
                # Clean up the name and track usage
                clean_name = self._clean_usage_name(used_name)
                if clean_name:
                    self.usage_graph[analyzer.module_name].add(clean_name)

    def _is_external_import(self, module: str) -> bool:
        """Check if import is external (stdlib or third-party)."""
        if not module:
            return True

        # Standard library modules (partial list)
        stdlib_modules = {
            'os', 'sys', 'json', 'ast', 'pathlib', 'collections', 'typing',
            'dataclasses', 'enum', 'functools', 'itertools', 'datetime',
            'unittest', 'pytest', 'logging', 'asyncio', 're', 'math',
            'random', 'string', 'time', 'uuid', 'copy', 'pickle'
        }

        # Check if it's a standard library module
        if module.split('.')[0] in stdlib_modules:
            return True

        # Check if it's a third-party package
        third_party_prefixes = [
            'fastapi', 'pydantic', 'sqlalchemy', 'alembic', 'pytest',
            'numpy', 'pandas', 'requests', 'aiohttp', 'uvicorn',
            'pymorphy3', 'langdetect', 'elasticsearch'
        ]

        return any(module.startswith(prefix) for prefix in third_party_prefixes)

    def _clean_usage_name(self, name: str) -> Optional[str]:
        """Clean and normalize usage names for matching."""
        if not name:
            return None

        # Remove common prefixes that indicate external usage
        if any(name.startswith(prefix) for prefix in ['self.', 'super().', 'cls.']):
            return None

        # Handle dotted names - extract the base name
        if '.' in name:
            parts = name.split('.')
            # For method calls like obj.method, we want to track 'method'
            return parts[-1]

        return name

    def find_unused_code(self) -> Dict[str, Any]:
        """Find unused classes, functions, and methods."""
        print("🕵️  Finding unused code...")

        # Collect all usages across the codebase
        all_usages = set()
        for used_names in self.usage_graph.values():
            all_usages.update(used_names)

        # Also include imported names as used
        for filepath, analyzer in self.files.items():
            for module, names in analyzer.imports.items():
                all_usages.update(names)

        # Find unused definitions
        unused = {
            'classes': [],
            'functions': [],
            'methods': []
        }

        for class_name, filepath in self.all_definitions['classes'].items():
            if class_name not in all_usages:
                unused['classes'].append({
                    'name': class_name,
                    'file': filepath,
                    'type': 'class'
                })

        for func_name, filepath in self.all_definitions['functions'].items():
            # Skip special functions
            if not func_name.startswith('_') and func_name not in all_usages:
                unused['functions'].append({
                    'name': func_name,
                    'file': filepath,
                    'type': 'function'
                })

        for method_name, filepath in self.all_definitions['methods'].items():
            class_name, method = method_name.split('.', 1)
            # Skip special methods and private methods
            if (not method.startswith('_') and
                method not in all_usages and
                method_name not in all_usages):
                unused['methods'].append({
                    'name': method_name,
                    'file': filepath,
                    'type': 'method'
                })

        return unused

    def analyze_imports(self) -> Dict[str, Any]:
        """Analyze import relationships."""
        print("📦 Analyzing imports...")

        import_stats = {
            'total_imports': 0,
            'internal_imports': 0,
            'external_imports': 0,
            'unused_imports': [],
            'import_chains': []
        }

        for filepath, analyzer in self.files.items():
            for module, names in analyzer.imports.items():
                import_stats['total_imports'] += len(names)

                if self._is_external_import(module):
                    import_stats['external_imports'] += len(names)
                else:
                    import_stats['internal_imports'] += len(names)

                    # Check for unused imports
                    for name in names:
                        if (name not in analyzer.function_calls and
                            name not in analyzer.class_instantiations and
                            name not in analyzer.attribute_access):
                            import_stats['unused_imports'].append({
                                'name': name,
                                'module': module,
                                'file': filepath
                            })

        return import_stats

    def generate_statistics(self) -> Dict[str, Any]:
        """Generate overall statistics."""
        stats = {
            'total_files': len(self.files),
            'total_classes': len(self.all_definitions['classes']),
            'total_functions': len(self.all_definitions['functions']),
            'total_methods': len(self.all_definitions['methods']),
            'files_by_size': [],
            'largest_classes': [],
            'most_imported_modules': []
        }

        # File sizes by definitions
        file_sizes = []
        for filepath, analyzer in self.files.items():
            size = (len(analyzer.classes) +
                   len(analyzer.functions) +
                   sum(len(methods) for methods in analyzer.methods.values()))
            file_sizes.append({
                'file': filepath,
                'definitions': size,
                'classes': len(analyzer.classes),
                'functions': len(analyzer.functions),
                'methods': sum(len(methods) for methods in analyzer.methods.values())
            })

        stats['files_by_size'] = sorted(file_sizes,
                                       key=lambda x: x['definitions'],
                                       reverse=True)[:10]

        # Largest classes by method count
        class_sizes = []
        for filepath, analyzer in self.files.items():
            for class_name, methods in analyzer.methods.items():
                class_sizes.append({
                    'class': class_name,
                    'file': filepath,
                    'methods': len(methods)
                })

        stats['largest_classes'] = sorted(class_sizes,
                                        key=lambda x: x['methods'],
                                        reverse=True)[:10]

        # Most imported modules
        import_counts = Counter()
        for filepath, analyzer in self.files.items():
            for module in analyzer.imports:
                if not self._is_external_import(module):
                    import_counts[module] += 1

        stats['most_imported_modules'] = [
            {'module': module, 'import_count': count}
            for module, count in import_counts.most_common(10)
        ]

        return stats

    def generate_report(self, output_file: Optional[str] = None) -> str:
        """Generate a comprehensive analysis report."""
        print("📊 Generating analysis report...")

        unused = self.find_unused_code()
        imports = self.analyze_imports()
        stats = self.generate_statistics()

        # Calculate unused percentages
        total_definitions = (stats['total_classes'] +
                           stats['total_functions'] +
                           stats['total_methods'])
        total_unused = (len(unused['classes']) +
                       len(unused['functions']) +
                       len(unused['methods']))

        unused_percentage = (total_unused / total_definitions * 100) if total_definitions > 0 else 0

        report = []
        report.append("# AI Service Usage Analysis Report")
        report.append("=" * 50)
        report.append("")

        # Executive Summary
        report.append("## Executive Summary")
        report.append(f"- **Total Files Analyzed**: {stats['total_files']}")
        report.append(f"- **Total Definitions**: {total_definitions}")
        report.append(f"- **Unused Definitions**: {total_unused} ({unused_percentage:.1f}%)")
        report.append(f"- **Classes**: {stats['total_classes']} ({len(unused['classes'])} unused)")
        report.append(f"- **Functions**: {stats['total_functions']} ({len(unused['functions'])} unused)")
        report.append(f"- **Methods**: {stats['total_methods']} ({len(unused['methods'])} unused)")
        report.append("")

        # Unused Code Section
        report.append("## Unused Code Analysis")
        report.append("")

        if unused['classes']:
            report.append("### Unused Classes")
            for item in sorted(unused['classes'], key=lambda x: x['name']):
                rel_path = str(Path(item['file']).relative_to(self.src_dir.parent))
                report.append(f"- **{item['name']}** in `{rel_path}`")
            report.append("")

        if unused['functions']:
            report.append("### Unused Functions")
            for item in sorted(unused['functions'], key=lambda x: x['name']):
                rel_path = str(Path(item['file']).relative_to(self.src_dir.parent))
                report.append(f"- **{item['name']}** in `{rel_path}`")
            report.append("")

        if unused['methods']:
            report.append("### Unused Methods")
            for item in sorted(unused['methods'], key=lambda x: x['name']):
                rel_path = str(Path(item['file']).relative_to(self.src_dir.parent))
                report.append(f"- **{item['name']}** in `{rel_path}`")
            report.append("")

        # Import Analysis
        report.append("## Import Analysis")
        report.append(f"- **Total Imports**: {imports['total_imports']}")
        report.append(f"- **Internal Imports**: {imports['internal_imports']}")
        report.append(f"- **External Imports**: {imports['external_imports']}")
        report.append("")

        if imports['unused_imports']:
            report.append("### Potentially Unused Imports")
            for item in imports['unused_imports'][:20]:  # Limit to first 20
                rel_path = str(Path(item['file']).relative_to(self.src_dir.parent))
                report.append(f"- **{item['name']}** from `{item['module']}` in `{rel_path}`")
            if len(imports['unused_imports']) > 20:
                report.append(f"... and {len(imports['unused_imports']) - 20} more")
            report.append("")

        # Statistics
        report.append("## File Statistics")
        report.append("")

        report.append("### Largest Files (by definitions)")
        for item in stats['files_by_size']:
            rel_path = str(Path(item['file']).relative_to(self.src_dir.parent))
            report.append(f"- `{rel_path}`: {item['definitions']} definitions "
                         f"({item['classes']} classes, {item['functions']} functions, "
                         f"{item['methods']} methods)")
        report.append("")

        if stats['largest_classes']:
            report.append("### Largest Classes (by method count)")
            for item in stats['largest_classes']:
                rel_path = str(Path(item['file']).relative_to(self.src_dir.parent))
                report.append(f"- **{item['class']}**: {item['methods']} methods in `{rel_path}`")
            report.append("")

        if stats['most_imported_modules']:
            report.append("### Most Imported Internal Modules")
            for item in stats['most_imported_modules']:
                report.append(f"- **{item['module']}**: imported {item['import_count']} times")
            report.append("")

        # Recommendations
        report.append("## Recommendations")
        report.append("")

        if total_unused > 0:
            report.append("### Code Cleanup Opportunities")
            report.append("1. **Review unused classes**: Consider removing or documenting why they're kept")
            report.append("2. **Remove unused functions**: Clean up functions that are no longer called")
            report.append("3. **Clean up unused methods**: Remove methods that aren't used by their classes")
            report.append("4. **Verify unused imports**: Remove imports that aren't being used")
            report.append("")

        report.append("### Analysis Notes")
        report.append("- This analysis may have false positives for code used via:")
        report.append("  - String-based imports (importlib, getattr)")
        report.append("  - Dynamic method calls")
        report.append("  - External API endpoints")
        report.append("  - Configuration-based usage")
        report.append("- Always verify before removing code!")
        report.append("")

        report_text = "\n".join(report)

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"📄 Report saved to {output_file}")

        return report_text


def main():
    """Main entry point for the usage analysis script."""
    parser = argparse.ArgumentParser(description='Analyze AI Service codebase for unused code')
    parser.add_argument('--src-dir', default='src',
                       help='Source directory to analyze (default: src)')
    parser.add_argument('--output', '-o',
                       help='Output file for the report (default: print to stdout)')
    parser.add_argument('--json', action='store_true',
                       help='Output detailed results as JSON')
    parser.add_argument('--exclude', nargs='*',
                       default=['__pycache__', 'test_', 'tests/'],
                       help='Patterns to exclude from analysis')

    args = parser.parse_args()

    # Ensure we're in the right directory
    if not os.path.exists(args.src_dir):
        print(f"❌ Source directory '{args.src_dir}' not found!")
        print("Make sure you're running this script from the repository root.")
        sys.exit(1)

    # Run analysis
    analyzer = UsageAnalyzer(args.src_dir, args.exclude)
    analyzer.analyze_codebase()

    if args.json:
        # Output detailed JSON results
        results = {
            'unused_code': analyzer.find_unused_code(),
            'import_analysis': analyzer.analyze_imports(),
            'statistics': analyzer.generate_statistics()
        }

        output = json.dumps(results, indent=2, default=str)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"📄 JSON results saved to {args.output}")
        else:
            print(output)
    else:
        # Generate and output the report
        report = analyzer.generate_report(args.output)

        if not args.output:
            print("\n" + report)


if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""
Migration Helper Script for AI Service Architecture Consolidation

This script helps migrate from old orchestrator implementations to UnifiedOrchestrator.
It scans the codebase for deprecated usage patterns and suggests fixes.

Usage:
    python migration_helper.py --scan          # Scan for deprecated patterns
    python migration_helper.py --migrate       # Interactive migration help
    python migration_helper.py --test          # Test unified architecture
"""

import argparse
import ast
import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict

# Add project to path
project_root = Path(__file__).parent / "src"
sys.path.insert(0, str(project_root))

class DeprecatedPatternScanner:
    """Scanner for deprecated orchestrator patterns"""

    DEPRECATED_IMPORTS = [
        "from ai_service.core.orchestrator_service import OrchestratorService",
        "from ai_service.core.orchestrator_v2 import OrchestratorV2",
        "from ai_service.orchestration.clean_orchestrator import CleanOrchestrator",
        "from ai_service.services.core.orchestrator_v2 import OrchestratorV2",
    ]

    DEPRECATED_CLASSES = [
        "OrchestratorService",
        "OrchestratorV2",
        "CleanOrchestrator"
    ]

    def __init__(self):
        self.findings = []

    def scan_file(self, file_path: Path) -> List[Dict]:
        """Scan a Python file for deprecated patterns"""
        findings = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for deprecated imports
            for line_num, line in enumerate(content.splitlines(), 1):
                for deprecated_import in self.DEPRECATED_IMPORTS:
                    if deprecated_import in line:
                        findings.append({
                            "file": str(file_path),
                            "line": line_num,
                            "type": "deprecated_import",
                            "content": line.strip(),
                            "suggestion": self._get_import_suggestion(deprecated_import)
                        })

            # Parse AST for class instantiations
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                        if node.func.id in self.DEPRECATED_CLASSES:
                            findings.append({
                                "file": str(file_path),
                                "line": node.lineno,
                                "type": "deprecated_instantiation",
                                "content": f"{node.func.id}(...)",
                                "suggestion": self._get_instantiation_suggestion(node.func.id)
                            })
            except SyntaxError:
                # Skip files with syntax errors
                pass

        except Exception as e:
            print(f"Warning: Could not scan {file_path}: {e}")

        return findings

    def _get_import_suggestion(self, deprecated_import: str) -> str:
        """Get suggested replacement for deprecated import"""
        return (
            "# Replace with:\n"
            "from ai_service.core.orchestrator_factory import OrchestratorFactory\n"
            "# Then use: orchestrator = await OrchestratorFactory.create_production_orchestrator()"
        )

    def _get_instantiation_suggestion(self, class_name: str) -> str:
        """Get suggested replacement for deprecated class instantiation"""
        return (
            f"# Replace {class_name}(...) with:\n"
            "orchestrator = await OrchestratorFactory.create_production_orchestrator()\n"
            "# Or for testing:\n"
            "orchestrator = await OrchestratorFactory.create_testing_orchestrator()"
        )

    def scan_directory(self, directory: Path) -> List[Dict]:
        """Scan directory recursively for deprecated patterns"""
        all_findings = []

        for py_file in directory.rglob("*.py"):
            # Skip certain directories
            if any(skip_dir in str(py_file) for skip_dir in [".git", "__pycache__", "venv", "node_modules"]):
                continue

            findings = self.scan_file(py_file)
            all_findings.extend(findings)

        return all_findings


def print_scan_results(findings: List[Dict]):
    """Print scan results in a readable format"""
    if not findings:
        print("✅ No deprecated orchestrator patterns found!")
        return

    print(f"🔍 Found {len(findings)} deprecated patterns:")
    print("=" * 60)

    by_file = {}
    for finding in findings:
        file_path = finding["file"]
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(finding)

    for file_path, file_findings in by_file.items():
        print(f"\n📁 {file_path}")
        print("-" * 40)

        for finding in file_findings:
            print(f"  Line {finding['line']}: {finding['type']}")
            print(f"    Code: {finding['content']}")
            print(f"    💡 Suggestion:")
            for line in finding['suggestion'].split('\n'):
                print(f"       {line}")
            print()


def interactive_migration():
    """Interactive migration guidance"""
    print("🚀 Interactive Migration Guide")
    print("=" * 40)

    print("\n1. Update imports in your code:")
    print("   OLD: from ai_service.core.orchestrator_service import OrchestratorService")
    print("   NEW: from ai_service.core.orchestrator_factory import OrchestratorFactory")

    print("\n2. Update orchestrator initialization:")
    print("   OLD: orchestrator = OrchestratorService(cache_size=10000)")
    print("   NEW: orchestrator = await OrchestratorFactory.create_production_orchestrator()")

    print("\n3. Update processing calls:")
    print("   OLD: result = await orchestrator.process_text(text)")
    print("   NEW: result = await orchestrator.process(text)")

    print("\n4. Update result handling:")
    print("   The new UnifiedProcessingResult has additional fields:")
    print("   - result.signals.persons  # Structured person data")
    print("   - result.signals.organizations  # Structured org data")
    print("   - result.trace  # Token-level tracing")

    print("\n5. Run tests:")
    print("   python -m pytest tests/integration/test_pipeline_end2end.py")

    print("\n📖 See CONSOLIDATION_SUMMARY.md for complete migration guide")


async def test_unified_architecture():
    """Test the unified architecture"""
    print("🧪 Testing Unified Architecture")
    print("=" * 40)

    try:
        # Import test runner
        from test_unified_architecture import test_unified_architecture

        print("Running unified architecture test...")
        success = await test_unified_architecture()

        if success:
            print("✅ Unified architecture test passed!")
            return True
        else:
            print("❌ Unified architecture test failed!")
            return False

    except ImportError:
        print("❌ Test runner not found. Make sure test_unified_architecture.py exists.")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


def main():
    """Main migration helper entry point"""
    parser = argparse.ArgumentParser(description="AI Service Migration Helper")
    parser.add_argument("--scan", action="store_true", help="Scan for deprecated patterns")
    parser.add_argument("--migrate", action="store_true", help="Interactive migration help")
    parser.add_argument("--test", action="store_true", help="Test unified architecture")
    parser.add_argument("--directory", default=".", help="Directory to scan (default: current)")

    args = parser.parse_args()

    if args.scan:
        print("🔍 Scanning for deprecated orchestrator patterns...")
        scanner = DeprecatedPatternScanner()
        directory = Path(args.directory)
        findings = scanner.scan_directory(directory)
        print_scan_results(findings)

        if findings:
            print("\n💡 Run --migrate for interactive migration guidance")

    elif args.migrate:
        interactive_migration()

    elif args.test:
        import asyncio
        success = asyncio.run(test_unified_architecture())
        sys.exit(0 if success else 1)

    else:
        print("AI Service Migration Helper")
        print("Use --help for options")
        print("\nQuick start:")
        print("  python migration_helper.py --scan     # Find deprecated patterns")
        print("  python migration_helper.py --migrate  # Get migration help")
        print("  python migration_helper.py --test     # Test new architecture")


if __name__ == "__main__":
    main()
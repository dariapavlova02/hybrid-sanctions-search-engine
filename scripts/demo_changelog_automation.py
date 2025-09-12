#!/usr/bin/env python3
"""
Demonstration of changelog automation workflow
Shows how the changelog automation works in practice
"""

import os
import sys
import tempfile
from pathlib import Path

# Add the project root to the path so we can import our modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.integration.test_changelog_automation import (
    ChangelogAutomation,
    ChangelogWorkflow,
    ChangelogValidator,
    ChangelogEntry
)


def demonstrate_changelog_automation():
    """Demonstrate the complete changelog automation workflow"""
    print("🚀 Changelog Automation Demonstration")
    print("=" * 50)

    # Create temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        demo_path = Path(temp_dir)
        changelog_path = demo_path / "CHANGELOG.md"

        print(f"📁 Demo directory: {demo_path}")
        print()

        # Step 1: Create a new changelog
        print("📝 Step 1: Creating new changelog...")
        automation = ChangelogAutomation(str(changelog_path))
        automation.create_empty_changelog()

        print("✅ Created new changelog file")
        print()

        # Step 2: Add some entries
        print("📝 Step 2: Adding changelog entries...")

        entries = [
            ChangelogEntry("1.0.0", "2025-01-01", ["Initial release", "Basic functionality"], "Added"),
            ChangelogEntry("1.1.0", "2025-01-15", ["New feature X", "Performance improvements"], "Added"),
            ChangelogEntry("1.1.1", "2025-01-20", ["Critical bug fix", "Security patch"], "Fixed")
        ]

        for entry in entries:
            automation.add_entry(entry)
            print(f"  ✅ Added version {entry.version}")

        print()

        # Step 3: Validate the changelog
        print("🔍 Step 3: Validating changelog format...")
        validator = ChangelogValidator()
        result = validator.validate_keep_a_changelog_format(str(changelog_path))

        if result["valid"]:
            print("✅ Changelog format is valid")
            print(f"  📊 Found {result['versions_found']} version entries")
        else:
            print("❌ Changelog validation failed:")
            for error in result["errors"]:
                print(f"  - {error}")

        print()

        # Step 4: Show changelog contents
        print("📄 Step 4: Current changelog contents:")
        print("-" * 30)
        with open(changelog_path, 'r') as f:
            content = f.read()
            # Show first 20 lines
            lines = content.split('\n')[:20]
            for i, line in enumerate(lines, 1):
                if line.strip():
                    print(f"{i:2d}: {line}")

        if len(content.split('\n')) > 20:
            print("    ... (truncated)")

        print()

        # Step 5: Demonstrate workflow integration
        print("🔄 Step 5: Testing workflow integration...")

        # Create mock git repo structure
        git_dir = demo_path / ".git"
        git_dir.mkdir()

        workflow = ChangelogWorkflow(str(demo_path))

        # Test CI readiness
        ci_result = workflow.validate_for_ci()
        print(f"🔧 CI readiness: {'✅ Ready' if ci_result['valid'] else '❌ Not ready'}")

        if ci_result["has_unreleased"]:
            print("  📝 Has unreleased section")

        # Test PR processing
        pr_data = {
            "title": "Add new authentication feature",
            "body": "This PR adds OAuth2 authentication support",
            "labels": ["feature", "enhancement"]
        }

        pr_entry = workflow.process_pr_changelog(pr_data)
        if pr_entry:
            print(f"  📋 PR would create entry: {pr_entry.version} - {pr_entry.changes[0]}")

        print()

        # Step 6: Demonstrate automation utilities
        print("🛠️  Step 6: Testing automation utilities...")

        # Parse and analyze
        parsed = automation.parse_changelog()
        print(f"  📊 Total versions: {len(parsed['versions'])}")

        latest_version = automation.get_latest_version()
        print(f"  🏷️  Latest version: {latest_version}")

        # Test semantic versioning
        test_versions = ["1.0.0", "2.1.3", "1.0.0-alpha.1", "invalid.version"]
        print("  🔍 Semantic version validation:")
        for version in test_versions:
            is_valid = validator.is_valid_semver(version)
            status = "✅" if is_valid else "❌"
            print(f"    {status} {version}")

        print()

        # Step 7: Show automation benefits
        print("💡 Step 7: Changelog automation benefits:")
        benefits = [
            "✅ Consistent formatting following Keep a Changelog standard",
            "✅ Automatic validation in CI/CD pipeline",
            "✅ Integration with Git workflows and PR processes",
            "✅ Semantic versioning compliance checking",
            "✅ Automated release notes generation",
            "✅ Pre-commit hooks for validation",
            "✅ CLI tools for manual management",
            "✅ Comprehensive test coverage"
        ]

        for benefit in benefits:
            print(f"  {benefit}")

        print()

        print("🎉 Demonstration completed successfully!")
        print(f"📁 Demo files were created in: {demo_path}")
        print("   (Temporary directory - will be cleaned up automatically)")


def demonstrate_cli_tools():
    """Demonstrate CLI tools functionality"""
    print()
    print("🔧 CLI Tools Demonstration")
    print("=" * 30)

    # Show available commands
    print("📋 Available CLI commands:")
    commands = [
        ("validate", "Validate changelog format"),
        ("create", "Create new changelog"),
        ("add", "Add new changelog entry"),
        ("auto-update", "Auto-update from git commits"),
        ("ci-check", "Check CI readiness"),
        ("release-notes", "Generate release notes"),
        ("list", "List all versions")
    ]

    for cmd, desc in commands:
        print(f"  📝 {cmd:<12} - {desc}")

    print()
    print("💡 Example usage:")
    examples = [
        "poetry run python scripts/changelog_tools.py validate",
        "poetry run python scripts/changelog_tools.py create",
        "poetry run python scripts/changelog_tools.py add 1.2.0 'New feature' 'Bug fix'",
        "poetry run python scripts/changelog_tools.py list",
        "poetry run python scripts/changelog_tools.py ci-check"
    ]

    for example in examples:
        print(f"  $ {example}")


def demonstrate_github_workflow():
    """Demonstrate GitHub workflow integration"""
    print()
    print("🔄 GitHub Workflow Integration")
    print("=" * 35)

    print("📋 Workflow triggers:")
    triggers = [
        ("Push to main/develop", "Validates changelog format"),
        ("Pull Request", "Checks for changelog updates, suggests entries"),
        ("Release created", "Auto-generates release changelog entry"),
        ("Manual trigger", "Allows for manual changelog operations")
    ]

    for trigger, action in triggers:
        print(f"  🔄 {trigger:<20} → {action}")

    print()
    print("🛡️  Workflow protections:")
    protections = [
        "Validates Keep a Changelog format compliance",
        "Ensures semantic versioning for all entries",
        "Checks for unreleased section in PRs",
        "Runs comprehensive test suite",
        "Auto-commits changelog updates with [skip ci]",
        "Generates release notes from changelog data"
    ]

    for protection in protections:
        print(f"  ✅ {protection}")


if __name__ == "__main__":
    try:
        demonstrate_changelog_automation()
        demonstrate_cli_tools()
        demonstrate_github_workflow()
    except KeyboardInterrupt:
        print("\n⚠️  Demonstration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        sys.exit(1)
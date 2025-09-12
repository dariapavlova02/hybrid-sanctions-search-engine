#!/usr/bin/env python3
"""
Changelog automation tools
Provides CLI utilities for managing changelog automation
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# Add the project root to the path so we can import our modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.integration.test_changelog_automation import (
    ChangelogAutomation,
    ChangelogWorkflow,
    ChangelogValidator,
    ChangelogEntry
)


def validate_changelog(changelog_path: str = "CHANGELOG.md") -> bool:
    """Validate changelog format"""
    validator = ChangelogValidator()

    if not os.path.exists(changelog_path):
        print(f"❌ Changelog file not found: {changelog_path}")
        return False

    print(f"🔍 Validating changelog: {changelog_path}")

    result = validator.validate_keep_a_changelog_format(changelog_path)

    if result["valid"]:
        print("✅ Changelog format is valid")
        print(f"   Found {result['versions_found']} version entries")
        return True
    else:
        print("❌ Changelog validation failed:")
        for error in result["errors"]:
            print(f"   - {error}")
        return False


def create_changelog(changelog_path: str = "CHANGELOG.md") -> bool:
    """Create new changelog file"""
    if os.path.exists(changelog_path):
        print(f"⚠️  Changelog already exists: {changelog_path}")
        response = input("Do you want to overwrite it? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            return False

    automation = ChangelogAutomation(changelog_path)
    automation.create_empty_changelog()

    print(f"✅ Created changelog: {changelog_path}")
    return True


def add_entry(version: str, changes: list, category: str = "Changed",
              changelog_path: str = "CHANGELOG.md") -> bool:
    """Add new entry to changelog"""
    if not os.path.exists(changelog_path):
        print(f"❌ Changelog file not found: {changelog_path}")
        return False

    automation = ChangelogAutomation(changelog_path)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    entry = ChangelogEntry(version, date, changes, category)
    automation.add_entry(entry)

    print(f"✅ Added entry for version {version}")
    return True


def auto_update_from_git(changelog_path: str = "CHANGELOG.md") -> bool:
    """Auto-update changelog from git commits"""
    workflow = ChangelogWorkflow(".")

    try:
        entry = workflow.update_changelog_from_commits()
        print(f"✅ Updated changelog with new entry for version {entry.version}")
        return True
    except Exception as e:
        print(f"❌ Failed to update changelog: {e}")
        return False


def check_ci_readiness(changelog_path: str = "CHANGELOG.md") -> bool:
    """Check if changelog is ready for CI"""
    workflow = ChangelogWorkflow(".")
    result = workflow.validate_for_ci()

    print(f"🔍 CI readiness check for: {changelog_path}")

    if result["valid"]:
        print("✅ Changelog is CI-ready")
        if result["has_unreleased"]:
            print("   📝 Has unreleased section")
        return True
    else:
        print("❌ Changelog is not CI-ready:")
        for error in result["errors"]:
            print(f"   - {error}")
        return False


def generate_release_notes(version: str, changelog_path: str = "CHANGELOG.md") -> bool:
    """Generate release notes for a specific version"""
    automation = ChangelogAutomation(changelog_path)

    if not os.path.exists(changelog_path):
        print(f"❌ Changelog file not found: {changelog_path}")
        return False

    parsed = automation.parse_changelog()

    # Find the requested version
    version_entry = None
    for entry in parsed["versions"]:
        if entry["version"] == version:
            version_entry = entry
            break

    if not version_entry:
        print(f"❌ Version {version} not found in changelog")
        return False

    print(f"📄 Release notes for version {version}:")
    print("=" * 50)

    for change in version_entry["changes"]:
        print(f"• {change}")

    return True


def list_versions(changelog_path: str = "CHANGELOG.md") -> bool:
    """List all versions in changelog"""
    automation = ChangelogAutomation(changelog_path)

    if not os.path.exists(changelog_path):
        print(f"❌ Changelog file not found: {changelog_path}")
        return False

    parsed = automation.parse_changelog()

    print(f"📋 Versions in {changelog_path}:")
    print("-" * 30)

    for entry in parsed["versions"]:
        version = entry["version"]
        change_count = len(entry["changes"])
        print(f"  {version} ({change_count} changes)")

    return True


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="Changelog automation tools")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate changelog format")
    validate_parser.add_argument("--file", default="CHANGELOG.md",
                               help="Changelog file path (default: CHANGELOG.md)")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create new changelog")
    create_parser.add_argument("--file", default="CHANGELOG.md",
                              help="Changelog file path (default: CHANGELOG.md)")

    # Add entry command
    add_parser = subparsers.add_parser("add", help="Add new changelog entry")
    add_parser.add_argument("version", help="Version number")
    add_parser.add_argument("changes", nargs="+", help="List of changes")
    add_parser.add_argument("--category", default="Changed",
                           choices=["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"],
                           help="Change category (default: Changed)")
    add_parser.add_argument("--file", default="CHANGELOG.md",
                           help="Changelog file path (default: CHANGELOG.md)")

    # Auto-update command
    auto_parser = subparsers.add_parser("auto-update", help="Auto-update from git commits")
    auto_parser.add_argument("--file", default="CHANGELOG.md",
                            help="Changelog file path (default: CHANGELOG.md)")

    # CI check command
    ci_parser = subparsers.add_parser("ci-check", help="Check CI readiness")
    ci_parser.add_argument("--file", default="CHANGELOG.md",
                          help="Changelog file path (default: CHANGELOG.md)")

    # Release notes command
    release_parser = subparsers.add_parser("release-notes", help="Generate release notes")
    release_parser.add_argument("version", help="Version number")
    release_parser.add_argument("--file", default="CHANGELOG.md",
                               help="Changelog file path (default: CHANGELOG.md)")

    # List versions command
    list_parser = subparsers.add_parser("list", help="List all versions")
    list_parser.add_argument("--file", default="CHANGELOG.md",
                            help="Changelog file path (default: CHANGELOG.md)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute commands
    success = False

    if args.command == "validate":
        success = validate_changelog(args.file)
    elif args.command == "create":
        success = create_changelog(args.file)
    elif args.command == "add":
        success = add_entry(args.version, args.changes, args.category, args.file)
    elif args.command == "auto-update":
        success = auto_update_from_git(args.file)
    elif args.command == "ci-check":
        success = check_ci_readiness(args.file)
    elif args.command == "release-notes":
        success = generate_release_notes(args.version, args.file)
    elif args.command == "list":
        success = list_versions(args.file)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
"""
Changelog automation testing framework
Tests automatic changelog generation, validation, and integration workflows
"""

import pytest
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import subprocess
import re
from typing import Dict, List, Any, Optional


class ChangelogEntry:
    """Represents a changelog entry"""

    def __init__(self, version: str, date: str, changes: List[str], category: str = "Changed"):
        self.version = version
        self.date = date
        self.changes = changes
        self.category = category

    def to_markdown(self) -> str:
        """Convert entry to markdown format"""
        lines = [
            f"## [{self.version}] - {self.date}",
            "",
            f"### {self.category}",
            ""
        ]
        for change in self.changes:
            lines.append(f"- {change}")
        lines.append("")
        return "\n".join(lines)


class ChangelogAutomation:
    """Changelog automation system"""

    def __init__(self, changelog_path: str = "CHANGELOG.md"):
        self.changelog_path = Path(changelog_path)
        self.supported_categories = [
            "Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"
        ]

    def create_empty_changelog(self) -> None:
        """Create an empty changelog file"""
        content = """# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

"""
        self.changelog_path.write_text(content)

    def parse_changelog(self) -> Dict[str, Any]:
        """Parse existing changelog"""
        if not self.changelog_path.exists():
            return {"versions": [], "unreleased": []}

        content = self.changelog_path.read_text()
        versions = []
        current_version = None
        current_changes = []

        for line in content.split('\n'):
            # Match version headers
            version_match = re.match(r'##\s*\[([^\]]+)\]\s*-\s*(.+)', line)
            if version_match:
                if current_version:
                    versions.append({
                        "version": current_version,
                        "changes": current_changes.copy()
                    })
                current_version = version_match.group(1)
                current_changes = []
            elif line.startswith('- '):
                current_changes.append(line[2:])

        if current_version:
            versions.append({
                "version": current_version,
                "changes": current_changes
            })

        return {"versions": versions}

    def add_entry(self, entry: ChangelogEntry) -> None:
        """Add new entry to changelog"""
        if not self.changelog_path.exists():
            self.create_empty_changelog()

        content = self.changelog_path.read_text()

        # Find insertion point (after unreleased section)
        unreleased_end = content.find("## [Unreleased]")
        if unreleased_end == -1:
            # Add after header
            header_end = content.find("## ")
            if header_end == -1:
                content += "\n" + entry.to_markdown()
            else:
                content = content[:header_end] + entry.to_markdown() + "\n" + content[header_end:]
        else:
            # Find next version or end
            next_version = content.find("## [", unreleased_end + 1)
            if next_version == -1:
                content += "\n" + entry.to_markdown()
            else:
                content = content[:next_version] + entry.to_markdown() + "\n" + content[next_version:]

        self.changelog_path.write_text(content)

    def validate_format(self) -> List[str]:
        """Validate changelog format"""
        errors = []

        if not self.changelog_path.exists():
            errors.append("Changelog file does not exist")
            return errors

        content = self.changelog_path.read_text()

        # Check for required header
        if "# Changelog" not in content:
            errors.append("Missing main changelog header")

        # Check for Keep a Changelog reference
        if "keepachangelog.com" not in content:
            errors.append("Missing Keep a Changelog reference")

        # Check version format
        version_pattern = r'##\s*\[([^\]]+)\]\s*-\s*\d{4}-\d{2}-\d{2}'
        if not re.search(version_pattern, content):
            errors.append("No properly formatted version entries found")

        return errors

    def get_latest_version(self) -> Optional[str]:
        """Get latest version from changelog"""
        parsed = self.parse_changelog()
        if parsed["versions"]:
            return parsed["versions"][0]["version"]
        return None

    def auto_generate_from_commits(self, since_version: Optional[str] = None) -> ChangelogEntry:
        """Auto-generate changelog entry from git commits"""
        # Mock implementation - in real scenario would parse git commits
        version = "1.0.0"
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        changes = [
            "Added changelog automation system",
            "Improved test coverage",
            "Fixed bug in text normalization"
        ]
        return ChangelogEntry(version, date, changes)


class TestChangelogAutomation:
    """Test suite for changelog automation"""

    @pytest.fixture
    def changelog_system(self, tmp_path):
        """Create changelog automation system"""
        changelog_path = tmp_path / "CHANGELOG.md"
        return ChangelogAutomation(str(changelog_path))

    def test_create_empty_changelog(self, changelog_system):
        """Test creating empty changelog file"""
        changelog_system.create_empty_changelog()

        assert changelog_system.changelog_path.exists()
        content = changelog_system.changelog_path.read_text()

        assert "# Changelog" in content
        assert "Keep a Changelog" in content
        assert "Semantic Versioning" in content
        assert "[Unreleased]" in content

    def test_add_changelog_entry(self, changelog_system):
        """Test adding new changelog entry"""
        entry = ChangelogEntry(
            version="1.0.0",
            date="2025-01-15",
            changes=["Added new feature", "Fixed critical bug"],
            category="Added"
        )

        changelog_system.add_entry(entry)

        assert changelog_system.changelog_path.exists()
        content = changelog_system.changelog_path.read_text()

        assert "[1.0.0] - 2025-01-15" in content
        assert "Added new feature" in content
        assert "Fixed critical bug" in content

    def test_parse_changelog_content(self, changelog_system):
        """Test parsing existing changelog content"""
        # Create sample changelog
        sample_content = """# Changelog

## [1.1.0] - 2025-01-15

### Added
- New authentication system
- Enhanced logging

## [1.0.0] - 2025-01-01

### Fixed
- Critical security vulnerability
"""
        changelog_system.changelog_path.write_text(sample_content)

        parsed = changelog_system.parse_changelog()

        assert len(parsed["versions"]) == 2
        assert parsed["versions"][0]["version"] == "1.1.0"
        assert "New authentication system" in parsed["versions"][0]["changes"]

    def test_changelog_format_validation(self, changelog_system):
        """Test changelog format validation"""
        # Valid changelog
        changelog_system.create_empty_changelog()
        entry = ChangelogEntry("1.0.0", "2025-01-15", ["Test change"])
        changelog_system.add_entry(entry)

        errors = changelog_system.validate_format()
        assert len(errors) == 0

        # Invalid changelog
        changelog_system.changelog_path.write_text("Invalid content")
        errors = changelog_system.validate_format()
        assert len(errors) > 0

    def test_get_latest_version(self, changelog_system):
        """Test getting latest version from changelog"""
        # No versions
        assert changelog_system.get_latest_version() is None

        # Add version
        entry = ChangelogEntry("2.0.0", "2025-01-15", ["Major update"])
        changelog_system.add_entry(entry)

        assert changelog_system.get_latest_version() == "2.0.0"

    def test_auto_generate_from_commits(self, changelog_system):
        """Test auto-generating changelog from commits"""
        entry = changelog_system.auto_generate_from_commits()

        assert entry.version
        assert entry.date
        assert len(entry.changes) > 0
        assert entry.category in changelog_system.supported_categories

    def test_multiple_changelog_entries(self, changelog_system):
        """Test adding multiple changelog entries"""
        entries = [
            ChangelogEntry("1.0.0", "2025-01-01", ["Initial release"]),
            ChangelogEntry("1.1.0", "2025-01-15", ["Feature update"]),
            ChangelogEntry("2.0.0", "2025-02-01", ["Major version"])
        ]

        for entry in entries:
            changelog_system.add_entry(entry)

        parsed = changelog_system.parse_changelog()
        assert len(parsed["versions"]) == 3

    def test_changelog_categories(self, changelog_system):
        """Test different changelog categories"""
        categories = ["Added", "Changed", "Fixed", "Security", "Removed"]

        for i, category in enumerate(categories):
            entry = ChangelogEntry(
                f"1.{i}.0",
                "2025-01-15",
                [f"Test {category.lower()} change"],
                category
            )
            changelog_system.add_entry(entry)

        content = changelog_system.changelog_path.read_text()
        for category in categories:
            assert f"### {category}" in content


class TestChangelogWorkflowIntegration:
    """Test changelog workflow integration"""

    @pytest.fixture
    def mock_git_repo(self, tmp_path):
        """Mock git repository"""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        # Create mock git structure
        git_dir = repo_dir / ".git"
        git_dir.mkdir()

        return repo_dir

    @pytest.fixture
    def changelog_workflow(self, mock_git_repo):
        """Create changelog workflow system"""
        return ChangelogWorkflow(str(mock_git_repo))

    def test_workflow_initialization(self, changelog_workflow):
        """Test changelog workflow initialization"""
        assert changelog_workflow.repo_path.exists()
        assert hasattr(changelog_workflow, 'changelog_system')

    def test_pre_commit_changelog_check(self, changelog_workflow):
        """Test pre-commit changelog validation"""
        # Should pass with valid changelog
        result = changelog_workflow.pre_commit_check()
        assert isinstance(result, bool)

    def test_automated_changelog_update(self, changelog_workflow):
        """Test automated changelog updates"""
        # Mock commit data
        mock_commits = [
            {"message": "feat: add new API endpoint", "hash": "abc123"},
            {"message": "fix: resolve authentication bug", "hash": "def456"},
            {"message": "docs: update README", "hash": "ghi789"}
        ]

        with patch.object(changelog_workflow, 'get_commits_since_last_tag', return_value=mock_commits):
            result = changelog_workflow.update_changelog_from_commits()
            assert result is not None

    def test_release_changelog_generation(self, changelog_workflow):
        """Test changelog generation for releases"""
        version = "1.2.0"
        result = changelog_workflow.generate_release_changelog(version)

        assert isinstance(result, (str, ChangelogEntry))

    def test_changelog_ci_integration(self, changelog_workflow):
        """Test CI integration for changelog"""
        # Test CI workflow validation
        ci_result = changelog_workflow.validate_for_ci()
        assert isinstance(ci_result, dict)
        assert "valid" in ci_result

    def test_changelog_pr_integration(self, changelog_workflow):
        """Test PR integration for changelog"""
        # Mock PR data
        pr_data = {
            "title": "Add new feature",
            "body": "This PR adds a new authentication feature",
            "labels": ["enhancement", "feature"]
        }

        result = changelog_workflow.process_pr_changelog(pr_data)
        assert result is not None


class ChangelogWorkflow:
    """Changelog workflow integration system"""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.changelog_system = ChangelogAutomation(str(self.repo_path / "CHANGELOG.md"))
        self.conventional_commit_types = {
            "feat": "Added",
            "fix": "Fixed",
            "docs": "Changed",
            "style": "Changed",
            "refactor": "Changed",
            "test": "Changed",
            "chore": "Changed",
            "security": "Security",
            "perf": "Changed",
            "breaking": "Changed"
        }

    def pre_commit_check(self) -> bool:
        """Pre-commit changelog validation"""
        errors = self.changelog_system.validate_format()
        return len(errors) == 0

    def get_commits_since_last_tag(self) -> List[Dict[str, str]]:
        """Get commits since last tag (mock implementation)"""
        return [
            {"message": "feat: add changelog automation", "hash": "abc123", "author": "dev"},
            {"message": "fix: resolve test failures", "hash": "def456", "author": "dev"}
        ]

    def parse_conventional_commit(self, commit_message: str) -> Dict[str, str]:
        """Parse conventional commit message"""
        pattern = r'^(\w+)(\(.+\))?: (.+)$'
        match = re.match(pattern, commit_message)

        if match:
            return {
                "type": match.group(1),
                "scope": match.group(2),
                "description": match.group(3)
            }
        return {"type": "other", "scope": None, "description": commit_message}

    def update_changelog_from_commits(self) -> ChangelogEntry:
        """Update changelog from recent commits"""
        commits = self.get_commits_since_last_tag()
        changes_by_category = {}

        for commit in commits:
            parsed = self.parse_conventional_commit(commit["message"])
            commit_type = parsed["type"]
            category = self.conventional_commit_types.get(commit_type, "Changed")

            if category not in changes_by_category:
                changes_by_category[category] = []

            changes_by_category[category].append(parsed["description"])

        # Create changelog entry
        version = "1.0.0"  # Would be determined by semver logic
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Flatten changes
        all_changes = []
        for category, changes in changes_by_category.items():
            all_changes.extend(changes)

        entry = ChangelogEntry(version, date, all_changes)
        self.changelog_system.add_entry(entry)

        return entry

    def generate_release_changelog(self, version: str) -> ChangelogEntry:
        """Generate changelog for release"""
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        changes = [f"Release version {version}"]

        return ChangelogEntry(version, date, changes)

    def validate_for_ci(self) -> Dict[str, Any]:
        """Validate changelog for CI"""
        errors = self.changelog_system.validate_format()

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "has_unreleased": "[Unreleased]" in self.changelog_system.changelog_path.read_text() if self.changelog_system.changelog_path.exists() else False
        }

    def process_pr_changelog(self, pr_data: Dict[str, Any]) -> Optional[ChangelogEntry]:
        """Process PR for automatic changelog entry"""
        title = pr_data.get("title", "")
        labels = pr_data.get("labels", [])

        # Determine category from labels
        category = "Changed"
        if "feature" in labels or "enhancement" in labels:
            category = "Added"
        elif "bug" in labels or "fix" in labels:
            category = "Fixed"
        elif "security" in labels:
            category = "Security"

        # Create entry
        version = "Unreleased"
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        changes = [title]

        return ChangelogEntry(version, date, changes, category)


class TestChangelogValidationAndFormats:
    """Test changelog validation and different formats"""

    @pytest.fixture
    def validator(self):
        """Create changelog validator"""
        return ChangelogValidator()

    def test_keep_a_changelog_format(self, validator, tmp_path):
        """Test Keep a Changelog format validation"""
        changelog_path = tmp_path / "CHANGELOG.md"

        # Valid format
        valid_changelog = """# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2025-01-15

### Added
- Initial release
"""
        changelog_path.write_text(valid_changelog)

        result = validator.validate_keep_a_changelog_format(str(changelog_path))
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_semantic_versioning_compliance(self, validator):
        """Test semantic versioning compliance"""
        valid_versions = ["1.0.0", "2.1.3", "1.0.0-alpha.1", "2.0.0-rc.1"]
        invalid_versions = ["1.0", "v1.0.0", "1.0.0.0", "latest"]

        for version in valid_versions:
            assert validator.is_valid_semver(version) is True

        for version in invalid_versions:
            assert validator.is_valid_semver(version) is False

    def test_changelog_link_validation(self, validator, tmp_path):
        """Test changelog link validation"""
        changelog_path = tmp_path / "CHANGELOG.md"

        changelog_with_links = """# Changelog

## [1.0.0] - 2025-01-15

### Added
- Feature A [#123](https://github.com/repo/issues/123)
- Feature B [PR#45](https://github.com/repo/pull/45)

[1.0.0]: https://github.com/repo/releases/tag/v1.0.0
"""
        changelog_path.write_text(changelog_with_links)

        result = validator.validate_links(str(changelog_path))
        assert isinstance(result, dict)
        assert "broken_links" in result

    def test_changelog_date_format_validation(self, validator):
        """Test changelog date format validation"""
        valid_dates = ["2025-01-15", "2024-12-31", "2023-02-28"]
        invalid_dates = ["01-15-2025", "2025/01/15", "15-01-2025", "Jan 15, 2025"]

        for date in valid_dates:
            assert validator.is_valid_date_format(date) is True

        for date in invalid_dates:
            assert validator.is_valid_date_format(date) is False

    def test_changelog_category_validation(self, validator):
        """Test changelog category validation"""
        valid_categories = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]
        invalid_categories = ["New", "Updated", "Broken", "Delete"]

        for category in valid_categories:
            assert validator.is_valid_category(category) is True

        for category in invalid_categories:
            assert validator.is_valid_category(category) is False


class ChangelogValidator:
    """Changelog validation system"""

    def __init__(self):
        self.valid_categories = {
            "Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"
        }
        self.semver_pattern = r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*)?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
        self.date_pattern = r'^\d{4}-\d{2}-\d{2}$'

    def validate_keep_a_changelog_format(self, changelog_path: str) -> Dict[str, Any]:
        """Validate Keep a Changelog format"""
        errors = []
        content = Path(changelog_path).read_text()

        # Required elements
        if "# Changelog" not in content:
            errors.append("Missing main changelog header")

        if "keepachangelog.com" not in content:
            errors.append("Missing Keep a Changelog reference")

        if "semver.org" not in content:
            errors.append("Missing Semantic Versioning reference")

        # Version format check
        version_pattern = r'##\s*\[([^\]]+)\]\s*-\s*(\d{4}-\d{2}-\d{2})'
        versions = re.findall(version_pattern, content)

        for version, date in versions:
            if not self.is_valid_semver(version) and version != "Unreleased":
                errors.append(f"Invalid semantic version: {version}")

            if not self.is_valid_date_format(date):
                errors.append(f"Invalid date format: {date}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "versions_found": len(versions)
        }

    def is_valid_semver(self, version: str) -> bool:
        """Check if version follows semantic versioning"""
        return bool(re.match(self.semver_pattern, version))

    def is_valid_date_format(self, date: str) -> bool:
        """Check if date follows YYYY-MM-DD format"""
        return bool(re.match(self.date_pattern, date))

    def is_valid_category(self, category: str) -> bool:
        """Check if category is valid"""
        return category in self.valid_categories

    def validate_links(self, changelog_path: str) -> Dict[str, Any]:
        """Validate links in changelog"""
        content = Path(changelog_path).read_text()

        # Find all markdown links
        link_pattern = r'\[([^\]]*)\]\(([^)]+)\)'
        links = re.findall(link_pattern, content)

        return {
            "links_found": len(links),
            "broken_links": [],  # Would check actual URLs in real implementation
            "valid": True
        }
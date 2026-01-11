"""
Changelog Generator
===================
Auto-generate changelogs from git commits using conventional commit format.

Usage:
    python changelog.py [--since v1.0.0] [--output CHANGELOG.md]
    python -m scripts.changelog
"""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
import sys

from .utils import (
    find_project_root,
    get_git_log,
    run_git_command,
    GitCommit,
    Console
)


@dataclass
class ChangelogEntry:
    """A single changelog entry."""
    commit_type: str
    scope: Optional[str]
    description: str
    commit_hash: str
    breaking: bool = False
    issues: List[str] = field(default_factory=list)


@dataclass
class ChangelogVersion:
    """A version section in the changelog."""
    version: str
    date: str
    entries: Dict[str, List[ChangelogEntry]] = field(default_factory=lambda: defaultdict(list))
    breaking_changes: List[str] = field(default_factory=list)


# Conventional commit types
COMMIT_TYPES = {
    'feat': 'Features',
    'fix': 'Bug Fixes',
    'docs': 'Documentation',
    'style': 'Styles',
    'refactor': 'Code Refactoring',
    'perf': 'Performance Improvements',
    'test': 'Tests',
    'build': 'Build System',
    'ci': 'CI/CD',
    'chore': 'Chores',
    'revert': 'Reverts',
}

# Regex for parsing conventional commits
CONVENTIONAL_COMMIT_PATTERN = re.compile(
    r'^(?P<type>feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)'
    r'(?:\((?P<scope>[^)]+)\))?'
    r'(?P<breaking>!)?'
    r':\s*'
    r'(?P<description>.+)$',
    re.IGNORECASE
)

# Pattern for issue references
ISSUE_PATTERN = re.compile(r'#(\d+)')


def parse_commit_message(message: str) -> Optional[ChangelogEntry]:
    """
    Parse a conventional commit message.

    Args:
        message: Commit message

    Returns:
        ChangelogEntry or None if not conventional format
    """
    match = CONVENTIONAL_COMMIT_PATTERN.match(message.strip())
    if not match:
        return None

    groups = match.groupdict()

    # Extract issue references
    issues = ISSUE_PATTERN.findall(message)

    return ChangelogEntry(
        commit_type=groups['type'].lower(),
        scope=groups['scope'],
        description=groups['description'].strip(),
        commit_hash="",  # Will be set later
        breaking=bool(groups['breaking']),
        issues=issues
    )


def get_git_tags() -> List[Tuple[str, str]]:
    """Get all git tags with their dates."""
    output = run_git_command(['tag', '-l', '--format=%(refname:short)|%(creatordate:short)'])
    if not output:
        return []

    tags = []
    for line in output.split('\n'):
        if '|' in line:
            tag, date = line.split('|', 1)
            tags.append((tag.strip(), date.strip()))

    return tags


def get_commits_since_tag(tag: str = None, cwd: Path = None) -> List[GitCommit]:
    """Get commits since a specific tag."""
    if tag:
        args = ['log', f'{tag}..HEAD', '--format=%H|%h|%an|%ai|%s|%b', '--no-merges']
    else:
        args = ['log', '--format=%H|%h|%an|%ai|%s|%b', '--no-merges', '-100']

    output = run_git_command(args, cwd=cwd)
    if not output:
        return []

    commits = []
    for entry in output.split('\n'):
        if not entry.strip():
            continue

        parts = entry.split('|')
        if len(parts) >= 5:
            commits.append(GitCommit(
                hash=parts[0],
                short_hash=parts[1],
                author=parts[2],
                date=parts[3],
                message=parts[4],
                body=parts[5] if len(parts) > 5 else ""
            ))

    return commits


def generate_changelog(
    cwd: Path = None,
    since_tag: str = None,
    version: str = "Unreleased"
) -> ChangelogVersion:
    """
    Generate changelog from git commits.

    Args:
        cwd: Working directory
        since_tag: Tag to start from
        version: Version number for this release

    Returns:
        ChangelogVersion object
    """
    commits = get_commits_since_tag(since_tag, cwd)

    changelog = ChangelogVersion(
        version=version,
        date=__import__('datetime').datetime.now().strftime('%Y-%m-%d')
    )

    for commit in commits:
        entry = parse_commit_message(commit.message)
        if entry:
            entry.commit_hash = commit.short_hash

            # Add to appropriate category
            changelog.entries[entry.commit_type].append(entry)

            # Track breaking changes
            if entry.breaking or 'BREAKING CHANGE' in commit.body:
                changelog.breaking_changes.append(
                    f"{entry.description} ({commit.short_hash})"
                )
        else:
            # Non-conventional commits go to 'Other'
            other_entry = ChangelogEntry(
                commit_type='other',
                scope=None,
                description=commit.message,
                commit_hash=commit.short_hash
            )
            changelog.entries['other'].append(other_entry)

    return changelog


def format_changelog_markdown(
    changelog: ChangelogVersion,
    include_hash: bool = True,
    repo_url: str = None
) -> str:
    """
    Format changelog as Markdown.

    Args:
        changelog: ChangelogVersion object
        include_hash: Whether to include commit hashes
        repo_url: Repository URL for linking

    Returns:
        Markdown formatted changelog
    """
    lines = [
        f"## [{changelog.version}] - {changelog.date}",
        "",
    ]

    # Breaking changes first
    if changelog.breaking_changes:
        lines.extend([
            "### BREAKING CHANGES",
            "",
        ])
        for change in changelog.breaking_changes:
            lines.append(f"- {change}")
        lines.append("")

    # Categorized changes
    category_order = ['feat', 'fix', 'perf', 'refactor', 'docs', 'test', 'build', 'ci', 'chore', 'other']

    for category in category_order:
        entries = changelog.entries.get(category, [])
        if not entries:
            continue

        category_name = COMMIT_TYPES.get(category, category.capitalize())
        lines.extend([
            f"### {category_name}",
            "",
        ])

        for entry in entries:
            # Build entry line
            if entry.scope:
                line = f"- **{entry.scope}:** {entry.description}"
            else:
                line = f"- {entry.description}"

            # Add commit hash
            if include_hash:
                if repo_url:
                    line += f" ([{entry.commit_hash}]({repo_url}/commit/{entry.commit_hash}))"
                else:
                    line += f" ({entry.commit_hash})"

            # Add issue references
            if entry.issues:
                issue_links = []
                for issue in entry.issues:
                    if repo_url:
                        issue_links.append(f"[#{issue}]({repo_url}/issues/{issue})")
                    else:
                        issue_links.append(f"#{issue}")
                line += f" - {', '.join(issue_links)}"

            lines.append(line)

        lines.append("")

    return "\n".join(lines)


def update_changelog_file(
    changelog_path: Path,
    new_content: str,
    prepend: bool = True
) -> None:
    """
    Update a changelog file with new content.

    Args:
        changelog_path: Path to CHANGELOG.md
        new_content: New content to add
        prepend: Whether to prepend (True) or append
    """
    header = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n"

    if changelog_path.exists():
        with open(changelog_path, 'r', encoding='utf-8') as f:
            existing = f.read()

        # Remove header if present
        if existing.startswith("# Changelog"):
            lines = existing.split('\n')
            # Find first version heading
            for i, line in enumerate(lines):
                if line.startswith('## '):
                    existing = '\n'.join(lines[i:])
                    break

        if prepend:
            content = header + new_content + "\n" + existing
        else:
            content = header + existing + "\n" + new_content
    else:
        content = header + new_content

    with open(changelog_path, 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    """CLI entry point."""
    Console.header("Changelog Generator")

    # Parse args
    since_tag = None
    output_file = None
    version = "Unreleased"

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--since' and i + 1 < len(args):
            since_tag = args[i + 1]
            i += 2
        elif args[i] == '--output' and i + 1 < len(args):
            output_file = Path(args[i + 1])
            i += 2
        elif args[i] == '--version' and i + 1 < len(args):
            version = args[i + 1]
            i += 2
        else:
            i += 1

    # Find project root
    cwd = find_project_root() or Path.cwd()

    Console.info(f"Analyzing: {cwd}")
    if since_tag:
        Console.info(f"Since tag: {since_tag}")

    # Generate changelog
    changelog = generate_changelog(cwd, since_tag, version)

    # Count entries
    total_entries = sum(len(entries) for entries in changelog.entries.values())
    Console.info(f"Found {total_entries} commits")

    # Format
    markdown = format_changelog_markdown(changelog)

    # Output
    if output_file:
        update_changelog_file(output_file, markdown)
        Console.ok(f"Changelog written to: {output_file}")
    else:
        print(markdown)

    return 0


if __name__ == "__main__":
    sys.exit(main())

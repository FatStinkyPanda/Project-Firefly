"""
Git History Index
=================
Index git commits, blame, and file evolution for AI agents.

Usage:
    python mcp.py git-history [file]
    python mcp.py blame [file]
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import re
import subprocess
import sys

from .utils import Console, find_project_root


@dataclass
class Commit:
    """A git commit."""
    hash: str
    short_hash: str
    author: str
    email: str
    date: str
    message: str
    files_changed: List[str] = field(default_factory=list)


@dataclass
class BlameInfo:
    """Blame info for a line."""
    line_num: int
    commit_hash: str
    author: str
    date: str
    content: str


@dataclass
class FileHistory:
    """History of a file."""
    path: str
    commits: List[Commit] = field(default_factory=list)
    authors: List[str] = field(default_factory=list)
    first_commit: Optional[str] = None
    last_commit: Optional[str] = None


def run_git(args: List[str], cwd: Path = None) -> Optional[str]:
    """Run git command and return output."""
    try:
        result = subprocess.run(
            ['git'] + args,
            capture_output=True,
            text=True,
            cwd=cwd or Path.cwd()
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None


def get_commits(
    path: Path = None,
    since: str = None,
    limit: int = 100,
    file_path: Path = None
) -> List[Commit]:
    """Get list of commits."""
    args = [
        'log',
        f'-{limit}',
        '--format=%H|%h|%an|%ae|%aI|%s',
        '--name-only'
    ]

    if since:
        args.append(f'--since={since}')

    if file_path:
        args.extend(['--', str(file_path)])

    output = run_git(args, path)
    if not output:
        return []

    commits = []
    current_commit = None

    for line in output.split('\n'):
        if '|' in line and line.count('|') >= 5:
            # Commit line
            parts = line.split('|', 5)
            if current_commit:
                commits.append(current_commit)

            current_commit = Commit(
                hash=parts[0],
                short_hash=parts[1],
                author=parts[2],
                email=parts[3],
                date=parts[4],
                message=parts[5] if len(parts) > 5 else ""
            )
        elif line.strip() and current_commit:
            # File changed
            current_commit.files_changed.append(line.strip())

    if current_commit:
        commits.append(current_commit)

    return commits


def get_blame(file_path: Path, root: Path = None) -> List[BlameInfo]:
    """Get blame info for file."""
    root = root or find_project_root() or Path.cwd()

    args = ['blame', '--line-porcelain', str(file_path)]
    output = run_git(args, root)

    if not output:
        return []

    blame_info = []
    current = {}
    line_num = 0

    for line in output.split('\n'):
        if line.startswith('author '):
            current['author'] = line[7:]
        elif line.startswith('author-time '):
            ts = int(line[12:])
            current['date'] = datetime.fromtimestamp(ts).isoformat()
        elif line.startswith('\t'):
            line_num += 1
            if 'commit_hash' in current:
                blame_info.append(BlameInfo(
                    line_num=line_num,
                    commit_hash=current.get('commit_hash', ''),
                    author=current.get('author', 'Unknown'),
                    date=current.get('date', ''),
                    content=line[1:]  # Remove tab
                ))
            current = {}
        elif len(line) == 40 and all(c in '0123456789abcdef' for c in line[:40].split()[0]):
            current['commit_hash'] = line.split()[0]

    return blame_info


def get_file_history(file_path: Path, root: Path = None) -> FileHistory:
    """Get complete history of a file."""
    root = root or find_project_root() or Path.cwd()

    commits = get_commits(root, file_path=file_path)

    authors = list(set(c.author for c in commits))

    return FileHistory(
        path=str(file_path),
        commits=commits,
        authors=authors,
        first_commit=commits[-1].short_hash if commits else None,
        last_commit=commits[0].short_hash if commits else None
    )


def get_change_intent(file_path: Path, root: Path = None) -> str:
    """Get the intent behind recent changes to a file."""
    history = get_file_history(file_path, root)

    if not history.commits:
        return "No git history available"

    # Summarize recent commits
    recent = history.commits[:5]

    lines = [f"Recent changes to {file_path.name}:", ""]
    for commit in recent:
        lines.append(f"- {commit.message} ({commit.author}, {commit.date[:10]})")

    lines.append("")
    lines.append(f"Authors: {', '.join(history.authors[:5])}")
    lines.append(f"Total commits: {len(history.commits)}")

    return '\n'.join(lines)


def search_commits(query: str, root: Path = None, limit: int = 20) -> List[Commit]:
    """Search commit messages."""
    root = root or find_project_root() or Path.cwd()

    args = [
        'log',
        f'-{limit}',
        '--format=%H|%h|%an|%ae|%aI|%s',
        f'--grep={query}',
        '-i'  # Case insensitive
    ]

    output = run_git(args, root)
    if not output:
        return []

    commits = []
    for line in output.split('\n'):
        if '|' in line:
            parts = line.split('|', 5)
            commits.append(Commit(
                hash=parts[0],
                short_hash=parts[1],
                author=parts[2],
                email=parts[3],
                date=parts[4],
                message=parts[5] if len(parts) > 5 else ""
            ))

    return commits


def index_git_history(root: Path = None, since: str = "3 months") -> Dict:
    """Build git history index."""
    root = root or find_project_root() or Path.cwd()

    Console.info(f"Indexing git history (since {since})...")

    commits = get_commits(root, since=since, limit=500)

    # Build index
    index = {
        "commit_count": len(commits),
        "authors": {},
        "files": {},
        "commits": []
    }

    for commit in commits:
        # Track authors
        if commit.author not in index["authors"]:
            index["authors"][commit.author] = 0
        index["authors"][commit.author] += 1

        # Track files
        for file in commit.files_changed:
            if file not in index["files"]:
                index["files"][file] = []
            index["files"][file].append(commit.short_hash)

        # Store commit (without files to save space)
        index["commits"].append({
            "hash": commit.short_hash,
            "author": commit.author,
            "date": commit.date,
            "message": commit.message
        })

    # Save index
    index_path = root / '.mcp' / 'git_index.json'
    index_path.parent.mkdir(parents=True, exist_ok=True)

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2)

    Console.ok(f"Indexed {len(commits)} commits from {len(index['authors'])} authors")

    return index


def main():
    """CLI entry point."""
    Console.header("Git History Index")

    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    root = find_project_root() or Path.cwd()

    if '--index' in sys.argv:
        since = "3 months"
        for i, arg in enumerate(sys.argv):
            if arg == '--since' and i + 1 < len(sys.argv):
                since = sys.argv[i + 1]
        index_git_history(root, since)
        return 0

    if '--search' in sys.argv and args:
        query = args[0]
        Console.info(f"Searching commits: {query}")
        commits = search_commits(query, root)

        for commit in commits:
            print(f"{commit.short_hash} {commit.message[:60]} ({commit.author})")
        return 0

    if '--blame' in sys.argv and args:
        file_path = Path(args[0])
        Console.info(f"Blame: {file_path}")

        blame = get_blame(file_path, root)
        for info in blame[:30]:
            print(f"{info.line_num:4d} {info.commit_hash[:7]} {info.author[:15]:15} {info.content[:50]}")
        return 0

    # Default: show file history
    if args:
        file_path = Path(args[0])
        intent = get_change_intent(file_path, root)
        print(intent)
    else:
        # Show recent commits
        commits = get_commits(root, limit=10)
        Console.info(f"Recent commits:")
        for commit in commits:
            print(f"  {commit.short_hash} {commit.message[:50]} ({commit.author})")

    return 0


if __name__ == "__main__":
    sys.exit(main())

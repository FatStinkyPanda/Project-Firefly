"""
TODO/FIXME Index
================
Scan and index all TODOs, FIXMEs, HACKs, and NOTEs in code.

Usage:
    python mcp.py todos
    python mcp.py todos --priority high
"""

from collections import Counter
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import re
import sys

from .utils import Console, find_python_files, find_project_root


@dataclass
class TodoItem:
    """A TODO/FIXME item."""
    type: str  # TODO, FIXME, HACK, XXX, NOTE
    message: str
    file: str
    line: int
    author: Optional[str] = None
    priority: int = 2  # 1=high, 2=medium, 3=low
    context: str = ""


# Patterns to detect
TODO_PATTERNS = [
    (r'#\s*(TODO|FIXME|HACK|XXX|NOTE)(?:\(([^)]+)\))?:\s*(.+?)$', 'python'),
    (r'//\s*(TODO|FIXME|HACK|XXX|NOTE)(?:\(([^)]+)\))?:\s*(.+?)$', 'js'),
    (r'/\*\s*(TODO|FIXME|HACK|XXX|NOTE)(?:\(([^)]+)\))?:\s*(.+?)\*/', 'block'),
]

PRIORITY_MAP = {
    'FIXME': 1,
    'XXX': 1,
    'HACK': 2,
    'TODO': 2,
    'NOTE': 3,
}

PRIORITY_KEYWORDS = {
    'urgent': 1,
    'critical': 1,
    'important': 1,
    'P0': 1, 'P1': 1,
    'P2': 2, 'P3': 3,
    'low': 3,
    'minor': 3,
}


def detect_priority(todo_type: str, message: str, author: str = None) -> int:
    """Detect priority from type and message."""
    priority = PRIORITY_MAP.get(todo_type, 2)

    # Check for priority keywords
    text = (message + (author or '')).lower()
    for keyword, p in PRIORITY_KEYWORDS.items():
        if keyword.lower() in text:
            priority = min(priority, p)
            break

    # ! at end indicates high priority
    if message.rstrip().endswith('!'):
        priority = 1

    return priority


def scan_file(file_path: Path) -> List[TodoItem]:
    """Scan a file for TODOs."""
    todos = []

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception:
        return todos

    for i, line in enumerate(lines, 1):
        for pattern, _ in TODO_PATTERNS:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                todo_type = match.group(1).upper()
                author = match.group(2) if match.lastindex >= 2 else None
                message = match.group(3) if match.lastindex >= 3 else match.group(2)

                if message:
                    # Get context (surrounding lines)
                    context_start = max(0, i - 2)
                    context_end = min(len(lines), i + 2)
                    context = ''.join(lines[context_start:context_end])

                    todos.append(TodoItem(
                        type=todo_type,
                        message=message.strip(),
                        file=str(file_path),
                        line=i,
                        author=author,
                        priority=detect_priority(todo_type, message, author),
                        context=context[:200]
                    ))
                break

    return todos


def scan_project(
    root: Path,
    exclude_patterns: List[str] = None
) -> List[TodoItem]:
    """Scan entire project for TODOs."""
    all_todos = []

    # Find all code files
    extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.c', '.cpp', '.h']

    for ext in extensions:
        for file_path in root.rglob(f'*{ext}'):
            # Skip excluded
            if exclude_patterns:
                skip = False
                for pattern in exclude_patterns:
                    if pattern in str(file_path):
                        skip = True
                        break
                if skip:
                    continue

            todos = scan_file(file_path)
            all_todos.extend(todos)

    return all_todos


def group_by_priority(todos: List[TodoItem]) -> Dict[int, List[TodoItem]]:
    """Group TODOs by priority."""
    groups = {1: [], 2: [], 3: []}
    for todo in todos:
        groups[todo.priority].append(todo)
    return groups


def group_by_type(todos: List[TodoItem]) -> Dict[str, List[TodoItem]]:
    """Group TODOs by type."""
    groups = {}
    for todo in todos:
        if todo.type not in groups:
            groups[todo.type] = []
        groups[todo.type].append(todo)
    return groups


def index_todos(root: Path = None) -> Dict:
    """Build TODO index and save to disk."""
    root = root or find_project_root() or Path.cwd()

    Console.info(f"Scanning for TODOs in {root}...")

    exclude = ['node_modules', 'venv', '.venv', '__pycache__', '.git', 'vendor']
    todos = scan_project(root, exclude)

    # Build index
    index = {
        "total": len(todos),
        "by_type": {},
        "by_priority": {1: 0, 2: 0, 3: 0},
        "by_file": {},
        "items": []
    }

    for todo in todos:
        # Count by type
        if todo.type not in index["by_type"]:
            index["by_type"][todo.type] = 0
        index["by_type"][todo.type] += 1

        # Count by priority
        index["by_priority"][todo.priority] += 1

        # Count by file
        if todo.file not in index["by_file"]:
            index["by_file"][todo.file] = 0
        index["by_file"][todo.file] += 1

        # Store item
        index["items"].append(asdict(todo))

    # Save index
    index_path = root / '.mcp' / 'todo_index.json'
    index_path.parent.mkdir(parents=True, exist_ok=True)

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2)

    Console.ok(f"Found {len(todos)} TODOs ({index['by_priority'][1]} high, {index['by_priority'][2]} medium, {index['by_priority'][3]} low)")

    return index


def main():
    """CLI entry point."""
    Console.header("TODO/FIXME Index")

    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    root = find_project_root() or Path.cwd()

    if '--index' in sys.argv:
        index_todos(root)
        return 0

    # Scan and display
    exclude = ['node_modules', 'venv', '.venv', '__pycache__', '.git', 'vendor']
    todos = scan_project(root, exclude)

    if not todos:
        Console.ok("No TODOs found!")
        return 0

    # Filter by priority
    if '--high' in sys.argv or '--priority' in sys.argv:
        todos = [t for t in todos if t.priority == 1]

    # Filter by type
    for todo_type in ['TODO', 'FIXME', 'HACK', 'NOTE']:
        if f'--{todo_type.lower()}' in sys.argv:
            todos = [t for t in todos if t.type == todo_type]

    # Group by priority
    by_priority = group_by_priority(todos)

    # Display
    priority_names = {1: 'HIGH', 2: 'MEDIUM', 3: 'LOW'}
    priority_colors = {1: '\033[91m', 2: '\033[93m', 3: '\033[92m'}
    NC = '\033[0m'

    for priority in [1, 2, 3]:
        items = by_priority[priority]
        if items:
            print(f"\n## {priority_colors[priority]}{priority_names[priority]}{NC} ({len(items)})")
            for todo in items[:10]:
                rel_path = Path(todo.file).name
                print(f"  [{todo.type}] {todo.message[:50]} ({rel_path}:{todo.line})")

    print(f"\n**Total: {len(todos)} items**")

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Codebase Summarizer
===================
Generate context summaries for AI agents to quickly understand codebases.

Usage:
    python summarize.py [path] [--output CODEBASE_SUMMARY.md]
    python -m scripts.summarize [path]
"""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
import sys

from .utils import (
    find_python_files,
    find_project_root,
    analyze_module,
    get_git_log,
    get_changed_files,
    ModuleInfo,
    Console,
    format_as_json
)


@dataclass
class CodebaseSummary:
    """Summary of an entire codebase."""
    root: Path
    total_files: int = 0
    total_lines: int = 0
    total_functions: int = 0
    total_classes: int = 0

    # Structure
    directory_tree: Dict[str, Any] = field(default_factory=dict)
    modules: List[ModuleInfo] = field(default_factory=list)

    # Dependencies
    external_deps: List[str] = field(default_factory=list)
    internal_deps: Dict[str, List[str]] = field(default_factory=dict)

    # Entry points
    entry_points: List[str] = field(default_factory=list)

    # Patterns
    patterns: List[str] = field(default_factory=list)

    # Recent changes
    recent_changes: List[str] = field(default_factory=list)


def count_lines(path: Path) -> int:
    """Count non-empty lines in a file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def build_directory_tree(root: Path, files: List[Path]) -> Dict[str, Any]:
    """
    Build a hierarchical directory tree structure.

    Args:
        root: Root directory
        files: List of file paths

    Returns:
        Nested dictionary representing directory structure
    """
    tree: Dict[str, Any] = {}

    for file in files:
        try:
            relative = file.relative_to(root)
            parts = relative.parts
        except ValueError:
            parts = file.parts

        current = tree
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Add file with info
        current[parts[-1]] = {
            '_type': 'file',
            '_lines': count_lines(file)
        }

    return tree


def format_tree_ascii(tree: Dict[str, Any], prefix: str = "", is_last: bool = True) -> str:
    """Format directory tree as ASCII art."""
    lines = []

    items = sorted(tree.items(), key=lambda x: (x[1].get('_type') != 'file' if isinstance(x[1], dict) else 0, x[0]))

    for i, (name, value) in enumerate(items):
        if name.startswith('_'):
            continue

        is_last_item = i == len(items) - 1
        connector = "└── " if is_last_item else "├── "

        if isinstance(value, dict) and value.get('_type') == 'file':
            line_count = value.get('_lines', 0)
            lines.append(f"{prefix}{connector}{name} ({line_count} lines)")
        elif isinstance(value, dict):
            lines.append(f"{prefix}{connector}{name}/")
            extension = "    " if is_last_item else "│   "
            lines.append(format_tree_ascii(value, prefix + extension, is_last_item))
        else:
            lines.append(f"{prefix}{connector}{name}")

    return "\n".join(filter(None, lines))


def detect_patterns(modules: List[ModuleInfo]) -> List[str]:
    """Detect common patterns in the codebase."""
    patterns = []

    # Check for common patterns
    all_decorators = set()
    all_bases = set()
    all_imports = set()

    for module in modules:
        for func in module.functions:
            all_decorators.update(func.decorators)
        for cls in module.classes:
            all_bases.update(cls.bases)
            all_decorators.update(cls.decorators)
        all_imports.update(module.imports)
        for mod, names in module.from_imports:
            all_imports.add(mod)

    # Detect patterns
    if 'dataclass' in all_decorators or 'dataclasses' in all_imports:
        patterns.append("Uses dataclasses for data structures")

    if 'pytest' in all_imports or 'unittest' in all_imports:
        patterns.append("Has test infrastructure")

    if 'flask' in all_imports or 'fastapi' in all_imports:
        patterns.append("Web application (Flask/FastAPI)")

    if 'django' in all_imports:
        patterns.append("Django web framework")

    if 'asyncio' in all_imports or any('async' in str(d) for d in all_decorators):
        patterns.append("Uses async/await patterns")

    if 'typing' in all_imports:
        patterns.append("Uses type hints")

    if 'pydantic' in all_imports:
        patterns.append("Uses Pydantic for validation")

    if 'sqlalchemy' in all_imports:
        patterns.append("Uses SQLAlchemy ORM")

    if 'click' in all_imports or 'argparse' in all_imports:
        patterns.append("Has CLI interface")

    if 'logging' in all_imports:
        patterns.append("Has logging infrastructure")

    if any('ABC' in b or 'Protocol' in b for b in all_bases):
        patterns.append("Uses abstract base classes/protocols")

    return patterns


def find_entry_points(root: Path, modules: List[ModuleInfo]) -> List[str]:
    """Find likely entry points in the codebase."""
    entry_points = []

    for module in modules:
        # Check for if __name__ == '__main__'
        try:
            with open(module.path, 'r', encoding='utf-8') as f:
                content = f.read()
                if "if __name__" in content and "__main__" in content:
                    relative = module.path.relative_to(root) if module.path.is_relative_to(root) else module.path
                    entry_points.append(str(relative))
        except Exception:
            pass

    # Check for common entry point files
    common_entry_points = ['main.py', 'app.py', 'cli.py', 'run.py', '__main__.py', 'manage.py']
    for ep in common_entry_points:
        for module in modules:
            if module.path.name == ep:
                relative = module.path.relative_to(root) if module.path.is_relative_to(root) else module.path
                if str(relative) not in entry_points:
                    entry_points.append(str(relative))

    return entry_points


def extract_external_deps(modules: List[ModuleInfo]) -> List[str]:
    """Extract external dependencies from imports."""
    stdlib_modules = {
        'os', 'sys', 're', 'json', 'pathlib', 'typing', 'collections',
        'itertools', 'functools', 'datetime', 'time', 'logging', 'ast',
        'subprocess', 'threading', 'multiprocessing', 'queue', 'socket',
        'http', 'urllib', 'email', 'html', 'xml', 'configparser',
        'argparse', 'io', 'string', 'textwrap', 'copy', 'pprint',
        'dataclasses', 'abc', 'contextlib', 'warnings', 'traceback',
        'unittest', 'doctest', 'sqlite3', 'csv', 'pickle', 'shelve',
        'hashlib', 'hmac', 'secrets', 'random', 'math', 'statistics',
        'fractions', 'decimal', 'struct', 'codecs', 'unicodedata',
        'locale', 'gettext', 'operator', 'enum', 'graphlib', 'bisect',
        'heapq', 'array', 'weakref', 'types', 'inspect', 'dis',
        'gc', 'atexit', 'builtins', 'tempfile', 'shutil', 'glob',
        'fnmatch', 'linecache', 'platform', 'errno', 'ctypes', 'io'
    }

    external = set()

    for module in modules:
        for imp in module.imports:
            base = imp.split('.')[0]
            if base not in stdlib_modules:
                external.add(base)

        for mod, names in module.from_imports:
            base = mod.split('.')[0]
            if base not in stdlib_modules:
                external.add(base)

    return sorted(external)


def summarize_codebase(root: Path, exclude_patterns: List[str] = None) -> CodebaseSummary:
    """
    Generate a comprehensive summary of a codebase.

    Args:
        root: Root directory
        exclude_patterns: Patterns to exclude

    Returns:
        CodebaseSummary object
    """
    summary = CodebaseSummary(root=root)

    Console.info(f"Scanning {root}...")

    # Find all Python files
    files = list(find_python_files(root, exclude_patterns))
    summary.total_files = len(files)

    Console.info(f"Found {len(files)} Python files")

    # Build directory tree
    summary.directory_tree = build_directory_tree(root, files)

    # Analyze each module
    for path in files:
        module_info = analyze_module(path)
        if module_info:
            summary.modules.append(module_info)
            summary.total_lines += count_lines(path)
            summary.total_functions += len(module_info.functions)
            summary.total_classes += len(module_info.classes)

    Console.info(f"Analyzed {len(summary.modules)} modules")

    # Extract patterns
    summary.patterns = detect_patterns(summary.modules)

    # Find entry points
    summary.entry_points = find_entry_points(root, summary.modules)

    # Extract external dependencies
    summary.external_deps = extract_external_deps(summary.modules)

    # Get recent changes
    commits = get_git_log(count=10, cwd=root)
    summary.recent_changes = [f"{c.short_hash}: {c.message}" for c in commits]

    return summary


def format_summary_markdown(summary: CodebaseSummary) -> str:
    """Format summary as Markdown."""
    lines = [
        "# Codebase Summary",
        "",
        f"**Root:** `{summary.root}`",
        f"**Generated:** {__import__('datetime').datetime.now().isoformat()}",
        "",
        "## Overview",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Python Files | {summary.total_files} |",
        f"| Total Lines | {summary.total_lines:,} |",
        f"| Functions | {summary.total_functions} |",
        f"| Classes | {summary.total_classes} |",
        "",
    ]

    # Directory Structure
    if summary.directory_tree:
        lines.extend([
            "## Directory Structure",
            "",
            "```",
            format_tree_ascii(summary.directory_tree),
            "```",
            "",
        ])

    # Entry Points
    if summary.entry_points:
        lines.extend([
            "## Entry Points",
            "",
        ])
        for ep in summary.entry_points:
            lines.append(f"- `{ep}`")
        lines.append("")

    # Patterns
    if summary.patterns:
        lines.extend([
            "## Detected Patterns",
            "",
        ])
        for pattern in summary.patterns:
            lines.append(f"- {pattern}")
        lines.append("")

    # External Dependencies
    if summary.external_deps:
        lines.extend([
            "## External Dependencies",
            "",
        ])
        for dep in summary.external_deps:
            lines.append(f"- `{dep}`")
        lines.append("")

    # Key Modules
    if summary.modules:
        lines.extend([
            "## Key Modules",
            "",
        ])

        # Sort by number of functions + classes
        sorted_modules = sorted(
            summary.modules,
            key=lambda m: len(m.functions) + len(m.classes),
            reverse=True
        )[:10]  # Top 10

        for module in sorted_modules:
            relative = module.path.relative_to(summary.root) if module.path.is_relative_to(summary.root) else module.path
            lines.append(f"### `{relative}`")

            if module.docstring:
                lines.append(f"> {module.docstring.split(chr(10))[0]}")

            if module.functions:
                func_list = ", ".join(f"`{f.name}`" for f in module.functions[:5])
                if len(module.functions) > 5:
                    func_list += f" (+{len(module.functions) - 5} more)"
                lines.append(f"- **Functions:** {func_list}")

            if module.classes:
                class_list = ", ".join(f"`{c.name}`" for c in module.classes[:5])
                lines.append(f"- **Classes:** {class_list}")

            lines.append("")

    # Recent Changes
    if summary.recent_changes:
        lines.extend([
            "## Recent Changes",
            "",
        ])
        for change in summary.recent_changes[:10]:
            lines.append(f"- {change}")
        lines.append("")

    return "\n".join(lines)


def main():
    """CLI entry point."""
    Console.header("Codebase Summarizer")

    # Parse args
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    output_file = None

    for i, arg in enumerate(sys.argv):
        if arg == '--output' and i + 1 < len(sys.argv):
            output_file = Path(sys.argv[i + 1])

    # Get path
    if args:
        path = Path(args[0])
    else:
        path = find_project_root() or Path.cwd()

    if not path.exists():
        Console.fail(f"Path not found: {path}")
        sys.exit(1)

    Console.info(f"Analyzing: {path}")

    summary = summarize_codebase(path)
    markdown = format_summary_markdown(summary)

    # Output
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown)
        Console.ok(f"Summary written to: {output_file}")
    else:
        # Handle Windows encoding issues
        try:
            print(markdown)
        except UnicodeEncodeError:
            # Fallback: replace problematic characters
            print(markdown.encode('ascii', 'replace').decode('ascii'))

    Console.ok("Summary complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())

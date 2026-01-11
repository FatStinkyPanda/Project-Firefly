"""
Dependency Analyzer
===================
Analyze and visualize project dependencies, detect circular imports.

Usage:
    python deps.py [path] [--output deps.md]
    python -m scripts.deps [path]
"""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import ast
import sys

from .utils import (
    find_python_files,
    find_project_root,
    parse_file,
    Console,
    format_as_markdown_table
)


@dataclass
class DependencyInfo:
    """Dependency information for a module."""
    path: Path
    module_name: str
    imports: Set[str] = field(default_factory=set)
    from_imports: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))

    @property
    def all_dependencies(self) -> Set[str]:
        """Get all dependencies."""
        deps = set(self.imports)
        deps.update(self.from_imports.keys())
        return deps


@dataclass
class DependencyReport:
    """Report of dependency analysis."""
    modules: Dict[str, DependencyInfo] = field(default_factory=dict)
    external_deps: Set[str] = field(default_factory=set)
    internal_deps: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    circular_deps: List[Tuple[str, str]] = field(default_factory=list)
    missing_deps: List[Tuple[str, str]] = field(default_factory=list)


# Standard library modules
STDLIB_MODULES = {
    'abc', 'aifc', 'argparse', 'array', 'ast', 'asyncio', 'atexit',
    'base64', 'bdb', 'binascii', 'bisect', 'builtins', 'bz2',
    'calendar', 'cgi', 'cgitb', 'chunk', 'cmath', 'cmd', 'code',
    'codecs', 'codeop', 'collections', 'colorsys', 'compileall',
    'concurrent', 'configparser', 'contextlib', 'copy', 'copyreg',
    'cProfile', 'crypt', 'csv', 'ctypes', 'curses',
    'dataclasses', 'datetime', 'dbm', 'decimal', 'difflib', 'dis',
    'distutils', 'doctest',
    'email', 'encodings', 'enum', 'errno',
    'faulthandler', 'fcntl', 'filecmp', 'fileinput', 'fnmatch',
    'fractions', 'ftplib', 'functools',
    'gc', 'getopt', 'getpass', 'gettext', 'glob', 'graphlib', 'grp', 'gzip',
    'hashlib', 'heapq', 'hmac', 'html', 'http',
    'imaplib', 'imghdr', 'imp', 'importlib', 'inspect', 'io', 'ipaddress',
    'itertools',
    'json',
    'keyword',
    'lib2to3', 'linecache', 'locale', 'logging', 'lzma',
    'mailbox', 'mailcap', 'marshal', 'math', 'mimetypes', 'mmap',
    'modulefinder', 'multiprocessing',
    'netrc', 'nis', 'nntplib', 'numbers',
    'operator', 'optparse', 'os', 'ossaudiodev',
    'pathlib', 'pdb', 'pickle', 'pickletools', 'pipes', 'pkgutil',
    'platform', 'plistlib', 'poplib', 'posix', 'posixpath', 'pprint',
    'profile', 'pstats', 'pty', 'pwd', 'py_compile', 'pyclbr', 'pydoc',
    'queue', 'quopri',
    'random', 're', 'readline', 'reprlib', 'resource', 'rlcompleter', 'runpy',
    'sched', 'secrets', 'select', 'selectors', 'shelve', 'shlex', 'shutil',
    'signal', 'site', 'smtpd', 'smtplib', 'sndhdr', 'socket', 'socketserver',
    'spwd', 'sqlite3', 'ssl', 'stat', 'statistics', 'string', 'stringprep',
    'struct', 'subprocess', 'sunau', 'symtable', 'sys', 'sysconfig', 'syslog',
    'tabnanny', 'tarfile', 'telnetlib', 'tempfile', 'termios', 'test',
    'textwrap', 'threading', 'time', 'timeit', 'tkinter', 'token', 'tokenize',
    'trace', 'traceback', 'tracemalloc', 'tty', 'turtle', 'turtledemo',
    'types', 'typing',
    'unicodedata', 'unittest', 'urllib', 'uu', 'uuid',
    'venv',
    'warnings', 'wave', 'weakref', 'webbrowser', 'winreg', 'winsound', 'wsgiref',
    'xdrlib', 'xml', 'xmlrpc',
    'zipapp', 'zipfile', 'zipimport', 'zlib',
    '_thread', '__future__',
}


def analyze_imports(path: Path) -> Optional[DependencyInfo]:
    """
    Analyze imports in a Python file.

    Args:
        path: Path to Python file

    Returns:
        DependencyInfo or None if parsing fails
    """
    tree = parse_file(path)
    if tree is None:
        return None

    info = DependencyInfo(
        path=path,
        module_name=path.stem
    )

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                info.imports.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                base_module = node.module.split('.')[0]
                info.imports.add(base_module)
                for alias in node.names:
                    info.from_imports[node.module].add(alias.name)

    return info


def path_to_module_name(path: Path, root: Path) -> str:
    """Convert a file path to a module name."""
    try:
        relative = path.relative_to(root)
        parts = list(relative.with_suffix('').parts)
        return '.'.join(parts)
    except ValueError:
        return path.stem


def analyze_dependencies(
    root: Path,
    exclude_patterns: List[str] = None
) -> DependencyReport:
    """
    Analyze dependencies in a Python project.

    Args:
        root: Root directory
        exclude_patterns: Patterns to exclude

    Returns:
        DependencyReport
    """
    report = DependencyReport()

    Console.info(f"Scanning {root} for Python files...")

    files = list(find_python_files(root, exclude_patterns))
    Console.info(f"Found {len(files)} Python files")

    # Build module name mapping
    module_names = set()
    for path in files:
        module_name = path_to_module_name(path, root)
        module_names.add(module_name.split('.')[0])

    # Analyze each file
    for path in files:
        info = analyze_imports(path)
        if info:
            module_name = path_to_module_name(path, root)
            report.modules[module_name] = info

            # Categorize dependencies
            for dep in info.all_dependencies:
                base_dep = dep.split('.')[0]

                if base_dep in STDLIB_MODULES:
                    continue  # Skip stdlib
                elif base_dep in module_names or dep in module_names:
                    report.internal_deps[module_name].add(dep)
                else:
                    report.external_deps.add(base_dep)

    Console.info("Detecting circular dependencies...")

    # Detect circular dependencies
    for module, deps in report.internal_deps.items():
        base_module = module.split('.')[0]
        for dep in deps:
            base_dep = dep.split('.')[0]
            # Check if the dependency also imports this module
            for other_module, other_deps in report.internal_deps.items():
                other_base = other_module.split('.')[0]
                if other_base == base_dep:
                    for other_dep in other_deps:
                        if other_dep.split('.')[0] == base_module:
                            pair = tuple(sorted([base_module, base_dep]))
                            if pair not in report.circular_deps:
                                report.circular_deps.append(pair)

    return report


def generate_mermaid_diagram(report: DependencyReport, max_nodes: int = 20) -> str:
    """
    Generate a Mermaid diagram of dependencies.

    Args:
        report: DependencyReport
        max_nodes: Maximum number of nodes to show

    Returns:
        Mermaid diagram code
    """
    lines = ["```mermaid", "graph LR"]

    # Track nodes we've added
    nodes_added = set()
    edges_added = set()

    # Add internal dependencies
    for module, deps in list(report.internal_deps.items())[:max_nodes]:
        base_module = module.split('.')[0]

        if base_module not in nodes_added:
            lines.append(f'    {base_module}["{base_module}"]')
            nodes_added.add(base_module)

        for dep in list(deps)[:5]:  # Limit edges per node
            base_dep = dep.split('.')[0]

            if base_dep not in nodes_added and len(nodes_added) < max_nodes:
                lines.append(f'    {base_dep}["{base_dep}"]')
                nodes_added.add(base_dep)

            edge = (base_module, base_dep)
            if edge not in edges_added and base_dep in nodes_added:
                lines.append(f'    {base_module} --> {base_dep}')
                edges_added.add(edge)

    # Highlight circular dependencies
    for mod1, mod2 in report.circular_deps:
        if mod1 in nodes_added and mod2 in nodes_added:
            lines.append(f'    {mod1} <-.->|circular| {mod2}')

    lines.append("```")
    return "\n".join(lines)


def format_report_markdown(report: DependencyReport) -> str:
    """Format dependency report as Markdown."""
    lines = [
        "# Dependency Analysis",
        "",
        "## Summary",
        "",
        f"- **Internal Modules:** {len(report.modules)}",
        f"- **External Dependencies:** {len(report.external_deps)}",
        f"- **Circular Dependencies:** {len(report.circular_deps)}",
        "",
    ]

    # External dependencies
    if report.external_deps:
        lines.extend([
            "## External Dependencies",
            "",
            "These packages need to be installed:",
            "",
        ])
        for dep in sorted(report.external_deps):
            lines.append(f"- `{dep}`")
        lines.append("")

    # Circular dependencies (warning)
    if report.circular_deps:
        lines.extend([
            "## Circular Dependencies [WARNING]",
            "",
            "The following modules have circular imports:",
            "",
        ])
        for mod1, mod2 in report.circular_deps:
            lines.append(f"- `{mod1}` <-> `{mod2}`")
        lines.append("")

    # Dependency graph
    if report.internal_deps:
        lines.extend([
            "## Dependency Graph",
            "",
            generate_mermaid_diagram(report),
            "",
        ])

    # Internal dependencies table
    if report.internal_deps:
        lines.extend([
            "## Internal Dependencies",
            "",
        ])

        rows = []
        for module, deps in sorted(report.internal_deps.items()):
            dep_list = ", ".join(sorted(deps)[:5])
            if len(deps) > 5:
                dep_list += f" (+{len(deps)-5} more)"
            rows.append([module, dep_list])

        lines.append(format_as_markdown_table(["Module", "Depends On"], rows))
        lines.append("")

    return "\n".join(lines)


def main():
    """CLI entry point."""
    Console.header("Dependency Analyzer")

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

    report = analyze_dependencies(path)
    markdown = format_report_markdown(report)

    # Output
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown)
        Console.ok(f"Report written to: {output_file}")
    else:
        print(markdown)

    # Summary
    if report.circular_deps:
        Console.warn(f"Found {len(report.circular_deps)} circular dependencies")
    else:
        Console.ok("No circular dependencies detected")

    Console.ok(f"Found {len(report.external_deps)} external dependencies")

    return 1 if report.circular_deps else 0


if __name__ == "__main__":
    sys.exit(main())

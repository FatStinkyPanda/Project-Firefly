"""
Impact Analysis
================
Analyze what breaks when code changes.

Usage:
    python mcp.py impact [file]
    python mcp.py impact --test [file]  # Show affected tests
"""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import ast
import json
import sys

from .utils import Console, find_python_files, find_project_root


@dataclass
class ImpactReport:
    """Report of change impact."""
    file: str
    direct_dependents: List[str] = field(default_factory=list)  # Files that import this
    indirect_dependents: List[str] = field(default_factory=list)  # Transitive deps
    affected_tests: List[str] = field(default_factory=list)
    total_impact: int = 0

    def to_markdown(self) -> str:
        lines = [
            f"# Impact Report: {Path(self.file).name}",
            "",
            f"**Total Impact:** {self.total_impact} files",
            "",
        ]

        if self.direct_dependents:
            lines.append("## Direct Dependents")
            for dep in self.direct_dependents[:10]:
                lines.append(f"- {dep}")
            lines.append("")

        if self.indirect_dependents:
            lines.append("## Indirect Dependents")
            for dep in self.indirect_dependents[:10]:
                lines.append(f"- {dep}")
            lines.append("")

        if self.affected_tests:
            lines.append("## Affected Tests")
            for test in self.affected_tests[:10]:
                lines.append(f"- {test}")

        return '\n'.join(lines)


class DependencyGraph:
    """Graph of file dependencies."""

    def __init__(self):
        self.imports: Dict[str, Set[str]] = defaultdict(set)  # file -> what it imports
        self.imported_by: Dict[str, Set[str]] = defaultdict(set)  # file -> who imports it
        self.module_to_file: Dict[str, str] = {}  # module name -> file path

    def add_file(self, file_path: Path, root: Path):
        """Add a file's imports to the graph."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            tree = ast.parse(source)
        except Exception:
            return

        file_key = str(file_path.relative_to(root))

        # Register this module
        module_name = str(file_path.relative_to(root).with_suffix('')).replace('\\', '.').replace('/', '.')
        self.module_to_file[module_name] = file_key

        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.imports[file_key].add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.imports[file_key].add(node.module)

    def build(self, root: Path, exclude_patterns: List[str] = None):
        """Build full dependency graph."""
        for file_path in find_python_files(root, exclude_patterns):
            self.add_file(file_path, root)

        # Build reverse mapping
        for file_key, imports in self.imports.items():
            for imp in imports:
                # Try to resolve import to file
                if imp in self.module_to_file:
                    self.imported_by[self.module_to_file[imp]].add(file_key)

    def get_dependents(self, file_path: str) -> Set[str]:
        """Get files that depend on this file."""
        return self.imported_by.get(file_path, set())

    def get_dependencies(self, file_path: str) -> Set[str]:
        """Get files this file depends on."""
        return self.imports.get(file_path, set())

    def get_transitive_dependents(self, file_path: str, visited: Set[str] = None) -> Set[str]:
        """Get all transitive dependents."""
        if visited is None:
            visited = set()

        if file_path in visited:
            return set()

        visited.add(file_path)

        all_deps = set()
        direct = self.get_dependents(file_path)
        all_deps.update(direct)

        for dep in direct:
            all_deps.update(self.get_transitive_dependents(dep, visited))

        return all_deps


def build_dependency_graph(root: Path = None) -> DependencyGraph:
    """Build and return dependency graph."""
    root = root or find_project_root() or Path.cwd()

    Console.info("Building dependency graph...")

    graph = DependencyGraph()
    exclude = ['node_modules', 'venv', '.venv', '__pycache__', '.git', 'vendor']
    graph.build(root, exclude)

    Console.ok(f"Indexed {len(graph.imports)} files")

    return graph


def analyze_impact(file_path: Path, root: Path = None) -> ImpactReport:
    """Analyze impact of changing a file."""
    root = root or find_project_root() or Path.cwd()

    graph = build_dependency_graph(root)

    try:
        file_key = str(file_path.relative_to(root))
    except ValueError:
        file_key = str(file_path)

    direct = list(graph.get_dependents(file_key))

    all_deps = graph.get_transitive_dependents(file_key)
    indirect = [d for d in all_deps if d not in direct]

    # Find affected tests
    tests = [d for d in all_deps if 'test' in d.lower() or d.startswith('tests/')]

    return ImpactReport(
        file=file_key,
        direct_dependents=direct,
        indirect_dependents=indirect,
        affected_tests=tests,
        total_impact=len(all_deps)
    )


def save_impact_graph(root: Path = None):
    """Save dependency graph to disk."""
    root = root or find_project_root() or Path.cwd()

    graph = build_dependency_graph(root)

    # Convert to serializable format
    data = {
        "imports": {k: list(v) for k, v in graph.imports.items()},
        "imported_by": {k: list(v) for k, v in graph.imported_by.items()},
        "file_count": len(graph.imports)
    }

    index_path = root / '.mcp' / 'impact_graph.json'
    index_path.parent.mkdir(parents=True, exist_ok=True)

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    Console.ok(f"Saved impact graph to {index_path}")


def main():
    """CLI entry point."""
    Console.header("Impact Analysis")

    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    root = find_project_root() or Path.cwd()

    if '--index' in sys.argv:
        save_impact_graph(root)
        return 0

    if not args:
        Console.info("Usage: python impact.py <file>")
        Console.info("Options:")
        Console.info("  --index    Save dependency graph")
        Console.info("  --test     Show only affected tests")
        return 1

    file_path = Path(args[0])

    if not file_path.exists():
        Console.fail(f"File not found: {file_path}")
        return 1

    report = analyze_impact(file_path, root)

    if '--test' in sys.argv:
        Console.info(f"Affected tests for {file_path.name}:")
        for test in report.affected_tests:
            print(f"  - {test}")
        print(f"\nTotal: {len(report.affected_tests)} tests")
    else:
        print(report.to_markdown())

    return 0


if __name__ == "__main__":
    sys.exit(main())

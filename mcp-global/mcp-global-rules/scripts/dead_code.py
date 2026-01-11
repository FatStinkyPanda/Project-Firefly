"""
Dead Code Detector
==================
Find unused functions, classes, imports, and variables in Python code.

Usage:
    python dead_code.py [path]
    python -m scripts.dead_code [path]
"""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple
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
class DeadCodeReport:
    """Report of detected dead code."""
    unused_imports: List[Tuple[Path, int, str]] = field(default_factory=list)
    unused_functions: List[Tuple[Path, int, str]] = field(default_factory=list)
    unused_classes: List[Tuple[Path, int, str]] = field(default_factory=list)
    unused_variables: List[Tuple[Path, int, str]] = field(default_factory=list)

    @property
    def total_issues(self) -> int:
        return (len(self.unused_imports) + len(self.unused_functions) +
                len(self.unused_classes) + len(self.unused_variables))

    def to_markdown(self) -> str:
        """Convert report to markdown format."""
        lines = ["# Dead Code Report\n"]

        if self.total_issues == 0:
            lines.append("No dead code detected.\n")
            return "\n".join(lines)

        lines.append(f"**Total issues found: {self.total_issues}**\n")

        if self.unused_imports:
            lines.append("## Unused Imports\n")
            rows = [[str(p), str(line), name] for p, line, name in self.unused_imports]
            lines.append(format_as_markdown_table(["File", "Line", "Import"], rows))
            lines.append("")

        if self.unused_functions:
            lines.append("## Unused Functions\n")
            rows = [[str(p), str(line), name] for p, line, name in self.unused_functions]
            lines.append(format_as_markdown_table(["File", "Line", "Function"], rows))
            lines.append("")

        if self.unused_classes:
            lines.append("## Unused Classes\n")
            rows = [[str(p), str(line), name] for p, line, name in self.unused_classes]
            lines.append(format_as_markdown_table(["File", "Line", "Class"], rows))
            lines.append("")

        if self.unused_variables:
            lines.append("## Unused Variables\n")
            rows = [[str(p), str(line), name] for p, line, name in self.unused_variables]
            lines.append(format_as_markdown_table(["File", "Line", "Variable"], rows))
            lines.append("")

        return "\n".join(lines)


class DefinitionCollector(ast.NodeVisitor):
    """Collect all definitions in a module."""

    def __init__(self, path: Path):
        self.path = path
        self.imports: Dict[str, int] = {}  # name -> lineno
        self.functions: Dict[str, int] = {}
        self.classes: Dict[str, int] = {}
        self.variables: Dict[str, int] = {}
        self._in_class = False

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.asname or alias.name.split('.')[0]
            self.imports[name] = node.lineno
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        for alias in node.names:
            if alias.name != '*':
                name = alias.asname or alias.name
                self.imports[name] = node.lineno
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if not self._in_class and not node.name.startswith('_'):
            self.functions[node.name] = node.lineno
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        if not self._in_class and not node.name.startswith('_'):
            self.functions[node.name] = node.lineno
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        if not node.name.startswith('_'):
            self.classes[node.name] = node.lineno

        old_in_class = self._in_class
        self._in_class = True
        self.generic_visit(node)
        self._in_class = old_in_class

    def visit_Assign(self, node: ast.Assign):
        if not self._in_class:
            for target in node.targets:
                if isinstance(target, ast.Name) and not target.id.startswith('_'):
                    # Skip common constants/configs
                    if target.id.isupper():
                        continue
                    self.variables[target.id] = node.lineno
        self.generic_visit(node)


class UsageCollector(ast.NodeVisitor):
    """Collect all name usages in a module."""

    def __init__(self):
        self.used_names: Set[str] = set()

    def visit_Name(self, node: ast.Name):
        self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        # Track the base name
        if isinstance(node.value, ast.Name):
            self.used_names.add(node.value.id)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            self.used_names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                self.used_names.add(node.func.value.id)
        self.generic_visit(node)


def analyze_file(path: Path) -> Tuple[Dict[str, Dict[str, int]], Set[str]]:
    """
    Analyze a single file for definitions and usages.

    Returns:
        Tuple of (definitions dict, used names set)
    """
    tree = parse_file(path)
    if tree is None:
        return {}, set()

    # Collect definitions
    def_collector = DefinitionCollector(path)
    def_collector.visit(tree)

    # Collect usages
    usage_collector = UsageCollector()
    usage_collector.visit(tree)

    definitions = {
        'imports': def_collector.imports,
        'functions': def_collector.functions,
        'classes': def_collector.classes,
        'variables': def_collector.variables
    }

    return definitions, usage_collector.used_names


def detect_dead_code(
    root: Path,
    exclude_patterns: List[str] = None
) -> DeadCodeReport:
    """
    Detect dead code in a Python project.

    Args:
        root: Root directory to analyze
        exclude_patterns: Patterns to exclude

    Returns:
        DeadCodeReport with findings
    """
    report = DeadCodeReport()

    # Collect all definitions and usages across the project
    all_definitions: Dict[Path, Dict[str, Dict[str, int]]] = {}
    all_usages: Set[str] = set()

    # Known always-used names (builtins, common patterns)
    always_used = {
        'self', 'cls', 'args', 'kwargs',
        'main', 'setup', 'teardown',
        '__all__', '__version__', '__name__', '__main__'
    }
    all_usages.update(always_used)

    Console.info(f"Scanning for Python files in {root}...")

    files = list(find_python_files(root, exclude_patterns))
    Console.info(f"Found {len(files)} Python files")

    for path in files:
        definitions, usages = analyze_file(path)
        if definitions:
            all_definitions[path] = definitions
            all_usages.update(usages)

    Console.info("Analyzing for dead code...")

    # Check each definition against all usages
    for path, definitions in all_definitions.items():
        relative_path = path.relative_to(root) if path.is_relative_to(root) else path

        # Check imports (only within the same file typically)
        for name, lineno in definitions.get('imports', {}).items():
            file_defs, file_usages = analyze_file(path)
            if name not in file_usages and name not in always_used:
                report.unused_imports.append((relative_path, lineno, name))

        # Check functions (project-wide)
        for name, lineno in definitions.get('functions', {}).items():
            if name not in all_usages:
                report.unused_functions.append((relative_path, lineno, name))

        # Check classes (project-wide)
        for name, lineno in definitions.get('classes', {}).items():
            if name not in all_usages:
                report.unused_classes.append((relative_path, lineno, name))

        # Check variables (file-local typically)
        for name, lineno in definitions.get('variables', {}).items():
            file_defs, file_usages = analyze_file(path)
            # Variables should be used at least twice (definition + usage)
            # Count occurrences in source
            if name not in file_usages:
                report.unused_variables.append((relative_path, lineno, name))

    return report


def main():
    """CLI entry point."""
    Console.header("Dead Code Detector")

    # Get path from args or use project root
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        path = find_project_root() or Path.cwd()

    if not path.exists():
        Console.fail(f"Path not found: {path}")
        sys.exit(1)

    Console.info(f"Analyzing: {path}")

    report = detect_dead_code(path)

    print(report.to_markdown())

    if report.total_issues > 0:
        Console.warn(f"Found {report.total_issues} potential dead code issues")
    else:
        Console.ok("No dead code detected")

    return report.total_issues


if __name__ == "__main__":
    sys.exit(main())

"""
Auto-Refactorer
===============
Detect and suggest code refactorings for improved quality.

Usage:
    python refactor.py [path] [--apply]
    python -m scripts.refactor src/
"""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import ast
import hashlib
import sys

from .utils import (
    find_python_files,
    find_project_root,
    parse_file,
    Console,
    format_as_markdown_table
)


@dataclass
class RefactoringSuggestion:
    """A suggested refactoring."""
    path: Path
    line_start: int
    line_end: int
    severity: str  # 'high', 'medium', 'low'
    category: str  # 'long_function', 'duplicate', 'complex', 'naming'
    message: str
    suggestion: str


@dataclass
class RefactoringReport:
    """Complete refactoring report."""
    suggestions: List[RefactoringSuggestion] = field(default_factory=list)

    @property
    def high_priority(self) -> List[RefactoringSuggestion]:
        return [s for s in self.suggestions if s.severity == 'high']

    def to_markdown(self) -> str:
        lines = [
            "# Refactoring Suggestions",
            "",
            f"**Total suggestions:** {len(self.suggestions)}",
            f"**High priority:** {len(self.high_priority)}",
            "",
        ]

        # Group by severity
        for severity in ['high', 'medium', 'low']:
            items = [s for s in self.suggestions if s.severity == severity]
            if not items:
                continue

            lines.append(f"## {severity.upper()} Priority")
            lines.append("")

            for s in items:
                lines.append(f"### {s.category}: {s.path}:{s.line_start}")
                lines.append(f"**Issue:** {s.message}")
                lines.append(f"**Suggestion:** {s.suggestion}")
                lines.append("")

        return "\n".join(lines)


class LongFunctionDetector(ast.NodeVisitor):
    """Detect functions that are too long."""

    MAX_LINES = 50

    def __init__(self, path: Path):
        self.path = path
        self.issues: List[RefactoringSuggestion] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(self, node):
        if node.end_lineno:
            length = node.end_lineno - node.lineno
            if length > self.MAX_LINES:
                self.issues.append(RefactoringSuggestion(
                    path=self.path,
                    line_start=node.lineno,
                    line_end=node.end_lineno,
                    severity='high' if length > 100 else 'medium',
                    category='long_function',
                    message=f"Function '{node.name}' is {length} lines (max: {self.MAX_LINES})",
                    suggestion=f"Extract helper functions from '{node.name}'"
                ))


class ComplexityDetector(ast.NodeVisitor):
    """Detect overly complex code."""

    MAX_NESTED = 4
    MAX_CONDITIONS = 5

    def __init__(self, path: Path):
        self.path = path
        self.issues: List[RefactoringSuggestion] = []
        self._nesting_level = 0
        self._current_function = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        old_func = self._current_function
        self._current_function = node.name
        self._nesting_level = 0
        self.generic_visit(node)
        self._current_function = old_func

    def visit_If(self, node: ast.If):
        self._check_nesting(node)
        self._nesting_level += 1
        self.generic_visit(node)
        self._nesting_level -= 1

    def visit_For(self, node: ast.For):
        self._check_nesting(node)
        self._nesting_level += 1
        self.generic_visit(node)
        self._nesting_level -= 1

    def visit_While(self, node: ast.While):
        self._check_nesting(node)
        self._nesting_level += 1
        self.generic_visit(node)
        self._nesting_level -= 1

    def visit_Try(self, node: ast.Try):
        self._check_nesting(node)
        self._nesting_level += 1
        self.generic_visit(node)
        self._nesting_level -= 1

    def _check_nesting(self, node):
        if self._nesting_level >= self.MAX_NESTED:
            self.issues.append(RefactoringSuggestion(
                path=self.path,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                severity='high',
                category='deep_nesting',
                message=f"Deeply nested code ({self._nesting_level + 1} levels)",
                suggestion="Extract nested logic into helper functions"
            ))


class DuplicateCodeDetector:
    """Detect duplicate code blocks."""

    MIN_LINES = 5

    def __init__(self):
        self.code_hashes: Dict[str, List[Tuple[Path, int, int]]] = defaultdict(list)
        self.issues: List[RefactoringSuggestion] = []

    def analyze_file(self, path: Path, tree: ast.Module, source_lines: List[str]):
        """Analyze file for duplicate blocks."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.end_lineno:
                    start = node.lineno - 1
                    end = node.end_lineno
                    if end - start >= self.MIN_LINES:
                        content = '\n'.join(source_lines[start:end])
                        # Normalize whitespace
                        normalized = ' '.join(content.split())
                        code_hash = hashlib.md5(normalized.encode()).hexdigest()
                        self.code_hashes[code_hash].append((path, start + 1, end))

    def finalize(self):
        """Generate issues for duplicates."""
        for code_hash, locations in self.code_hashes.items():
            if len(locations) > 1:
                files = list(set(str(loc[0]) for loc in locations))
                for path, start, end in locations:
                    self.issues.append(RefactoringSuggestion(
                        path=path,
                        line_start=start,
                        line_end=end,
                        severity='medium',
                        category='duplicate_code',
                        message=f"Duplicate code found in {len(locations)} locations",
                        suggestion=f"Extract common code into shared function"
                    ))


class NamingConventionChecker(ast.NodeVisitor):
    """Check naming conventions."""

    def __init__(self, path: Path):
        self.path = path
        self.issues: List[RefactoringSuggestion] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._check_function_name(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self._check_class_name(node)
        self.generic_visit(node)

    def _check_function_name(self, node):
        name = node.name
        if name.startswith('_'):
            return

        # Check for camelCase
        if any(c.isupper() for c in name[1:]) and '_' not in name:
            self.issues.append(RefactoringSuggestion(
                path=self.path,
                line_start=node.lineno,
                line_end=node.lineno,
                severity='low',
                category='naming',
                message=f"Function '{name}' uses camelCase",
                suggestion=f"Rename to snake_case: '{self._to_snake_case(name)}'"
            ))

        # Check single letter names (except i, j, k, x, y, z)
        if len(name) == 1 and name not in 'ijkxyz':
            self.issues.append(RefactoringSuggestion(
                path=self.path,
                line_start=node.lineno,
                line_end=node.lineno,
                severity='low',
                category='naming',
                message=f"Function '{name}' has single-letter name",
                suggestion="Use descriptive function name"
            ))

    def _check_class_name(self, node):
        name = node.name
        if name.startswith('_'):
            return

        # Check for snake_case in class names
        if '_' in name:
            self.issues.append(RefactoringSuggestion(
                path=self.path,
                line_start=node.lineno,
                line_end=node.lineno,
                severity='low',
                category='naming',
                message=f"Class '{name}' uses snake_case",
                suggestion=f"Rename to CamelCase: '{self._to_camel_case(name)}'"
            ))

    def _to_snake_case(self, name: str) -> str:
        result = []
        for i, c in enumerate(name):
            if c.isupper() and i > 0:
                result.append('_')
            result.append(c.lower())
        return ''.join(result)

    def _to_camel_case(self, name: str) -> str:
        return ''.join(word.capitalize() for word in name.split('_'))


class ParameterCountChecker(ast.NodeVisitor):
    """Check for functions with too many parameters."""

    MAX_PARAMS = 5

    def __init__(self, path: Path):
        self.path = path
        self.issues: List[RefactoringSuggestion] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._check_params(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._check_params(node)
        self.generic_visit(node)

    def _check_params(self, node):
        # Count params excluding self/cls
        params = [a for a in node.args.args if a.arg not in ('self', 'cls')]
        if len(params) > self.MAX_PARAMS:
            self.issues.append(RefactoringSuggestion(
                path=self.path,
                line_start=node.lineno,
                line_end=node.lineno,
                severity='medium',
                category='too_many_params',
                message=f"Function '{node.name}' has {len(params)} parameters (max: {self.MAX_PARAMS})",
                suggestion="Consider using a configuration object or dataclass"
            ))


def analyze_file(path: Path) -> List[RefactoringSuggestion]:
    """Analyze a single file for refactoring opportunities."""
    issues = []

    tree = parse_file(path)
    if tree is None:
        return issues

    try:
        with open(path, 'r', encoding='utf-8') as f:
            source_lines = f.readlines()
    except Exception:
        return issues

    # Run all detectors
    detectors = [
        LongFunctionDetector(path),
        ComplexityDetector(path),
        NamingConventionChecker(path),
        ParameterCountChecker(path),
    ]

    for detector in detectors:
        detector.visit(tree)
        issues.extend(detector.issues)

    return issues


def analyze_project(
    root: Path,
    exclude_patterns: List[str] = None
) -> RefactoringReport:
    """Analyze project for refactoring opportunities."""
    report = RefactoringReport()
    duplicate_detector = DuplicateCodeDetector()

    Console.info(f"Analyzing {root}...")

    files = list(find_python_files(root, exclude_patterns))
    Console.info(f"Found {len(files)} Python files")

    for path in files:
        # Single file analysis
        issues = analyze_file(path)
        report.suggestions.extend(issues)

        # Collect for duplicate detection
        tree = parse_file(path)
        if tree:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    source_lines = f.readlines()
                duplicate_detector.analyze_file(path, tree, source_lines)
            except Exception:
                pass

    # Finalize duplicate detection
    duplicate_detector.finalize()
    report.suggestions.extend(duplicate_detector.issues)

    return report


def main():
    """CLI entry point."""
    Console.header("Auto-Refactorer")

    # Parse args
    args = [a for a in sys.argv[1:] if not a.startswith('-')]

    if args:
        path = Path(args[0])
    else:
        path = find_project_root() or Path.cwd()

    if not path.exists():
        Console.fail(f"Path not found: {path}")
        return 1

    Console.info(f"Analyzing: {path}")

    report = analyze_project(path)

    print(report.to_markdown())

    Console.info(f"Found {len(report.suggestions)} refactoring suggestions")
    Console.info(f"High priority: {len(report.high_priority)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

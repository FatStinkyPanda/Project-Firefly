"""
Performance Profiler
====================
Static analysis for performance bottlenecks and code complexity.

Usage:
    python profile.py [path]
    python -m scripts.profile src/
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set
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
class PerformanceIssue:
    """A performance finding."""
    path: Path
    line: int
    severity: str  # 'critical', 'high', 'medium', 'low'
    category: str
    title: str
    description: str
    complexity: Optional[str] = None  # Big-O notation
    suggestion: Optional[str] = None


@dataclass
class PerformanceReport:
    """Complete performance analysis report."""
    issues: List[PerformanceIssue] = field(default_factory=list)
    complexity_scores: Dict[str, int] = field(default_factory=dict)

    def to_markdown(self) -> str:
        lines = [
            "# Performance Analysis Report",
            "",
            "## Summary",
            "",
            f"**Total Issues:** {len(self.issues)}",
            "",
        ]

        if self.complexity_scores:
            lines.extend([
                "## Complexity Scores (Cyclomatic)",
                "",
                "| Function | Score |",
                "|----------|-------|",
            ])
            sorted_scores = sorted(
                self.complexity_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            for name, score in sorted_scores:
                status = "HIGH" if score > 10 else "OK" if score <= 5 else "MEDIUM"
                lines.append(f"| `{name}` | {score} ({status}) |")
            lines.append("")

        if self.issues:
            lines.extend(["## Issues", ""])

            for issue in sorted(self.issues, key=lambda x: (
                {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(x.severity, 4)
            )):
                lines.append(f"### {issue.title}")
                lines.append(f"**File:** `{issue.path}:{issue.line}`")
                lines.append(f"**Severity:** {issue.severity.upper()}")
                if issue.complexity:
                    lines.append(f"**Complexity:** {issue.complexity}")
                lines.append("")
                lines.append(issue.description)
                if issue.suggestion:
                    lines.append("")
                    lines.append(f"**Suggestion:** {issue.suggestion}")
                lines.append("")

        return "\n".join(lines)


class ComplexityAnalyzer(ast.NodeVisitor):
    """Calculate cyclomatic complexity."""

    def __init__(self):
        self.complexity = 1  # Base complexity

    def visit_If(self, node: ast.If):
        self.complexity += 1
        # Count elif branches
        for _ in node.orelse:
            if isinstance(_, ast.If):
                self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp):
        # Each and/or adds a decision point
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension):
        self.complexity += 1
        self.complexity += len(node.ifs)
        self.generic_visit(node)


class PerformanceAnalyzer(ast.NodeVisitor):
    """Analyze code for performance issues."""

    def __init__(self, path: Path):
        self.path = path
        self.issues: List[PerformanceIssue] = []
        self.complexity_scores: Dict[str, int] = {}
        self._current_function: Optional[str] = None
        self._loop_depth = 0

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._analyze_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._analyze_function(node)
        self.generic_visit(node)

    def _analyze_function(self, node):
        # Calculate complexity
        analyzer = ComplexityAnalyzer()
        analyzer.visit(node)

        func_name = f"{self.path.stem}.{node.name}"
        self.complexity_scores[func_name] = analyzer.complexity

        # Check for high complexity
        if analyzer.complexity > 15:
            self.issues.append(PerformanceIssue(
                path=self.path,
                line=node.lineno,
                severity='high',
                category='complexity',
                title=f"High cyclomatic complexity: {node.name}",
                description=f"Function has complexity of {analyzer.complexity} (threshold: 15)",
                suggestion="Break down into smaller functions"
            ))
        elif analyzer.complexity > 10:
            self.issues.append(PerformanceIssue(
                path=self.path,
                line=node.lineno,
                severity='medium',
                category='complexity',
                title=f"Medium complexity: {node.name}",
                description=f"Function has complexity of {analyzer.complexity} (threshold: 10)",
                suggestion="Consider refactoring"
            ))

        # Check function body
        old_func = self._current_function
        self._current_function = node.name

        for child in ast.walk(node):
            if isinstance(child, ast.For):
                self._check_nested_loops(child, node)
            elif isinstance(child, ast.ListComp):
                self._check_list_comprehension(child)
            elif isinstance(child, ast.Call):
                self._check_expensive_calls(child)

        self._current_function = old_func

    def _check_nested_loops(self, node: ast.For, parent_func):
        """Detect nested loops (O(n^2) or worse)."""
        nested = 0
        for child in ast.walk(node):
            if isinstance(child, ast.For) and child != node:
                nested += 1

        if nested >= 2:
            self.issues.append(PerformanceIssue(
                path=self.path,
                line=node.lineno,
                severity='high',
                category='algorithm',
                title="Deeply nested loops",
                description=f"Found {nested + 1} levels of nested loops",
                complexity=f"O(n^{nested + 1})",
                suggestion="Consider using sets, dicts, or algorithmic optimizations"
            ))
        elif nested == 1:
            self.issues.append(PerformanceIssue(
                path=self.path,
                line=node.lineno,
                severity='medium',
                category='algorithm',
                title="Nested loop",
                description="Nested loop detected - may be O(n^2)",
                complexity="O(n^2)",
                suggestion="Consider if this can be optimized with data structures"
            ))

    def _check_list_comprehension(self, node: ast.ListComp):
        """Check for expensive list comprehensions."""
        # Check for nested comprehensions
        for gen in node.generators:
            if isinstance(gen.iter, ast.ListComp):
                self.issues.append(PerformanceIssue(
                    path=self.path,
                    line=node.lineno,
                    severity='medium',
                    category='memory',
                    title="Nested list comprehension",
                    description="Nested comprehensions create intermediate lists",
                    suggestion="Consider using generator expressions"
                ))

    def _check_expensive_calls(self, node: ast.Call):
        """Check for expensive function calls."""
        func_name = self._get_func_name(node.func)

        # String concatenation in loop
        if func_name == 'join':
            pass  # join is good

        # len() in loop condition
        # (would need more context to detect)

        # Regular expression compilation in loop
        if func_name in ('re.match', 're.search', 're.findall'):
            # Check if inside a loop
            pass  # Would need parent context

    def _get_func_name(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                return f"{node.value.id}.{node.attr}"
            return node.attr
        return ""


class MemoryAnalyzer(ast.NodeVisitor):
    """Analyze code for memory issues."""

    def __init__(self, path: Path):
        self.path = path
        self.issues: List[PerformanceIssue] = []

    def visit_Call(self, node: ast.Call):
        func_name = self._get_func_name(node.func)

        # Check for reading entire files
        if func_name in ('read', 'readlines'):
            self.issues.append(PerformanceIssue(
                path=self.path,
                line=node.lineno,
                severity='low',
                category='memory',
                title="Reading entire file into memory",
                description="Using read()/readlines() loads entire file",
                suggestion="Consider iterating line by line for large files"
            ))

        # Large list operations
        if func_name == 'sorted' or func_name == 'list':
            self.issues.append(PerformanceIssue(
                path=self.path,
                line=node.lineno,
                severity='low',
                category='memory',
                title="Potential memory allocation",
                description=f"{func_name}() creates a new list in memory",
                suggestion="Consider if generator/iterator would work"
            ))

        self.generic_visit(node)

    def _get_func_name(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return ""


class AsyncAnalyzer(ast.NodeVisitor):
    """Analyze async code for issues."""

    def __init__(self, path: Path):
        self.path = path
        self.issues: List[PerformanceIssue] = []
        self._in_async = False

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        old_in_async = self._in_async
        self._in_async = True
        self.generic_visit(node)
        self._in_async = old_in_async

    def visit_Call(self, node: ast.Call):
        if self._in_async:
            func_name = self._get_func_name(node.func)

            # Blocking calls in async code
            blocking = {
                'time.sleep': 'asyncio.sleep',
                'requests.get': 'aiohttp.get',
                'requests.post': 'aiohttp.post',
                'open': 'aiofiles.open',
            }

            if func_name in blocking:
                self.issues.append(PerformanceIssue(
                    path=self.path,
                    line=node.lineno,
                    severity='high',
                    category='async',
                    title=f"Blocking call in async: {func_name}",
                    description=f"{func_name}() blocks the event loop",
                    suggestion=f"Use {blocking[func_name]}() instead"
                ))

        self.generic_visit(node)

    def _get_func_name(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                return f"{node.value.id}.{node.attr}"
            return node.attr
        return ""


def analyze_file(path: Path) -> Tuple[List[PerformanceIssue], Dict[str, int]]:
    """Analyze a single file for performance issues."""
    issues = []
    complexity = {}

    tree = parse_file(path)
    if tree is None:
        return issues, complexity

    # Run analyzers
    perf = PerformanceAnalyzer(path)
    perf.visit(tree)
    issues.extend(perf.issues)
    complexity.update(perf.complexity_scores)

    mem = MemoryAnalyzer(path)
    mem.visit(tree)
    issues.extend(mem.issues)

    async_analyzer = AsyncAnalyzer(path)
    async_analyzer.visit(tree)
    issues.extend(async_analyzer.issues)

    return issues, complexity


def analyze_project(
    root: Path,
    exclude_patterns: List[str] = None
) -> PerformanceReport:
    """Analyze project for performance issues."""
    report = PerformanceReport()

    Console.info(f"Analyzing {root}...")

    files = list(find_python_files(root, exclude_patterns))
    Console.info(f"Found {len(files)} Python files")

    for path in files:
        issues, complexity = analyze_file(path)
        report.issues.extend(issues)
        report.complexity_scores.update(complexity)

    return report


# Required for type hints
from typing import Tuple


def main():
    """CLI entry point."""
    Console.header("Performance Profiler")

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

    # Summary
    high_complexity = sum(1 for s in report.complexity_scores.values() if s > 10)

    if high_complexity > 0:
        Console.warn(f"Found {high_complexity} functions with high complexity")

    Console.info(f"Found {len(report.issues)} performance issues")

    return 0


if __name__ == "__main__":
    sys.exit(main())

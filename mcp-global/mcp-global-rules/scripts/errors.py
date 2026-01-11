"""
Error Pattern Analyzer
======================
Analyze exception handling and error patterns in code.

Usage:
    python errors.py [path]
    python -m scripts.errors src/
"""

from collections import Counter
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
class ErrorPattern:
    """An error handling pattern."""
    path: Path
    line: int
    pattern_type: str  # 'bare_except', 'swallowed', 'broad', 'reraise', 'logged'
    exception_type: Optional[str] = None
    severity: str = 'medium'
    description: str = ""


@dataclass
class ErrorReport:
    """Complete error analysis report."""
    patterns: List[ErrorPattern] = field(default_factory=list)
    exception_usage: Counter = field(default_factory=Counter)
    total_try_blocks: int = 0

    @property
    def issues(self) -> List[ErrorPattern]:
        return [p for p in self.patterns if p.severity in ('high', 'medium')]

    def to_markdown(self) -> str:
        lines = [
            "# Error Handling Analysis",
            "",
            "## Summary",
            "",
            f"- **Try blocks:** {self.total_try_blocks}",
            f"- **Issues found:** {len(self.issues)}",
            "",
        ]

        # Exception types used
        if self.exception_usage:
            lines.extend([
                "## Exception Types Used",
                "",
                "| Exception | Count |",
                "|-----------|-------|",
            ])
            for exc, count in self.exception_usage.most_common(10):
                lines.append(f"| `{exc}` | {count} |")
            lines.append("")

        # Issues by severity
        for severity in ['high', 'medium', 'low']:
            items = [p for p in self.patterns if p.severity == severity]
            if not items:
                continue

            lines.append(f"## {severity.upper()} Severity")
            lines.append("")

            for p in items:
                lines.append(f"### {p.pattern_type}: {p.path}:{p.line}")
                lines.append(p.description)
                lines.append("")

        return "\n".join(lines)


# Known exception fixes
EXCEPTION_FIXES = {
    'FileNotFoundError': "Check file exists before opening, or use try/except with specific handling",
    'KeyError': "Use dict.get() with default, or check key existence first",
    'IndexError': "Check list length before accessing, or use try/except",
    'ValueError': "Validate input before processing",
    'TypeError': "Check types before operations, consider type hints",
    'AttributeError': "Check object type or use hasattr() before attribute access",
    'ZeroDivisionError': "Check divisor is not zero before division",
    'ImportError': "Wrap import in try/except for optional dependencies",
    'ConnectionError': "Implement retry logic with exponential backoff",
    'TimeoutError': "Implement timeout handling and retry logic",
}


class ExceptionAnalyzer(ast.NodeVisitor):
    """Analyze exception handling patterns."""

    def __init__(self, path: Path):
        self.path = path
        self.patterns: List[ErrorPattern] = []
        self.exception_usage: Counter = Counter()
        self.try_count = 0

    def visit_Try(self, node: ast.Try):
        self.try_count += 1

        for handler in node.handlers:
            self._analyze_handler(handler)

        self.generic_visit(node)

    def _analyze_handler(self, handler: ast.ExceptHandler):
        # Get exception type
        if handler.type is None:
            # Bare except
            self.patterns.append(ErrorPattern(
                path=self.path,
                line=handler.lineno,
                pattern_type='bare_except',
                severity='high',
                description="Bare 'except:' catches all exceptions including KeyboardInterrupt"
            ))
            self.exception_usage['Exception'] += 1
        elif isinstance(handler.type, ast.Name):
            exc_name = handler.type.id
            self.exception_usage[exc_name] += 1

            # Check for broad exception
            if exc_name == 'Exception':
                self.patterns.append(ErrorPattern(
                    path=self.path,
                    line=handler.lineno,
                    pattern_type='broad_exception',
                    exception_type=exc_name,
                    severity='medium',
                    description="Catching 'Exception' is too broad, catch specific exceptions"
                ))
            elif exc_name == 'BaseException':
                self.patterns.append(ErrorPattern(
                    path=self.path,
                    line=handler.lineno,
                    pattern_type='base_exception',
                    exception_type=exc_name,
                    severity='high',
                    description="Never catch 'BaseException', it includes SystemExit and KeyboardInterrupt"
                ))
        elif isinstance(handler.type, ast.Tuple):
            for elt in handler.type.elts:
                if isinstance(elt, ast.Name):
                    self.exception_usage[elt.id] += 1

        # Check for swallowed exceptions (empty except body or just 'pass')
        if self._is_swallowed(handler):
            self.patterns.append(ErrorPattern(
                path=self.path,
                line=handler.lineno,
                pattern_type='swallowed_exception',
                severity='high',
                description="Exception is caught but silently ignored (no logging or re-raise)"
            ))

        # Check for proper logging
        if self._has_logging(handler):
            self.patterns.append(ErrorPattern(
                path=self.path,
                line=handler.lineno,
                pattern_type='logged_exception',
                severity='info',
                description="Exception is properly logged"
            ))

    def _is_swallowed(self, handler: ast.ExceptHandler) -> bool:
        """Check if exception is swallowed (ignored)."""
        if not handler.body:
            return True

        if len(handler.body) == 1:
            stmt = handler.body[0]
            # Just 'pass'
            if isinstance(stmt, ast.Pass):
                return True
            # Just '...'
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                if stmt.value.value is ...:
                    return True

        # Check if there's any logging or re-raise
        for node in ast.walk(handler):
            if isinstance(node, ast.Raise):
                return False
            if isinstance(node, ast.Call):
                func = self._get_func_name(node.func)
                if any(x in func for x in ['log', 'error', 'warn', 'print', 'logger']):
                    return False

        return False

    def _has_logging(self, handler: ast.ExceptHandler) -> bool:
        """Check if handler has logging."""
        for node in ast.walk(handler):
            if isinstance(node, ast.Call):
                func = self._get_func_name(node.func)
                if any(x in func for x in ['logging', 'logger', 'log']):
                    return True
        return False

    def _get_func_name(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id.lower()
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                return f"{node.value.id}.{node.attr}".lower()
            return node.attr.lower()
        return ""


class RaiseAnalyzer(ast.NodeVisitor):
    """Analyze raise statements."""

    def __init__(self, path: Path):
        self.path = path
        self.patterns: List[ErrorPattern] = []
        self.exception_usage: Counter = Counter()

    def visit_Raise(self, node: ast.Raise):
        if node.exc:
            if isinstance(node.exc, ast.Call):
                if isinstance(node.exc.func, ast.Name):
                    self.exception_usage[node.exc.func.id] += 1

                    # Check for generic Exception raise
                    if node.exc.func.id == 'Exception':
                        self.patterns.append(ErrorPattern(
                            path=self.path,
                            line=node.lineno,
                            pattern_type='generic_raise',
                            exception_type='Exception',
                            severity='low',
                            description="Raising generic 'Exception', consider using specific exception types"
                        ))

        self.generic_visit(node)


def analyze_file(path: Path) -> Tuple[List[ErrorPattern], Counter, int]:
    """Analyze a file for error patterns."""
    patterns = []
    exception_usage: Counter = Counter()
    try_count = 0

    tree = parse_file(path)
    if tree is None:
        return patterns, exception_usage, try_count

    # Exception handling analysis
    exc_analyzer = ExceptionAnalyzer(path)
    exc_analyzer.visit(tree)
    patterns.extend(exc_analyzer.patterns)
    exception_usage.update(exc_analyzer.exception_usage)
    try_count = exc_analyzer.try_count

    # Raise analysis
    raise_analyzer = RaiseAnalyzer(path)
    raise_analyzer.visit(tree)
    patterns.extend(raise_analyzer.patterns)
    exception_usage.update(raise_analyzer.exception_usage)

    return patterns, exception_usage, try_count


def analyze_project(
    root: Path,
    exclude_patterns: List[str] = None
) -> ErrorReport:
    """Analyze project for error patterns."""
    report = ErrorReport()

    Console.info(f"Analyzing {root}...")

    files = list(find_python_files(root, exclude_patterns))
    Console.info(f"Found {len(files)} Python files")

    for path in files:
        patterns, exc_usage, try_count = analyze_file(path)
        report.patterns.extend(patterns)
        report.exception_usage.update(exc_usage)
        report.total_try_blocks += try_count

    return report


# Required for type hints
from typing import Tuple


def main():
    """CLI entry point."""
    Console.header("Error Pattern Analyzer")

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
    issues = report.issues
    if issues:
        Console.warn(f"Found {len(issues)} error handling issues")
    else:
        Console.ok("No error handling issues found")

    Console.info(f"Analyzed {report.total_try_blocks} try blocks")

    return 0


if __name__ == "__main__":
    sys.exit(main())

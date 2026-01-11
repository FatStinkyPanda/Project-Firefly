"""
Code Review Automation
======================
Pre-commit code review checklist - validates code quality before commit.

Usage:
    python review.py [path] [--strict]
    python -m scripts.review [path]
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import ast
import sys

from .utils import (
    find_python_files,
    find_project_root,
    parse_file,
    get_staged_files,
    analyze_module,
    Console,
    format_as_markdown_table
)


class Severity(Enum):
    """Severity level for review issues."""
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ReviewIssue:
    """A single code review issue."""
    file: Path
    line: int
    severity: Severity
    category: str
    message: str


@dataclass
class ReviewReport:
    """Complete code review report."""
    issues: List[ReviewIssue] = field(default_factory=list)
    files_reviewed: int = 0

    @property
    def errors(self) -> List[ReviewIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> List[ReviewIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0


# Review checks
class ReviewChecks:
    """Collection of review check functions."""

    @staticmethod
    def check_docstrings(path: Path, tree: ast.Module) -> List[ReviewIssue]:
        """Check for missing docstrings."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip private and dunder methods
                if node.name.startswith('_'):
                    continue

                if not ast.get_docstring(node):
                    issues.append(ReviewIssue(
                        file=path,
                        line=node.lineno,
                        severity=Severity.WARNING,
                        category="documentation",
                        message=f"Function '{node.name}' is missing a docstring"
                    ))

            elif isinstance(node, ast.ClassDef):
                if node.name.startswith('_'):
                    continue

                if not ast.get_docstring(node):
                    issues.append(ReviewIssue(
                        file=path,
                        line=node.lineno,
                        severity=Severity.WARNING,
                        category="documentation",
                        message=f"Class '{node.name}' is missing a docstring"
                    ))

        return issues

    @staticmethod
    def check_type_hints(path: Path, tree: ast.Module) -> List[ReviewIssue]:
        """Check for missing type hints."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip private and dunder methods
                if node.name.startswith('_'):
                    continue

                # Check return type
                if node.returns is None and node.name != '__init__':
                    issues.append(ReviewIssue(
                        file=path,
                        line=node.lineno,
                        severity=Severity.INFO,
                        category="types",
                        message=f"Function '{node.name}' is missing return type hint"
                    ))

                # Check argument types
                for arg in node.args.args:
                    if arg.arg not in ('self', 'cls') and arg.annotation is None:
                        issues.append(ReviewIssue(
                            file=path,
                            line=node.lineno,
                            severity=Severity.INFO,
                            category="types",
                            message=f"Parameter '{arg.arg}' in '{node.name}' is missing type hint"
                        ))

        return issues

    @staticmethod
    def check_todo_fixme(path: Path) -> List[ReviewIssue]:
        """Check for TODO/FIXME comments."""
        issues = []

        try:
            with open(path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f, 1):
                    line_upper = line.upper()
                    if 'TODO' in line_upper:
                        issues.append(ReviewIssue(
                            file=path,
                            line=i,
                            severity=Severity.INFO,
                            category="todo",
                            message=f"TODO comment found: {line.strip()[:50]}..."
                        ))
                    elif 'FIXME' in line_upper:
                        issues.append(ReviewIssue(
                            file=path,
                            line=i,
                            severity=Severity.WARNING,
                            category="fixme",
                            message=f"FIXME comment found: {line.strip()[:50]}..."
                        ))
                    elif 'XXX' in line_upper or 'HACK' in line_upper:
                        issues.append(ReviewIssue(
                            file=path,
                            line=i,
                            severity=Severity.WARNING,
                            category="hack",
                            message=f"HACK/XXX comment found: {line.strip()[:50]}..."
                        ))
        except Exception:
            pass

        return issues

    @staticmethod
    def check_naming_conventions(path: Path, tree: ast.Module) -> List[ReviewIssue]:
        """Check naming conventions."""
        issues = []

        for node in ast.walk(tree):
            # Classes should be CamelCase
            if isinstance(node, ast.ClassDef):
                if not node.name[0].isupper() or '_' in node.name:
                    if not node.name.startswith('_'):
                        issues.append(ReviewIssue(
                            file=path,
                            line=node.lineno,
                            severity=Severity.WARNING,
                            category="naming",
                            message=f"Class '{node.name}' should use CamelCase"
                        ))

            # Functions should be snake_case
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith('_'):
                    # Check for camelCase (has lowercase followed by uppercase)
                    import re
                    if re.search(r'[a-z][A-Z]', node.name):
                        issues.append(ReviewIssue(
                            file=path,
                            line=node.lineno,
                            severity=Severity.INFO,
                            category="naming",
                            message=f"Function '{node.name}' should use snake_case"
                        ))

        return issues

    @staticmethod
    def check_file_length(path: Path, max_lines: int = 500) -> List[ReviewIssue]:
        """Check file length."""
        issues = []

        try:
            with open(path, 'r', encoding='utf-8') as f:
                line_count = sum(1 for _ in f)

            if line_count > max_lines:
                issues.append(ReviewIssue(
                    file=path,
                    line=1,
                    severity=Severity.WARNING,
                    category="complexity",
                    message=f"File has {line_count} lines (max recommended: {max_lines})"
                ))
        except Exception:
            pass

        return issues

    @staticmethod
    def check_function_length(path: Path, tree: ast.Module, max_lines: int = 50) -> List[ReviewIssue]:
        """Check function length."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.end_lineno:
                    length = node.end_lineno - node.lineno
                    if length > max_lines:
                        issues.append(ReviewIssue(
                            file=path,
                            line=node.lineno,
                            severity=Severity.WARNING,
                            category="complexity",
                            message=f"Function '{node.name}' is {length} lines (max: {max_lines})"
                        ))

        return issues

    @staticmethod
    def check_unused_imports(path: Path, tree: ast.Module) -> List[ReviewIssue]:
        """Check for potentially unused imports."""
        issues = []

        # Collect imports
        imports = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split('.')[0]
                    imports[name] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name != '*':
                        name = alias.asname or alias.name
                        imports[name] = node.lineno

        # Collect all used names
        used_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)

        # Check for unused
        for name, lineno in imports.items():
            if name not in used_names:
                issues.append(ReviewIssue(
                    file=path,
                    line=lineno,
                    severity=Severity.WARNING,
                    category="imports",
                    message=f"Import '{name}' appears to be unused"
                ))

        return issues

    @staticmethod
    def check_security_issues(path: Path, tree: ast.Module) -> List[ReviewIssue]:
        """Check for common security issues."""
        issues = []

        for node in ast.walk(tree):
            # Check for eval/exec
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ('eval', 'exec'):
                        issues.append(ReviewIssue(
                            file=path,
                            line=node.lineno,
                            severity=Severity.ERROR,
                            category="security",
                            message=f"Use of '{node.func.id}' is a security risk"
                        ))
                    elif node.func.id == 'input':
                        issues.append(ReviewIssue(
                            file=path,
                            line=node.lineno,
                            severity=Severity.INFO,
                            category="security",
                            message="User input should be validated"
                        ))

            # Check for hardcoded secrets
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name_lower = target.id.lower()
                        if any(s in name_lower for s in ['password', 'secret', 'api_key', 'token']):
                            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                                if len(node.value.value) > 0:
                                    issues.append(ReviewIssue(
                                        file=path,
                                        line=node.lineno,
                                        severity=Severity.ERROR,
                                        category="security",
                                        message=f"Hardcoded secret in '{target.id}'"
                                    ))

        return issues


def review_file(path: Path, strict: bool = False) -> List[ReviewIssue]:
    """
    Review a single Python file.

    Args:
        path: Path to file
        strict: Enable strict mode (more checks)

    Returns:
        List of review issues
    """
    issues = []

    tree = parse_file(path)
    if tree is None:
        return issues

    # Run all checks
    issues.extend(ReviewChecks.check_docstrings(path, tree))
    issues.extend(ReviewChecks.check_todo_fixme(path))
    issues.extend(ReviewChecks.check_naming_conventions(path, tree))
    issues.extend(ReviewChecks.check_file_length(path))
    issues.extend(ReviewChecks.check_function_length(path, tree))
    issues.extend(ReviewChecks.check_unused_imports(path, tree))
    issues.extend(ReviewChecks.check_security_issues(path, tree))

    if strict:
        issues.extend(ReviewChecks.check_type_hints(path, tree))

    return issues


def review_project(
    root: Path,
    staged_only: bool = False,
    strict: bool = False,
    exclude_patterns: List[str] = None
) -> ReviewReport:
    """
    Review a Python project.

    Args:
        root: Root directory
        staged_only: Only review staged files
        strict: Enable strict mode
        exclude_patterns: Patterns to exclude

    Returns:
        ReviewReport
    """
    report = ReviewReport()

    if staged_only:
        Console.info("Reviewing staged files only...")
        staged = get_staged_files(cwd=root)
        files = [root / f for f in staged if f.endswith('.py')]
    else:
        Console.info(f"Reviewing all Python files in {root}...")
        files = list(find_python_files(root, exclude_patterns))

    Console.info(f"Found {len(files)} files to review")
    report.files_reviewed = len(files)

    for path in files:
        issues = review_file(path, strict=strict)
        report.issues.extend(issues)

    return report


def format_report_console(report: ReviewReport) -> None:
    """Print report to console."""
    if not report.issues:
        Console.ok("No issues found")
        return

    # Group by file
    by_file: Dict[Path, List[ReviewIssue]] = {}
    for issue in report.issues:
        if issue.file not in by_file:
            by_file[issue.file] = []
        by_file[issue.file].append(issue)

    for file, issues in sorted(by_file.items()):
        print(f"\n{file}:")
        for issue in sorted(issues, key=lambda x: x.line):
            severity_color = {
                Severity.ERROR: Console.fail,
                Severity.WARNING: Console.warn,
                Severity.INFO: Console.info
            }
            severity_color[issue.severity](f"  L{issue.line}: [{issue.category}] {issue.message}")


def format_report_markdown(report: ReviewReport) -> str:
    """Format report as Markdown."""
    lines = [
        "# Code Review Report",
        "",
        "## Summary",
        "",
        f"- **Files Reviewed:** {report.files_reviewed}",
        f"- **Total Issues:** {len(report.issues)}",
        f"- **Errors:** {len(report.errors)}",
        f"- **Warnings:** {len(report.warnings)}",
        f"- **Status:** {'PASSED' if report.passed else 'FAILED'}",
        "",
    ]

    if report.errors:
        lines.extend([
            "## Errors (Must Fix)",
            "",
        ])
        rows = [[str(i.file), str(i.line), i.category, i.message] for i in report.errors]
        lines.append(format_as_markdown_table(["File", "Line", "Category", "Message"], rows))
        lines.append("")

    if report.warnings:
        lines.extend([
            "## Warnings",
            "",
        ])
        rows = [[str(i.file), str(i.line), i.category, i.message] for i in report.warnings]
        lines.append(format_as_markdown_table(["File", "Line", "Category", "Message"], rows))
        lines.append("")

    return "\n".join(lines)


def main():
    """CLI entry point."""
    Console.header("Code Review Automation")

    # Parse args
    strict = '--strict' in sys.argv
    staged_only = '--staged' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('-')]

    # Get path
    if args:
        path = Path(args[0])
    else:
        path = find_project_root() or Path.cwd()

    if not path.exists():
        Console.fail(f"Path not found: {path}")
        sys.exit(1)

    Console.info(f"Reviewing: {path}")
    Console.info(f"Mode: {'strict' if strict else 'standard'}")

    report = review_project(path, staged_only=staged_only, strict=strict)

    print()
    format_report_console(report)
    print()

    # Summary
    Console.info(f"Reviewed {report.files_reviewed} files")
    Console.info(f"Found {len(report.issues)} issues ({len(report.errors)} errors, {len(report.warnings)} warnings)")

    if report.passed:
        Console.ok("Code review PASSED")
        return 0
    else:
        Console.fail("Code review FAILED (errors found)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
